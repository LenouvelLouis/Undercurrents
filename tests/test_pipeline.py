import pytest

from undercurrents.ingestion.pipeline import (
    ArtistNotFoundError,
    fetch_and_store_all_setlists,
    resolve_artist_mbid,
)
from undercurrents.ingestion.setlistfm_client import SetlistFmError
from tests.helpers import make_raw_setlist_dict


class FakeClient:
    def __init__(self, responses: dict):
        self._responses = responses
        self.calls = []

    def get(self, path, params):
        self.calls.append((path, dict(params)))
        key = (path, tuple(sorted(params.items())))
        if key not in self._responses:
            raise AssertionError(f"Unexpected call: {path} {params}")
        return self._responses[key]


def test_resolve_artist_mbid_returns_exact_match(tmp_conn):
    responses = {
        ("/search/artists", (("artistName", "Tame Impala"),)): (
            200,
            {
                "type": "artists",
                "itemsPerPage": 30,
                "page": 1,
                "total": 2,
                "artist": [
                    {"mbid": "wrong-id", "name": "Tame Impala Tribute Band"},
                    {"mbid": "correct-id", "name": "Tame Impala"},
                ],
            },
        )
    }
    client = FakeClient(responses)
    mbid = resolve_artist_mbid(tmp_conn, client)
    assert mbid == "correct-id"


def test_resolve_artist_mbid_raises_when_no_exact_match(tmp_conn):
    responses = {
        ("/search/artists", (("artistName", "Tame Impala"),)): (
            200,
            {
                "type": "artists",
                "itemsPerPage": 30,
                "page": 1,
                "total": 1,
                "artist": [{"mbid": "x", "name": "Tame Impala Tribute Band"}],
            },
        )
    }
    client = FakeClient(responses)
    with pytest.raises(ArtistNotFoundError):
        resolve_artist_mbid(tmp_conn, client)


def test_fetch_and_store_all_setlists_paginates_and_stores(tmp_conn):
    page1 = {
        "type": "setlists", "itemsPerPage": 1, "page": 1, "total": 2,
        "setlist": [make_raw_setlist_dict(setlist_id="setlist-a")],
    }
    page2 = {
        "type": "setlists", "itemsPerPage": 1, "page": 2, "total": 2,
        "setlist": [make_raw_setlist_dict(setlist_id="setlist-b")],
    }
    responses = {
        ("/artist/abc/setlists", (("p", 1),)): (200, page1),
        ("/artist/abc/setlists", (("p", 2),)): (200, page2),
    }
    client = FakeClient(responses)

    count = fetch_and_store_all_setlists(tmp_conn, client, "abc")

    assert count == 2
    rows = tmp_conn.execute("SELECT id FROM setlists ORDER BY id").fetchall()
    assert [r["id"] for r in rows] == ["setlist-a", "setlist-b"]


def test_fetch_and_store_all_setlists_is_idempotent(tmp_conn):
    page = {
        "type": "setlists", "itemsPerPage": 20, "page": 1, "total": 1,
        "setlist": [make_raw_setlist_dict(setlist_id="setlist-a")],
    }
    responses = {("/artist/abc/setlists", (("p", 1),)): (200, page)}
    client = FakeClient(responses)

    fetch_and_store_all_setlists(tmp_conn, client, "abc")
    calls_after_first_run = len(client.calls)
    fetch_and_store_all_setlists(tmp_conn, client, "abc")

    count = tmp_conn.execute("SELECT COUNT(*) AS c FROM setlists").fetchone()["c"]
    assert count == 1
    # The second run should be served entirely from cache, no new HTTP calls.
    assert len(client.calls) == calls_after_first_run


def test_fetch_and_store_all_setlists_skips_malformed_entry(tmp_conn):
    malformed = make_raw_setlist_dict(setlist_id="bad")
    del malformed["eventDate"]
    page = {
        "type": "setlists", "itemsPerPage": 2, "page": 1, "total": 2,
        "setlist": [make_raw_setlist_dict(setlist_id="good"), malformed],
    }
    responses = {("/artist/abc/setlists", (("p", 1),)): (200, page)}
    client = FakeClient(responses)

    count = fetch_and_store_all_setlists(tmp_conn, client, "abc")

    assert count == 1
    ids = [r["id"] for r in tmp_conn.execute("SELECT id FROM setlists").fetchall()]
    assert ids == ["good"]


def test_fetch_and_store_all_setlists_skips_entry_with_invalid_date(tmp_conn):
    malformed = make_raw_setlist_dict(setlist_id="bad-date", event_date="not-a-date")
    page = {
        "type": "setlists", "itemsPerPage": 2, "page": 1, "total": 2,
        "setlist": [make_raw_setlist_dict(setlist_id="good"), malformed],
    }
    responses = {("/artist/abc/setlists", (("p", 1),)): (200, page)}
    client = FakeClient(responses)

    count = fetch_and_store_all_setlists(tmp_conn, client, "abc")

    assert count == 1
    ids = [r["id"] for r in tmp_conn.execute("SELECT id FROM setlists").fetchall()]
    assert ids == ["good"]


def test_fetch_and_store_all_setlists_skips_failing_page_and_continues(tmp_conn):
    page1 = {
        "type": "setlists", "itemsPerPage": 1, "page": 1, "total": 3,
        "setlist": [make_raw_setlist_dict(setlist_id="setlist-a")],
    }
    page3 = {
        "type": "setlists", "itemsPerPage": 1, "page": 3, "total": 3,
        "setlist": [make_raw_setlist_dict(setlist_id="setlist-c")],
    }

    class FailingOnPage2Client(FakeClient):
        def get(self, path, params):
            if params.get("p") == 2:
                self.calls.append((path, dict(params)))
                raise SetlistFmError("boom")
            return super().get(path, params)

    responses = {
        ("/artist/abc/setlists", (("p", 1),)): (200, page1),
        ("/artist/abc/setlists", (("p", 3),)): (200, page3),
    }
    client = FailingOnPage2Client(responses)

    count = fetch_and_store_all_setlists(tmp_conn, client, "abc")

    assert count == 2
    ids = {r["id"] for r in tmp_conn.execute("SELECT id FROM setlists").fetchall()}
    assert ids == {"setlist-a", "setlist-c"}
