import json
import logging

from pydantic import ValidationError

from undercurrents.ingestion.normalize import normalize_setlist
from undercurrents.ingestion.raw_schema import (
    RawSearchArtistsResponse,
    RawSetlist,
    RawSetlistsPage,
)
from undercurrents.ingestion.setlistfm_client import SetlistFmError, params_hash
from undercurrents.storage import db

logger = logging.getLogger(__name__)

ARTIST_NAME = "Tame Impala"
SEARCH_ARTISTS_ENDPOINT = "/search/artists"
SETLISTS_ENDPOINT_TEMPLATE = "/artist/{mbid}/setlists"


class ArtistNotFoundError(Exception):
    pass


def cached_get(conn, client, endpoint: str, params: dict, force_refresh: bool = False) -> dict:
    p_hash = params_hash(params)
    if not force_refresh:
        cached_payload = db.get_cached_response(conn, endpoint, p_hash)
        if cached_payload is not None:
            return json.loads(cached_payload)

    status, payload = client.get(endpoint, params)
    db.cache_response(conn, endpoint, p_hash, status, json.dumps(payload))
    return payload


def resolve_artist_mbid(
    conn, client, artist_name: str = ARTIST_NAME, force_refresh: bool = False
) -> str:
    payload = cached_get(
        conn, client, SEARCH_ARTISTS_ENDPOINT, {"artistName": artist_name}, force_refresh
    )
    search_result = RawSearchArtistsResponse.model_validate(payload)

    for candidate in search_result.artist:
        if candidate.name.strip().lower() == artist_name.strip().lower():
            return candidate.mbid

    raise ArtistNotFoundError(
        f"No exact match for artist '{artist_name}'. "
        f"Candidates: {[c.name for c in search_result.artist]}"
    )


def fetch_and_store_all_setlists(
    conn, client, artist_mbid: str, force_refresh: bool = False
) -> int:
    endpoint = SETLISTS_ENDPOINT_TEMPLATE.format(mbid=artist_mbid)
    page = 1
    total_pages = None
    stored_count = 0

    while total_pages is None or page <= total_pages:
        try:
            payload = cached_get(conn, client, endpoint, {"p": page}, force_refresh)
        except SetlistFmError as exc:
            if total_pages is None:
                raise
            logger.warning("Skipping page %s after fetch failure: %s", page, exc)
            page += 1
            continue

        raw_page = RawSetlistsPage.model_validate(payload)
        if total_pages is None:
            items_per_page = raw_page.itemsPerPage or 1
            total_pages = -(-raw_page.total // items_per_page)

        for raw_item in raw_page.setlist:
            try:
                raw_setlist = RawSetlist.model_validate(raw_item)
                normalized = normalize_setlist(raw_setlist)
            except (ValidationError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed setlist entry %s: %s",
                    raw_item.get("id", "<unknown>"),
                    exc,
                )
                continue
            db.save_setlist(conn, normalized)
            stored_count += 1

        page += 1

    return stored_count
