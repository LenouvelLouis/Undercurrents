from fastapi import APIRouter, Depends, HTTPException

from undercurrents.api.dependencies import get_conn
from undercurrents.clustering import annotations, stats as clustering_stats
from undercurrents.clustering.features import build_song_transition_matrix
from undercurrents.storage import db

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# (name, start_year, end_year) -- end_year=None means "open ended, use the dataset's max year".
# start_year=None means "open ended, use the dataset's min year". Approximate album-era
# boundaries, documented as such in the design spec -- no era table exists in the database.
ERA_BOUNDARIES = [
    ("Innerspeaker", None, 2011),
    ("Lonerism", 2012, 2014),
    ("Currents", 2015, 2019),
    ("Slow Rush -> Deadbeat", 2020, None),
]


def _era_for_year(year: int) -> str:
    for name, start, end in ERA_BOUNDARIES:
        if (start is None or year >= start) and (end is None or year <= end):
            return name
    return "Unknown"


@router.get("/venues")
def get_venues(conn=Depends(get_conn)):
    db.ensure_venues_capacity_column(conn)
    rows = conn.execute(
        """
        SELECT v.id, v.name, v.city, v.country, v.capacity,
               COUNT(s.id) AS show_count, MAX(s.event_date) AS last_visited
        FROM venues v
        LEFT JOIN setlists s ON s.venue_id = v.id
        GROUP BY v.id
        ORDER BY show_count DESC, v.name
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "city": row["city"],
            "country": row["country"],
            "show_count": row["show_count"],
            "capacity": row["capacity"],
            "last_visited": row["last_visited"],
        }
        for row in rows
    ]


@router.get("/setlist-trend")
def get_setlist_trend(conn=Depends(get_conn)):
    by_year = clustering_stats.average_setlist_length_by_year(conn)
    if not by_year:
        return {"by_year": {}, "eras": []}

    min_year, max_year = min(by_year), max(by_year)
    eras = []
    for name, start, end in ERA_BOUNDARIES:
        eras.append(
            {
                "name": name,
                "start_year": start if start is not None else min_year,
                "end_year": end if end is not None else max_year,
            }
        )

    return {
        "by_year": {str(year): round(avg, 2) for year, avg in by_year.items()},
        "eras": eras,
    }


def _dominant_period(date_start: str, date_end: str) -> str:
    start_year = int(date_start[:4])
    end_year = int(date_end[:4])
    mid_year = (start_year + end_year) // 2
    return _era_for_year(mid_year)


@router.get("/clusters")
def get_clusters(conn=Depends(get_conn)):
    summaries = clustering_stats.cluster_summary(conn, top_n=1)
    return [
        {
            "cluster_id": s["cluster_id"],
            "size": s["size"],
            "date_start": s["date_start"],
            "date_end": s["date_end"],
            "dominant_period": _dominant_period(s["date_start"], s["date_end"]),
        }
        for s in summaries
    ]


@router.get("/clusters/{cluster_id}")
def get_cluster_detail(cluster_id: int, conn=Depends(get_conn)):
    db.ensure_songs_clustering_columns(conn)
    summaries = clustering_stats.cluster_summary(conn, top_n=8)
    match = next((s for s in summaries if s["cluster_id"] == cluster_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    song_names = {row["id"]: row["name"] for row in db.get_all_songs(conn)}
    return {
        "cluster_id": match["cluster_id"],
        "size": match["size"],
        "date_start": match["date_start"],
        "date_end": match["date_end"],
        "dominant_period": _dominant_period(match["date_start"], match["date_end"]),
        "typical_songs": [
            {"song_id": song_id, "song_name": song_names[song_id]}
            for song_id in match["top_song_ids"]
        ],
    }


SONG_FLAG_TAGS = {
    "is_debut": "song debut",
    "is_fan_request": "fan request",
    "has_tease": "tease",
    "was_extended": "extended outro",
    "was_restarted": "restarted",
}
SETLIST_FLAG_TAGS = {
    "is_incomplete": "incomplete setlist",
    "is_out_of_order": "out of order",
    "was_disrupted": "disrupted show",
}


@router.get("/transitions/{song_id}")
def get_transitions(song_id: int, conn=Depends(get_conn)):
    db.ensure_songs_clustering_columns(conn)
    row = conn.execute("SELECT name FROM songs WHERE id = ?", (song_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Song not found")

    song_ids, matrix = build_song_transition_matrix(conn)
    song_names = {r["id"]: r["name"] for r in db.get_all_songs(conn)}

    follow_ons = []
    if song_id in song_ids:
        i = song_ids.index(song_id)
        total_out = matrix[i, :].sum()
        if total_out > 0:
            for j, target_id in enumerate(song_ids):
                count = matrix[i, j]
                if count > 0:
                    follow_ons.append(
                        {
                            "song_id": target_id,
                            "song_name": song_names[target_id],
                            "probability": round(float(count / total_out), 4),
                        }
                    )
            follow_ons.sort(key=lambda entry: entry["probability"], reverse=True)

    return {"song_id": song_id, "song_name": row["name"], "follow_ons": follow_ons}


def _build_anecdotes(
    song_plays: list[dict],
    setlists_flagged: list[dict],
    event_dates: dict[str, str],
    song_names: dict[int, str],
    milestones: list[dict],
) -> list[dict]:
    """Pure aggregation, deliberately decoupled from the DB/regex classification in
    `clustering.annotations` so it can be unit-tested with hand-built input. `song_plays` /
    `setlists_flagged` are shaped like `annotations.annotated_song_plays` /
    `annotated_setlists`'s output; `milestones` is shaped like `_compute_milestones`'s
    output."""
    entries = []
    for play in song_plays:
        for flag, tag in SONG_FLAG_TAGS.items():
            if play.get(flag):
                song_name = song_names.get(play["song_id"], "Unknown song")
                description = play.get("info") or f"'{song_name}' — {tag}."
                entries.append(
                    {
                        "date": event_dates.get(play["setlist_id"], ""),
                        "tag": tag,
                        "description": description,
                    }
                )

    for setlist in setlists_flagged:
        for flag, tag in SETLIST_FLAG_TAGS.items():
            if setlist.get(flag):
                description = setlist.get("info") or f"Setlist — {tag}."
                entries.append(
                    {
                        "date": event_dates.get(setlist["setlist_id"], ""),
                        "tag": tag,
                        "description": description,
                    }
                )

    for milestone in milestones:
        entries.append(
            {"date": milestone["date"], "tag": "milestone", "description": milestone["description"]}
        )

    entries.sort(key=lambda entry: entry["date"], reverse=True)
    return entries


def _compute_milestones(ordered_shows: list[dict]) -> list[dict]:
    """`ordered_shows`: chronologically ascending list of {id, event_date, length}. Flags a
    show as a milestone when it's a round-numbered concert (every 100th) or the longest
    setlist logged so far."""
    milestones = []
    longest_so_far = 0
    for index, show in enumerate(ordered_shows, start=1):
        if index % 100 == 0:
            milestones.append(
                {
                    "date": show["event_date"],
                    "description": f"{index}th logged concert.",
                }
            )
        if show["length"] > longest_so_far:
            longest_so_far = show["length"]
            if index > 1:  # the very first logged show is trivially "the longest so far"
                milestones.append(
                    {
                        "date": show["event_date"],
                        "description": f"Longest setlist yet — {show['length']} songs.",
                    }
                )
    return milestones


@router.get("/anecdotes")
def get_anecdotes(limit: int = 30, conn=Depends(get_conn)):
    db.ensure_songs_clustering_columns(conn)
    event_dates = {row["id"]: row["event_date"] for row in conn.execute("SELECT id, event_date FROM setlists")}
    song_names = {row["id"]: row["name"] for row in db.get_all_songs(conn)}

    song_plays = annotations.annotated_song_plays(conn)
    setlists_flagged = annotations.annotated_setlists(conn)

    length_by_setlist: dict[str, int] = {}
    for row in conn.execute("SELECT setlist_id, COUNT(*) AS c FROM setlist_songs GROUP BY setlist_id"):
        length_by_setlist[row["setlist_id"]] = row["c"]
    ordered_shows = [
        {"id": setlist_id, "event_date": event_date, "length": length_by_setlist.get(setlist_id, 0)}
        for setlist_id, event_date in sorted(event_dates.items(), key=lambda item: item[1])
    ]
    milestones = _compute_milestones(ordered_shows)

    entries = _build_anecdotes(song_plays, setlists_flagged, event_dates, song_names, milestones)
    return entries[:limit]


# ---------------------------------------------------------------------------
# Tours, covers, encores, the song map and cities all read tables the ingestion
# pipeline already fills but the API never exposed. Every figure below is a
# straight aggregate of stored rows -- nothing is modelled or estimated here.
# ---------------------------------------------------------------------------


@router.get("/tours")
def get_tours(conn=Depends(get_conn)):
    rows = conn.execute(
        """
        SELECT t.id, t.name, t.year_start, t.year_end,
               COUNT(DISTINCT s.id)        AS show_count,
               MIN(s.event_date)           AS date_start,
               MAX(s.event_date)           AS date_end,
               COUNT(DISTINCT s.venue_id)  AS venue_count,
               COUNT(DISTINCT v.country)   AS country_count
        FROM tours t
        LEFT JOIN setlists s ON s.tour_id = t.id
        LEFT JOIN venues v   ON v.id = s.venue_id
        GROUP BY t.id
        ORDER BY date_start
        """
    ).fetchall()

    # Average songs per show, per tour. Tape entries are intro/outro playback rather than
    # a performance, so they are excluded here exactly as they are in the length model.
    avg_rows = conn.execute(
        """
        SELECT s.tour_id, AVG(song_count) AS avg_songs
        FROM (
            SELECT ss.setlist_id, COUNT(*) AS song_count
            FROM setlist_songs ss
            WHERE ss.is_tape = 0
            GROUP BY ss.setlist_id
        ) counts
        JOIN setlists s ON s.id = counts.setlist_id
        WHERE s.tour_id IS NOT NULL
        GROUP BY s.tour_id
        """
    ).fetchall()
    avg_by_tour = {r["tour_id"]: r["avg_songs"] for r in avg_rows}

    # Distance is only known for consecutive shows where both venues geocoded, so the totals
    # below are a floor, not a full mileage. `legs_known` says how much of each tour it covers.
    db.ensure_derived_feature_tables(conn)
    travel_rows = conn.execute(
        """
        SELECT s.tour_id,
               SUM(f.travel_km)                                     AS total_km,
               MAX(f.travel_km)                                     AS longest_km,
               SUM(CASE WHEN f.travel_km IS NOT NULL THEN 1 ELSE 0 END) AS legs_known,
               COUNT(*)                                             AS legs_total
        FROM setlist_features f
        JOIN setlists s ON s.id = f.setlist_id
        WHERE s.tour_id IS NOT NULL
        GROUP BY s.tour_id
        """
    ).fetchall()
    travel_by_tour = {r["tour_id"]: r for r in travel_rows}

    return [
        {
            "tour_id": row["id"],
            "name": row["name"],
            "year_start": row["year_start"],
            "year_end": row["year_end"],
            "show_count": row["show_count"],
            "date_start": row["date_start"],
            "date_end": row["date_end"],
            "venue_count": row["venue_count"],
            "country_count": row["country_count"],
            "avg_songs": (
                round(avg_by_tour[row["id"]], 1) if row["id"] in avg_by_tour else None
            ),
            "travel_km": (
                round(travel_by_tour[row["id"]]["total_km"])
                if row["id"] in travel_by_tour and travel_by_tour[row["id"]]["total_km"] is not None
                else None
            ),
            "longest_hop_km": (
                round(travel_by_tour[row["id"]]["longest_km"])
                if row["id"] in travel_by_tour and travel_by_tour[row["id"]]["longest_km"] is not None
                else None
            ),
            "legs_known": travel_by_tour[row["id"]]["legs_known"] if row["id"] in travel_by_tour else 0,
            "legs_total": travel_by_tour[row["id"]]["legs_total"] if row["id"] in travel_by_tour else 0,
        }
        for row in rows
    ]


@router.get("/covers")
def get_covers(conn=Depends(get_conn)):
    rows = conn.execute(
        """
        SELECT a.id AS artist_id, a.name AS artist_name,
               COUNT(*)                     AS play_count,
               COUNT(DISTINCT ss.song_id)   AS song_count,
               MIN(sl.event_date)           AS first_played,
               MAX(sl.event_date)           AS last_played
        FROM setlist_songs ss
        JOIN artists a   ON a.id = ss.cover_artist_id
        JOIN setlists sl ON sl.id = ss.setlist_id
        WHERE ss.is_cover = 1
        GROUP BY a.id
        ORDER BY play_count DESC, a.name
        """
    ).fetchall()

    song_rows = conn.execute(
        """
        SELECT ss.cover_artist_id AS artist_id, s.name AS song_name, COUNT(*) AS play_count
        FROM setlist_songs ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.is_cover = 1 AND ss.cover_artist_id IS NOT NULL
        GROUP BY ss.cover_artist_id, s.id
        ORDER BY play_count DESC
        """
    ).fetchall()
    songs_by_artist: dict[str, list[dict]] = {}
    for row in song_rows:
        songs_by_artist.setdefault(row["artist_id"], []).append(
            {"song_name": row["song_name"], "play_count": row["play_count"]}
        )

    return [
        {
            "artist_id": row["artist_id"],
            "artist_name": row["artist_name"],
            "play_count": row["play_count"],
            "song_count": row["song_count"],
            "first_played": row["first_played"],
            "last_played": row["last_played"],
            "songs": songs_by_artist.get(row["artist_id"], []),
        }
        for row in rows
    ]


@router.get("/encores")
def get_encores(conn=Depends(get_conn)):
    rows = conn.execute(
        """
        SELECT s.id AS song_id, s.name AS song_name, COUNT(*) AS encore_count
        FROM setlist_songs ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.is_encore = 1
        GROUP BY s.id
        ORDER BY encore_count DESC, s.name
        """
    ).fetchall()

    totals = conn.execute(
        """
        SELECT
          (SELECT COUNT(DISTINCT setlist_id) FROM setlist_songs WHERE is_encore = 1) AS shows_with_encore,
          (SELECT COUNT(*) FROM setlists)                                            AS shows_total,
          (SELECT COUNT(*) FROM setlist_songs WHERE is_encore = 1)                   AS encore_entries
        """
    ).fetchone()

    shows_total = totals["shows_total"] or 0
    shows_with_encore = totals["shows_with_encore"] or 0
    return {
        "shows_with_encore": shows_with_encore,
        "shows_total": shows_total,
        "encore_entries": totals["encore_entries"] or 0,
        "encore_rate": round(shows_with_encore / shows_total, 4) if shows_total else None,
        "songs": [
            {
                "song_id": row["song_id"],
                "song_name": row["song_name"],
                "encore_count": row["encore_count"],
            }
            for row in rows
        ],
    }


@router.get("/song-map")
def get_song_map(conn=Depends(get_conn)):
    """The 2D song embedding the clustering pipeline already stores. x/y are the stored
    coordinates as-is; no projection is recomputed here."""
    rows = conn.execute(
        """
        SELECT sc.song_id, s.name AS song_name, sc.x, sc.y, sc.cluster_id,
               (SELECT COUNT(*) FROM setlist_songs ss WHERE ss.song_id = sc.song_id) AS play_count
        FROM song_clusters sc
        JOIN songs s ON s.id = sc.song_id
        ORDER BY play_count DESC
        """
    ).fetchall()
    return [
        {
            "song_id": row["song_id"],
            "song_name": row["song_name"],
            "x": row["x"],
            "y": row["y"],
            "cluster_id": row["cluster_id"],
            "play_count": row["play_count"],
        }
        for row in rows
    ]


@router.get("/cities")
def get_cities(conn=Depends(get_conn)):
    rows = conn.execute(
        """
        SELECT v.city, v.country,
               COUNT(s.id)                AS show_count,
               COUNT(DISTINCT v.id)       AS venue_count,
               MAX(s.event_date)          AS last_visited
        FROM venues v
        JOIN setlists s ON s.venue_id = v.id
        WHERE v.city IS NOT NULL AND v.city != ''
        GROUP BY v.city, v.country
        ORDER BY show_count DESC, v.city
        """
    ).fetchall()
    return [
        {
            "city": row["city"],
            "country": row["country"],
            "show_count": row["show_count"],
            "venue_count": row["venue_count"],
            "last_visited": row["last_visited"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Derived feature tables and heatmaps
#
# The heatmaps are plain cross-tabs of `setlist_songs`; the feature endpoints read the
# two derived tables, which `undercurrents.derived.cli build` recomputes from the same
# rows. Nothing here trains or infers anything.
# ---------------------------------------------------------------------------

HEATMAP_SONG_LIMIT = 40
COOCCURRENCE_SONG_LIMIT = 28
POSITION_BUCKETS = 10


@router.get("/song-features")
def get_song_features(conn=Depends(get_conn)):
    db.ensure_derived_feature_tables(conn)
    rows = conn.execute(
        """
        SELECT f.*, s.name AS song_name
        FROM song_features f
        JOIN songs s ON s.id = f.song_id
        ORDER BY f.play_count DESC
        """
    ).fetchall()
    return [
        {
            "song_id": r["song_id"],
            "song_name": r["song_name"],
            "play_count": r["play_count"],
            "show_count": r["show_count"],
            "first_played": r["first_played"],
            "last_played": r["last_played"],
            "longest_gap_days": r["longest_gap_days"],
            "current_streak": r["current_streak"],
            "opener_count": r["opener_count"],
            "closer_count": r["closer_count"],
            "encore_count": r["encore_count"],
            "cover_count": r["cover_count"],
            "avg_position_pct": r["avg_position_pct"],
            "dominant_era": r["dominant_era"],
        }
        for r in rows
    ]


@router.get("/setlist-features/summary")
def get_setlist_feature_summary(conn=Depends(get_conn)):
    db.ensure_derived_feature_tables(conn)
    row = conn.execute(
        """
        SELECT COUNT(*) AS shows,
               AVG(song_count)          AS avg_songs,
               AVG(encore_count)        AS avg_encores,
               AVG(novelty_rate)        AS avg_novelty,
               AVG(days_since_previous) AS avg_gap_days,
               AVG(travel_km)           AS avg_travel_km,
               SUM(travel_km)           AS total_travel_km,
               SUM(CASE WHEN travel_km IS NOT NULL THEN 1 ELSE 0 END) AS legs_known,
               SUM(cover_count)         AS covers,
               SUM(duration_complete)   AS shows_fully_timed
        FROM setlist_features
        """
    ).fetchone()
    if row is None or not row["shows"]:
        return {"shows": 0}

    # Novelty over time: how much a setlist changes from one show to the next, by year.
    by_year = conn.execute(
        """
        SELECT substr(event_date, 1, 4) AS year,
               AVG(novelty_rate) AS avg_novelty,
               AVG(song_count)   AS avg_songs,
               COUNT(*)          AS shows
        FROM setlist_features
        WHERE novelty_rate IS NOT NULL
        GROUP BY year
        ORDER BY year
        """
    ).fetchall()

    return {
        "shows": row["shows"],
        "avg_songs": round(row["avg_songs"], 2) if row["avg_songs"] is not None else None,
        "avg_encores": round(row["avg_encores"], 2) if row["avg_encores"] is not None else None,
        "avg_novelty": round(row["avg_novelty"], 4) if row["avg_novelty"] is not None else None,
        "avg_gap_days": round(row["avg_gap_days"], 1) if row["avg_gap_days"] is not None else None,
        "avg_travel_km": round(row["avg_travel_km"]) if row["avg_travel_km"] is not None else None,
        "total_travel_km": round(row["total_travel_km"]) if row["total_travel_km"] is not None else None,
        "legs_known": row["legs_known"] or 0,
        "covers": row["covers"] or 0,
        "shows_fully_timed": row["shows_fully_timed"] or 0,
        "by_year": [
            {
                "year": int(r["year"]),
                "avg_novelty": round(r["avg_novelty"], 4),
                "avg_songs": round(r["avg_songs"], 2),
                "shows": r["shows"],
            }
            for r in by_year
        ],
    }


@router.get("/heatmap/songs-by-year")
def get_songs_by_year(conn=Depends(get_conn)):
    """Rows are the most-played songs, columns are years, values are performance counts.
    Capped at the top songs so the grid stays legible and the payload small."""
    top = conn.execute(
        """
        SELECT ss.song_id, s.name AS song_name, COUNT(*) AS plays
        FROM setlist_songs ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.is_tape = 0
        GROUP BY ss.song_id
        ORDER BY plays DESC
        LIMIT ?
        """,
        (HEATMAP_SONG_LIMIT,),
    ).fetchall()
    song_ids = [r["song_id"] for r in top]
    if not song_ids:
        return {"songs": [], "years": [], "cells": []}

    placeholders = ",".join("?" for _ in song_ids)
    cells = conn.execute(
        f"""
        SELECT ss.song_id, CAST(substr(sl.event_date, 1, 4) AS INTEGER) AS year, COUNT(*) AS plays
        FROM setlist_songs ss
        JOIN setlists sl ON sl.id = ss.setlist_id
        WHERE ss.is_tape = 0 AND ss.song_id IN ({placeholders})
        GROUP BY ss.song_id, year
        """,
        song_ids,
    ).fetchall()

    years = sorted({c["year"] for c in cells})
    return {
        "songs": [{"song_id": r["song_id"], "song_name": r["song_name"], "plays": r["plays"]} for r in top],
        "years": years,
        "cells": [{"song_id": c["song_id"], "year": c["year"], "plays": c["plays"]} for c in cells],
    }


@router.get("/heatmap/calendar")
def get_calendar_heatmap(conn=Depends(get_conn)):
    """Shows per month per year: the touring calendar, including the empty stretches."""
    rows = conn.execute(
        """
        SELECT CAST(substr(event_date, 1, 4) AS INTEGER) AS year,
               CAST(substr(event_date, 6, 2) AS INTEGER) AS month,
               COUNT(*) AS shows
        FROM setlists
        GROUP BY year, month
        ORDER BY year, month
        """
    ).fetchall()
    years = sorted({r["year"] for r in rows})
    return {
        "years": years,
        "cells": [{"year": r["year"], "month": r["month"], "shows": r["shows"]} for r in rows],
    }


@router.get("/heatmap/song-positions")
def get_song_position_heatmap(conn=Depends(get_conn)):
    """Where each song lands within a show, as deciles of the running order. Position is
    normalised per show (first song = bucket 0, last = bucket 9) so shows of different
    lengths are comparable; encores therefore sit in the last buckets by construction."""
    rows = conn.execute(
        """
        SELECT ss.setlist_id, ss.song_id, ss.position
        FROM setlist_songs ss
        WHERE ss.is_tape = 0
        ORDER BY ss.setlist_id, ss.position
        """
    ).fetchall()

    by_show: dict[str, list] = {}
    for r in rows:
        by_show.setdefault(r["setlist_id"], []).append(r)

    counts: dict[tuple[int, int], int] = {}
    totals: dict[int, int] = {}
    for entries in by_show.values():
        n = len(entries)
        if n == 0:
            continue
        for index, entry in enumerate(entries):
            bucket = 0 if n == 1 else min(POSITION_BUCKETS - 1, int(index / n * POSITION_BUCKETS))
            key = (entry["song_id"], bucket)
            counts[key] = counts.get(key, 0) + 1
            totals[entry["song_id"]] = totals.get(entry["song_id"], 0) + 1

    top_ids = sorted(totals, key=lambda sid: totals[sid], reverse=True)[:HEATMAP_SONG_LIMIT]
    names = {r["id"]: r["name"] for r in db.get_all_songs(conn)}
    top_set = set(top_ids)
    return {
        "buckets": POSITION_BUCKETS,
        "songs": [
            {"song_id": sid, "song_name": names.get(sid, "Unknown"), "plays": totals[sid]}
            for sid in top_ids
        ],
        "cells": [
            {"song_id": sid, "bucket": bucket, "plays": plays}
            for (sid, bucket), plays in counts.items()
            if sid in top_set
        ],
    }


@router.get("/heatmap/cooccurrence")
def get_cooccurrence_heatmap(conn=Depends(get_conn)):
    """How often each pair of songs appears in the same setlist, for the most-played songs.
    The diagonal is each song's own show count, so a cell can be read against it."""
    top = conn.execute(
        """
        SELECT ss.song_id, s.name AS song_name, COUNT(DISTINCT ss.setlist_id) AS shows
        FROM setlist_songs ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.is_tape = 0
        GROUP BY ss.song_id
        ORDER BY shows DESC
        LIMIT ?
        """,
        (COOCCURRENCE_SONG_LIMIT,),
    ).fetchall()
    song_ids = [r["song_id"] for r in top]
    if not song_ids:
        return {"songs": [], "pairs": []}

    placeholders = ",".join("?" for _ in song_ids)
    rows = conn.execute(
        f"""
        SELECT a.song_id AS a_id, b.song_id AS b_id, COUNT(*) AS shows
        FROM setlist_songs a
        JOIN setlist_songs b
          ON b.setlist_id = a.setlist_id AND b.song_id > a.song_id
        WHERE a.is_tape = 0 AND b.is_tape = 0
          AND a.song_id IN ({placeholders}) AND b.song_id IN ({placeholders})
        GROUP BY a.song_id, b.song_id
        """,
        song_ids + song_ids,
    ).fetchall()

    return {
        "songs": [
            {"song_id": r["song_id"], "song_name": r["song_name"], "shows": r["shows"]}
            for r in top
        ],
        "pairs": [
            {"a_id": r["a_id"], "b_id": r["b_id"], "shows": r["shows"]} for r in rows
        ],
    }


@router.get("/night-notes")
def get_night_notes(conn=Depends(get_conn)):
    """Everything the archive records about what actually happened on a given night, as
    opposed to which songs were played: the shape of the show, who came on stage, and what
    the contributors wrote in the margin.

    All of it was already in the setlist.fm payloads and simply was not being read.
    """
    formats = [
        dict(row)
        for row in conn.execute(
            """
            SELECT set_name AS name,
                   COUNT(DISTINCT setlist_id) AS shows,
                   COUNT(*) AS songs
            FROM setlist_songs
            WHERE set_name IS NOT NULL
            GROUP BY set_name
            ORDER BY shows DESC, songs DESC
            """
        )
    ]

    guests = [
        dict(row)
        for row in conn.execute(
            """
            SELECT ss.guest_name AS guest,
                   s.name AS song_name,
                   sl.event_date,
                   v.city,
                   v.country
            FROM setlist_songs ss
            JOIN setlists sl ON sl.id = ss.setlist_id
            JOIN songs s ON s.id = ss.song_id
            LEFT JOIN venues v ON v.id = sl.venue_id
            WHERE ss.guest_name IS NOT NULL
            ORDER BY sl.event_date DESC
            """
        )
    ]

    try:
        flag_rows = conn.execute(
            """
            SELECT is_debut, is_long_awaited_return, is_jam, is_snippet, is_reprise,
                   is_instrumental, is_partial, is_solo, is_fan_request, is_dedication,
                   is_tour_debut, is_intro_outro, is_guest_mentioned, teases
            FROM performance_notes
            """
        ).fetchall()
    except Exception:
        # The notes table is built by a derived-features run; a database without it should
        # still serve the format and guest sections rather than failing outright.
        flag_rows = []

    flag_names = [
        "debut", "long_awaited_return", "jam", "snippet", "reprise", "instrumental",
        "partial", "solo", "fan_request", "dedication", "tour_debut", "intro_outro",
        "guest_mentioned",
    ]
    flags = [
        {"flag": name, "count": sum(1 for r in flag_rows if r[f"is_{name}"])}
        for name in flag_names
    ]
    flags.sort(key=lambda item: -item["count"])

    import json as _json

    tease_counts: dict[str, int] = {}
    for row in flag_rows:
        for title in _json.loads(row["teases"] or "[]"):
            tease_counts[title] = tease_counts.get(title, 0) + 1
    teases = [
        {"title": title, "count": count}
        for title, count in sorted(tease_counts.items(), key=lambda kv: -kv[1])
    ][:12]

    return {
        "formats": formats,
        "guests": guests,
        "flags": flags,
        "teases": teases,
        "notes_total": len(flag_rows),
    }


@router.get("/night-notes/debut-check")
def get_debut_check(conn=Depends(get_conn)):
    """How many "live debut" notes the archive itself backs up.

    A contributor's note is a claim; the performance history is evidence. Where they
    disagree, neither is assumed right: the archive thins out before about 2010, so an early
    contradiction may mean the note is correct and a show is missing. The point is that the
    disagreement is visible.
    """
    from undercurrents.derived import notes

    try:
        result = notes.verify_debuts(conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Performance notes have not been built yet")

    names = {row["id"]: row["name"] for row in db.get_all_songs(conn)}
    for contradiction in result["contradictions"]:
        contradiction["song_name"] = names.get(contradiction["song_id"], "unknown")
    return result


@router.get("/audio")
def get_audio(conn=Depends(get_conn)):
    """Tempo, key and loudness per song, plus how much of the catalogue they cover.

    Coverage is reported two ways on purpose. By song it looks thin, because the rare deep
    cuts and the 2025 album are missing: AcousticBrainz stopped accepting analyses in 2022,
    so nothing from Deadbeat will ever appear. By performance it is far higher, because what
    is missing is mostly what is rarely played.
    """
    from undercurrents.clustering import audio_features

    try:
        coverage = audio_features.coverage(conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Audio features have not been fetched yet")

    songs = [
        dict(row)
        for row in conn.execute(
            """
            SELECT s.name AS song_name, s.bpm, s.musical_key, s.musical_scale,
                   s.loudness, s.danceability, COUNT(ss.song_id) AS play_count
            FROM songs s
            JOIN setlist_songs ss ON ss.song_id = s.id AND ss.is_tape = 0
            WHERE s.bpm IS NOT NULL
            GROUP BY s.id
            ORDER BY s.bpm
            """
        )
    ]

    keys: dict[str, int] = {}
    for song in songs:
        if song["musical_key"]:
            label = f"{song['musical_key']} {song['musical_scale'] or ''}".strip()
            keys[label] = keys.get(label, 0) + 1

    # Average tempo by position in the set, over shows where every song is known. This is the
    # shape of a night, and it only means anything where the whole running order has a tempo.
    arc = [
        dict(row)
        for row in conn.execute(
            """
            SELECT ss.position, ROUND(AVG(s.bpm), 1) AS avg_bpm, COUNT(*) AS samples
            FROM setlist_songs ss
            JOIN songs s ON s.id = ss.song_id
            WHERE s.bpm IS NOT NULL AND ss.is_tape = 0 AND ss.position <= 24
            GROUP BY ss.position
            HAVING samples >= 20
            ORDER BY ss.position
            """
        )
    ]

    return {
        "coverage": coverage,
        "songs": songs,
        "keys": [{"key": k, "songs": n} for k, n in sorted(keys.items(), key=lambda kv: -kv[1])],
        "tempo_arc": arc,
        "source": "AcousticBrainz, frozen upstream since 2022",
    }


@router.get("/weather")
def get_weather(conn=Depends(get_conn)):
    """Weather at each show, and the only comparison it can honestly support.

    Coordinates are city-level and most shows are indoors, where the weather cannot plausibly
    change a setlist. So the figures are split by whether the venue is outdoors, and the
    indoor rows are there as a control rather than as a finding.
    """
    try:
        rows = conn.execute(
            """
            SELECT v.is_outdoor,
                   COUNT(*) AS shows,
                   ROUND(AVG(w.precipitation_mm), 2) AS avg_rain_mm,
                   ROUND(AVG(w.temp_max_c), 1) AS avg_temp_max_c,
                   ROUND(AVG(f.song_count), 2) AS avg_songs
            FROM show_weather w
            JOIN setlists sl ON sl.id = w.setlist_id
            JOIN venues v ON v.id = sl.venue_id
            LEFT JOIN setlist_features f ON f.setlist_id = sl.id
            WHERE v.is_outdoor IS NOT NULL
            GROUP BY v.is_outdoor
            """
        ).fetchall()
    except Exception:
        raise HTTPException(status_code=404, detail="Weather has not been fetched yet")

    covered = conn.execute("SELECT COUNT(*) FROM show_weather").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM setlists").fetchone()[0]

    wet_dry = [
        dict(row)
        for row in conn.execute(
            """
            SELECT CASE WHEN w.precipitation_mm >= 1.0 THEN 'wet' ELSE 'dry' END AS condition,
                   COUNT(*) AS shows,
                   ROUND(AVG(f.song_count), 2) AS avg_songs
            FROM show_weather w
            JOIN setlists sl ON sl.id = w.setlist_id
            JOIN venues v ON v.id = sl.venue_id
            JOIN setlist_features f ON f.setlist_id = sl.id
            WHERE v.is_outdoor = 1
            GROUP BY condition
            """
        )
    ]

    return {
        "shows_with_weather": covered,
        "shows_total": total,
        "by_venue_kind": [dict(row) for row in rows],
        "outdoor_wet_vs_dry": wet_dry,
        "caveat": (
            "City-level coordinates, and the outdoor split covers only the venues Wikidata "
            "could type. Indoor rows are a control, not a finding."
        ),
    }
