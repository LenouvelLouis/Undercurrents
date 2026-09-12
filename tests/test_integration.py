import httpx
import respx

from undercurrents.ingestion.pipeline import fetch_and_store_all_setlists, resolve_artist_mbid
from undercurrents.ingestion.setlistfm_client import RateLimiter, SetlistFmClient
from undercurrents.storage import db
from tests.helpers import make_raw_setlist_dict


@respx.mock
def test_full_pipeline_paginates_caches_and_is_idempotent(tmp_path):
    search_route = respx.get("https://api.setlist.fm/rest/1.0/search/artists").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "artists", "itemsPerPage": 30, "page": 1, "total": 1,
                "artist": [{"mbid": "tame-impala-mbid-fake", "name": "Tame Impala"}],
            },
        )
    )
    page1_route = respx.get(
        "https://api.setlist.fm/rest/1.0/artist/tame-impala-mbid-fake/setlists",
        params={"p": "1"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "setlists", "itemsPerPage": 1, "page": 1, "total": 2,
                "setlist": [make_raw_setlist_dict(setlist_id="setlist-a")],
            },
        )
    )
    page2_route = respx.get(
        "https://api.setlist.fm/rest/1.0/artist/tame-impala-mbid-fake/setlists",
        params={"p": "2"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "setlists", "itemsPerPage": 1, "page": 2, "total": 2,
                "setlist": [make_raw_setlist_dict(setlist_id="setlist-b")],
            },
        )
    )

    conn = db.get_connection(str(tmp_path / "test.db"))
    db.initialize_schema(conn)
    client = SetlistFmClient(
        api_key="test-key",
        rate_limiter=RateLimiter(sleep_fn=lambda s: None),
        sleep_fn=lambda s: None,
    )

    mbid = resolve_artist_mbid(conn, client)
    count = fetch_and_store_all_setlists(conn, client, mbid)

    assert count == 2
    assert search_route.call_count == 1
    assert page1_route.call_count == 1
    assert page2_route.call_count == 1

    mbid_again = resolve_artist_mbid(conn, client)
    count_again = fetch_and_store_all_setlists(conn, client, mbid_again)

    assert count_again == 2
    assert search_route.call_count == 1
    assert page1_route.call_count == 1
    assert page2_route.call_count == 1

    total_setlists = conn.execute("SELECT COUNT(*) AS c FROM setlists").fetchone()["c"]
    assert total_setlists == 2
    conn.close()
