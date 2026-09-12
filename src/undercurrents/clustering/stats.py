import math
from datetime import datetime

import numpy as np

from undercurrents.clustering.features import build_setlist_song_matrix

LEG_GAP_THRESHOLD_DAYS = 14


def consecutive_setlist_similarity(conn) -> list[dict]:
    """For each setlist in chronological order (using the same filtered/canonicalized song
    set as `build_setlist_song_matrix`), the Jaccard similarity of its song set with the
    immediately preceding setlist's. The first setlist has no predecessor and is omitted."""
    setlist_ids, _, matrix = build_setlist_song_matrix(conn)
    dates = {row["id"]: row["event_date"] for row in conn.execute("SELECT id, event_date FROM setlists")}

    order = sorted(range(len(setlist_ids)), key=lambda i: (dates[setlist_ids[i]], setlist_ids[i]))

    results = []
    previous_row = None
    for i in order:
        current_row = matrix[i] > 0
        if previous_row is not None:
            intersection = np.logical_and(current_row, previous_row).sum()
            union = np.logical_or(current_row, previous_row).sum()
            similarity = float(intersection / union) if union else 0.0
            results.append(
                {
                    "setlist_id": setlist_ids[i],
                    "event_date": dates[setlist_ids[i]],
                    "similarity_to_previous": similarity,
                }
            )
        previous_row = current_row
    return results


def _tour_leg_assignments(conn, tour_id: int) -> dict[str, tuple[int, int]]:
    """Maps each setlist id in `tour_id` to (leg_number, show_number_in_leg), both 1-indexed.
    A new leg starts whenever the gap since the previous chronological show in the tour
    exceeds LEG_GAP_THRESHOLD_DAYS days."""
    rows = conn.execute(
        "SELECT id, event_date FROM setlists WHERE tour_id = ? ORDER BY event_date, id",
        (tour_id,),
    ).fetchall()

    assignments: dict[str, tuple[int, int]] = {}
    leg = 1
    show_in_leg = 0
    previous_date = None
    for row in rows:
        current_date = datetime.strptime(row["event_date"], "%Y-%m-%d").date()
        if previous_date is not None and (current_date - previous_date).days > LEG_GAP_THRESHOLD_DAYS:
            leg += 1
            show_in_leg = 0
        show_in_leg += 1
        assignments[row["id"]] = (leg, show_in_leg)
        previous_date = current_date
    return assignments


def _setlist_tour_id(conn, setlist_id: str) -> int | None:
    row = conn.execute("SELECT tour_id FROM setlists WHERE id = ?", (setlist_id,)).fetchone()
    if row is None or row["tour_id"] is None:
        return None
    return row["tour_id"]


def tour_leg_number(conn, setlist_id: str) -> int | None:
    tour_id = _setlist_tour_id(conn, setlist_id)
    if tour_id is None:
        return None
    return _tour_leg_assignments(conn, tour_id)[setlist_id][0]


def show_number_in_leg(conn, setlist_id: str) -> int | None:
    tour_id = _setlist_tour_id(conn, setlist_id)
    if tour_id is None:
        return None
    return _tour_leg_assignments(conn, tour_id)[setlist_id][1]


def song_frequency_by_year(conn, canonical_song_id: int) -> dict[int, int]:
    rows = conn.execute(
        """
        SELECT substr(s.event_date, 1, 4) AS year, COUNT(*) AS c
        FROM setlist_songs ss
        JOIN setlists s ON s.id = ss.setlist_id
        WHERE ss.song_id = ?
        GROUP BY year ORDER BY year
        """,
        (canonical_song_id,),
    ).fetchall()
    return {int(row["year"]): row["c"] for row in rows}


def song_frequency_by_tour(conn, canonical_song_id: int) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT t.name AS tour_name, COUNT(*) AS c
        FROM setlist_songs ss
        JOIN setlists s ON s.id = ss.setlist_id
        LEFT JOIN tours t ON t.id = s.tour_id
        WHERE ss.song_id = ?
        GROUP BY t.name
        """,
        (canonical_song_id,),
    ).fetchall()
    return {row["tour_name"]: row["c"] for row in rows}


def average_relative_position(conn, canonical_song_id: int) -> float | None:
    """Average of position / setlist_length across every play of `canonical_song_id` — how
    far through the average set the song tends to fall (0 = always opens, 1 = always closes),
    comparable across eras with very different average setlist lengths."""
    rows = conn.execute(
        """
        SELECT ss.position,
               (SELECT COUNT(*) FROM setlist_songs ss2 WHERE ss2.setlist_id = ss.setlist_id) AS setlist_length
        FROM setlist_songs ss
        WHERE ss.song_id = ?
        """,
        (canonical_song_id,),
    ).fetchall()
    ratios = [row["position"] / row["setlist_length"] for row in rows if row["setlist_length"]]
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def _chronological_setlist_order(conn, setlist_ids: list[str]) -> list[int]:
    dates = {row["id"]: row["event_date"] for row in conn.execute("SELECT id, event_date FROM setlists")}
    return sorted(range(len(setlist_ids)), key=lambda i: (dates[setlist_ids[i]], setlist_ids[i]))


def current_consecutive_streak(conn, canonical_song_id: int) -> int:
    """Number of most-recent consecutive setlists (chronologically, using the same filtered
    song set as `build_setlist_song_matrix`) that include `canonical_song_id`, counting back
    from the most recent one. 0 if it wasn't played in the very last setlist (or never)."""
    setlist_ids, song_ids, matrix = build_setlist_song_matrix(conn)
    if canonical_song_id not in song_ids:
        return 0
    order = _chronological_setlist_order(conn, setlist_ids)
    col = song_ids.index(canonical_song_id)

    streak = 0
    for i in reversed(order):
        if matrix[i, col] > 0:
            streak += 1
        else:
            break
    return streak


def longest_consecutive_streak(conn, canonical_song_id: int) -> int:
    """The longest run of consecutive setlists (anywhere in the chronological history) that
    included `canonical_song_id`."""
    setlist_ids, song_ids, matrix = build_setlist_song_matrix(conn)
    if canonical_song_id not in song_ids:
        return 0
    order = _chronological_setlist_order(conn, setlist_ids)
    col = song_ids.index(canonical_song_id)

    longest = 0
    current = 0
    for i in order:
        if matrix[i, col] > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def show_number_in_tour(conn, setlist_id: str) -> int | None:
    """1-indexed chronological position of `setlist_id` within its tour, or `None` if the
    setlist doesn't exist or has no tour."""
    setlist = conn.execute(
        "SELECT event_date, tour_id FROM setlists WHERE id = ?", (setlist_id,)
    ).fetchone()
    if setlist is None or setlist["tour_id"] is None:
        return None

    row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM setlists
        WHERE tour_id = ?
          AND (event_date < ? OR (event_date = ? AND id <= ?))
        """,
        (setlist["tour_id"], setlist["event_date"], setlist["event_date"], setlist_id),
    ).fetchone()
    return row["c"]


def average_setlist_length_by_year(conn) -> dict[int, float]:
    """Average number of canonical-and-otherwise songs logged per setlist, by year. Setlists
    with zero `setlist_songs` rows are excluded — a known Phase 0 data gap (no setlist ever
    transcribed), not a real 0-song show, so counting them would understate typical length."""
    per_setlist_counts: dict[str, int] = {}
    for entry in conn.execute("SELECT setlist_id, COUNT(*) AS c FROM setlist_songs GROUP BY setlist_id"):
        per_setlist_counts[entry["setlist_id"]] = entry["c"]

    year_totals: dict[int, list[int]] = {}
    for row in conn.execute("SELECT id, event_date FROM setlists"):
        count = per_setlist_counts.get(row["id"])
        if count is None:
            continue
        year = int(row["event_date"][:4])
        year_totals.setdefault(year, []).append(count)

    return {year: sum(counts) / len(counts) for year, counts in sorted(year_totals.items())}


def cluster_song_entropy(conn) -> dict[int, float]:
    """Shannon entropy (base 2, bits) of each setlist cluster's song-frequency distribution —
    how varied (high) vs. predictable (low, dominated by a few staples) that era's song
    choices are, comparable across clusters."""
    cluster_rows = conn.execute("SELECT setlist_id, cluster_id FROM setlist_clusters").fetchall()
    if not cluster_rows:
        return {}

    setlist_to_cluster = {row["setlist_id"]: row["cluster_id"] for row in cluster_rows}
    cluster_song_counts: dict[int, dict[int, int]] = {}
    seen_pairs = set()
    for entry in conn.execute("SELECT setlist_id, song_id FROM setlist_songs"):
        setlist_id, song_id = entry["setlist_id"], entry["song_id"]
        if setlist_id not in setlist_to_cluster:
            continue
        pair = (setlist_id, song_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        cluster_id = setlist_to_cluster[setlist_id]
        cluster_song_counts.setdefault(cluster_id, {})
        cluster_song_counts[cluster_id][song_id] = cluster_song_counts[cluster_id].get(song_id, 0) + 1

    entropy_by_cluster = {}
    for cluster_id, song_counts in cluster_song_counts.items():
        total = sum(song_counts.values())
        entropy_by_cluster[cluster_id] = -sum(
            (count / total) * math.log2(count / total) for count in song_counts.values()
        )
    return entropy_by_cluster


def cluster_summary(conn, top_n: int = 5) -> list[dict]:
    """One row per setlist cluster: cluster_id, size, event_date range, and the song ids
    played in a higher share of that cluster's setlists than of all clustered setlists."""
    cluster_rows = conn.execute("SELECT setlist_id, cluster_id FROM setlist_clusters").fetchall()
    if not cluster_rows:
        return []

    setlist_to_cluster = {row["setlist_id"]: row["cluster_id"] for row in cluster_rows}
    dates = {row["id"]: row["event_date"] for row in conn.execute("SELECT id, event_date FROM setlists")}

    cluster_setlists: dict[int, set[str]] = {}
    for setlist_id, cluster_id in setlist_to_cluster.items():
        cluster_setlists.setdefault(cluster_id, set()).add(setlist_id)

    global_song_counts: dict[int, int] = {}
    cluster_song_counts: dict[int, dict[int, int]] = {}
    seen_pairs = set()
    for entry in conn.execute("SELECT setlist_id, song_id FROM setlist_songs"):
        setlist_id, song_id = entry["setlist_id"], entry["song_id"]
        if setlist_id not in setlist_to_cluster:
            continue
        pair = (setlist_id, song_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        global_song_counts[song_id] = global_song_counts.get(song_id, 0) + 1
        cluster_id = setlist_to_cluster[setlist_id]
        cluster_song_counts.setdefault(cluster_id, {})
        cluster_song_counts[cluster_id][song_id] = cluster_song_counts[cluster_id].get(song_id, 0) + 1

    total_setlists = len(setlist_to_cluster)
    summaries = []
    for cluster_id, setlists in sorted(cluster_setlists.items()):
        size = len(setlists)
        cluster_dates = [dates[sid] for sid in setlists]
        song_scores = []
        for song_id, count_in_cluster in cluster_song_counts.get(cluster_id, {}).items():
            share_in_cluster = count_in_cluster / size
            share_globally = global_song_counts[song_id] / total_setlists
            song_scores.append((song_id, share_in_cluster - share_globally))
        song_scores.sort(key=lambda item: item[1], reverse=True)

        summaries.append(
            {
                "cluster_id": cluster_id,
                "size": size,
                "date_start": min(cluster_dates),
                "date_end": max(cluster_dates),
                "top_song_ids": [song_id for song_id, _ in song_scores[:top_n]],
            }
        )
    return summaries
