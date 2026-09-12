import httpx
import respx

from undercurrents.clustering.wikidata_client import WikidataClient, WikidataError


def make_client(max_retries=3, sleeps=None):
    return WikidataClient(
        max_retries=max_retries,
        sleep_fn=(sleeps.append if sleeps is not None else (lambda s: None)),
    )


@respx.mock
def test_get_returns_status_and_json_on_success():
    respx.get("https://www.wikidata.org/w/api.php").mock(
        return_value=httpx.Response(200, json={"search": []})
    )
    client = make_client()
    status, payload = client.get("/api.php", {"action": "wbsearchentities"})
    assert status == 200
    assert payload == {"search": []}


@respx.mock
def test_get_sends_user_agent_header():
    route = respx.get("https://www.wikidata.org/w/api.php").mock(
        return_value=httpx.Response(200, json={})
    )
    client = make_client()
    client.get("/api.php", {"action": "wbsearchentities"})
    assert "Undercurrents" in route.calls.last.request.headers["User-Agent"]


@respx.mock
def test_get_retries_on_server_error_then_succeeds():
    respx.get("https://www.wikidata.org/w/api.php").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"search": []})]
    )
    sleeps = []
    client = make_client(sleeps=sleeps)
    status, payload = client.get("/api.php", {"action": "wbsearchentities"})
    assert status == 200
    assert sleeps == [1]


@respx.mock
def test_get_raises_after_exhausting_retries():
    respx.get("https://www.wikidata.org/w/api.php").mock(return_value=httpx.Response(500))
    client = make_client(max_retries=2)
    try:
        client.get("/api.php", {"action": "wbsearchentities"})
        assert False, "expected WikidataError"
    except WikidataError:
        pass
