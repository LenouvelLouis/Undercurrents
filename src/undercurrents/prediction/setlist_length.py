from collections import deque
from datetime import date, datetime

import numpy as np
from sklearn.linear_model import Ridge

from undercurrents.prediction.features import _is_holiday_flag

DATE_FORMAT = "%Y-%m-%d"
RECENT_WINDOW = 5

FEATURE_ORDER = [
    "recent_avg_length",
    "global_avg_length",
    "tour_avg_length",
    "country_avg_length",
    "cluster_avg_length",
    "show_number_in_tour",
    "days_since_last_show",
    "is_holiday",
]


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def _ordered_setlists_with_length(conn) -> list[dict]:
    """Setlists ordered chronologically, with raw `setlist_songs` row counts (intros/tape/
    covers included -- matches `clustering/stats.py`'s `average_setlist_length_by_year`, a
    different definition than `prediction/features.py`'s canonicalized song-set count).
    Setlists with zero `setlist_songs` rows are excluded (a Phase 0 data gap, not a real
    0-song show). Each entry: {id, event_date (date), tour_id, cluster_id (or None),
    country (or None), length (int)}."""
    counts = {
        row["setlist_id"]: row["c"]
        for row in conn.execute(
            "SELECT setlist_id, COUNT(*) AS c FROM setlist_songs GROUP BY setlist_id"
        )
    }
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
        length = counts.get(row["id"])
        if not length:
            continue
        result.append(
            {
                "id": row["id"],
                "event_date": _parse_event_date(row["event_date"]),
                "tour_id": row["tour_id"],
                "cluster_id": cluster_by_setlist.get(row["id"]),
                "country": row["country"],
                "length": length,
            }
        )
    return result


class LengthStats:
    """Accumulates, in chronological order, everything needed to compute leakage-free
    setlist-length features for the *next* show. Feed setlists to `observe` in ascending
    `event_date` order; call `features_for` in between observations to get features computed
    only from setlists observed so far."""

    def __init__(self):
        self.recent_lengths = deque(maxlen=RECENT_WINDOW)
        self.global_total_length = 0
        self.global_count = 0
        self.tour_total_length: dict = {}
        self.tour_count: dict = {}
        self.country_total_length: dict = {}
        self.country_count: dict = {}
        self.cluster_total_length: dict = {}
        self.cluster_count: dict = {}
        self.last_cluster_id = None
        self.last_event_date = None

    def _global_avg(self) -> float:
        return self.global_total_length / self.global_count if self.global_count else 0.0

    def features_for(self, tour_id, current_date, country=None) -> dict:
        global_avg_length = self._global_avg()
        recent_avg_length = (
            sum(self.recent_lengths) / len(self.recent_lengths)
            if self.recent_lengths
            else global_avg_length
        )

        if tour_id is not None and self.tour_count.get(tour_id, 0) > 0:
            tour_avg_length = self.tour_total_length[tour_id] / self.tour_count[tour_id]
        else:
            tour_avg_length = global_avg_length

        if country is not None and self.country_count.get(country, 0) > 0:
            country_avg_length = self.country_total_length[country] / self.country_count[country]
        else:
            country_avg_length = global_avg_length

        if self.last_cluster_id is not None and self.cluster_count.get(self.last_cluster_id, 0) > 0:
            cluster_avg_length = (
                self.cluster_total_length[self.last_cluster_id]
                / self.cluster_count[self.last_cluster_id]
            )
        else:
            cluster_avg_length = global_avg_length

        show_number_in_tour = (
            float(self.tour_count.get(tour_id, 0) + 1) if tour_id is not None else 0.0
        )
        days_since_last_show = (
            float((current_date - self.last_event_date).days)
            if self.last_event_date is not None
            else 0.0
        )

        return {
            "recent_avg_length": recent_avg_length,
            "global_avg_length": global_avg_length,
            "tour_avg_length": tour_avg_length,
            "country_avg_length": country_avg_length,
            "cluster_avg_length": cluster_avg_length,
            "show_number_in_tour": show_number_in_tour,
            "days_since_last_show": days_since_last_show,
            "is_holiday": _is_holiday_flag(country, current_date),
        }

    def observe(self, setlist: dict) -> None:
        tour_id = setlist["tour_id"]
        cluster_id = setlist["cluster_id"]
        country = setlist["country"]
        length = setlist["length"]

        self.recent_lengths.append(length)
        self.global_total_length += length
        self.global_count += 1

        if tour_id is not None:
            self.tour_total_length[tour_id] = self.tour_total_length.get(tour_id, 0) + length
            self.tour_count[tour_id] = self.tour_count.get(tour_id, 0) + 1
        if country is not None:
            self.country_total_length[country] = self.country_total_length.get(country, 0) + length
            self.country_count[country] = self.country_count.get(country, 0) + 1
        if cluster_id is not None:
            self.cluster_total_length[cluster_id] = self.cluster_total_length.get(cluster_id, 0) + length
            self.cluster_count[cluster_id] = self.cluster_count.get(cluster_id, 0) + 1
            self.last_cluster_id = cluster_id

        self.last_event_date = setlist["event_date"]


def _accumulate_stats_before(setlists: list[dict], before_date: date | None) -> "LengthStats":
    stats = LengthStats()
    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        stats.observe(setlist)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[float]]:
    """Walks setlists chronologically (stopping before `before_date` if given). Emits one
    leakage-free feature row and label (the actual length) per setlist, including the first
    (whose features are all fallback zeros -- one degenerate row is negligible noise against
    ~700 real setlists)."""
    setlists = _ordered_setlists_with_length(conn)
    stats = LengthStats()
    rows: list[dict] = []
    labels: list[float] = []

    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        row = stats.features_for(setlist["tour_id"], setlist["event_date"], country=setlist["country"])
        rows.append(row)
        labels.append(float(setlist["length"]))
        stats.observe(setlist)

    return rows, labels


def build_prediction_features(
    conn, reference_date: date, tour_id: int | None = None, country: str | None = None
) -> dict:
    """Feature row for the next show at `reference_date`, from setlists strictly before it."""
    setlists = _ordered_setlists_with_length(conn)
    stats = _accumulate_stats_before(setlists, reference_date)
    return stats.features_for(tour_id, reference_date, country=country)


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[float]) -> Ridge:
    model = Ridge()
    model.fit(_to_matrix(rows), np.array(labels))
    return model


def predict(model: Ridge, features: dict) -> float:
    return float(model.predict(_to_matrix([features]))[0])
