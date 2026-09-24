"""Turning the free-text note on a performance into something you can query.

`setlist_songs.info` holds 536 notes written by setlist.fm contributors. They are short and
highly repetitive ("Reprise", "Snippet", "Live debut", "'Sestri Levante' outro"), which is
what makes a regex classifier reasonable here rather than lazy: the vocabulary is small and
it can be read, argued with and corrected, which a learned classifier on 536 examples could
not be.

Two honesty rules shape this module. Every flag stores the substring that triggered it, so a
wrong classification can be traced to the phrase that caused it instead of being taken on
faith. And the debut flag is never trusted: the notes claim a live debut 65 times, and
`verify_debuts` checks each claim against the performance history the database already holds,
because a contributor's note is a claim and the setlist archive is evidence.
"""

import json
import re
import sqlite3
from datetime import datetime

# Each flag is one or more patterns. Ordered loosely by how often they fire, which only
# affects which phrase is reported when several match.
PATTERNS: dict[str, str] = {
    # A first ever performance, per the contributor. The negative lookahead is the whole
    # point of this pattern: "first time played" and "first time played since 2015" mean
    # opposite things, and an earlier version of this flag scored 17 returns as debuts. The
    # verification below is what caught it.
    "debut": (
        r"(?i)\blive\s+debut\b|\bdebut\s+live\b|\bfirst\s+ever\b"
        r"|\bfirst\s+(?:time\s+)?(?:played|performance)\b"
        r"(?!\s+(?:live\s+)?(?:since|during|of\b|in\s+\d|at\b))"
    ),
    # The mirror image, and a genuinely useful signal of its own: a song coming back after
    # years away, which is exactly what the comeback predictor tries to anticipate.
    "long_awaited_return": r"(?i)\bfirst\b[^.;]{0,40}\bsince\b",
    # first outing of a given tour, which is a different and weaker claim
    "tour_debut": r"(?i)\b(?:\d{4}\s+)?tour\s+debut\b",
    "reprise": r"(?i)\breprise\b",
    "instrumental": r"(?i)\binstrumental\b",
    # a fragment of another song dropped inside this one
    "snippet": r"(?i)\bsnippet\b|\btease[ds]?\b|\binterpolat\w*\b|\bmotifs?\s+from\b|\bexcerpt\b",
    "jam": r"(?i)\bjam\b|\bextended\b",
    "intro_outro": r"(?i)\bintro\b|\boutro\b",
    "partial": r"(?i)\bpartial\b|\bplayed\s+half\b|\bcut\s+short\b|\baborted\b",
    "solo": r"(?i)\b(?:drum|guitar|bass|keyboard)\s+solo\b",
    # the crowd got what it asked for, usually via a sign in the front row
    "fan_request": r"(?i)\bfan\s+request\b|\brequest(?:ed)?\b|\bsign\b",
    "dedication": r"(?i)\bdedicat\w*\b|\btribute\b|\bin\s+memor\w*\b",
    "guest_mentioned": r"(?i)\bwith\s+\w|\bw/\s|\bjoined\s+by\b|\bfeaturing\b",
}

# Titles inside the note, in any of the quote styles contributors actually use. These are the
# songs being teased, not the song being played.
QUOTED = re.compile(
    '"([^"]{3,60})"'
    r"|\u201c([^\u201d]{3,60})\u201d"
    r"|\u2018([^\u2019]{3,60})\u2019"
    r"|'([^']{3,60})'"
)

# Contributors write an unreleased instrumental as 'New' Jam or 'Newer' Jam. Those are
# placeholders for a song with no title yet, not a tease of a song called "New".
NOT_A_TITLE = {"new", "newer", "newest", "unknown", "untitled"}

FLAGS = tuple(PATTERNS)


def classify(info: str | None) -> dict:
    """Returns one boolean per flag plus the phrase that triggered each one."""
    result = {flag: False for flag in FLAGS}
    evidence: dict[str, str] = {}
    if not info:
        return {"flags": result, "evidence": evidence, "teases": []}

    for flag, pattern in PATTERNS.items():
        match = re.search(pattern, info)
        if match:
            result[flag] = True
            evidence[flag] = match.group(0)

    return {"flags": result, "evidence": evidence, "teases": extract_teases(info)}


def extract_teases(info: str | None) -> list[str]:
    """Quoted song titles mentioned in a note, deduplicated, order preserved."""
    if not info:
        return []
    seen: list[str] = []
    for groups in QUOTED.findall(info):
        candidate = next((g for g in groups if g), "")
        cleaned = candidate.strip(" .,;:-")
        if cleaned and cleaned.lower() not in NOT_A_TITLE and cleaned not in seen:
            seen.append(cleaned)
    return seen


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS performance_notes (
            setlist_id  TEXT NOT NULL,
            position    INTEGER NOT NULL,
            song_id     INTEGER REFERENCES songs(id),
            info        TEXT NOT NULL,
            {", ".join(f"is_{flag} INTEGER NOT NULL DEFAULT 0" for flag in FLAGS)},
            evidence    TEXT NOT NULL,
            teases      TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            PRIMARY KEY (setlist_id, position)
        )
        """
    )
    # `CREATE TABLE IF NOT EXISTS` does nothing to a table that already exists, so a new flag
    # added to PATTERNS would blow up on insert against an older database. Adding the missing
    # columns here keeps the flag list the single source of truth.
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(performance_notes)")}
    for flag in FLAGS:
        column = f"is_{flag}"
        if column not in existing:
            conn.execute(
                f"ALTER TABLE performance_notes ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"
            )
    conn.commit()


def rebuild(conn: sqlite3.Connection) -> dict:
    """Classifies every note. Rebuilt wholesale rather than incrementally, because the
    patterns change more often than the notes do."""
    ensure_table(conn)
    conn.execute("DELETE FROM performance_notes")

    rows = conn.execute(
        """
        SELECT setlist_id, position, song_id, info
        FROM setlist_songs
        WHERE info IS NOT NULL AND TRIM(info) <> ''
        """
    ).fetchall()

    computed_at = datetime.now().isoformat(timespec="seconds")
    counts = {flag: 0 for flag in FLAGS}
    tease_total = 0
    columns = ", ".join(f"is_{flag}" for flag in FLAGS)
    placeholders = ", ".join("?" for _ in FLAGS)

    for row in rows:
        result = classify(row["info"])
        flags = result["flags"]
        for flag, on in flags.items():
            counts[flag] += 1 if on else 0
        tease_total += len(result["teases"])
        conn.execute(
            f"""
            INSERT INTO performance_notes
                (setlist_id, position, song_id, info, {columns}, evidence, teases, computed_at)
            VALUES (?, ?, ?, ?, {placeholders}, ?, ?, ?)
            """,
            (
                row["setlist_id"],
                row["position"],
                row["song_id"],
                row["info"],
                *(int(flags[flag]) for flag in FLAGS),
                json.dumps(result["evidence"], ensure_ascii=False),
                json.dumps(result["teases"], ensure_ascii=False),
                computed_at,
            ),
        )

    conn.commit()
    return {"notes_classified": len(rows), "by_flag": counts, "teases_extracted": tease_total}


def verify_debuts(conn: sqlite3.Connection) -> dict:
    """Checks every "live debut" note against the performance history.

    A note is confirmed when the show it sits on really is the earliest appearance of that
    song in the archive. It is contradicted when an earlier performance exists. Neither
    outcome is a bug on its own: the archive is incomplete before about 2010, so an early
    contradiction may mean the debut note is right and the earlier show is missing something.
    What matters is that the discrepancy is visible rather than silently trusted.
    """
    rows = conn.execute(
        """
        SELECT n.setlist_id, n.song_id, s.event_date, n.info
        FROM performance_notes n
        JOIN setlists s ON s.id = n.setlist_id
        WHERE n.is_debut = 1 AND n.song_id IS NOT NULL
        """
    ).fetchall()

    first_played = {
        row["song_id"]: row["first_date"]
        for row in conn.execute(
            """
            SELECT ss.song_id, MIN(s.event_date) AS first_date
            FROM setlist_songs ss JOIN setlists s ON s.id = ss.setlist_id
            WHERE ss.is_tape = 0
            GROUP BY ss.song_id
            """
        )
    }

    confirmed, contradicted = [], []
    for row in rows:
        earliest = first_played.get(row["song_id"])
        target = confirmed if earliest == row["event_date"] else contradicted
        target.append(
            {
                "setlist_id": row["setlist_id"],
                "song_id": row["song_id"],
                "claimed_on": row["event_date"],
                "earliest_in_archive": earliest,
                "days_earlier": (
                    (
                        datetime.strptime(row["event_date"], "%Y-%m-%d")
                        - datetime.strptime(earliest, "%Y-%m-%d")
                    ).days
                    if earliest and earliest != row["event_date"]
                    else 0
                ),
            }
        )

    return {
        "claims": len(rows),
        "confirmed": len(confirmed),
        "contradicted": len(contradicted),
        "contradictions": sorted(contradicted, key=lambda c: -c["days_earlier"])[:10],
    }
