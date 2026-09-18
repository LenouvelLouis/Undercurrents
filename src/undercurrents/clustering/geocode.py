"""Venue latitude/longitude from OpenStreetMap's Nominatim.

Nominatim's usage policy asks for at most one request per second, a User-Agent that
identifies the caller with a way to reach them, and no parallelism. All three are honoured
here: the same RateLimiter the other clients use, the repository URL in the User-Agent, and
a single serial loop. Results are written back as they arrive, so an interrupted run keeps
what it already resolved and the next run picks up where it stopped.

Queries are structured (city + country) rather than free text, because a venue name alone
resolves badly: many are generic ("Olympia", "The Forum") and some no longer exist. Placing
the venue at its city is honest about what we actually know, and it is enough for the thing
these coordinates are for, which is measuring how far the band travelled between shows.
"""

import logging
import ssl

import httpx
import truststore

from undercurrents.ingestion.setlistfm_client import RateLimiter
from undercurrents.storage import db

logger = logging.getLogger(__name__)

ENDPOINT = "https://nominatim.openstreetmap.org/search"
USER_AGENT = (
    "Undercurrents/0.1 (https://github.com/LenouvelLouis/Undercurrents; "
    "personal non-commercial research project)"
)
# Their policy caps automated use at one request per second; 1.1 leaves a margin so clock
# jitter never pushes two requests into the same second.
MIN_INTERVAL = 1.1
TIMEOUT = 20.0


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))


def geocode_city(client: httpx.Client, city: str, country: str | None) -> tuple[float, float] | None:
    params = {"city": city, "format": "json", "limit": 1}
    if country:
        params["country"] = country
    response = client.get(ENDPOINT, params=params, headers={"User-Agent": USER_AGENT})
    if response.status_code != 200:
        logger.warning("Nominatim returned %s for %s, %s", response.status_code, city, country)
        return None
    payload = response.json()
    if not payload:
        return None
    try:
        return float(payload[0]["lat"]), float(payload[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return None


def enrich(conn, client: httpx.Client | None = None, limit: int | None = None) -> dict[str, int]:
    """Fill coordinates for venues that lack them. One lookup per distinct (city, country),
    not per venue: 556 venues share far fewer cities, which cuts the request count by more
    than half and asks Nominatim nothing it has not already answered."""
    db.ensure_venues_coordinate_columns(conn)
    owns_client = client is None
    client = client or _client()
    limiter = RateLimiter(min_interval=MIN_INTERVAL)

    rows = conn.execute(
        """
        SELECT DISTINCT city, country
        FROM venues
        WHERE latitude IS NULL AND city IS NOT NULL AND city != ''
        ORDER BY city
        """
    ).fetchall()
    if limit is not None:
        rows = rows[:limit]

    resolved = failed = venues_updated = 0
    try:
        for row in rows:
            limiter.wait()
            try:
                point = geocode_city(client, row["city"], row["country"])
            except httpx.HTTPError as exc:
                logger.warning("Geocoding failed for %s, %s: %s", row["city"], row["country"], exc)
                failed += 1
                continue

            if point is None:
                failed += 1
                continue

            latitude, longitude = point
            cursor = conn.execute(
                """
                UPDATE venues SET latitude = ?, longitude = ?
                WHERE latitude IS NULL AND city = ? AND (country IS ? OR country = ?)
                """,
                (latitude, longitude, row["city"], row["country"], row["country"]),
            )
            venues_updated += cursor.rowcount
            resolved += 1
            conn.commit()
    finally:
        if owns_client:
            client.close()

    return {
        "cities_queried": len(rows),
        "cities_resolved": resolved,
        "cities_unresolved": failed,
        "venues_updated": venues_updated,
    }
