"""Concert explorer: every show in the archive, and one show in full.

The detail view puts three kinds of fact side by side and keeps them apart: what the source
recorded (setlist, notes, guests), what the archive derives from earlier shows only (how rare
each song was at that point), and what the setlist model predicted the night before, taken
from the walk-forward replay in `prediction/replay.py`. The frozen production model is never
used here: it has seen every show and would be grading itself on its own training data.
"""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from undercurrents.api.dependencies import get_conn
from undercurrents.api.predictions import store
from undercurrents.clustering.features import build_canonical_song_map
from undercurrents.prediction import features

router = APIRouter(prefix="/api/shows", tags=["shows"])


def _optional(conn, sql: str, params: tuple, many: bool = False):
    """Notes, weather and derived features live in tables created by their own enrichment
    steps; on a database that has not run them yet the show is still served, without them."""
    try:
        cursor = conn.execute(sql, params)
        return cursor.fetchall() if many else cursor.fetchone()
    except sqlite3.OperationalError:
        return [] if many else None


def _replay_by_setlist(conn) -> dict[str, dict]:
    try:
        replay = store.get_backtest("replay", conn)
    except ValueError:
        return {}
    return {show["setlist_id"]: show for show in replay["shows"]}


@router.get("")
def list_shows(conn=Depends(get_conn)):
    rows = conn.execute(
        """
        SELECT s.id, s.event_date, s.venue_id, v.name AS venue, v.city, v.country, t.name AS tour,
               (SELECT COUNT(*) FROM setlist_songs ss WHERE ss.setlist_id = s.id AND ss.is_tape = 0) AS songs
        FROM setlists s
        LEFT JOIN venues v ON v.id = s.venue_id
        LEFT JOIN tours t ON t.id = s.tour_id
        ORDER BY s.event_date DESC, s.id
        """
    ).fetchall()
    replay = _replay_by_setlist(conn)
    return [
        {
            "id": r["id"],
            "event_date": r["event_date"],
            "venue_id": r["venue_id"],
            "venue": r["venue"],
            "city": r["city"],
            "country": r["country"],
            "tour": r["tour"],
            "songs": r["songs"],
            "replay_accuracy": replay[r["id"]]["accuracy"] if r["id"] in replay else None,
        }
        for r in rows
    ]


def _rarity_at(conn, setlist_id: str) -> tuple[dict[int, dict], str | None, str | None]:
    """For each canonical song of the given show: plays and shows-since-last-play counted over
    earlier shows only. Also returns the previous and next show ids with a setlist."""
    ordered = features._ordered_setlists_with_songs(conn)
    index = next((i for i, s in enumerate(ordered) if s["id"] == setlist_id), None)
    if index is None:
        return {}, None, None
    plays: dict[int, int] = {}
    last_seen: dict[int, int] = {}
    for i in range(index):
        for song_id in ordered[i]["songs"]:
            plays[song_id] = plays.get(song_id, 0) + 1
            last_seen[song_id] = i
    rarity = {}
    for song_id in ordered[index]["songs"]:
        prior = plays.get(song_id, 0)
        rarity[song_id] = {
            "prior_plays": prior,
            "shows_since_last": (index - last_seen[song_id]) if song_id in last_seen else None,
            "first_time": prior == 0,
            "prior_play_rate": round(prior / index, 4) if index else None,
        }
    prev_id = ordered[index - 1]["id"] if index > 0 else None
    next_id = ordered[index + 1]["id"] if index + 1 < len(ordered) else None
    return rarity, prev_id, next_id


@router.get("/{setlist_id}")
def get_show(setlist_id: str, conn=Depends(get_conn)):
    show = conn.execute(
        """
        SELECT s.id, s.event_date, s.url, s.info, t.name AS tour,
               v.id AS venue_id, v.name AS venue, v.city, v.country, v.capacity, v.venue_kind,
               v.is_outdoor, v.latitude, v.longitude
        FROM setlists s
        LEFT JOIN venues v ON v.id = s.venue_id
        LEFT JOIN tours t ON t.id = s.tour_id
        WHERE s.id = ?
        """,
        (setlist_id,),
    ).fetchone()
    if show is None:
        raise HTTPException(status_code=404, detail="Unknown setlist")

    canonical = build_canonical_song_map(conn)
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM songs")}
    song_columns = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    album_sql = "album, release_date" if {"album", "release_date"} <= song_columns else "NULL AS album, NULL AS release_date"
    records = {r["id"]: r for r in conn.execute(f"SELECT id, {album_sql} FROM songs")}
    notes = {
        r["position"]: dict(r)
        for r in _optional(conn, "SELECT * FROM performance_notes WHERE setlist_id = ?", (setlist_id,), many=True)
    }
    rarity, prev_id, next_id = _rarity_at(conn, setlist_id)
    replay = _replay_by_setlist(conn).get(setlist_id)

    songs = []
    for r in conn.execute(
        """
        SELECT ss.position, ss.set_number, ss.set_name, ss.song_id, ss.is_encore, ss.is_cover,
               ss.is_tape, ss.info, ss.guest_name, a.name AS cover_artist
        FROM setlist_songs ss LEFT JOIN artists a ON a.id = ss.cover_artist_id
        WHERE ss.setlist_id = ? ORDER BY ss.position
        """,
        (setlist_id,),
    ):
        cid = canonical.get(r["song_id"], r["song_id"])
        note = notes.get(r["position"])
        flags = [k[3:] for k, v in (note or {}).items() if k.startswith("is_") and v]
        songs.append(
            {
                "position": r["position"],
                "set_name": r["set_name"],
                "song_id": cid,
                "name": names.get(r["song_id"]),
                "is_encore": bool(r["is_encore"]),
                "is_cover": bool(r["is_cover"]),
                "is_tape": bool(r["is_tape"]),
                "cover_artist": r["cover_artist"],
                "guest": r["guest_name"],
                "info": r["info"],
                "album": records[r["song_id"]]["album"] if r["song_id"] in records else None,
                # released after this night: the crowd was hearing it before the record existed
                "before_release": (
                    records[r["song_id"]]["release_date"] > show["event_date"]
                    if r["song_id"] in records and records[r["song_id"]]["release_date"] and not r["is_cover"]
                    else False
                ),
                "note_flags": flags,
                "rarity": rarity.get(cid),
                "predicted_probability": (replay or {}).get("played_probability", {}).get(str(cid)),
                "predicted_rank": (replay or {}).get("played_rank", {}).get(str(cid)),
            }
        )

    weather = _optional(
        conn,
        "SELECT temp_max_c, temp_min_c, precipitation_mm, wind_max_kmh FROM show_weather WHERE setlist_id = ?",
        (setlist_id,),
    )
    derived = _optional(
        conn,
        "SELECT known_duration_ms, novelty_rate, days_since_previous, travel_km FROM setlist_features WHERE setlist_id = ?",
        (setlist_id,),
    )

    fmt = _optional(conn, "SELECT format, signals FROM show_format WHERE setlist_id = ?", (setlist_id,))

    replay_block = None
    if replay:
        played = {s["song_id"] for s in songs if not s["is_tape"]}
        replay_block = {
            "accuracy": replay["accuracy"],
            "baseline_accuracy": replay["baseline_accuracy"],
            "hits": replay["hits"],
            "played": replay["played"],
            "trained_through": replay["trained_through"],
            "trained_on_shows": replay["trained_on_shows"],
            "unseen_songs": [names.get(i, str(i)) for i in replay["unseen_songs"]],
            "top": [
                {"song_id": sid, "name": names.get(sid), "probability": p, "played": sid in played}
                for sid, p in replay["top"][: max(replay["played"] + 5, 15)]
            ],
        }

    return {
        "id": show["id"],
        "event_date": show["event_date"],
        "url": show["url"],
        "info": show["info"],
        "tour": show["tour"],
        "venue": {
            "id": show["venue_id"],
            "name": show["venue"],
            "city": show["city"],
            "country": show["country"],
            "capacity": show["capacity"],
            "kind": show["venue_kind"],
            "is_outdoor": None if show["is_outdoor"] is None else bool(show["is_outdoor"]),
        },
        "weather": dict(weather) if weather else None,
        "derived": dict(derived) if derived else None,
        "format": {"kind": fmt["format"], "signals": json.loads(fmt["signals"])} if fmt else None,
        "songs": songs,
        "replay": replay_block,
        "previous_id": prev_id,
        "next_id": next_id,
    }
