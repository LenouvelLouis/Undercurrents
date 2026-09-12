import math
from collections import deque
from datetime import date, datetime

import numpy as np
from sklearn.linear_model import Ridge

DATE_FORMAT = "%Y-%m-%d"
RECENT_WINDOW = 5
LEG_GAP_THRESHOLD_DAYS = 14

FEATURE_ORDER = [
    "last_gap_days",
    "recent_avg_gap_days",
    "current_leg_avg_gap_days",
    "show_number_in_current_leg",
    "days_since_leg_started",
    "global_avg_gap_days",
]


def _parse_event_date(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def _ordered_show_dates(conn) -> list[date]:
    """Every setlist's event date, chronologically ordered (ties broken by id). Unlike the
    other two targets, no filtering by song content -- a show having happened is a real event
    regardless of whether its setlist was ever fully transcribed."""
    rows = conn.execute("SELECT event_date FROM setlists ORDER BY event_date, id").fetchall()
    return [_parse_event_date(row["event_date"]) for row in rows]


class GapStats:
    """Accumulates, in chronological order, everything needed to compute leakage-free
    next-show-gap features. Feed show dates to `observe` in ascending order; call
    `features_for` in between observations to get features computed only from shows observed
    so far. Tracks touring "legs" itself (a new leg starts whenever an observed gap exceeds
    `LEG_GAP_THRESHOLD_DAYS`) rather than reusing `clustering/stats.py`'s version, which looks
    at a tour's entire date range and isn't leakage-safe."""

    def __init__(self):
        self.last_event_date: date | None = None
        self.last_gap_days: float | None = None
        self.recent_gaps = deque(maxlen=RECENT_WINDOW)
        self.global_gap_sum = 0
        self.global_gap_count = 0
        self.current_leg_start_date: date | None = None
        self.current_leg_gap_sum = 0
        self.current_leg_gap_count = 0
        self.current_leg_show_count = 0

    def features_for(self) -> dict:
        global_avg_gap_days = (
            self.global_gap_sum / self.global_gap_count if self.global_gap_count else 0.0
        )
        recent_avg_gap_days = (
            sum(self.recent_gaps) / len(self.recent_gaps) if self.recent_gaps else global_avg_gap_days
        )
        current_leg_avg_gap_days = (
            self.current_leg_gap_sum / self.current_leg_gap_count
            if self.current_leg_gap_count
            else recent_avg_gap_days
        )
        days_since_leg_started = (
            float((self.last_event_date - self.current_leg_start_date).days)
            if self.current_leg_start_date is not None
            else 0.0
        )

        return {
            "last_gap_days": float(self.last_gap_days) if self.last_gap_days is not None else 0.0,
            "recent_avg_gap_days": recent_avg_gap_days,
            "current_leg_avg_gap_days": current_leg_avg_gap_days,
            "show_number_in_current_leg": float(self.current_leg_show_count),
            "days_since_leg_started": days_since_leg_started,
            "global_avg_gap_days": global_avg_gap_days,
        }

    def observe(self, event_date: date) -> None:
        if self.last_event_date is not None:
            gap = (event_date - self.last_event_date).days
            self.recent_gaps.append(gap)
            self.global_gap_sum += gap
            self.global_gap_count += 1

            if gap > LEG_GAP_THRESHOLD_DAYS:
                self.current_leg_start_date = event_date
                self.current_leg_gap_sum = 0
                self.current_leg_gap_count = 0
                self.current_leg_show_count = 1
            else:
                self.current_leg_gap_sum += gap
                self.current_leg_gap_count += 1
                self.current_leg_show_count += 1
            self.last_gap_days = gap
        else:
            self.current_leg_start_date = event_date
            self.current_leg_show_count = 1

        self.last_event_date = event_date


def _accumulate_stats_before(dates: list[date], before_date: date | None) -> "GapStats":
    stats = GapStats()
    for event_date in dates:
        if before_date is not None and event_date >= before_date:
            break
        stats.observe(event_date)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[float]]:
    """Walks show dates chronologically (stopping before `before_date` if given). From the
    second show onward, emits a leakage-free feature row (from state strictly before that
    show) and a log1p-transformed gap label, then observes it. The first show contributes no
    row -- there's no gap yet to label."""
    dates = _ordered_show_dates(conn)
    stats = GapStats()
    rows: list[dict] = []
    labels: list[float] = []

    for event_date in dates:
        if before_date is not None and event_date >= before_date:
            break
        if stats.last_event_date is not None:
            row = stats.features_for()
            gap = (event_date - stats.last_event_date).days
            rows.append(row)
            labels.append(math.log1p(gap))
        stats.observe(event_date)

    return rows, labels


def build_prediction_features(conn, as_of_date: date) -> tuple[dict, date]:
    """Feature row for the gap until the next show, anchored on the last known show at or
    before `as_of_date`. Returns (features, anchor_date) -- the caller adds the predicted gap
    to `anchor_date` to get the predicted show date."""
    dates = _ordered_show_dates(conn)
    stats = GapStats()
    for event_date in dates:
        if event_date > as_of_date:
            break
        stats.observe(event_date)

    if stats.last_event_date is None:
        raise ValueError(f"No shows observed at or before {as_of_date}; cannot anchor a prediction")

    return stats.features_for(), stats.last_event_date


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[float]) -> Ridge:
    model = Ridge()
    model.fit(_to_matrix(rows), np.array(labels))
    return model


def predict_gap_days(model: Ridge, features: dict) -> float:
    log_gap = model.predict(_to_matrix([features]))[0]
    return float(np.expm1(log_gap))
