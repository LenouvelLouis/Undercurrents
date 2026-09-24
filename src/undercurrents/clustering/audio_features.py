"""Audio features per song, from AcousticBrainz.

AcousticBrainz holds Essentia analyses of recordings contributed by listeners: tempo, key,
mode, loudness, and a set of trained classifiers. It is free, needs no key, and is indexed
by MusicBrainz *recording* id.

That indexing is the whole difficulty. A song has one entry in this project's `songs` table
and one stored recording mbid, but MusicBrainz holds many recordings per song (album master,
single edit, remaster, radio session, live takes), and AcousticBrainz has an analysis for
some of them and not others. Looking up only the stored mbid found 43 of 81 songs and, worse,
missed Elephant, Let It Happen and The Less I Know the Better, three of the most played
things in the catalogue. All three are analysed, just under a different recording id.

So the lookup is two-stage: ask MusicBrainz for every recording of a title by this artist,
then ask AcousticBrainz for all of them at once and keep the first that comes back. The
recording actually used is stored alongside the features, because "we have a tempo for
Elephant" and "we have a tempo for one particular recording of Elephant" are different
claims and only the second one is true.

The project is frozen upstream: no new analyses have been accepted since 2022, so a song
missing today will stay missing. That is a reason to record coverage honestly, not a reason
to guess.
"""

import json
import sqlite3
import ssl
import time
from datetime import datetime

import httpx
import truststore

from undercurrents.clustering.mbid_client import MusicBrainzClient
from undercurrents.ingestion.setlistfm_client import RateLimiter
from undercurrents.storage import db

ACOUSTICBRAINZ_URL = "https://acousticbrainz.org/api/v1"
# The API accepts a batch of recording ids; 25 is its documented maximum per call.
BATCH_SIZE = 25
USER_AGENT = (
    "Undercurrents/0.1 (https://github.com/LenouvelLouis/Undercurrents; "
    "personal non-commercial research project)"
)


def _default_http_client() -> httpx.Client:
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(base_url=ACOUSTICBRAINZ_URL, timeout=30.0, verify=ssl_context)


class AcousticBrainzClient:
    def __init__(self, http_client: httpx.Client | None = None, rate_limiter: RateLimiter | None = None):
        self._client = http_client or _default_http_client()
        self._rate_limiter = rate_limiter or RateLimiter(min_interval=1.0)

    def low_level(self, recording_ids: list[str]) -> dict:
        """Raw analyses for a batch of recordings. Missing ids are simply absent."""
        if not recording_ids:
            return {}
        self._rate_limiter.wait()
        response = self._client.get(
            "/low-level",
            params={"recording_ids": ";".join(recording_ids[:BATCH_SIZE])},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        if response.status_code != 200:
            return {}
        return response.json()


def ensure_columns(conn: sqlite3.Connection) -> None:
    # `songs.mbid` arrives with the clustering migration, and this module reads it. Calling
    # that here means the enrichment works on a database that has never been clustered.
    db.ensure_songs_clustering_columns(conn)
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(songs)")}
    columns = {
        "bpm": "REAL",
        "musical_key": "TEXT",
        "musical_scale": "TEXT",
        "loudness": "REAL",
        "danceability": "REAL",
        # which recording the numbers above actually describe
        "audio_recording_mbid": "TEXT",
    }
    for column, kind in columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE songs ADD COLUMN {column} {kind}")
    conn.commit()


def _extract(analysis: dict) -> dict | None:
    """Pulls the handful of fields worth keeping out of a very large Essentia document."""
    if not analysis:
        return None
    # A recording can carry several submissions, keyed "0", "1", ... Any one of them is a
    # legitimate analysis of the same audio; the first is taken rather than averaged, because
    # averaging a key across submissions is meaningless.
    document = analysis.get("0") if isinstance(analysis, dict) and "0" in analysis else analysis
    rhythm = document.get("rhythm") or {}
    tonal = document.get("tonal") or {}
    lowlevel = document.get("lowlevel") or {}
    if not rhythm.get("bpm"):
        return None
    return {
        "bpm": round(float(rhythm["bpm"]), 2),
        "musical_key": tonal.get("key_key"),
        "musical_scale": tonal.get("key_scale"),
        "loudness": round(float(lowlevel["average_loudness"]), 4) if lowlevel.get("average_loudness") is not None else None,
        "danceability": round(float(rhythm["danceability"]), 4) if rhythm.get("danceability") is not None else None,
    }


def candidate_recordings(
    mb_client: MusicBrainzClient, title: str, artist: str = "Tame Impala", limit: int = 25
) -> list[str]:
    """Every MusicBrainz recording id for a title by this artist, most relevant first."""
    status, payload = mb_client.get(
        "/recording",
        {"query": f'recording:"{title}" AND artist:"{artist}"', "fmt": "json", "limit": limit},
    )
    if status != 200:
        return []
    return [r["id"] for r in payload.get("recordings", []) if r.get("id")]


def enrich(
    conn: sqlite3.Connection,
    mb_client: MusicBrainzClient | None = None,
    ab_client: AcousticBrainzClient | None = None,
    limit: int | None = None,
    artist: str = "Tame Impala",
) -> dict:
    """Fills the audio columns for songs that do not have them yet.

    Commits per song, so an interrupted run keeps whatever it already resolved instead of
    losing an hour of rate-limited lookups.
    """
    ensure_columns(conn)
    mb_client = mb_client or MusicBrainzClient()
    ab_client = ab_client or AcousticBrainzClient()

    rows = conn.execute(
        """
        SELECT s.id, s.name, s.mbid, COUNT(ss.song_id) AS plays
        FROM songs s
        JOIN setlist_songs ss ON ss.song_id = s.id AND ss.is_tape = 0
        WHERE s.bpm IS NULL
        GROUP BY s.id
        ORDER BY plays DESC
        """
    ).fetchall()
    if limit:
        rows = rows[:limit]

    resolved, unresolved = 0, []
    for row in rows:
        # The stored mbid goes first: when it is analysed, that is the closest match to what
        # this project already considers the canonical recording.
        candidates = [row["mbid"]] if row["mbid"] else []
        candidates += [r for r in candidate_recordings(mb_client, row["name"], artist) if r not in candidates]

        features = None
        used = None
        for start in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[start:start + BATCH_SIZE]
            payload = ab_client.low_level(batch)
            for recording_id in batch:
                features = _extract(payload.get(recording_id))
                if features:
                    used = recording_id
                    break
            if features:
                break

        if not features:
            unresolved.append(row["name"])
            continue

        conn.execute(
            """
            UPDATE songs
            SET bpm = ?, musical_key = ?, musical_scale = ?, loudness = ?,
                danceability = ?, audio_recording_mbid = ?
            WHERE id = ?
            """,
            (
                features["bpm"],
                features["musical_key"],
                features["musical_scale"],
                features["loudness"],
                features["danceability"],
                used,
                row["id"],
            ),
        )
        conn.commit()
        resolved += 1

    return {
        "songs_considered": len(rows),
        "resolved": resolved,
        "unresolved": len(unresolved),
        "unresolved_names": unresolved[:15],
        "ran_at": datetime.now().isoformat(timespec="seconds"),
    }


def coverage(conn: sqlite3.Connection) -> dict:
    """How much of the catalogue, and of the performances, the audio features actually cover.

    Both numbers matter and they differ: the songs with features skew towards the ones people
    bothered to analyse, which correlates with how often they are played.
    """
    songs = conn.execute(
        """
        SELECT s.bpm IS NOT NULL AS has_audio, COUNT(DISTINCT s.id) AS songs, COUNT(ss.song_id) AS plays
        FROM songs s JOIN setlist_songs ss ON ss.song_id = s.id AND ss.is_tape = 0
        GROUP BY has_audio
        """
    ).fetchall()
    totals = {bool(r["has_audio"]): {"songs": r["songs"], "plays": r["plays"]} for r in songs}
    with_audio = totals.get(True, {"songs": 0, "plays": 0})
    without = totals.get(False, {"songs": 0, "plays": 0})
    song_total = with_audio["songs"] + without["songs"]
    play_total = with_audio["plays"] + without["plays"]
    return {
        "songs_with_audio": with_audio["songs"],
        "songs_total": song_total,
        "song_coverage": round(with_audio["songs"] / song_total, 4) if song_total else 0.0,
        "performances_covered": with_audio["plays"],
        "performances_total": play_total,
        "performance_coverage": round(with_audio["plays"] / play_total, 4) if play_total else 0.0,
    }
