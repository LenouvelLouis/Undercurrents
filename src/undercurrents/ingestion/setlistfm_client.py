import hashlib
import json
import ssl
import time

import httpx
import truststore

BASE_URL = "https://api.setlist.fm/rest/1.0"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _default_http_client() -> httpx.Client:
    # Uses the OS certificate store instead of the bundled certifi CA list, needed
    # on machines behind a corporate proxy or custom CA (same reason uv needs
    # native-tls in pyproject.toml). Harmless on unrestricted networks.
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(base_url=BASE_URL, timeout=10.0, verify=ssl_context)


class SetlistFmError(Exception):
    pass


class RateLimiter:
    def __init__(
        self,
        min_interval: float = 0.5,
        time_fn=time.monotonic,
        sleep_fn=time.sleep,
    ):
        self._min_interval = min_interval
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._last_call: float | None = None

    def wait(self) -> None:
        now = self._time_fn()
        if self._last_call is not None:
            elapsed = now - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                self._sleep_fn(remaining)
                now = self._time_fn()
        self._last_call = now


class SetlistFmClient:
    def __init__(
        self,
        api_key: str,
        http_client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 5,
        sleep_fn=time.sleep,
    ):
        self._api_key = api_key
        self._client = http_client or _default_http_client()
        self._rate_limiter = rate_limiter or RateLimiter()
        self._max_retries = max_retries
        self._sleep_fn = sleep_fn

    def _headers(self) -> dict:
        return {"x-api-key": self._api_key, "Accept": "application/json"}

    def get(self, path: str, params: dict) -> tuple[int, dict]:
        attempt = 0
        while True:
            self._rate_limiter.wait()
            response = self._client.get(path, params=params, headers=self._headers())
            if response.status_code == 200:
                return response.status_code, response.json()
            if response.status_code in RETRYABLE_STATUSES and attempt < self._max_retries:
                backoff = min(2**attempt, 60)
                self._sleep_fn(backoff)
                attempt += 1
                continue
            raise SetlistFmError(
                f"Request to {path} failed with status {response.status_code}: {response.text}"
            )


def params_hash(params: dict) -> str:
    serialized = json.dumps(params, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
