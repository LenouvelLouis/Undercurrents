from undercurrents.clustering.features import build_canonical_song_map, excluded_song_ids
from undercurrents.storage import db


def total_show_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM setlists").fetchone()["c"]


def date_range(conn) -> tuple[str, str] | None:
    row = conn.execute("SELECT MIN(event_date) AS start, MAX(event_date) AS end FROM setlists").fetchone()
    if row["start"] is None:
        return None
    return row["start"], row["end"]


def most_played_song(conn) -> tuple[str, int] | None:
    canonical_map = build_canonical_song_map(conn)
    excluded = excluded_song_ids(conn)

    counts: dict[int, int] = {}
    for entry in db.get_setlist_song_entries(conn):
        song_id = entry["song_id"]
        if song_id in excluded:
            continue
        canonical_id = canonical_map[song_id]
        if canonical_id in excluded:
            continue
        counts[canonical_id] = counts.get(canonical_id, 0) + 1

    if not counts:
        return None
    best_id = max(counts, key=counts.get)
    name = next(row["name"] for row in db.get_all_songs(conn) if row["id"] == best_id)
    return name, counts[best_id]


def last_played_date(conn, canonical_song_id: int) -> str | None:
    canonical_map = build_canonical_song_map(conn)
    matching_ids = [sid for sid, cid in canonical_map.items() if cid == canonical_song_id]
    if not matching_ids:
        return None
    placeholders = ",".join("?" * len(matching_ids))
    row = conn.execute(
        f"""
        SELECT MAX(s.event_date) AS d FROM setlist_songs ss
        JOIN setlists s ON s.id = ss.setlist_id
        WHERE ss.song_id IN ({placeholders})
        """,
        matching_ids,
    ).fetchone()
    return row["d"]
