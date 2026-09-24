import ssl
import time

import httpx
import truststore

from undercurrents.ingestion.setlistfm_client import RateLimiter

BASE_URL = "https://musicbrainz.org/ws/2"
# MusicBrainz asks for an application name, a version and a contact the operator can reach.
# This string was missing the contact, which is the same defect that produced the 403s from
# Wikidata and is a documented cause of throttling and 503s here. The public repository URL
# satisfies it without putting a personal address in an outbound header.
USER_AGENT = (
    "Undercurrents/0.1 (https://github.com/LenouvelLouis/Undercurrents; "
    "personal non-commercial research project)"
)
RETRYABLE_STATUSES = {503}


def _default_http_client() -> httpx.Client:
    # See ingestion/setlistfm_client.py's _default_http_client for why: the OS certificate
    # store instead of the bundled certifi CA list, needed behind a corporate proxy/custom CA.
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(base_url=BASE_URL, timeout=10.0, verify=ssl_context)


class MusicBrainzError(Exception):
    pass


class MusicBrainzClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 5,
        sleep_fn=time.sleep,
    ):
        self._client = http_client or _default_http_client()
        # MusicBrainz's documented limit for unauthenticated use is 1 req/s, but its public
        # server has been observed 503'ing ("currently busy") under real load well within
        # that limit — 1.5s adds headroom without meaningfully slowing a ~150-song run.
        self._rate_limiter = rate_limiter or RateLimiter(min_interval=1.5)
        self._max_retries = max_retries
        self._sleep_fn = sleep_fn

    def _headers(self) -> dict:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

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
            raise MusicBrainzError(
                f"Request to {path} failed with status {response.status_code}: {response.text}"
            )
