import json
import logging

from undercurrents.clustering import aliases
from undercurrents.clustering.mbid_client import MusicBrainzError
from undercurrents.ingestion.setlistfm_client import params_hash
from undercurrents.storage import db

logger = logging.getLogger(__name__)

RECORDING_SEARCH_ENDPOINT = "/recording"
MIN_SCORE = 90
ARTIST_NAME = "Tame Impala"


def _escape_lucene(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _cached_get(conn, client, endpoint: str, params: dict, force_refresh: bool) -> dict:
    p_hash = params_hash(params)
    if not force_refresh:
        cached_payload = db.get_cached_response(conn, endpoint, p_hash)
        if cached_payload is not None:
            return json.loads(cached_payload)

    status, payload = client.get(endpoint, params)
    db.cache_response(conn, endpoint, p_hash, status, json.dumps(payload))
    return payload


def _search_mbid_for_title(conn, client, title: str, force_refresh: bool) -> str | None:
    query = f'recording:"{_escape_lucene(title)}" AND artist:"{ARTIST_NAME}"'
    payload = _cached_get(
        conn,
        client,
        RECORDING_SEARCH_ENDPOINT,
        {"query": query, "fmt": "json", "limit": 5},
        force_refresh,
    )
    recordings = payload.get("recordings", [])
    if not recordings:
        return None
    best = max(recordings, key=lambda r: r.get("score", 0))
    if best.get("score", 0) < MIN_SCORE:
        return None
    return best["id"]


def resolve_song_titles(conn, client, force_refresh: bool = False) -> None:
    db.ensure_songs_clustering_columns(conn)

    if force_refresh:
        conn.execute(
            "UPDATE songs SET mbid = NULL, canonical_song_id = NULL, excluded_from_clustering = 0"
        )
        conn.commit()

    for song in db.get_unresolved_songs(conn):
        try:
            _resolve_one(conn, client, song["id"], song["name"], force_refresh)
        except MusicBrainzError as exc:
            logger.warning(
                "Skipping title resolution for '%s' after a MusicBrainz error: %s. "
                "It stays unresolved and will be retried on the next run.",
                song["name"],
                exc,
            )
            continue

    _merge_songs_sharing_mbid(conn)


def _resolve_one(conn, client, song_id: int, name: str, force_refresh: bool) -> None:
    if name in aliases.EXCLUDE:
        db.set_song_excluded(conn, song_id)
        return

    if name in aliases.MERGE:
        target_name = aliases.MERGE[name]
        target_id = db.get_song_id_by_name(conn, target_name)
        if target_id is None:
            raise ValueError(f"MERGE alias target '{target_name}' not found for '{name}'")
        db.set_song_canonical(conn, song_id, target_id)
        return

    if name in aliases.FIX_TEXT:
        name = aliases.FIX_TEXT[name]
        db.rename_song(conn, song_id, name)

    mbid = _search_mbid_for_title(conn, client, name, force_refresh)
    if mbid is not None:
        db.set_song_mbid(conn, song_id, mbid)


def _merge_songs_sharing_mbid(conn) -> None:
    rows = conn.execute(
        "SELECT id, mbid FROM songs WHERE mbid IS NOT NULL AND canonical_song_id IS NULL ORDER BY id"
    ).fetchall()
    seen: dict[str, int] = {}
    for row in rows:
        canonical_id = seen.get(row["mbid"])
        if canonical_id is None:
            seen[row["mbid"]] = row["id"]
        else:
            db.set_song_canonical(conn, row["id"], canonical_id)
