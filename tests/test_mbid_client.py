import httpx
import respx

from undercurrents.clustering.mbid_client import MusicBrainzClient, MusicBrainzError
from undercurrents.ingestion.setlistfm_client import RateLimiter


def make_client(max_retries=3, sleeps=None):
    return MusicBrainzClient(
        rate_limiter=RateLimiter(sleep_fn=lambda s: None),
        max_retries=max_retries,
        sleep_fn=(sleeps.append if sleeps is not None else (lambda s: None)),
    )


@respx.mock
def test_get_returns_status_and_json_on_success():
    respx.get("https://musicbrainz.org/ws/2/recording").mock(
        return_value=httpx.Response(200, json={"recordings": []})
    )
    client = make_client()
    status, payload = client.get("/recording", {"query": "foo"})
    assert status == 200
    assert payload == {"recordings": []}


@respx.mock
def test_get_sends_user_agent_header():
    route = respx.get("https://musicbrainz.org/ws/2/recording").mock(
        return_value=httpx.Response(200, json={})
    )
    client = make_client()
    client.get("/recording", {"query": "foo"})
    assert "Undercurrents" in route.calls.last.request.headers["User-Agent"]


@respx.mock
def test_get_retries_on_503_then_succeeds():
    respx.get("https://musicbrainz.org/ws/2/recording").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"recordings": []})]
    )
    sleeps = []
    client = make_client(sleeps=sleeps)
    status, payload = client.get("/recording", {"query": "foo"})
    assert status == 200
    assert sleeps == [1]


@respx.mock
def test_get_raises_after_exhausting_retries():
    respx.get("https://musicbrainz.org/ws/2/recording").mock(return_value=httpx.Response(503))
    client = make_client(max_retries=2)
    try:
        client.get("/recording", {"query": "foo"})
        assert False, "expected MusicBrainzError"
    except MusicBrainzError:
        pass
