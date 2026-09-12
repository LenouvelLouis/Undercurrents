import numpy as np

from undercurrents.storage import db


def _resolve_canonical_id(song_id: int, canonical_map: dict[int, int]) -> int:
    seen = set()
    current = song_id
    while current in canonical_map:
        if current in seen:
            raise ValueError(f"Cycle detected resolving canonical song id for {song_id}")
        seen.add(current)
        current = canonical_map[current]
    return current


def build_canonical_song_map(conn) -> dict[int, int]:
    all_songs = db.get_all_songs(conn)
    canonical_map = {
        row["id"]: row["canonical_song_id"]
        for row in all_songs
        if row["canonical_song_id"] is not None
    }
    return {row["id"]: _resolve_canonical_id(row["id"], canonical_map) for row in all_songs}


def excluded_song_ids(conn) -> set[int]:
    return {row["id"] for row in db.get_all_songs(conn) if row["excluded_from_clustering"]}


def variant_song_ids(conn, canonical_song_id: int) -> list[int]:
    """All song ids that resolve to `canonical_song_id` via `songs.canonical_song_id`,
    including `canonical_song_id` itself. Use this instead of querying `setlist_songs` by a
    single song id directly, since a merged variant's plays are recorded under its own id."""
    canonical_map = build_canonical_song_map(conn)
    return [sid for sid, cid in canonical_map.items() if cid == canonical_song_id]


def build_setlist_song_matrix(conn):
    """Returns (setlist_ids, song_ids, matrix): matrix[i, j] = 1.0 if setlist setlist_ids[i]
    contains canonical song song_ids[j], after excluding non-song entries and merging
    alias/MusicBrainz duplicates. Setlists left with zero remaining songs are dropped."""
    canonical_map = build_canonical_song_map(conn)
    excluded = excluded_song_ids(conn)

    setlist_songs: dict[str, set[int]] = {}
    for entry in db.get_setlist_song_entries(conn):
        song_id = entry["song_id"]
        if song_id in excluded:
            continue
        canonical_id = canonical_map[song_id]
        if canonical_id in excluded:
            continue
        setlist_songs.setdefault(entry["setlist_id"], set()).add(canonical_id)

    setlist_songs = {sid: songs for sid, songs in setlist_songs.items() if songs}

    setlist_ids = sorted(setlist_songs)
    song_ids = sorted({song for songs in setlist_songs.values() for song in songs})
    song_index = {song_id: i for i, song_id in enumerate(song_ids)}

    matrix = np.zeros((len(setlist_ids), len(song_ids)), dtype=np.float64)
    for i, setlist_id in enumerate(setlist_ids):
        for song_id in setlist_songs[setlist_id]:
            matrix[i, song_index[song_id]] = 1.0

    return setlist_ids, song_ids, matrix


def build_song_cooccurrence_matrix(conn):
    """Returns (song_ids, matrix): matrix[i, j] = number of setlists containing both
    canonical song song_ids[i] and song_ids[j] (0 on the diagonal)."""
    _, song_ids, setlist_song_matrix = build_setlist_song_matrix(conn)
    cooccurrence = setlist_song_matrix.T @ setlist_song_matrix
    np.fill_diagonal(cooccurrence, 0)
    return song_ids, cooccurrence


def build_song_transition_matrix(conn):
    """Returns (song_ids, matrix): matrix[i, j] = number of times canonical song song_ids[i]
    was immediately followed by song_ids[j] within the same setlist (directed, not symmetric
    like co-occurrence). Excluded songs (intros/jams) are filtered out before computing
    adjacency, so they act as invisible connective tissue rather than breaking a transition
    between the two real songs surrounding them."""
    canonical_map = build_canonical_song_map(conn)
    excluded = excluded_song_ids(conn)

    ordered_by_setlist: dict[str, list[tuple[int, int]]] = {}
    for entry in db.get_setlist_song_entries(conn):
        song_id = entry["song_id"]
        if song_id in excluded:
            continue
        canonical_id = canonical_map[song_id]
        if canonical_id in excluded:
            continue
        ordered_by_setlist.setdefault(entry["setlist_id"], []).append(
            (entry["position"], canonical_id)
        )

    song_ids = sorted(
        {
            canonical_id
            for entries in ordered_by_setlist.values()
            for _, canonical_id in entries
        }
    )
    song_index = {song_id: i for i, song_id in enumerate(song_ids)}

    matrix = np.zeros((len(song_ids), len(song_ids)), dtype=np.float64)
    for entries in ordered_by_setlist.values():
        entries.sort(key=lambda item: item[0])
        for (_, from_id), (_, to_id) in zip(entries, entries[1:]):
            matrix[song_index[from_id], song_index[to_id]] += 1

    return song_ids, matrix
