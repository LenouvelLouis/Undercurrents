"""Which songs close the show: predicting the encore.

The encore is not a random tail of the set. A handful of songs carry it almost every night
and the rest never appear there, which makes the naive ranking (order every song by how many
encores it has ever been in, take the top k) genuinely hard to beat. That ranking is the
baseline here, and the model has to beat it on held-out shows to earn its place on the page.

Features are accumulated walking forward in time, so a row describing the show of
2019-06-01 only ever sees shows strictly before it. Nothing about a show contributes to its
own features.
"""

from collections import defaultdict, deque
from datetime import date, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from undercurrents.prediction import selection

DATE_FORMAT = "%Y-%m-%d"
RECENT_WINDOW = 10
DEFAULT_HOLDOUT_SHOWS = 60

FEATURE_ORDER = [
    "encore_rate",
    "encore_count",
    "play_count",
    "recent_play_rate",
    "recent_encore_rate",
    "shows_since_last_encore",
    "was_in_previous_encore",
    "closer_rate",
]


def _parse(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def load_shows(conn) -> list[dict]:
    """Shows oldest first, each with its full song list and the subset flagged as encore.
    Tape entries are dropped: walk-on and walk-off playback is not a performance and would
    otherwise pollute both the encore set and the closer."""
    rows = conn.execute(
        """
        SELECT s.id AS setlist_id, s.event_date, ss.position, ss.song_id, ss.is_encore
        FROM setlists s
        JOIN setlist_songs ss ON ss.setlist_id = s.id
        WHERE ss.is_tape = 0
        ORDER BY s.event_date, s.id, ss.position
        """
    ).fetchall()

    shows: dict[str, dict] = {}
    for row in rows:
        show = shows.setdefault(
            row["setlist_id"],
            {
                "setlist_id": row["setlist_id"],
                "event_date": row["event_date"],
                "songs": [],
                "encore": [],
            },
        )
        show["songs"].append(row["song_id"])
        if row["is_encore"]:
            show["encore"].append(row["song_id"])

    ordered = sorted(shows.values(), key=lambda s: (s["event_date"], s["setlist_id"]))
    return [s for s in ordered if s["songs"]]


class EncoreStats:
    """Running per-song counts, updated show by show in chronological order."""

    def __init__(self):
        self.shows_seen = 0
        self.plays: dict[int, int] = defaultdict(int)
        self.encores: dict[int, int] = defaultdict(int)
        self.closers: dict[int, int] = defaultdict(int)
        self.last_encore_show: dict[int, int] = {}
        self.recent_plays: dict[int, deque] = defaultdict(lambda: deque(maxlen=RECENT_WINDOW))
        self.recent_encores: dict[int, deque] = defaultdict(lambda: deque(maxlen=RECENT_WINDOW))
        self.previous_encore: set[int] = set()

    def known_song_ids(self) -> list[int]:
        return sorted(self.plays)

    def features_for(self, song_id: int) -> dict:
        plays = self.plays.get(song_id, 0)
        encores = self.encores.get(song_id, 0)
        recent_plays = self.recent_plays.get(song_id)
        recent_encores = self.recent_encores.get(song_id)
        last_encore = self.last_encore_show.get(song_id)
        return {
            "encore_rate": encores / plays if plays else 0.0,
            "encore_count": float(encores),
            "play_count": float(plays),
            "recent_play_rate": (sum(recent_plays) / len(recent_plays)) if recent_plays else 0.0,
            "recent_encore_rate": (
                (sum(recent_encores) / len(recent_encores)) if recent_encores else 0.0
            ),
            # a song never encored yet is given the full history as its distance, which is
            # the largest honest value available rather than a sentinel the model would have
            # to learn to special-case
            "shows_since_last_encore": float(
                self.shows_seen - last_encore if last_encore is not None else self.shows_seen
            ),
            "was_in_previous_encore": 1.0 if song_id in self.previous_encore else 0.0,
            "closer_rate": self.closers.get(song_id, 0) / plays if plays else 0.0,
        }

    def observe(self, show: dict) -> None:
        played = set(show["songs"])
        encore = set(show["encore"])
        for song_id in played:
            self.plays[song_id] += 1
        for song_id in encore:
            self.encores[song_id] += 1
            self.last_encore_show[song_id] = self.shows_seen
        if show["songs"]:
            self.closers[show["songs"][-1]] += 1
        for song_id in set(self.plays) | played:
            self.recent_plays[song_id].append(1 if song_id in played else 0)
            self.recent_encores[song_id].append(1 if song_id in encore else 0)
        self.previous_encore = encore
        self.shows_seen += 1


def _accumulate_before(shows: list[dict], before_date: date | None) -> EncoreStats:
    stats = EncoreStats()
    for show in shows:
        if before_date is not None and _parse(show["event_date"]) >= before_date:
            break
        stats.observe(show)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[int]]:
    """One row per (show, song known at that point). The label is whether the song was in
    that show's encore. Shows with no encore at all are skipped: they carry no positive
    example and would only teach the model the overall encore base rate, which the intercept
    already covers."""
    shows = load_shows(conn)
    stats = EncoreStats()
    rows: list[dict] = []
    labels: list[int] = []

    for show in shows:
        if before_date is not None and _parse(show["event_date"]) >= before_date:
            break
        if show["encore"] and stats.shows_seen > 0:
            encore = set(show["encore"])
            for song_id in stats.known_song_ids():
                rows.append(stats.features_for(song_id))
                labels.append(1 if song_id in encore else 0)
        stats.observe(show)

    return rows, labels


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[int]):
    """Scaled logistic regression. `class_weight="balanced"` because an encore is two or
    three songs out of a hundred-odd candidates, so an unweighted fit would be rewarded for
    predicting "no" everywhere."""
    matrix = _to_matrix(rows)
    classes = set(labels)
    if len(classes) < 2:
        # A classifier cannot be fitted from a single class, and inventing a spread would be
        # worse than admitting there is none: with one outcome ever observed, the only
        # defensible probability is that outcome's own rate. Returning a constant keeps the
        # ranking code working and lets the method comparison quietly pass this model over.
        constant = float(next(iter(classes))) if classes else 0.0
        return {"scaler": None, "classifier": None, "constant": constant}

    scaler = StandardScaler().fit(matrix)
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced")
    classifier.fit(scaler.transform(matrix), np.array(labels))
    return {"scaler": scaler, "classifier": classifier, "constant": None}


def predict_proba(model: dict, feature_by_song: dict[int, dict]) -> dict[int, float]:
    if not feature_by_song:
        return {}
    song_ids = list(feature_by_song)
    if model.get("constant") is not None:
        return {song_id: model["constant"] for song_id in song_ids}
    matrix = model["scaler"].transform(_to_matrix([feature_by_song[s] for s in song_ids]))
    probabilities = model["classifier"].predict_proba(matrix)[:, 1]
    return {song_id: float(p) for song_id, p in zip(song_ids, probabilities)}


def predict_next(conn, model: dict, reference_date: date | None = None, top_n: int = 10) -> list[dict]:
    """Ranked encore candidates for the next show."""
    shows = load_shows(conn)
    stats = _accumulate_before(shows, reference_date)
    feature_by_song = {song_id: stats.features_for(song_id) for song_id in stats.known_song_ids()}
    probabilities = predict_proba(model, feature_by_song)
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [
        {
            "song_id": song_id,
            "probability": round(probability, 4),
            "encore_count": int(stats.encores.get(song_id, 0)),
            "play_count": int(stats.plays.get(song_id, 0)),
        }
        for song_id, probability in ranked
    ]


def _rank_methods(known, feature_by_song, stats, model, k) -> dict[str, list[int]]:
    """Every candidate method's top-k pick for one show, all handed the same k."""
    probabilities = predict_proba(model, feature_by_song) if model else {}
    return {
        "model": [s for s, _ in sorted(probabilities.items(), key=lambda i: -i[1])[:k]],
        # every song ever encored, most encored first
        "lifetime": sorted(known, key=lambda s: -stats.encores.get(s, 0))[:k],
        # what a fan would actually guess: whatever they encored lately, lifetime count
        # only breaking ties
        "recent": sorted(
            known,
            key=lambda s: (-feature_by_song[s]["recent_encore_rate"], -stats.encores.get(s, 0)),
        )[:k],
    }


METHOD_NAMES = {
    "model": "logistic regression on encore history",
    "lifetime": "the most encored songs of all time",
    "recent": "whatever was encored in the last 10 shows",
}

# Lowest is simplest. Used only to break a tie the validation folds cannot break; see
# `prediction.selection`.
METHOD_COMPLEXITY = {"lifetime": 0, "recent": 1, "model": 2}


def _evaluate_window(conn, shows, start: date, end: date | None) -> dict:
    """Scores every method over the shows in [start, end), training on everything before
    `start`. Returns precision per method plus how many encore slots were scored."""
    rows, labels = build_training_rows(conn, before_date=start)
    model = train(rows, labels) if any(labels) else None

    stats = _accumulate_before(shows, start)
    hits = {name: 0 for name in METHOD_NAMES}
    slots = 0
    scored_shows = 0

    for show in shows:
        show_date = _parse(show["event_date"])
        if show_date < start:
            continue
        if end is not None and show_date >= end:
            break
        if show["encore"] and stats.shows_seen > 0:
            encore = set(show["encore"])
            k = len(encore)
            known = stats.known_song_ids()
            feature_by_song = {song_id: stats.features_for(song_id) for song_id in known}
            for name, pick in _rank_methods(known, feature_by_song, stats, model, k).items():
                hits[name] += len(set(pick) & encore)
            slots += k
            scored_shows += 1
        stats.observe(show)

    return {
        "precision": {
            name: (round(hits[name] / slots, 4) if slots else 0.0) for name in METHOD_NAMES
        },
        "slots": slots,
        "shows": scored_shows,
        "train_rows": len(rows),
    }


VALIDATION_FOLDS = 3
VALIDATION_FOLD_SHOWS = 40


def _fold_windows(anchor: list[dict], holdout_shows: int) -> tuple[date, list[tuple[date, date]]]:
    """The test window's start date, and the validation folds that precede it.

    Folds walk forward and never overlap each other or the test window, so a method that only
    looks good on one stretch of the tour cannot win the selection on its own.
    """
    needed = holdout_shows + VALIDATION_FOLDS * VALIDATION_FOLD_SHOWS
    if len(anchor) <= needed:
        raise ValueError(
            f"Only {len(anchor)} scoreable shows; need more than {needed} for "
            f"{VALIDATION_FOLDS} validation folds plus a {holdout_shows}-show test window"
        )

    test_start = _parse(anchor[-holdout_shows]["event_date"])
    windows = []
    for fold in range(VALIDATION_FOLDS):
        end_offset = holdout_shows + fold * VALIDATION_FOLD_SHOWS
        start_offset = end_offset + VALIDATION_FOLD_SHOWS
        windows.append(
            (_parse(anchor[-start_offset]["event_date"]), _parse(anchor[-end_offset]["event_date"]))
        )
    return test_start, list(reversed(windows))


def backtest(conn, holdout_shows: int = DEFAULT_HOLDOUT_SHOWS) -> dict:
    """Two stages, and more than one validation window on purpose.

    The last `holdout_shows` encore-bearing shows are the test set and are scored once. The
    method that ships is chosen on several earlier folds, never on the test window: picking
    the winner off the test numbers would quietly turn the test set into a training set.

    A single validation window turned out not to be enough. On one 60-show stretch the trained
    model beat the recency heuristic, and on the test window that followed it lost. That is
    selection noise, not a real ordering, so the choice is now made on the mean across
    `VALIDATION_FOLDS` separate stretches, and every fold's number is reported so the spread
    stays visible rather than being hidden behind an average.
    """
    shows = load_shows(conn)
    with_encore = [s for s in shows if s["encore"]]
    test_start, fold_windows = _fold_windows(with_encore, holdout_shows)

    folds = [_evaluate_window(conn, shows, start, end) for start, end in fold_windows]
    fold_precisions = {name: [f["precision"][name] for f in folds] for name in METHOD_NAMES}
    mean = {
        name: round(sum(values) / len(values), 4) for name, values in fold_precisions.items()
    }
    chosen, rationale = selection.choose(fold_precisions, METHOD_COMPLEXITY)

    test = _evaluate_window(conn, shows, test_start, None)
    runners_up = [p for name, p in test["precision"].items() if name != chosen]

    return {
        "task": "which songs are in tonight's encore",
        "chosen_method": chosen,
        "chosen_on": f"the mean of {len(folds)} validation folds, none overlapping the test window",
        "selection": rationale,
        "train_rows": test["train_rows"],
        "test_shows": test["shows"],
        "encore_slots": test["slots"],
        "validation_folds": len(folds),
        "validation_shows": sum(f["shows"] for f in folds),
        "precision": test["precision"][chosen],
        "methods": [
            {
                "key": name,
                "name": METHOD_NAMES[name],
                "validation_precision": mean[name],
                "fold_precisions": fold_precisions[name],
                "test_precision": test["precision"][name],
                "chosen": name == chosen,
            }
            for name in METHOD_NAMES
        ],
        "margin_over_next_best": round(test["precision"][chosen] - max(runners_up), 4),
    }


def predict_next_by_method(conn, method: str, model: dict | None, reference_date: date | None = None, top_n: int = 10) -> list[dict]:
    """Ranked encore candidates for the next show, using whichever method the backtest chose."""
    shows = load_shows(conn)
    stats = _accumulate_before(shows, reference_date)
    known = stats.known_song_ids()
    feature_by_song = {song_id: stats.features_for(song_id) for song_id in known}
    ranked = _rank_methods(known, feature_by_song, stats, model, top_n).get(method)
    if ranked is None:
        raise ValueError(f"Unknown encore method: {method}")
    probabilities = predict_proba(model, feature_by_song) if model else {}
    return [
        {
            "song_id": song_id,
            "probability": round(probabilities.get(song_id, 0.0), 4),
            "recent_encore_rate": round(feature_by_song[song_id]["recent_encore_rate"], 3),
            "encore_count": int(stats.encores.get(song_id, 0)),
            "play_count": int(stats.plays.get(song_id, 0)),
        }
        for song_id in ranked
    ]
