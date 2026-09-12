from datetime import date, datetime

from undercurrents.clustering.features import build_canonical_song_map, excluded_song_ids
from undercurrents.storage import db

DATE_FORMAT = "%Y-%m-%d"


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def _ordered_setlists_with_songs(conn) -> list[dict]:
    """Setlists with >=1 canonical song, ordered chronologically. Each entry:
    {id, event_date (date), tour_id, cluster_id (or None), songs (set of canonical ids)}."""
    canonical_map = build_canonical_song_map(conn)
    excluded = excluded_song_ids(conn)

    songs_by_setlist: dict[str, set[int]] = {}
    for entry in db.get_setlist_song_entries(conn):
        song_id = entry["song_id"]
        if song_id in excluded:
            continue
        canonical_id = canonical_map[song_id]
        if canonical_id in excluded:
            continue
        songs_by_setlist.setdefault(entry["setlist_id"], set()).add(canonical_id)

    cluster_by_setlist = {
        row["setlist_id"]: row["cluster_id"]
        for row in conn.execute("SELECT setlist_id, cluster_id FROM setlist_clusters")
    }

    rows = conn.execute(
        "SELECT id, event_date, tour_id FROM setlists ORDER BY event_date, id"
    ).fetchall()

    result = []
    for row in rows:
        songs = songs_by_setlist.get(row["id"])
        if not songs:
            continue
        result.append(
            {
                "id": row["id"],
                "event_date": _parse_event_date(row["event_date"]),
                "tour_id": row["tour_id"],
                "cluster_id": cluster_by_setlist.get(row["id"]),
                "songs": songs,
            }
        )
    return result


def _accumulate_stats_before(setlists: list[dict], before_date: date | None) -> "RunningStats":
    stats = RunningStats()
    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        stats.observe(setlist)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[int]]:
    """Walks setlists chronologically (stopping before `before_date` if given). For each
    setlist and each canonical song already seen in an earlier setlist, emits one
    leakage-free feature row and its label (1 if that song was played here, else 0)."""
    setlists = _ordered_setlists_with_songs(conn)
    stats = RunningStats()
    rows: list[dict] = []
    labels: list[int] = []

    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        for song_id in sorted(stats.known_song_ids()):
            rows.append(stats.features_for(song_id, setlist["tour_id"], setlist["event_date"]))
            labels.append(1 if song_id in setlist["songs"] else 0)
        stats.observe(setlist)

    return rows, labels


def build_prediction_features(
    conn, reference_date: date, tour_id: int | None = None
) -> dict[int, dict]:
    """Feature row per canonical song already seen strictly before `reference_date` — the
    input `model.py` needs to score candidates for the *next* show."""
    setlists = _ordered_setlists_with_songs(conn)
    stats = _accumulate_stats_before(setlists, reference_date)
    return {
        song_id: stats.features_for(song_id, tour_id, reference_date)
        for song_id in stats.known_song_ids()
    }


class RunningStats:
    """Accumulates, in chronological order, everything needed to compute leakage-free
    features for the *next* setlist without re-scanning history on every call. Feed
    setlists to `observe` in ascending `event_date` order; call `features_for` in between
    observations to get features computed only from setlists observed so far."""

    def __init__(self):
        self.setlists_seen = 0
        self.global_count: dict = {}
        self.tour_setlists: dict = {}
        self.tour_count: dict = {}
        self.cluster_setlists: dict = {}
        self.cluster_count: dict = {}
        self.last_seen_index: dict = {}
        self.last_seen_date: dict = {}
        self.last_cluster_id = None

    def known_song_ids(self) -> set:
        return set(self.global_count)

    def features_for(self, song_id, tour_id, current_date) -> dict:
        global_frequency = (
            self.global_count.get(song_id, 0) / self.setlists_seen if self.setlists_seen else 0.0
        )

        if tour_id is not None and self.tour_setlists.get(tour_id, 0) > 0:
            tour_frequency = self.tour_count.get((tour_id, song_id), 0) / self.tour_setlists[tour_id]
        else:
            tour_frequency = global_frequency

        if self.last_cluster_id is not None and self.cluster_setlists.get(self.last_cluster_id, 0) > 0:
            cluster_frequency = (
                self.cluster_count.get((self.last_cluster_id, song_id), 0)
                / self.cluster_setlists[self.last_cluster_id]
            )
        else:
            cluster_frequency = global_frequency

        if song_id in self.last_seen_index:
            shows_since_last_played = float(self.setlists_seen - self.last_seen_index[song_id])
            days_since_last_played = float((current_date - self.last_seen_date[song_id]).days)
        else:
            shows_since_last_played = None
            days_since_last_played = None

        return {
            "global_frequency": global_frequency,
            "tour_frequency": tour_frequency,
            "cluster_frequency": cluster_frequency,
            "shows_since_last_played": shows_since_last_played,
            "days_since_last_played": days_since_last_played,
        }

    def observe(self, setlist: dict) -> None:
        tour_id = setlist["tour_id"]
        cluster_id = setlist["cluster_id"]

        if tour_id is not None:
            self.tour_setlists[tour_id] = self.tour_setlists.get(tour_id, 0) + 1
        if cluster_id is not None:
            self.cluster_setlists[cluster_id] = self.cluster_setlists.get(cluster_id, 0) + 1

        for song_id in setlist["songs"]:
            self.global_count[song_id] = self.global_count.get(song_id, 0) + 1
            if tour_id is not None:
                key = (tour_id, song_id)
                self.tour_count[key] = self.tour_count.get(key, 0) + 1
            if cluster_id is not None:
                ckey = (cluster_id, song_id)
                self.cluster_count[ckey] = self.cluster_count.get(ckey, 0) + 1
            self.last_seen_index[song_id] = self.setlists_seen + 1
            self.last_seen_date[song_id] = setlist["event_date"]

        self.setlists_seen += 1
        if cluster_id is not None:
            self.last_cluster_id = cluster_id
