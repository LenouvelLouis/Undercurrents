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
