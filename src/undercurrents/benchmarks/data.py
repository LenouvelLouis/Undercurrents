"""Shared data loading and the time-respecting split every benchmark uses.

The split is chronological, never random: the held-out shows are the most recent ones, the
same convention `prediction.evaluate.backtest` already follows. A random split would let a
model see 2026 shows while being scored on 2015 and inflate every number here.
"""

from undercurrents.storage import db

DEFAULT_HOLDOUT_SHOWS = 60


def load_sequences(conn) -> list[dict]:
    """Setlists as ordered song-id sequences, oldest first. Tape entries are dropped: they
    are intro/outro playback, not a performance, and including them would teach a sequence
    model to predict the walk-on music."""
    rows = conn.execute(
        """
        SELECT s.id AS setlist_id, s.event_date, ss.position, ss.song_id
        FROM setlists s
        JOIN setlist_songs ss ON ss.setlist_id = s.id
        WHERE ss.is_tape = 0
        ORDER BY s.event_date, s.id, ss.position
        """
    ).fetchall()

    shows: dict[str, dict] = {}
    for row in rows:
        show = shows.setdefault(
            row["setlist_id"],
            {"setlist_id": row["setlist_id"], "event_date": row["event_date"], "songs": []},
        )
        show["songs"].append(row["song_id"])

    ordered = sorted(shows.values(), key=lambda s: (s["event_date"], s["setlist_id"]))
    return [s for s in ordered if len(s["songs"]) >= 2]


def split(sequences: list[dict], holdout_shows: int = DEFAULT_HOLDOUT_SHOWS):
    if len(sequences) <= holdout_shows:
        raise ValueError(
            f"Need more than {holdout_shows} usable shows to hold any out; got {len(sequences)}"
        )
    return sequences[:-holdout_shows], sequences[-holdout_shows:]


def song_names(conn) -> dict[int, str]:
    return {r["id"]: r["name"] for r in db.get_all_songs(conn)}
