"""Will the next show be a festival slot, and how long should it run if so?

The label comes from `derived/show_format.py` (an estimate from venue and setlist signals, not
a ground truth), restricted to shows classed festival or headline. Three methods compete,
under the same protocol as the encore and comeback predictors: three chronological validation
folds pick the method, `selection.choose` keeps the simpler one when the folds cannot tell
them apart, and a later test window that played no part in the choice gives the score shown.

- base rate: the festival share over the previous 30 shows
- previous show: whatever the last show was
- model: logistic regression on the month (as a point on a circle, since December borders
  January), the previous show's type, the festival share of the last ten shows and the gap
  since the previous show

The score is 1 minus the Brier score, so higher is better and a coin flip scores 0.75.
"""

from __future__ import annotations

import math
import statistics
from datetime import date, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression

from undercurrents.prediction import selection

METHOD_NAMES = {"base_rate": "festival share of the last 30 shows", "previous": "same as the previous show", "model": "logistic regression on season and recent shows"}
METHOD_COMPLEXITY = {"base_rate": 0, "previous": 1, "model": 2}
VALIDATION_FOLDS = 3
FOLD_SHOWS = 40
TEST_SHOWS = 60


def load_shows(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT s.id, s.event_date, f.format,
               (SELECT COUNT(*) FROM setlist_songs ss WHERE ss.setlist_id = s.id AND ss.is_tape = 0) AS songs
        FROM show_format f JOIN setlists s ON s.id = f.setlist_id
        WHERE f.format IN ('festival', 'headline')
        ORDER BY s.event_date, s.id
        """
    ).fetchall()
    return [
        {"id": r["id"], "date": datetime.strptime(r["event_date"], "%Y-%m-%d").date(), "festival": r["format"] == "festival", "songs": r["songs"]}
        for r in rows
    ]


def features_for(history: list[dict], when: date) -> list[float]:
    angle = 2 * math.pi * (when.month - 1) / 12
    last = history[-1] if history else None
    recent = history[-10:]
    return [
        math.sin(angle),
        math.cos(angle),
        1.0 if last and last["festival"] else 0.0,
        sum(s["festival"] for s in recent) / len(recent) if recent else 0.0,
        min((when - last["date"]).days, 120) / 120 if last else 1.0,
    ]


def _fit(shows: list[dict]):
    X = [features_for(shows[:i], s["date"]) for i, s in enumerate(shows) if i > 0]
    y = [int(s["festival"]) for s in shows[1:]]
    if len(set(y)) < 2:
        return {"constant": float(y[0]) if y else 0.0}
    return LogisticRegression(max_iter=1000).fit(np.array(X), np.array(y))


def _predict(fitted, history: list[dict], when: date) -> float:
    if isinstance(fitted, dict):
        return fitted["constant"]
    return float(fitted.predict_proba(np.array([features_for(history, when)]))[0, 1])


def _method_probability(method: str, fitted, history: list[dict], when: date) -> float:
    if method == "base_rate":
        window = history[-30:]
        return sum(s["festival"] for s in window) / len(window) if window else 0.5
    if method == "previous":
        # hedged so a wrong call is not scored as maximally confident
        return 0.8 if history and history[-1]["festival"] else 0.2
    return _predict(fitted, history, when)


def _score_window(shows: list[dict], start: int, end: int) -> dict[str, float]:
    fitted = _fit(shows[:start])
    brier = {m: 0.0 for m in METHOD_NAMES}
    for i in range(start, end):
        outcome = 1.0 if shows[i]["festival"] else 0.0
        for m in METHOD_NAMES:
            p = _method_probability(m, fitted, shows[:i], shows[i]["date"])
            brier[m] += (p - outcome) ** 2
    n = end - start
    return {m: round(1 - brier[m] / n, 4) for m in METHOD_NAMES}


def backtest(conn) -> dict:
    shows = load_shows(conn)
    needed = TEST_SHOWS + VALIDATION_FOLDS * FOLD_SHOWS + 60
    if len(shows) < needed:
        raise ValueError(f"Not enough classified shows ({len(shows)}) for {VALIDATION_FOLDS} folds and a test window")
    test_start = len(shows) - TEST_SHOWS
    folds = []
    for k in range(VALIDATION_FOLDS):
        end = test_start - k * FOLD_SHOWS
        folds.append(_score_window(shows, end - FOLD_SHOWS, end))
    fold_scores = {m: [f[m] for f in folds] for m in METHOD_NAMES}
    chosen, rationale = selection.choose(fold_scores, METHOD_COMPLEXITY)
    test = _score_window(shows, test_start, len(shows))
    return {
        "metric": "1 - Brier score (higher is better; always saying 50% scores 0.75)",
        "chosen_method": chosen,
        "selection": rationale,
        "validation_folds": VALIDATION_FOLDS,
        "fold_shows": FOLD_SHOWS,
        "test_shows": TEST_SHOWS,
        "methods": [
            {"key": m, "name": METHOD_NAMES[m], "fold_scores": fold_scores[m], "validation_score": round(statistics.mean(fold_scores[m]), 4), "test_score": test[m], "chosen": m == chosen}
            for m in METHOD_NAMES
        ],
        "festival_share": round(sum(s["festival"] for s in shows) / len(shows), 4),
        "classified_shows": len(shows),
    }


def predict_next(conn, method: str, when: date | None = None) -> dict:
    shows = load_shows(conn)
    when = when or date.today()
    fitted = _fit(shows) if method == "model" else None
    p = _method_probability(method, fitted, shows, when)

    # How long each kind of night has run lately: the median of the last 20 of each.
    def recent_median(festival: bool) -> float | None:
        songs = [s["songs"] for s in shows if s["festival"] == festival][-20:]
        return statistics.median(songs) if songs else None

    return {
        "probability_festival": round(p, 4),
        "reference_month": when.strftime("%B"),
        "last_show": {"date": shows[-1]["date"].isoformat(), "festival": shows[-1]["festival"]} if shows else None,
        "songs_if_festival": recent_median(True),
        "songs_if_headline": recent_median(False),
        "expected_songs": round(p * (recent_median(True) or 0) + (1 - p) * (recent_median(False) or 0), 1),
    }
