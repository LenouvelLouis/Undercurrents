"""Walk-forward replay of the setlist model over the whole archive.

For every show after a warm-up period, this answers one question honestly: what would the
next-setlist model have said the evening before, knowing only the shows that came earlier?
The model is refitted every `refit_every` shows on everything strictly before the show being
scored (an expanding window), and the per-song features are rebuilt from earlier shows only,
exactly as `evaluate.backtest` does for its single held-out block. Nothing here reads the
frozen production model, which has seen every show and would grade itself on its own
training data.

The same pass produces what the model-health page needs: a calibration table (when the
model says 30%, how often is the song actually played?), a Brier score, and accuracy by
year next to a simple popularity baseline. It takes a couple of minutes, so it runs in
`train-models --with-sequence` and is served from JSON.
"""

from __future__ import annotations

from undercurrents.prediction import features, model

REFIT_EVERY = 25
MIN_TRAIN_SHOWS = 60
TOP_STORED = 40
CALIBRATION_BINS = 10


def _top_n_hits(probabilities: dict[int, float], played: set[int], n: int) -> int:
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:n]
    return sum(1 for song_id, _ in ranked if song_id in played)


def backtest(conn, refit_every: int = REFIT_EVERY, min_train_shows: int = MIN_TRAIN_SHOWS) -> dict:
    setlists = features._ordered_setlists_with_songs(conn)
    if len(setlists) <= min_train_shows:
        raise ValueError(
            f"Not enough setlists ({len(setlists)}) for a replay with {min_train_shows} warm-up shows"
        )

    duration_by_song = features._duration_minutes_by_song(conn)
    stats = features.RunningStats()
    rows: list[dict] = []
    labels: list[int] = []
    row_dates: list = []
    trained = None
    trained_through = None
    trained_on_shows = 0
    shows: list[dict] = []

    bins = [{"count": 0, "predicted_sum": 0.0, "played": 0} for _ in range(CALIBRATION_BINS)]
    brier_sum = 0.0
    brier_count = 0

    for index, setlist in enumerate(setlists):
        event_date = setlist["event_date"]
        is_holiday = features._is_holiday_flag(setlist["country"], event_date)
        feature_by_song: dict[int, dict] = {}
        for song_id in sorted(stats.known_song_ids()):
            row = stats.features_for(song_id, setlist["tour_id"], event_date, country=setlist["country"])
            row["is_holiday"] = is_holiday
            row["duration_minutes"] = duration_by_song[song_id]
            feature_by_song[song_id] = row

        if index >= min_train_shows and feature_by_song:
            if trained is None or (index - min_train_shows) % refit_every == 0:
                # Strictly earlier dates only: two shows on the same day must not train on
                # each other.
                keep = [i for i, d in enumerate(row_dates) if d < event_date]
                trained = model.train([rows[i] for i in keep], [labels[i] for i in keep])
                trained_through = max(row_dates[i] for i in keep).isoformat()
                trained_on_shows = sum(1 for s in setlists[:index] if s["event_date"] < event_date)

            probabilities = {k: float(v) for k, v in model.predict_proba(trained, feature_by_song).items()}
            played = setlist["songs"]
            predictable = played & set(probabilities)
            n = len(played)
            hits = _top_n_hits(probabilities, played, n)
            baseline = {song_id: row["global_frequency"] for song_id, row in feature_by_song.items()}
            baseline_hits = _top_n_hits(baseline, played, n)

            for song_id, p in probabilities.items():
                outcome = 1 if song_id in played else 0
                b = min(CALIBRATION_BINS - 1, int(p * CALIBRATION_BINS))
                bins[b]["count"] += 1
                bins[b]["predicted_sum"] += p
                bins[b]["played"] += outcome
                brier_sum += (p - outcome) ** 2
                brier_count += 1

            ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
            shows.append(
                {
                    "setlist_id": setlist["id"],
                    "event_date": event_date.isoformat(),
                    "played": n,
                    "hits": hits,
                    "accuracy": round(hits / n, 4) if n else 0.0,
                    "baseline_accuracy": round(baseline_hits / n, 4) if n else 0.0,
                    # songs played that night that the model had never seen: it cannot rank them
                    "unseen_songs": sorted(played - predictable),
                    "trained_through": trained_through,
                    "trained_on_shows": trained_on_shows,
                    "top": [[song_id, round(p, 4)] for song_id, p in ranked[:TOP_STORED]],
                    "played_probability": {
                        str(song_id): round(probabilities[song_id], 4) for song_id in sorted(predictable)
                    },
                    "played_rank": {
                        str(song_id): rank + 1
                        for rank, (song_id, _) in enumerate(ranked)
                        if song_id in played
                    },
                }
            )

        for song_id, row in feature_by_song.items():
            rows.append(row)
            labels.append(1 if song_id in setlist["songs"] else 0)
            row_dates.append(event_date)
        stats.observe(setlist)

    by_year: dict[str, dict] = {}
    for show in shows:
        y = by_year.setdefault(show["event_date"][:4], {"shows": 0, "accuracy": 0.0, "baseline": 0.0})
        y["shows"] += 1
        y["accuracy"] += show["accuracy"]
        y["baseline"] += show["baseline_accuracy"]
    for y in by_year.values():
        y["accuracy"] = round(y["accuracy"] / y["shows"], 4)
        y["baseline"] = round(y["baseline"] / y["shows"], 4)

    calibration = [
        {
            "bin_start": i / CALIBRATION_BINS,
            "bin_end": (i + 1) / CALIBRATION_BINS,
            "count": b["count"],
            "mean_predicted": round(b["predicted_sum"] / b["count"], 4) if b["count"] else None,
            "observed_rate": round(b["played"] / b["count"], 4) if b["count"] else None,
        }
        for i, b in enumerate(bins)
    ]

    return {
        "method": "expanding-window walk-forward",
        "refit_every": refit_every,
        "warm_up_shows": min_train_shows,
        "shows_scored": len(shows),
        "mean_accuracy": round(sum(s["accuracy"] for s in shows) / len(shows), 4),
        "mean_baseline_accuracy": round(sum(s["baseline_accuracy"] for s in shows) / len(shows), 4),
        "brier_score": round(brier_sum / brier_count, 5) if brier_count else None,
        "calibration": calibration,
        "by_year": dict(sorted(by_year.items())),
        "shows": shows,
    }
