"""Re-reading the payloads already on disk to fill columns the normalizer used to skip.

Three fields were in every setlist.fm response from the beginning and were simply never
extracted: the city's coordinates, the name of each set, and the guest credited on a song.
Adding them to the normalizer only helps future ingests, so this module walks
`raw_responses` and backfills the 767 setlists already stored. It makes no network call at
all, which is the point: the data was always there.

The coordinate half of this replaces a Nominatim geocoding run that queried 236 cities at
one request per second for something the payloads already carried, with better coverage
(766 of 767 shows against 552 of 556 venues). Nominatim stays useful only for whatever the
payloads omit.
"""

import json
import sqlite3

from undercurrents.ingestion.normalize import normalize_setlist
from undercurrents.ingestion.raw_schema import RawSetlist


def _iter_raw_setlists(conn: sqlite3.Connection):
    """Every setlist across every stored page, newest payload wins on duplicates.

    Pages overlap: the same setlist appears in several stored responses, and re-fetches
    produce newer copies. Keying by setlist id and letting later rows win means the backfill
    uses the freshest copy of each rather than whichever page happened to be read last.
    """
    by_id: dict[str, dict] = {}
    for (payload,) in conn.execute("SELECT payload_json FROM raw_responses ORDER BY id"):
        try:
            parsed = json.loads(payload)
        except (TypeError, ValueError):
            continue
        for entry in parsed.get("setlist") or []:
            if isinstance(entry, dict) and entry.get("id"):
                by_id[entry["id"]] = entry
    return by_id


def backfill(conn: sqlite3.Connection, overwrite_song_context: bool = False) -> dict:
    """Fills coordinates, set names and guest credits from the stored payloads.

    Coordinates are never overwritten: a venue that already has a point may have got it from
    a geocoding run covering a payload that carries none, and replacing that with NULL or a
    less precise value would be a regression.

    Set names and guest credits are different. They are a pure function of the payload, so
    re-deriving them is idempotent, and `overwrite_song_context` exists for the case that
    actually matters: the spelling map in `normalize` gains an entry and the stored values
    need to be brought back in line with it.
    """
    venues_updated = 0
    songs_updated = 0
    set_names = 0
    guests = 0
    skipped: list[str] = []

    known_venues = {
        row["id"] for row in conn.execute("SELECT id FROM venues WHERE latitude IS NOT NULL")
    }

    for setlist_id, raw in _iter_raw_setlists(conn).items():
        try:
            normalized = normalize_setlist(RawSetlist.model_validate(raw))
        except Exception as error:  # a single malformed entry must not stop the backfill
            skipped.append(f"{setlist_id}: {error}")
            continue

        venue = normalized.venue
        if venue.latitude is not None and venue.id not in known_venues:
            conn.execute(
                "UPDATE venues SET latitude = ?, longitude = ? WHERE id = ?",
                (venue.latitude, venue.longitude, venue.id),
            )
            known_venues.add(venue.id)
            venues_updated += 1

        for entry in normalized.songs:
            if entry.set_name is None and entry.guest_name is None:
                continue
            assignment = (
                "set_name = ?, guest_name = ?, guest_mbid = ?"
                if overwrite_song_context
                else (
                    "set_name = COALESCE(set_name, ?), "
                    "guest_name = COALESCE(guest_name, ?), "
                    "guest_mbid = COALESCE(guest_mbid, ?)"
                )
            )
            cursor = conn.execute(
                f"""
                UPDATE setlist_songs
                SET {assignment}
                WHERE setlist_id = ? AND position = ?
                """,
                (
                    entry.set_name,
                    entry.guest_name,
                    entry.guest_mbid,
                    setlist_id,
                    entry.position,
                ),
            )
            if cursor.rowcount:
                songs_updated += 1
                set_names += 1 if entry.set_name else 0
                guests += 1 if entry.guest_name else 0

    conn.commit()
    return {
        "venues_given_coordinates": venues_updated,
        "song_rows_updated": songs_updated,
        "set_names_written": set_names,
        "guest_credits_written": guests,
        "setlists_skipped": len(skipped),
        "skipped_detail": skipped[:5],
    }
