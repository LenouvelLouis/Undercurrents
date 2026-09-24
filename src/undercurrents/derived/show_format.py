"""What kind of night each show was: a festival slot, a headline show, a DJ set, or a special.

setlist.fm has no festival flag, so this is an estimate, built from signals that can each be
read back on the page rather than from a model nobody can inspect:

- the setlist's own note says so ("festival", a named sponsor "stage", "DJ set", "Tiny Desk")
- the venue name reads like festival ground (park, beach, field, showground, racecourse...)
  or like a room built for headline shows (arena, theatre, hall, centre...)
- the venue is typed as a park or recorded as outdoor (Wikidata, `venue_profile.py`)
- the set was short, or the music ran short, next to the shows around it (a festival slot is
  usually cut to an hour)
- the same site was played twice about a week apart, the pattern of two-weekend festivals

TV, radio and studio appearances are set apart first (a named show or studio), and a setlist
of five songs or fewer is marked incomplete: on this archive those are nearly all partial
fan transcriptions, too thin to say anything about the night. A show scoring 2 or more is then a festival slot; on this archive every
single signal worth 2 (a festival-ground name, or a set that was short on both song count and
running time) turned out, on inspection, to be a festival. There is no ground truth to score this against,
so the page shows the signals behind every call and the counts are presented as estimates.
"""

from __future__ import annotations

import json
import re
import statistics
from datetime import date, datetime

FESTIVAL_NOTE = re.compile(r"festival|\bfest\b|lineup|line-up|\bstage\b", re.IGNORECASE)
DJ_NOTE = re.compile(r"\bdj\b", re.IGNORECASE)
BROADCAST_VENUE = re.compile(
    r"late show|tonight show|kimmel|saturday night live|later with jools|conan|colbert|fallon|"
    r"studios?\b|triple j|deezer|\bbbc\b|kexp|\bnpr\b|tiny desk|\bradio\b|\btv\b",
    re.IGNORECASE,
)
PROMO_MAX_SONGS = 5
SPECIAL_NOTE = re.compile(r"tiny desk|radio|broadcast|television|\btv\b|session|acoustic set|recording for", re.IGNORECASE)
FESTIVAL_GROUND = re.compile(
    r"\b(park|parklands|parque|parc|beach|playa|field|fields|fairgrounds?|showgrounds?|racecourse|"
    r"festivales|farm|gardens|reserve|recinto|lotnisko|airfield|airport|aeroporto|aeropuerto|domaine|domein|castle|estate|racetrack|hippodrome|hip[oó]dromo|aut[oó]dromo|speedway|grounds|polo club|festival|island|sziget|meadows?)\b",
    re.IGNORECASE,
)
HEADLINE_ROOM = re.compile(
    r"\b(arena|theatre|theater|hall|centre|center|fillmore|palladium|forum|coliseum|dome|ballroom|"
    r"auditorium|stadium|festhalle|palacio|pavilion|academy|bowl)\b",
    re.IGNORECASE,
)
FESTIVAL_THRESHOLD = 2
NEIGHBOUR_DAYS = 45


def _parse(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS show_format (
            setlist_id  TEXT PRIMARY KEY REFERENCES setlists(id),
            format      TEXT NOT NULL,
            score       INTEGER NOT NULL,
            signals     TEXT NOT NULL,
            computed_at TEXT NOT NULL
        )
        """
    )


def _load(conn) -> list[dict]:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(venues)")}
    kind = "v.venue_kind" if "venue_kind" in columns else "NULL"
    outdoor = "v.is_outdoor" if "is_outdoor" in columns else "NULL"
    rows = conn.execute(
        f"""
        SELECT s.id, s.event_date, s.info, s.venue_id, v.name AS venue, {kind} AS venue_kind,
               {outdoor} AS is_outdoor,
               (SELECT COUNT(*) FROM setlist_songs ss WHERE ss.setlist_id = s.id AND ss.is_tape = 0) AS songs
        FROM setlists s LEFT JOIN venues v ON v.id = s.venue_id
        ORDER BY s.event_date, s.id
        """
    ).fetchall()
    durations = {}
    try:
        durations = {
            r["setlist_id"]: r["known_duration_ms"]
            for r in conn.execute("SELECT setlist_id, known_duration_ms FROM setlist_features")
        }
    except Exception:  # derived features not built yet
        pass
    return [
        {**dict(r), "date": _parse(r["event_date"]), "duration_ms": durations.get(r["id"])}
        for r in rows
        if r["songs"] > 0
    ]


def classify_all(shows: list[dict]) -> dict[str, dict]:
    by_venue: dict[str, list[date]] = {}
    for show in shows:
        by_venue.setdefault(show["venue_id"], []).append(show["date"])

    results = {}
    for show in shows:
        signals: list[str] = []
        score = 0
        info = show["info"] or ""
        venue = show["venue"] or ""

        if DJ_NOTE.search(info):
            results[show["id"]] = {"format": "dj_set", "score": 0, "signals": ["note mentions a DJ set"]}
            continue
        if SPECIAL_NOTE.search(info) or BROADCAST_VENUE.search(venue):
            results[show["id"]] = {"format": "special", "score": 0, "signals": ["TV, radio or studio session"]}
            continue
        if show["songs"] <= PROMO_MAX_SONGS and not FESTIVAL_NOTE.search(info):
            results[show["id"]] = {"format": "incomplete", "score": 0, "signals": [f"only {show['songs']} songs recorded"]}
            continue

        if FESTIVAL_NOTE.search(info):
            score += 3
            signals.append("note mentions a festival or a named stage")
        if FESTIVAL_GROUND.search(venue):
            score += 2
            signals.append("venue name reads like festival ground")
        if HEADLINE_ROOM.search(venue) or show["venue_kind"] in ("arena", "theatre", "concert hall", "stadium"):
            score -= 2
            signals.append("venue is a room built for headline shows")
        if show["venue_kind"] == "park":
            score += 2
            signals.append("venue typed as a park")
        elif show["is_outdoor"]:
            score += 1
            signals.append("outdoor venue")

        neighbours = [
            s for s in shows if s is not show and abs((s["date"] - show["date"]).days) <= NEIGHBOUR_DAYS
        ]
        if len(neighbours) >= 4:
            median_songs = statistics.median(s["songs"] for s in neighbours)
            if show["songs"] <= 0.8 * median_songs:
                score += 1
                signals.append(f"short set: {show['songs']} songs vs {median_songs:g} around it")
            durations = [s["duration_ms"] for s in neighbours if s["duration_ms"]]
            if show["duration_ms"] and len(durations) >= 4 and show["duration_ms"] <= 0.85 * statistics.median(durations):
                score += 1
                signals.append("music ran short next to the shows around it")

        if any(4 <= abs((d - show["date"]).days) <= 9 for d in by_venue[show["venue_id"]]):
            score += 1
            signals.append("same site played again about a week apart")

        results[show["id"]] = {
            "format": "festival" if score >= FESTIVAL_THRESHOLD else "headline",
            "score": score,
            "signals": signals,
        }
    return results


def rebuild(conn) -> dict:
    ensure_table(conn)
    shows = _load(conn)
    results = classify_all(shows)
    computed_at = datetime.now().isoformat(timespec="seconds")
    conn.execute("DELETE FROM show_format")
    conn.executemany(
        "INSERT INTO show_format (setlist_id, format, score, signals, computed_at) VALUES (?, ?, ?, ?, ?)",
        [(sid, r["format"], r["score"], json.dumps(r["signals"]), computed_at) for sid, r in results.items()],
    )
    conn.commit()
    counts: dict[str, int] = {}
    for r in results.values():
        counts[r["format"]] = counts.get(r["format"], 0) + 1
    return counts


if __name__ == "__main__":
    import sqlite3
    import sys

    connection = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/undercurrents.db")
    connection.row_factory = sqlite3.Row
    print(rebuild(connection))
