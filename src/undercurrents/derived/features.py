"""Per-song and per-setlist features derived from the ingested rows.

Everything here is a recomputation of data already in the database, never a new fact:
`rebuild` truncates both tables and fills them again from `setlists` / `setlist_songs`, so
it is safe to run at any time and produces the same result for the same input.

Travel distance is filled only when both this show and the previous one have venue
coordinates; a null there means "not known", never zero kilometres.

Tape entries (intro/outro playback) are excluded from song counts and from a setlist's
song count, matching how the length model already treats them, but they are still counted
separately in `tape_count` so the exclusion stays visible rather than silent.
"""

from datetime import date, datetime
from math import asin, cos, radians, sin, sqrt

from undercurrents.storage import db

# Same approximate album-era boundaries the API uses for its own era labelling. Kept as a
# local copy rather than imported from the API layer, so the derived features do not depend
# on the web layer.
ERA_BOUNDARIES = [
    ("Innerspeaker", None, 2011),
    ("Lonerism", 2012, 2014),
    ("Currents", 2015, 2019),
    ("Slow Rush -> Deadbeat", 2020, None),
]


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance. Straight-line, not routed: it measures how far apart two shows
    were, which is the question, not how far the bus actually drove."""
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    d_lat = lat2_r - lat1_r
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def _era_for_year(year: int) -> str:
    for name, start, end in ERA_BOUNDARIES:
        if (start is None or year >= start) and (end is None or year <= end):
            return name
    return "Unknown"


def _parse(event_date: str) -> date:
    return datetime.strptime(event_date, "%Y-%m-%d").date()


def _load_shows(conn) -> list[dict]:
    """Every setlist in chronological order, with its songs kept in playing order."""
    rows = conn.execute(
        """
        SELECT s.id AS setlist_id, s.event_date, s.venue_id,
               v.latitude, v.longitude,
               ss.position, ss.song_id, ss.is_encore, ss.is_cover, ss.is_tape
        FROM setlists s
        JOIN setlist_songs ss ON ss.setlist_id = s.id
        LEFT JOIN venues v ON v.id = s.venue_id
        ORDER BY s.event_date, s.id, ss.position
        """
    ).fetchall()

    shows: dict[str, dict] = {}
    for row in rows:
        show = shows.setdefault(
            row["setlist_id"],
            {
                "setlist_id": row["setlist_id"],
                "event_date": row["event_date"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "entries": [],
            },
        )
        show["entries"].append(
            {
                "position": row["position"],
                "song_id": row["song_id"],
                "is_encore": bool(row["is_encore"]),
                "is_cover": bool(row["is_cover"]),
                "is_tape": bool(row["is_tape"]),
            }
        )
    return sorted(shows.values(), key=lambda s: (s["event_date"], s["setlist_id"]))


def compute_song_features(shows: list[dict]) -> list[dict]:
    """Aggregate per song. `current_streak` counts back from the most recent show: how many
    consecutive shows, ending with the latest one, featured the song. A song absent from the
    latest show therefore has a streak of 0, which is what makes the number meaningful."""
    stats: dict[int, dict] = {}
    for show in shows:
        played = [e for e in show["entries"] if not e["is_tape"]]
        if not played:
            continue
        total = len(played)
        opener_id = played[0]["song_id"]
        closer_id = played[-1]["song_id"]
        for index, entry in enumerate(played):
            song = stats.setdefault(
                entry["song_id"],
                {
                    "song_id": entry["song_id"],
                    "play_count": 0,
                    "shows": set(),
                    "dates": [],
                    "opener_count": 0,
                    "closer_count": 0,
                    "encore_count": 0,
                    "cover_count": 0,
                    "position_pcts": [],
                    "years": {},
                },
            )
            song["play_count"] += 1
            song["shows"].add(show["setlist_id"])
            song["dates"].append(show["event_date"])
            song["position_pcts"].append(index / (total - 1) if total > 1 else 0.0)
            year = int(show["event_date"][:4])
            song["years"][year] = song["years"].get(year, 0) + 1
            if entry["is_encore"]:
                song["encore_count"] += 1
            if entry["is_cover"]:
                song["cover_count"] += 1
        if opener_id in stats:
            stats[opener_id]["opener_count"] += 1
        if closer_id in stats:
            stats[closer_id]["closer_count"] += 1

    # Streaks are read off the tail of the chronological show list, so they describe the
    # current moment rather than the longest run ever.
    show_song_sets = [
        (show["setlist_id"], {e["song_id"] for e in show["entries"] if not e["is_tape"]})
        for show in shows
    ]

    results = []
    for song_id, song in stats.items():
        dates = sorted(set(song["dates"]))
        longest_gap = None
        if len(dates) > 1:
            longest_gap = max(
                (_parse(b) - _parse(a)).days for a, b in zip(dates, dates[1:])
            )
        streak = 0
        for _, song_ids in reversed(show_song_sets):
            if song_id in song_ids:
                streak += 1
            else:
                break
        dominant_era = None
        if song["years"]:
            era_counts: dict[str, int] = {}
            for year, count in song["years"].items():
                era = _era_for_year(year)
                era_counts[era] = era_counts.get(era, 0) + count
            dominant_era = max(era_counts.items(), key=lambda kv: kv[1])[0]
        results.append(
            {
                "song_id": song_id,
                "play_count": song["play_count"],
                "show_count": len(song["shows"]),
                "first_played": dates[0] if dates else None,
                "last_played": dates[-1] if dates else None,
                "longest_gap_days": longest_gap,
                "current_streak": streak,
                "opener_count": song["opener_count"],
                "closer_count": song["closer_count"],
                "encore_count": song["encore_count"],
                "cover_count": song["cover_count"],
                "avg_position_pct": (
                    sum(song["position_pcts"]) / len(song["position_pcts"])
                    if song["position_pcts"]
                    else None
                ),
                "dominant_era": dominant_era,
            }
        )
    return results


def compute_setlist_features(shows: list[dict], durations_ms: dict[int, int]) -> list[dict]:
    """Aggregate per show. `novelty_rate` compares against the immediately previous show in
    time: the share of tonight's songs that were not played last time. The first show has no
    predecessor, so its novelty and gap are left null rather than defaulted to 0 or 1."""
    results = []
    previous_songs: set[int] | None = None
    previous_date: str | None = None
    previous_point: tuple[float, float] | None = None

    for show in shows:
        entries = show["entries"]
        played = [e for e in entries if not e["is_tape"]]
        song_ids = {e["song_id"] for e in played}

        known = [durations_ms[e["song_id"]] for e in played if e["song_id"] in durations_ms]
        complete = len(known) == len(played) and len(played) > 0

        novelty = None
        if previous_songs is not None and song_ids:
            novelty = len(song_ids - previous_songs) / len(song_ids)

        gap = None
        if previous_date is not None:
            gap = (_parse(show["event_date"]) - _parse(previous_date)).days

        point = (
            (show["latitude"], show["longitude"])
            if show["latitude"] is not None and show["longitude"] is not None
            else None
        )
        travel_km = None
        if point is not None and previous_point is not None:
            travel_km = round(haversine_km(*previous_point, *point), 1)

        results.append(
            {
                "setlist_id": show["setlist_id"],
                "event_date": show["event_date"],
                "song_count": len(played),
                "encore_count": sum(1 for e in played if e["is_encore"]),
                "cover_count": sum(1 for e in played if e["is_cover"]),
                "tape_count": sum(1 for e in entries if e["is_tape"]),
                "opener_song_id": played[0]["song_id"] if played else None,
                "closer_song_id": played[-1]["song_id"] if played else None,
                "known_duration_ms": sum(known) if known else None,
                "duration_complete": 1 if complete else 0,
                "novelty_rate": novelty,
                "days_since_previous": gap,
                "travel_km": travel_km,
            }
        )
        if song_ids:
            previous_songs = song_ids
            previous_date = show["event_date"]
            if point is not None:
                previous_point = point
    return results


def rebuild(conn) -> dict[str, int]:
    """Recompute both tables from scratch. Returns how many rows each one ended up with."""
    db.ensure_derived_feature_tables(conn)
    durations_ms = db.get_song_durations_ms(conn)
    shows = _load_shows(conn)

    song_rows = compute_song_features(shows)
    setlist_rows = compute_setlist_features(shows, durations_ms)
    computed_at = datetime.now().isoformat(timespec="seconds")

    conn.execute("DELETE FROM song_features")
    conn.executemany(
        """
        INSERT INTO song_features (
            song_id, play_count, show_count, first_played, last_played, longest_gap_days,
            current_streak, opener_count, closer_count, encore_count, cover_count,
            avg_position_pct, dominant_era, computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["song_id"], r["play_count"], r["show_count"], r["first_played"],
                r["last_played"], r["longest_gap_days"], r["current_streak"],
                r["opener_count"], r["closer_count"], r["encore_count"], r["cover_count"],
                r["avg_position_pct"], r["dominant_era"], computed_at,
            )
            for r in song_rows
        ],
    )

    conn.execute("DELETE FROM setlist_features")
    conn.executemany(
        """
        INSERT INTO setlist_features (
            setlist_id, event_date, song_count, encore_count, cover_count, tape_count,
            opener_song_id, closer_song_id, known_duration_ms, duration_complete,
            novelty_rate, days_since_previous, travel_km, computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["setlist_id"], r["event_date"], r["song_count"], r["encore_count"],
                r["cover_count"], r["tape_count"], r["opener_song_id"], r["closer_song_id"],
                r["known_duration_ms"], r["duration_complete"], r["novelty_rate"],
                r["days_since_previous"], r["travel_km"], computed_at,
            )
            for r in setlist_rows
        ],
    )
    conn.commit()
    return {"songs": len(song_rows), "setlists": len(setlist_rows)}
