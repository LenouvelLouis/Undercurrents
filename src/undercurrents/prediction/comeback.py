"""Which shelved songs come back: predicting a return to the setlist.

The question is narrower than "will this song be played", which `prediction.model` already
answers for the whole catalogue. Here only songs that were *absent from the previous show*
are candidates, which strips out the dozen songs played every single night and leaves the
genuinely uncertain ones: the deep cuts, the rotating slots, the things that vanish for two
years and reappear.

The baseline is each song's own base rate, the share of shows so far it has appeared in.
That is a real competitor, because a song played in 40% of shows is a decent bet on any
given night without knowing anything else. The model's claim is that *how overdue* a song
is relative to its own historical rhythm adds something on top of that rate.
"""

from collections import defaultdict, deque
from datetime import date, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from undercurrents.prediction import selection

DATE_FORMAT = "%Y-%m-%d"
RECENT_WINDOW = 10
MIN_PLAYS = 3
DEFAULT_HOLDOUT_SHOWS = 60

FEATURE_ORDER = [
    "base_rate",
    "play_count",
    "shows_since_last_play",
    "overdue_ratio",
    "mean_gap_shows",
    "recent_play_rate",
    "days_since_last_play",
    "shows_seen",
]


def _parse(event_date: str) -> date:
    return datetime.strptime(event_date, DATE_FORMAT).date()


def load_shows(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT s.id AS setlist_id, s.event_date, ss.song_id
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
            {"setlist_id": row["setlist_id"], "event_date": row["event_date"], "songs": []},
        )
        if row["song_id"] not in show["songs"]:
            show["songs"].append(row["song_id"])

    ordered = sorted(shows.values(), key=lambda s: (s["event_date"], s["setlist_id"]))
    return [s for s in ordered if s["songs"]]


class ComebackStats:
    def __init__(self):
        self.shows_seen = 0
        self.current_date: date | None = None
        self.plays: dict[int, int] = defaultdict(int)
        self.last_play_show: dict[int, int] = {}
        self.last_play_date: dict[int, date] = {}
        self.gaps: dict[int, list[int]] = defaultdict(list)
        self.recent: dict[int, deque] = defaultdict(lambda: deque(maxlen=RECENT_WINDOW))
        self.previous_songs: set[int] = set()

    def candidate_song_ids(self) -> list[int]:
        """Songs with enough history to have a rhythm at all, minus the ones played last
        night. A song needs a few plays before "overdue" means anything, and one played
        yesterday is not a comeback candidate by definition."""
        return sorted(
            song_id
            for song_id, plays in self.plays.items()
            if plays >= MIN_PLAYS and song_id not in self.previous_songs
        )

    def features_for(self, song_id: int, current_date: date | None = None) -> dict:
        plays = self.plays.get(song_id, 0)
        gaps = self.gaps.get(song_id) or []
        mean_gap = sum(gaps) / len(gaps) if gaps else float(self.shows_seen)
        since = float(self.shows_seen - self.last_play_show[song_id]) if song_id in self.last_play_show else float(self.shows_seen)
        recent = self.recent.get(song_id)
        last_date = self.last_play_date.get(song_id)
        if current_date is not None and last_date is not None:
            days_since = float((current_date - last_date).days)
        else:
            days_since = 0.0
        return {
            "base_rate": plays / self.shows_seen if self.shows_seen else 0.0,
            "play_count": float(plays),
            "shows_since_last_play": since,
            # the heart of the model: 1.0 means the song is exactly as overdue as it usually
            # gets before returning, 3.0 means it has been gone three times its usual absence
            "overdue_ratio": since / mean_gap if mean_gap > 0 else 0.0,
            "mean_gap_shows": float(mean_gap),
            "recent_play_rate": (sum(recent) / len(recent)) if recent else 0.0,
            "days_since_last_play": days_since,
            "shows_seen": float(self.shows_seen),
        }

    def observe(self, show: dict) -> None:
        played = set(show["songs"])
        for song_id in played:
            if song_id in self.last_play_show:
                self.gaps[song_id].append(self.shows_seen - self.last_play_show[song_id])
            self.plays[song_id] += 1
            self.last_play_show[song_id] = self.shows_seen
            self.last_play_date[song_id] = _parse(show["event_date"])
        for song_id in set(self.plays) | played:
            self.recent[song_id].append(1 if song_id in played else 0)
        self.previous_songs = played
        self.current_date = _parse(show["event_date"])
        self.shows_seen += 1


def _accumulate_before(shows: list[dict], before_date: date | None) -> ComebackStats:
    stats = ComebackStats()
    for show in shows:
        if before_date is not None and _parse(show["event_date"]) >= before_date:
            break
        stats.observe(show)
    return stats


def build_training_rows(conn, before_date: date | None = None) -> tuple[list[dict], list[int]]:
    shows = load_shows(conn)
    stats = ComebackStats()
    rows: list[dict] = []
    labels: list[int] = []

    for show in shows:
        if before_date is not None and _parse(show["event_date"]) >= before_date:
            break
        candidates = stats.candidate_song_ids()
        if candidates:
            played = set(show["songs"])
            show_date = _parse(show["event_date"])
            for song_id in candidates:
                rows.append(stats.features_for(song_id, show_date))
                labels.append(1 if song_id in played else 0)
        stats.observe(show)

    return rows, labels


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[int]):
    """Scaled logistic regression, class weights balanced."""
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


def predict_next(conn, model: dict, reference_date: date | None = None, top_n: int = 15) -> list[dict]:
    shows = load_shows(conn)
    stats = _accumulate_before(shows, reference_date)
    candidates = stats.candidate_song_ids()
    reference = reference_date or stats.current_date
    feature_by_song = {song_id: stats.features_for(song_id, reference) for song_id in candidates}
    probabilities = predict_proba(model, feature_by_song)
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [
        {
            "song_id": song_id,
            "probability": round(probability, 4),
            "shows_since_last_play": int(feature_by_song[song_id]["shows_since_last_play"]),
            "days_since_last_play": int(feature_by_song[song_id]["days_since_last_play"]),
            "overdue_ratio": round(feature_by_song[song_id]["overdue_ratio"], 2),
            "play_count": int(feature_by_song[song_id]["play_count"]),
        }
        for song_id, probability in ranked
    ]


METHOD_NAMES = {
    "model": "logistic regression on how overdue a song is",
    "base_rate": "each song's own base rate",
    "recent": "played most in the last 10 shows",
    "overdue": "most overdue against its own usual gap",
}

# Lowest is simplest. Used only to break a tie the validation folds cannot break; see
# `prediction.selection`.
METHOD_COMPLEXITY = {"base_rate": 0, "overdue": 0, "recent": 1, "model": 2}


def _rank_methods(candidates, feature_by_song, model, k) -> dict[str, list[int]]:
    probabilities = predict_proba(model, feature_by_song) if model else {}
    return {
        "model": [s for s, _ in sorted(probabilities.items(), key=lambda i: -i[1])[:k]],
        "base_rate": sorted(candidates, key=lambda s: -feature_by_song[s]["base_rate"])[:k],
        # a song that has been in most of the last ten shows and simply sat out last night
        "recent": sorted(candidates, key=lambda s: -feature_by_song[s]["recent_play_rate"])[:k],
        # the intuition this page is named after, used on its own
        "overdue": sorted(candidates, key=lambda s: -feature_by_song[s]["overdue_ratio"])[:k],
    }


def _evaluate_window(conn, shows, start: date, end: date | None) -> dict:
    rows, labels = build_training_rows(conn, before_date=start)
    model = train(rows, labels) if any(labels) else None

    stats = _accumulate_before(shows, start)
    hits = {name: 0 for name in METHOD_NAMES}
    slots = 0
    candidates_total = returns_total = 0
    scored_shows = 0

    for show in shows:
        show_date = _parse(show["event_date"])
        if show_date < start:
            continue
        if end is not None and show_date >= end:
            break
        candidates = stats.candidate_song_ids()
        played = set(show["songs"])
        returned = [s for s in candidates if s in played]
        if candidates and returned:
            feature_by_song = {s: stats.features_for(s, show_date) for s in candidates}
            k = len(returned)
            for name, pick in _rank_methods(candidates, feature_by_song, model, k).items():
                hits[name] += len(set(pick) & played)
            slots += k
            candidates_total += len(candidates)
            returns_total += k
            scored_shows += 1
        stats.observe(show)

    return {
        "precision": {
            name: (round(hits[name] / slots, 4) if slots else 0.0) for name in METHOD_NAMES
        },
        "slots": slots,
        "shows": scored_shows,
        "train_rows": len(rows),
        "candidate_return_rate": (
            round(returns_total / candidates_total, 4) if candidates_total else 0.0
        ),
    }


VALIDATION_FOLDS = 3
VALIDATION_FOLD_SHOWS = 40


def _fold_windows(anchor: list[dict], holdout_shows: int) -> tuple[date, list[tuple[date, date]]]:
    """Test-window start plus the non-overlapping validation folds before it. See
    `encore._fold_windows`, which this mirrors, for why there is more than one."""
    needed = holdout_shows + VALIDATION_FOLDS * VALIDATION_FOLD_SHOWS
    if len(anchor) <= needed:
        raise ValueError(
            f"Only {len(anchor)} shows; need more than {needed} for {VALIDATION_FOLDS} "
            f"validation folds plus a {holdout_shows}-show test window"
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
    """Same protocol as the encore predictor: the method is chosen on the mean of several
    earlier validation folds, and the test window is scored once, afterwards.

    `candidate_return_rate` is the floor worth comparing everything against: the share of
    candidates that came back at all, which is what picking at random would score.
    """
    shows = load_shows(conn)
    test_start, fold_windows = _fold_windows(shows, holdout_shows)

    folds = [_evaluate_window(conn, shows, start, end) for start, end in fold_windows]
    fold_precisions = {name: [f["precision"][name] for f in folds] for name in METHOD_NAMES}
    mean = {
        name: round(sum(values) / len(values), 4) for name, values in fold_precisions.items()
    }
    chosen, rationale = selection.choose(fold_precisions, METHOD_COMPLEXITY)

    test = _evaluate_window(conn, shows, test_start, None)
    runners_up = [p for name, p in test["precision"].items() if name != chosen]

    return {
        "task": "which songs absent from the last show return at the next one",
        "chosen_method": chosen,
        "chosen_on": f"the mean of {len(folds)} validation folds, none overlapping the test window",
        "selection": rationale,
        "train_rows": test["train_rows"],
        "test_shows": test["shows"],
        "return_slots": test["slots"],
        "validation_folds": len(folds),
        "validation_shows": sum(f["shows"] for f in folds),
        "candidate_return_rate": test["candidate_return_rate"],
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


def predict_next_by_method(conn, method: str, model: dict | None, reference_date: date | None = None, top_n: int = 15) -> list[dict]:
    shows = load_shows(conn)
    stats = _accumulate_before(shows, reference_date)
    candidates = stats.candidate_song_ids()
    reference = reference_date or stats.current_date
    feature_by_song = {song_id: stats.features_for(song_id, reference) for song_id in candidates}
    ranked = _rank_methods(candidates, feature_by_song, model, top_n).get(method)
    if ranked is None:
        raise ValueError(f"Unknown comeback method: {method}")
    probabilities = predict_proba(model, feature_by_song) if model else {}
    return [
        {
            "song_id": song_id,
            "probability": round(probabilities.get(song_id, 0.0), 4),
            "shows_since_last_play": int(feature_by_song[song_id]["shows_since_last_play"]),
            "days_since_last_play": int(feature_by_song[song_id]["days_since_last_play"]),
            "overdue_ratio": round(feature_by_song[song_id]["overdue_ratio"], 2),
            "recent_play_rate": round(feature_by_song[song_id]["recent_play_rate"], 3),
            "play_count": int(feature_by_song[song_id]["play_count"]),
        }
        for song_id in ranked
    ]
