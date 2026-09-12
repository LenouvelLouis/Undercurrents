import json
import logging

from undercurrents.clustering.mbid_client import MusicBrainzError
from undercurrents.clustering.title_resolution import _cached_get
from undercurrents.storage import db

logger = logging.getLogger(__name__)

RECORDING_LOOKUP_PARAMS = {"inc": "releases+genres+tags+work-rels", "fmt": "json"}
WORK_LOOKUP_PARAMS = {"inc": "recording-rels", "fmt": "json"}
RELATED_RECORDING_PARAMS = {"inc": "releases", "fmt": "json"}
MAX_RELATED_RECORDINGS = 5


def _earliest_release_date(releases: list[dict]) -> str | None:
    dates = [release["date"] for release in releases if release.get("date")]
    if not dates:
        return None

    def sort_key(date_str: str) -> tuple[int, int, int]:
        parts = date_str.split("-")
        parts += ["01"] * (3 - len(parts))
        return tuple(int(part) for part in parts)

    return min(dates, key=sort_key)


def _extract_genre_names(payload: dict) -> list[str]:
    tags = payload.get("genres") or payload.get("tags") or []
    return [tag["name"] for tag in tags if "name" in tag]


def _find_work_id(recording_payload: dict) -> str | None:
    for relation in recording_payload.get("relations", []):
        if relation.get("target-type") == "work" and relation.get("work"):
            return relation["work"]["id"]
    return None


def _find_related_studio_recording_ids(work_payload: dict, exclude_id: str) -> list[str]:
    """Recording ids linked to a work, other than `exclude_id`, whose disambiguation doesn't
    look like a cataloged live performance — MusicBrainz works are often linked to dozens of
    individually-dated live recordings with no attached release, so filtering those out (and
    capping the rest at `MAX_RELATED_RECORDINGS`) keeps the number of follow-up lookups
    bounded and focused on recordings actually likely to have a release date."""
    ids: list[str] = []
    for relation in work_payload.get("relations", []):
        if relation.get("target-type") != "recording":
            continue
        recording = relation.get("recording") or {}
        recording_id = recording.get("id")
        if not recording_id or recording_id == exclude_id or recording_id in ids:
            continue
        if "live" in (recording.get("disambiguation") or "").lower():
            continue
        ids.append(recording_id)
        if len(ids) >= MAX_RELATED_RECORDINGS:
            break
    return ids


def enrich_song_metadata(conn, client, force_refresh: bool = False) -> None:
    db.ensure_songs_enrichment_columns(conn)

    if force_refresh:
        conn.execute("UPDATE songs SET release_date = NULL, duration_ms = NULL, genre_tags = NULL")
        conn.commit()

    for song in db.get_songs_needing_enrichment(conn):
        try:
            _enrich_one(conn, client, song["id"], song["mbid"], force_refresh)
        except MusicBrainzError as exc:
            logger.warning(
                "Skipping metadata enrichment for song id %s after a MusicBrainz error: %s. "
                "It stays unenriched and will be retried on the next run.",
                song["id"],
                exc,
            )
            continue


def _enrich_one(conn, client, song_id: int, mbid: str, force_refresh: bool) -> None:
    payload = _cached_get(conn, client, f"/recording/{mbid}", RECORDING_LOOKUP_PARAMS, force_refresh)

    duration_ms = payload.get("length")
    all_releases = list(payload.get("releases") or [])

    work_id = _find_work_id(payload)
    if work_id is not None:
        work_payload = _cached_get(
            conn, client, f"/work/{work_id}", WORK_LOOKUP_PARAMS, force_refresh
        )
        for related_id in _find_related_studio_recording_ids(work_payload, exclude_id=mbid):
            related_payload = _cached_get(
                conn, client, f"/recording/{related_id}", RELATED_RECORDING_PARAMS, force_refresh
            )
            all_releases.extend(related_payload.get("releases") or [])

    release_date = _earliest_release_date(all_releases)
    genre_tags = json.dumps(_extract_genre_names(payload))

    db.set_song_metadata(
        conn, song_id, release_date=release_date, duration_ms=duration_ms, genre_tags=genre_tags
    )
