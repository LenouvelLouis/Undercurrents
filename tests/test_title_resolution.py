from undercurrents.clustering.mbid_client import MusicBrainzError
from undercurrents.clustering.title_resolution import resolve_song_titles
from undercurrents.storage import db
from tests.helpers import make_mbid_search_response


class FakeMbidClient:
    def __init__(self, responses_by_query_substring: dict):
        self._responses = responses_by_query_substring
        self.calls = []

    def get(self, path, params):
        self.calls.append((path, dict(params)))
        query = params["query"]
        for substring, payload in self._responses.items():
            if substring in query:
                return 200, payload
        return 200, {"recordings": []}


class FlakyOnSecondCallMbidClient:
    """Raises MusicBrainzError on the 2nd call, succeeds on every other call — simulates a
    transient 503 mid-run (what actually happened against the real API: MusicBrainz's
    server returned a sustained "busy" 503 partway through a batch of lookups)."""

    def __init__(self):
        self.calls = 0

    def get(self, path, params):
        self.calls += 1
        if self.calls == 2:
            raise MusicBrainzError("The MusicBrainz web server is currently busy.")
        return 200, {"recordings": []}


def test_resolve_song_titles_sets_mbid_on_match(tmp_conn):
    song_id = db.upsert_song(tmp_conn, "Elephant")
    tmp_conn.commit()
    client = FakeMbidClient({"Elephant": make_mbid_search_response()})

    resolve_song_titles(tmp_conn, client)

    row = tmp_conn.execute("SELECT mbid FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["mbid"] == "fake-mbid-1"


def test_resolve_song_titles_leaves_mbid_null_when_no_match(tmp_conn):
    song_id = db.upsert_song(tmp_conn, "Some Obscure Jam")
    tmp_conn.commit()
    client = FakeMbidClient({})

    resolve_song_titles(tmp_conn, client)

    row = tmp_conn.execute("SELECT mbid FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["mbid"] is None


def test_resolve_song_titles_does_not_requery_already_resolved_song(tmp_conn):
    db.upsert_song(tmp_conn, "Elephant")
    tmp_conn.commit()
    client = FakeMbidClient({"Elephant": make_mbid_search_response()})

    resolve_song_titles(tmp_conn, client)
    resolve_song_titles(tmp_conn, client)

    assert len(client.calls) == 1


def test_resolve_song_titles_applies_exclude_alias_without_api_call(tmp_conn):
    song_id = db.upsert_song(tmp_conn, "Intro")
    tmp_conn.commit()
    client = FakeMbidClient({})

    resolve_song_titles(tmp_conn, client)

    assert client.calls == []
    row = tmp_conn.execute(
        "SELECT excluded_from_clustering FROM songs WHERE id = ?", (song_id,)
    ).fetchone()
    assert row["excluded_from_clustering"] == 1


def test_resolve_song_titles_applies_merge_alias_without_api_call(tmp_conn):
    canonical_id = db.upsert_song(tmp_conn, "Halcyon + On + On")
    variant_id = db.upsert_song(tmp_conn, "Halcyon And On And On")
    tmp_conn.commit()
    client = FakeMbidClient({})

    resolve_song_titles(tmp_conn, client)

    # The variant is merged via the alias without ever being queried; the canonical song
    # itself is a distinct, still-unresolved song and legitimately gets its own MusicBrainz
    # lookup (which finds nothing here, since FakeMbidClient has no matching response).
    queried_titles = [call[1]["query"] for call in client.calls]
    assert not any("Halcyon And On And On" in query for query in queried_titles)
    assert any("Halcyon + On + On" in query for query in queried_titles)

    row = tmp_conn.execute(
        "SELECT canonical_song_id FROM songs WHERE id = ?", (variant_id,)
    ).fetchone()
    assert row["canonical_song_id"] == canonical_id


def test_resolve_song_titles_applies_fix_text_alias_then_still_queries_api(tmp_conn):
    song_id = db.upsert_song(tmp_conn, "Tomorrow’s Dust")
    tmp_conn.commit()
    client = FakeMbidClient(
        {
            "Tomorrow's Dust": make_mbid_search_response(
                [{"id": "fake-mbid-2", "score": 95, "title": "Tomorrow's Dust"}]
            )
        }
    )

    resolve_song_titles(tmp_conn, client)

    row = tmp_conn.execute("SELECT name, mbid FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["name"] == "Tomorrow's Dust"
    assert row["mbid"] == "fake-mbid-2"


def test_resolve_song_titles_ignores_low_score_matches(tmp_conn):
    song_id = db.upsert_song(tmp_conn, "Some Ambiguous Title")
    tmp_conn.commit()
    client = FakeMbidClient(
        {
            "Some Ambiguous Title": make_mbid_search_response(
                [{"id": "fake-mbid-3", "score": 40, "title": "Something Else"}]
            )
        }
    )

    resolve_song_titles(tmp_conn, client)

    row = tmp_conn.execute("SELECT mbid FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["mbid"] is None


def test_resolve_song_titles_merges_songs_sharing_same_mbid(tmp_conn):
    id_a = db.upsert_song(tmp_conn, "Song A")
    id_b = db.upsert_song(tmp_conn, "Song B")
    tmp_conn.commit()
    client = FakeMbidClient(
        {
            "Song A": make_mbid_search_response([{"id": "shared-mbid", "score": 100, "title": "Song A"}]),
            "Song B": make_mbid_search_response([{"id": "shared-mbid", "score": 100, "title": "Song B"}]),
        }
    )

    resolve_song_titles(tmp_conn, client)

    row_a = tmp_conn.execute("SELECT canonical_song_id FROM songs WHERE id = ?", (id_a,)).fetchone()
    row_b = tmp_conn.execute("SELECT canonical_song_id FROM songs WHERE id = ?", (id_b,)).fetchone()
    assert row_a["canonical_song_id"] is None
    assert row_b["canonical_song_id"] == id_a


def test_resolve_song_titles_skips_song_on_musicbrainz_error_and_continues(tmp_conn):
    db.upsert_song(tmp_conn, "Song A")
    db.upsert_song(tmp_conn, "Song B")
    db.upsert_song(tmp_conn, "Song C")
    tmp_conn.commit()
    client = FlakyOnSecondCallMbidClient()

    resolve_song_titles(tmp_conn, client)  # must not raise despite Song B's lookup erroring

    # All three were attempted (the error on Song B didn't stop Song C from being queried).
    assert client.calls == 3
    # Song B specifically is left unresolved (no cached response, no mbid) so a later run
    # retries it; Song A and Song C are also "unresolved" here only because this fake client
    # never returns a match — that's the same "no match found" case covered by
    # test_resolve_song_titles_leaves_mbid_null_when_no_match, not the error path.
    unresolved_names = {row["name"] for row in db.get_unresolved_songs(tmp_conn)}
    assert "Song B" in unresolved_names


def test_resolve_song_titles_force_refresh_requeries_resolved_song(tmp_conn):
    db.upsert_song(tmp_conn, "Elephant")
    tmp_conn.commit()
    client = FakeMbidClient({"Elephant": make_mbid_search_response()})

    resolve_song_titles(tmp_conn, client)
    resolve_song_titles(tmp_conn, client, force_refresh=True)

    assert len(client.calls) == 2
