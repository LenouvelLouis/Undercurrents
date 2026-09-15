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
