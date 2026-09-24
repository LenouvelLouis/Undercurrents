"""How much each song is listened to, from ListenBrainz.

ListenBrainz publishes, per artist, its recordings with a total listen count and the number of
distinct listeners (`/1/popularity/top-recordings-for-artist`). A song appears there under
several recordings (album track, single, remaster), so counts are summed per normalised title,
the same normalisation `albums.py` uses. ListenBrainz users are a small, self-selected sample
of listeners, so these are relative numbers: good for "which songs people play most", not an
estimate of streams. The sample also leans towards long-time listeners: on this artist the
2010 to 2012 records outscore Currents, the reverse of what streaming charts show, and the
page says so rather than presenting these as general popularity.
"""

from __future__ import annotations

import re
import ssl
from datetime import datetime

import httpx
import truststore

from undercurrents.clustering.albums import ARTIST_MBID, normalize_title
from undercurrents.clustering.mbid_client import USER_AGENT

URL = "https://api.listenbrainz.org/1/popularity/top-recordings-for-artist/{artist}"
# remixes, covers, edits, instrumentals and live takes are other people's or other versions:
# their listens belong to them, not to the song as played on stage
NOT_THE_SONG = re.compile(r"[\(\[][^\)\]]*\b(remix|cover|edit|instrumental|live|demo|version|mix)\b", re.IGNORECASE)


def fetch_top_recordings(artist_mbid: str = ARTIST_MBID, client: httpx.Client | None = None) -> list[dict]:
    client = client or httpx.Client(verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT), timeout=30)
    response = client.get(URL.format(artist=artist_mbid), headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.json()


def aggregate(recordings: list[dict]) -> dict[str, dict]:
    totals: dict[str, dict] = {}
    for rec in recordings:
        name = rec.get("recording_name") or ""
        if NOT_THE_SONG.search(name):
            continue
        title = normalize_title(name)
        if not title:
            continue
        t = totals.setdefault(title, {"listens": 0, "listeners": 0})
        t["listens"] += rec.get("total_listen_count") or 0
        # distinct listeners cannot be summed across recordings without double counting, so the
        # largest single recording's audience is kept as a lower bound
        t["listeners"] = max(t["listeners"], rec.get("total_user_count") or 0)
    return totals


def ensure_columns(conn) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    for column, kind in (("listen_count", "INTEGER"), ("listener_count", "INTEGER"), ("popularity_fetched_at", "TEXT")):
        if column not in existing:
            conn.execute(f"ALTER TABLE songs ADD COLUMN {column} {kind}")
    conn.commit()


def assign_popularity(conn, recordings: list[dict] | None = None) -> dict:
    ensure_columns(conn)
    totals = aggregate(recordings if recordings is not None else fetch_top_recordings())
    fetched_at = datetime.now().isoformat(timespec="seconds")
    matched = 0
    for song in conn.execute("SELECT id, name FROM songs").fetchall():
        hit = totals.get(normalize_title(song["name"]))
        if hit:
            matched += 1
            conn.execute(
                "UPDATE songs SET listen_count = ?, listener_count = ?, popularity_fetched_at = ? WHERE id = ?",
                (hit["listens"], hit["listeners"], fetched_at, song["id"]),
            )
    conn.commit()
    return {"recordings": len(totals), "songs_matched": matched}


if __name__ == "__main__":
    import sqlite3
    import sys

    connection = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/undercurrents.db")
    connection.row_factory = sqlite3.Row
    print(assign_popularity(connection))
