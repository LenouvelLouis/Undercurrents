from datetime import date, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression

DATE_FORMAT = "%Y-%m-%d"

FEATURE_ORDER = [
    "country_frequency",
    "tour_country_frequency",
    "is_last_show_country",
    "current_country_streak",
    "days_since_country_last_visited",
    "shows_since_country_last_visited",
]


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def _ordered_setlists_with_country(conn) -> list[dict]:
    """Every setlist with a known venue country, chronologically ordered (ties broken by
    id). Each entry: {id, event_date (date), tour_id, country}. No song-content filtering --
    a show's location is known regardless of whether its setlist content was ever
    transcribed (same reasoning as `next_show_date.py`'s show population)."""
    rows = conn.execute(
        """
        SELECT s.id, s.event_date, s.tour_id, v.country
        FROM setlists s LEFT JOIN venues v ON v.id = s.venue_id
        WHERE v.country IS NOT NULL
        ORDER BY s.event_date, s.id
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "event_date": _parse_event_date(row["event_date"]),
            "tour_id": row["tour_id"],
            "country": row["country"],
        }
        for row in rows
    ]


class CountryStats:
    """Accumulates, in chronological order, everything needed to compute leakage-free
    country features for the *next* show. Feed setlists to `observe` in ascending
    `event_date` order; call `features_for` in between observations to get features
    computed only from setlists observed so far. `features_for` must only be called for a
    country already in `known_country_ids()` -- recency features assume the country has
    been observed at least once."""

    def __init__(self):
        self.setlists_seen = 0
        self.global_count: dict = {}
        self.tour_setlists: dict = {}
        self.tour_count: dict = {}
        self.last_seen_index: dict = {}
        self.last_seen_date: dict = {}
        self.current_streak: dict = {}
        self.last_country: str | None = None

    def known_country_ids(self) -> set:
        return set(self.global_count)

    def features_for(self, country, tour_id, current_date) -> dict:
        country_frequency = (
            self.global_count.get(country, 0) / self.setlists_seen if self.setlists_seen else 0.0
        )

        if tour_id is not None and self.tour_setlists.get(tour_id, 0) > 0:
            tour_country_frequency = (
                self.tour_count.get((tour_id, country), 0) / self.tour_setlists[tour_id]
            )
        else:
            tour_country_frequency = country_frequency

        return {
            "country_frequency": country_frequency,
            "tour_country_frequency": tour_country_frequency,
            "is_last_show_country": 1.0 if country == self.last_country else 0.0,
            "current_country_streak": float(self.current_streak.get(country, 0)),
            "days_since_country_last_visited": float(
                (current_date - self.last_seen_date[country]).days
            ),
            "shows_since_country_last_visited": float(
                self.setlists_seen - self.last_seen_index[country]
            ),
        }

    def observe(self, setlist: dict) -> None:
        tour_id = setlist["tour_id"]
        country = setlist["country"]

        previously_known = set(self.global_count)
        for known_country in previously_known:
            self.current_streak[known_country] = (
                self.current_streak.get(known_country, 0) + 1
                if known_country == country
                else 0
            )
        if country not in previously_known:
            self.current_streak[country] = 1

        self.global_count[country] = self.global_count.get(country, 0) + 1
        if tour_id is not None:
            self.tour_setlists[tour_id] = self.tour_setlists.get(tour_id, 0) + 1
            key = (tour_id, country)
            self.tour_count[key] = self.tour_count.get(key, 0) + 1

        self.last_seen_index[country] = self.setlists_seen + 1
        self.last_seen_date[country] = setlist["event_date"]
        self.setlists_seen += 1
        self.last_country = country


def _accumulate_stats_before(setlists: list[dict], before_date: date | None) -> "CountryStats":
    stats = CountryStats()
    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        stats.observe(setlist)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[int]]:
    """Walks setlists chronologically (stopping before `before_date` if given). For each
    setlist and each country already known (observed in an earlier setlist, iterated in
    sorted order for determinism), emits one leakage-free feature row and its label (1 if
    that country is this setlist's actual country, else 0), then observes the setlist."""
    setlists = _ordered_setlists_with_country(conn)
    stats = CountryStats()
    rows: list[dict] = []
    labels: list[int] = []

    for setlist in setlists:
        if before_date is not None and setlist["event_date"] >= before_date:
            break
        for country in sorted(stats.known_country_ids()):
            row = stats.features_for(country, setlist["tour_id"], setlist["event_date"])
            rows.append(row)
            labels.append(1 if country == setlist["country"] else 0)
        stats.observe(setlist)

    return rows, labels


def build_prediction_features(
    conn, reference_date: date, tour_id: int | None = None
) -> dict[str, dict]:
    """Feature row per country already known strictly before `reference_date` -- the input
    `predict_proba` needs to score candidates for the next show."""
    setlists = _ordered_setlists_with_country(conn)
    stats = _accumulate_stats_before(setlists, reference_date)

    return {
        country: stats.features_for(country, tour_id, reference_date)
        for country in stats.known_country_ids()
    }


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[int]) -> LogisticRegression:
    model = LogisticRegression(max_iter=1000)
    model.fit(_to_matrix(rows), np.array(labels))
    return model


def predict_proba(model: LogisticRegression, feature_dicts_by_country: dict[str, dict]) -> dict[str, float]:
    countries = list(feature_dicts_by_country)
    matrix = _to_matrix([feature_dicts_by_country[country] for country in countries])
    positive_class_index = list(model.classes_).index(1)
    probabilities = model.predict_proba(matrix)[:, positive_class_index]
    return dict(zip(countries, probabilities))
