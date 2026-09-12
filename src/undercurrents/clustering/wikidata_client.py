import ssl
import time

import httpx
import truststore

from undercurrents.ingestion.setlistfm_client import RateLimiter

BASE_URL = "https://www.wikidata.org/w"
USER_AGENT = "Undercurrents/0.1 ( personal non-commercial research project )"
RETRYABLE_STATUSES = {500, 502, 503, 504}


def _default_http_client() -> httpx.Client:
    # See ingestion/setlistfm_client.py's _default_http_client for why: the OS certificate
    # store instead of the bundled certifi CA list, needed behind a corporate proxy/custom CA.
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(base_url=BASE_URL, timeout=15.0, verify=ssl_context)


class WikidataError(Exception):
    pass


class WikidataClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 3,
        sleep_fn=time.sleep,
    ):
        self._client = http_client or _default_http_client()
        self._rate_limiter = rate_limiter or RateLimiter(min_interval=1.0)
        self._max_retries = max_retries
        self._sleep_fn = sleep_fn

    def _headers(self) -> dict:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def get(self, path: str, params: dict) -> tuple[int, dict]:
        attempt = 0
        while True:
            self._rate_limiter.wait()
            try:
                response = self._client.get(path, params=params, headers=self._headers())
            except httpx.ConnectError as exc:
                raise WikidataError(f"Could not connect to Wikidata: {exc}") from exc

            if response.status_code == 200:
                return response.status_code, response.json()
            if response.status_code in RETRYABLE_STATUSES and attempt < self._max_retries:
                backoff = min(2**attempt, 30)
                self._sleep_fn(backoff)
                attempt += 1
                continue
            raise WikidataError(
                f"Request to {path} failed with status {response.status_code}: {response.text}"
            )
