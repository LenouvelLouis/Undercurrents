import math
from datetime import date, datetime

from undercurrents.clustering import calendar_features
from undercurrents.clustering.features import build_canonical_song_map, excluded_song_ids
from undercurrents.storage import db

DATE_FORMAT = "%Y-%m-%d"


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def _duration_minutes_by_song(conn) -> dict[int, float]:
    """Song id -> duration in minutes for every canonical song, imputing the mean of known
    durations (0.0 if none are known) for songs without one — a null shouldn't look like
    "zero minutes long" to the model."""
    known_ms = db.get_song_durations_ms(conn)
    mean_minutes = (sum(known_ms.values()) / len(known_ms) / 60000.0) if known_ms else 0.0
    return {
        row["id"]: known_ms[row["id"]] / 60000.0 if row["id"] in known_ms else mean_minutes
        for row in db.get_all_songs(conn)
    }


def _is_holiday_flag(country: str | None, event_date: date) -> float:
    if country is None:
        return 0.0
    return 1.0 if calendar_features.is_holiday(country, event_date) else 0.0


def _ordered_setlists_with_songs(conn) -> list[dict]:
    """Setlists with >=1 canonical song, ordered chronologically. Each entry:
    {id, event_date (date), tour_id, cluster_id (or None), country (or None),
    songs (set of canonical ids)}."""
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
        """
        SELECT s.id, s.event_date, s.tour_id, v.country
        FROM setlists s LEFT JOIN venues v ON v.id = s.venue_id
        ORDER BY s.event_date, s.id
        """
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
                "country": row["country"],
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
    duration_by_song = _duration_minutes_by_song(conn)
    rows: list[dict] = []
    labels: list[int] = []

    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        for song_id in sorted(stats.known_song_ids()):
            row = stats.features_for(
                song_id, setlist["tour_id"], setlist["event_date"], country=setlist["country"]
            )
            row["is_holiday"] = _is_holiday_flag(setlist["country"], setlist["event_date"])
            row["duration_minutes"] = duration_by_song[song_id]
            rows.append(row)
            labels.append(1 if song_id in setlist["songs"] else 0)
        stats.observe(setlist)

    return rows, labels


def build_prediction_features(
    conn, reference_date: date, tour_id: int | None = None, country: str | None = None
) -> dict[int, dict]:
    """Feature row per canonical song already seen strictly before `reference_date` — the
    input `model.py` needs to score candidates for the *next* show."""
    setlists = _ordered_setlists_with_songs(conn)
    stats = _accumulate_stats_before(setlists, reference_date)
    duration_by_song = _duration_minutes_by_song(conn)
    is_holiday = _is_holiday_flag(country, reference_date)

    result = {}
    for song_id in stats.known_song_ids():
        row = stats.features_for(song_id, tour_id, reference_date, country=country)
        row["is_holiday"] = is_holiday
        row["duration_minutes"] = duration_by_song[song_id]
        result[song_id] = row
    return result


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
        self.country_setlists: dict = {}
        self.country_count: dict = {}
        self.current_streak: dict = {}
        self.last_seen_index: dict = {}
        self.last_seen_date: dict = {}
        self.last_cluster_id = None

    def known_song_ids(self) -> set:
        return set(self.global_count)

    def _current_cluster_entropy(self) -> float:
        if self.last_cluster_id is None:
            return 0.0
        counts = [
            count
            for (cluster_id, _song_id), count in self.cluster_count.items()
            if cluster_id == self.last_cluster_id
        ]
        total = sum(counts)
        if total == 0:
            return 0.0
        return -sum((count / total) * math.log2(count / total) for count in counts)

    def features_for(self, song_id, tour_id, current_date, country=None) -> dict:
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

        if country is not None and self.country_setlists.get(country, 0) > 0:
            country_frequency = (
                self.country_count.get((country, song_id), 0) / self.country_setlists[country]
            )
        else:
            country_frequency = global_frequency

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
            "country_frequency": country_frequency,
            "shows_since_last_played": shows_since_last_played,
            "days_since_last_played": days_since_last_played,
            "current_streak": float(self.current_streak.get(song_id, 0)),
            "cluster_entropy": self._current_cluster_entropy(),
        }

    def observe(self, setlist: dict) -> None:
        tour_id = setlist["tour_id"]
        cluster_id = setlist["cluster_id"]
        country = setlist.get("country")
        played = setlist["songs"]

        previously_known = set(self.global_count)
        for song_id in previously_known:
            self.current_streak[song_id] = (
                self.current_streak.get(song_id, 0) + 1 if song_id in played else 0
            )

        if tour_id is not None:
            self.tour_setlists[tour_id] = self.tour_setlists.get(tour_id, 0) + 1
        if cluster_id is not None:
            self.cluster_setlists[cluster_id] = self.cluster_setlists.get(cluster_id, 0) + 1
        if country is not None:
            self.country_setlists[country] = self.country_setlists.get(country, 0) + 1

        for song_id in played:
            self.global_count[song_id] = self.global_count.get(song_id, 0) + 1
            if song_id not in previously_known:
                self.current_streak[song_id] = 1
            if tour_id is not None:
                key = (tour_id, song_id)
                self.tour_count[key] = self.tour_count.get(key, 0) + 1
            if cluster_id is not None:
                ckey = (cluster_id, song_id)
                self.cluster_count[ckey] = self.cluster_count.get(ckey, 0) + 1
            if country is not None:
                country_key = (country, song_id)
                self.country_count[country_key] = self.country_count.get(country_key, 0) + 1
            self.last_seen_index[song_id] = self.setlists_seen + 1
            self.last_seen_date[song_id] = setlist["event_date"]

        self.setlists_seen += 1
        if cluster_id is not None:
            self.last_cluster_id = cluster_id
