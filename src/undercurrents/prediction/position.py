from collections import deque
from datetime import date, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression

from undercurrents.clustering.features import build_canonical_song_map, excluded_song_ids
from undercurrents.storage import db

DATE_FORMAT = "%Y-%m-%d"
RECENT_WINDOW = 20

FEATURE_ORDER = [
    "own_opener_rate",
    "own_closer_rate",
    "own_encore_rate",
    "recent_own_opener_rate",
    "recent_own_closer_rate",
    "recent_own_encore_rate",
    "global_opener_rate",
    "global_closer_rate",
    "global_encore_rate",
    "times_played_before",
    "days_since_last_played",
]


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def _categorize(position: int, max_position: int, is_encore: bool) -> str:
    """Priority encore > opener > closer > mid -- verified against real data, where a show's
    last song is an encore song 56% of the time (see the design spec's Context section)."""
    if is_encore:
        return "encore"
    if position == 1:
        return "opener"
    if position == max_position:
        return "closer"
    return "mid"


def _ordered_song_plays(conn) -> list[dict]:
    """Chronologically ordered plays of canonicalized, non-excluded songs. `max_position` for
    `_categorize` is computed from each setlist's full, unfiltered `setlist_songs` entries
    before the canonicalization/exclusion filter is applied to individual rows -- so a
    trailing excluded entry (e.g. a tape outro) doesn't wrongly promote the real last song.
    Each entry: {setlist_id, event_date (date), song_id (canonical), category}."""
    canonical_map = build_canonical_song_map(conn)
    excluded = excluded_song_ids(conn)

    entries_by_setlist: dict[str, list] = {}
    for entry in db.get_setlist_song_entries(conn):
        entries_by_setlist.setdefault(entry["setlist_id"], []).append(entry)

    setlists = conn.execute(
        "SELECT id, event_date FROM setlists ORDER BY event_date, id"
    ).fetchall()

    result = []
    for setlist in setlists:
        entries = entries_by_setlist.get(setlist["id"])
        if not entries:
            continue
        max_position = max(entry["position"] for entry in entries)
        event_date = _parse_event_date(setlist["event_date"])

        for entry in entries:
            song_id = entry["song_id"]
            if song_id in excluded:
                continue
            canonical_id = canonical_map[song_id]
            if canonical_id in excluded:
                continue
            category = _categorize(entry["position"], max_position, bool(entry["is_encore"]))
            result.append(
                {
                    "setlist_id": setlist["id"],
                    "event_date": event_date,
                    "song_id": canonical_id,
                    "category": category,
                }
            )
    return result


class PositionStats:
    """Accumulates, in chronological order, everything needed to compute leakage-free
    position-category features for the *next* time a given song is played. Feed plays to
    `observe` in ascending `event_date` order; call `features_for` in between observations."""

    def __init__(self):
        self.own_category_count: dict = {}
        self.own_total: dict = {}
        self.own_recent_categories: dict = {}
        self.own_last_played_date: dict = {}
        self.global_category_count: dict = {}
        self.global_total = 0

    def _global_rate(self, category: str) -> float:
        return self.global_category_count.get(category, 0) / self.global_total if self.global_total else 0.0

    def features_for(self, song_id, current_date) -> dict:
        own_total = self.own_total.get(song_id, 0)
        recent = self.own_recent_categories.get(song_id)

        def own_rate(category: str) -> float:
            if own_total == 0:
                return self._global_rate(category)
            return self.own_category_count.get((song_id, category), 0) / own_total

        def recent_own_rate(category: str) -> float:
            if not recent:
                return self._global_rate(category)
            return sum(1 for c in recent if c == category) / len(recent)

        days_since_last_played = (
            float((current_date - self.own_last_played_date[song_id]).days)
            if song_id in self.own_last_played_date
            else 0.0
        )

        return {
            "own_opener_rate": own_rate("opener"),
            "own_closer_rate": own_rate("closer"),
            "own_encore_rate": own_rate("encore"),
            "recent_own_opener_rate": recent_own_rate("opener"),
            "recent_own_closer_rate": recent_own_rate("closer"),
            "recent_own_encore_rate": recent_own_rate("encore"),
            "global_opener_rate": self._global_rate("opener"),
            "global_closer_rate": self._global_rate("closer"),
            "global_encore_rate": self._global_rate("encore"),
            "times_played_before": float(own_total),
            "days_since_last_played": days_since_last_played,
        }

    def observe(self, play: dict) -> None:
        song_id = play["song_id"]
        category = play["category"]

        self.own_total[song_id] = self.own_total.get(song_id, 0) + 1
        key = (song_id, category)
        self.own_category_count[key] = self.own_category_count.get(key, 0) + 1
        self.own_recent_categories.setdefault(song_id, deque(maxlen=RECENT_WINDOW)).append(category)
        self.own_last_played_date[song_id] = play["event_date"]

        self.global_category_count[category] = self.global_category_count.get(category, 0) + 1
        self.global_total += 1


def _accumulate_stats_before(plays: list[dict], before_date: date | None) -> "PositionStats":
    stats = PositionStats()
    for play in plays:
        if before_date is not None and play["event_date"] >= before_date:
            break
        stats.observe(play)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[str]]:
    """Walks plays chronologically (stopping before `before_date` if given). Emits one
    leakage-free feature row and label (the actual category) per play, including the first
    (whose features are all fallback zeros -- negligible noise against ~8700 real plays)."""
    plays = _ordered_song_plays(conn)
    stats = PositionStats()
    rows: list[dict] = []
    labels: list[str] = []

    for play in plays:
        if before_date is not None and play["event_date"] >= before_date:
            break
        row = stats.features_for(play["song_id"], play["event_date"])
        rows.append(row)
        labels.append(play["category"])
        stats.observe(play)

    return rows, labels


def build_prediction_features(conn, song_id: int, reference_date: date) -> dict:
    """Feature row for `song_id`'s position category at the next show, from plays strictly
    before `reference_date`."""
    plays = _ordered_song_plays(conn)
    stats = _accumulate_stats_before(plays, reference_date)
    return stats.features_for(song_id, reference_date)


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[str]) -> LogisticRegression:
    model = LogisticRegression(max_iter=5000)
    model.fit(_to_matrix(rows), np.array(labels))
    return model


def predict_proba(model: LogisticRegression, features: dict) -> dict[str, float]:
    probabilities = model.predict_proba(_to_matrix([features]))[0]
    return dict(zip(model.classes_, probabilities))
