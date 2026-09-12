"""Deterministic keyword-based mining of the free-text `info` fields captured from setlist.fm
(per-song on `setlist_songs.info`, per-concert on `setlists.info`). Keywords were chosen
against real samples from the dataset (see the Phase-post-3 feature-enrichment notes in
CLAUDE.md) — a keyword miss is a false negative (flag stays False), never a false positive,
by construction of the substring checks below."""

SONG_DEBUT_KEYWORDS = ["debut"]
FAN_REQUEST_KEYWORDS = ["fan request", "fan's request", "requested by a fan"]
TEASE_KEYWORDS = ["tease"]
EXTENDED_KEYWORDS = ["extended"]
RESTARTED_KEYWORDS = ["restart"]

SETLIST_INCOMPLETE_KEYWORDS = ["incomplete"]
SETLIST_OUT_OF_ORDER_KEYWORDS = ["out of order"]
SETLIST_DISRUPTED_KEYWORDS = ["cancelled", "canceled", "cut short", "aborted"]


def classify_song_info(info: str | None) -> dict[str, bool]:
    lowered = (info or "").lower()
    return {
        "is_debut": any(keyword in lowered for keyword in SONG_DEBUT_KEYWORDS),
        "is_fan_request": any(keyword in lowered for keyword in FAN_REQUEST_KEYWORDS),
        "has_tease": any(keyword in lowered for keyword in TEASE_KEYWORDS),
        "was_extended": any(keyword in lowered for keyword in EXTENDED_KEYWORDS),
        "was_restarted": any(keyword in lowered for keyword in RESTARTED_KEYWORDS),
    }


def classify_setlist_info(info: str | None) -> dict[str, bool]:
    lowered = (info or "").lower()
    return {
        "is_incomplete": any(keyword in lowered for keyword in SETLIST_INCOMPLETE_KEYWORDS),
        "is_out_of_order": any(keyword in lowered for keyword in SETLIST_OUT_OF_ORDER_KEYWORDS),
        "was_disrupted": any(keyword in lowered for keyword in SETLIST_DISRUPTED_KEYWORDS),
    }


def annotated_song_plays(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT setlist_id, song_id, position, info FROM setlist_songs"
    ).fetchall()
    return [
        {
            "setlist_id": row["setlist_id"],
            "song_id": row["song_id"],
            "position": row["position"],
            "info": row["info"],
            **classify_song_info(row["info"]),
        }
        for row in rows
    ]


def annotated_setlists(conn) -> list[dict]:
    rows = conn.execute("SELECT id, info FROM setlists").fetchall()
    return [
        {"setlist_id": row["id"], "info": row["info"], **classify_setlist_info(row["info"])}
        for row in rows
    ]


def flag_counts(conn) -> dict[str, dict[str, int]]:
    song_plays = annotated_song_plays(conn)
    setlists = annotated_setlists(conn)

    song_flag_names = ["is_debut", "is_fan_request", "has_tease", "was_extended", "was_restarted"]
    setlist_flag_names = ["is_incomplete", "is_out_of_order", "was_disrupted"]

    return {
        "song": {
            flag: sum(1 for play in song_plays if play[flag]) for flag in song_flag_names
        },
        "setlist": {
            flag: sum(1 for setlist in setlists if setlist[flag]) for flag in setlist_flag_names
        },
    }
