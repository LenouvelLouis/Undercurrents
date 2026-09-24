"""What the weather was doing at every show.

Open-Meteo's archive serves reanalysis data back to 1940, free and without a key, which
covers the whole eighteen-year span of this archive. Every show already has city-level
coordinates and a date, so the join needs nothing new from the user.

Two honesty notes, both of which limit what the resulting page may claim. The coordinates are
city-level, not venue-level, so this is the weather over the city that evening, not over the
door of the venue. And most of these shows are indoors, where the weather has no plausible
effect on the set at all. The interesting question is therefore narrow: does an *outdoor*
show in the rain get treated differently? Anything broader than that would be reading noise.
Because the venue-type enrichment is what separates indoor from outdoor, the weather is worth
little on its own and the two belong together.
"""

import sqlite3
import ssl
from datetime import datetime

import httpx
import truststore

from undercurrents.ingestion.setlistfm_client import RateLimiter

BASE_URL = "https://archive-api.open-meteo.com/v1"
DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"


def _default_http_client() -> httpx.Client:
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(base_url=BASE_URL, timeout=30.0, verify=ssl_context)


class WeatherClient:
    def __init__(self, http_client: httpx.Client | None = None, rate_limiter: RateLimiter | None = None):
        self._client = http_client or _default_http_client()
        # Open-Meteo's free tier is generous but shared-IP limited. One request a second keeps
        # a 767-show run inside it and takes about thirteen minutes, which is fine for
        # something that only ever runs after an ingest.
        self._rate_limiter = rate_limiter or RateLimiter(min_interval=1.0)

    def daily(self, latitude: float, longitude: float, day: str) -> dict | None:
        self._rate_limiter.wait()
        response = self._client.get(
            "/archive",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": day,
                "end_date": day,
                "daily": DAILY_FIELDS,
                "timezone": "auto",
            },
        )
        if response.status_code != 200:
            return None
        daily = (response.json() or {}).get("daily") or {}
        if not daily.get("time"):
            return None
        return {
            "temp_max_c": (daily.get("temperature_2m_max") or [None])[0],
            "temp_min_c": (daily.get("temperature_2m_min") or [None])[0],
            "precipitation_mm": (daily.get("precipitation_sum") or [None])[0],
            "wind_max_kmh": (daily.get("wind_speed_10m_max") or [None])[0],
        }


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS show_weather (
            setlist_id       TEXT PRIMARY KEY REFERENCES setlists(id),
            event_date       TEXT NOT NULL,
            latitude         REAL NOT NULL,
            longitude        REAL NOT NULL,
            temp_max_c       REAL,
            temp_min_c       REAL,
            precipitation_mm REAL,
            wind_max_kmh     REAL,
            fetched_at       TEXT NOT NULL
        )
        """
    )
    conn.commit()


def pending_shows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Shows that have coordinates and no weather row yet, newest first."""
    return conn.execute(
        """
        SELECT s.id, s.event_date, v.latitude, v.longitude
        FROM setlists s
        JOIN venues v ON v.id = s.venue_id
        LEFT JOIN show_weather w ON w.setlist_id = s.id
        WHERE v.latitude IS NOT NULL AND w.setlist_id IS NULL
        ORDER BY s.event_date DESC
        """
    ).fetchall()


def enrich(conn: sqlite3.Connection, client: WeatherClient | None = None, limit: int | None = None) -> dict:
    """Fetches one day of weather per show. Commits as it goes, so a run interrupted after
    ten minutes keeps its ten minutes of results."""
    ensure_table(conn)
    client = client or WeatherClient()

    rows = pending_shows(conn)
    if limit:
        rows = rows[:limit]

    written, failed = 0, 0
    fetched_at = datetime.now().isoformat(timespec="seconds")
    for row in rows:
        daily = client.daily(row["latitude"], row["longitude"], row["event_date"])
        if daily is None:
            failed += 1
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO show_weather
                (setlist_id, event_date, latitude, longitude,
                 temp_max_c, temp_min_c, precipitation_mm, wind_max_kmh, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], row["event_date"], row["latitude"], row["longitude"],
                daily["temp_max_c"], daily["temp_min_c"],
                daily["precipitation_mm"], daily["wind_max_kmh"], fetched_at,
            ),
        )
        conn.commit()
        written += 1

    return {"shows_pending": len(rows), "written": written, "failed": failed}
