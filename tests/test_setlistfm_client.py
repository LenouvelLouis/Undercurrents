import httpx
import pytest
import respx

from undercurrents.ingestion.setlistfm_client import (
    RateLimiter,
    SetlistFmClient,
    SetlistFmError,
    params_hash,
)


def make_client(max_retries=3, sleeps=None):
    return SetlistFmClient(
        api_key="test-key",
        rate_limiter=RateLimiter(sleep_fn=lambda s: None),
        max_retries=max_retries,
        sleep_fn=(sleeps.append if sleeps is not None else (lambda s: None)),
    )


@respx.mock
def test_get_returns_status_and_json_on_success():
    respx.get("https://api.setlist.fm/rest/1.0/foo").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = make_client()
    status, payload = client.get("/foo", {"a": "b"})
    assert status == 200
    assert payload == {"ok": True}


@respx.mock
def test_get_sends_api_key_header():
    route = respx.get("https://api.setlist.fm/rest/1.0/foo").mock(
        return_value=httpx.Response(200, json={})
    )
    client = make_client()
    client.get("/foo", {})
    assert route.calls.last.request.headers["x-api-key"] == "test-key"


@respx.mock
def test_get_retries_on_429_then_succeeds():
    respx.get("https://api.setlist.fm/rest/1.0/foo").mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json={"ok": True})]
    )
    sleeps = []
    client = make_client(sleeps=sleeps)
    status, payload = client.get("/foo", {})
    assert status == 200
    assert payload == {"ok": True}
    assert sleeps == [1]


@respx.mock
def test_get_raises_after_exhausting_retries():
    respx.get("https://api.setlist.fm/rest/1.0/foo").mock(return_value=httpx.Response(500))
    client = make_client(max_retries=2)
    with pytest.raises(SetlistFmError):
        client.get("/foo", {})


def test_params_hash_is_deterministic_and_order_independent():
    assert params_hash({"a": 1, "b": 2}) == params_hash({"b": 2, "a": 1})


def test_params_hash_differs_for_different_params():
    assert params_hash({"p": 1}) != params_hash({"p": 2})
