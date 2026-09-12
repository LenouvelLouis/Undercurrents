import statistics
from datetime import date, timedelta

from undercurrents.prediction import features, model, next_show_date, position, setlist_length


def backtest(conn, holdout_shows: int = 10) -> list[dict]:
    """Holds out the last `holdout_shows` chronological setlists as a test set, trains on
    everything strictly before the earliest held-out show's date, and for each held-out show
    computes top-N accuracy (N = number of songs actually played there): the fraction of
    those songs that appear among the model's N highest-probability predictions."""
    setlists = features._ordered_setlists_with_songs(conn)
    if len(setlists) <= holdout_shows:
        raise ValueError(
            f"Not enough setlists ({len(setlists)}) to hold out {holdout_shows} for backtesting"
        )

    test_setlists = setlists[-holdout_shows:]
    cutoff_date = test_setlists[0]["event_date"]

    rows, labels = features.build_training_rows(conn, before_date=cutoff_date)
    trained_model = model.train(rows, labels)

    stats = features._accumulate_stats_before(setlists, cutoff_date)
    duration_by_song = features._duration_minutes_by_song(conn)
    results = []
    for setlist in test_setlists:
        is_holiday = features._is_holiday_flag(setlist["country"], setlist["event_date"])
        feature_by_song = {}
        for song_id in stats.known_song_ids():
            row = stats.features_for(
                song_id, setlist["tour_id"], setlist["event_date"], country=setlist["country"]
            )
            row["is_holiday"] = is_holiday
            row["duration_minutes"] = duration_by_song[song_id]
            feature_by_song[song_id] = row
        probabilities = model.predict_proba(trained_model, feature_by_song)

        n = len(setlist["songs"])
        top_n_ids = {
            song_id
            for song_id, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:n]
        }
        hits = len(setlist["songs"] & top_n_ids)

        results.append(
            {
                "setlist_id": setlist["id"],
                "event_date": setlist["event_date"].isoformat(),
                "actual_song_count": n,
                "top_n_accuracy": hits / n if n else 0.0,
            }
        )
        stats.observe(setlist)

    return results


def backtest_setlist_length(conn, holdout_shows: int = 10) -> list[dict]:
    """Holds out the last `holdout_shows` chronological setlists, trains on everything
    strictly before the earliest held-out show's date, and for each held-out show predicts
    the raw setlist length (see `setlist_length.py`'s length definition), walking the
    accumulator forward through held-out shows as it goes -- matching how this would be used
    in production, where each new real show becomes part of the history for the next one."""
    setlists = setlist_length._ordered_setlists_with_length(conn)
    if len(setlists) <= holdout_shows:
        raise ValueError(
            f"Not enough setlists ({len(setlists)}) to hold out {holdout_shows} for backtesting"
        )

    test_setlists = setlists[-holdout_shows:]
    cutoff_date = test_setlists[0]["event_date"]

    rows, labels = setlist_length.build_training_rows(conn, before_date=cutoff_date)
    trained_model = setlist_length.train(rows, labels)

    stats = setlist_length._accumulate_stats_before(setlists, cutoff_date)
    results = []
    for setlist in test_setlists:
        features_row = stats.features_for(
            setlist["tour_id"], setlist["event_date"], country=setlist["country"]
        )
        predicted = setlist_length.predict(trained_model, features_row)
        actual = setlist["length"]

        results.append(
            {
                "setlist_id": setlist["id"],
                "event_date": setlist["event_date"].isoformat(),
                "actual_length": actual,
                "predicted_length": predicted,
                "absolute_error": abs(predicted - actual),
            }
        )
        stats.observe(setlist)

    return results


def backtest_position_category(conn, holdout_shows: int = 10) -> list[dict]:
    """Holds out the last `holdout_shows` chronological setlists (by each play's first-seen
    setlist), trains on everything strictly before the earliest held-out show's date, and for
    every held-out play predicts a position category, walking the accumulator forward through
    held-out plays as it goes."""
    plays = position._ordered_song_plays(conn)

    setlist_dates: dict[str, date] = {}
    for play in plays:
        setlist_dates.setdefault(play["setlist_id"], play["event_date"])
    ordered_setlists = list(setlist_dates.items())
    if len(ordered_setlists) <= holdout_shows:
        raise ValueError(
            f"Not enough setlists ({len(ordered_setlists)}) to hold out {holdout_shows} for backtesting"
        )
    cutoff_date = ordered_setlists[-holdout_shows][1]

    rows, labels = position.build_training_rows(conn, before_date=cutoff_date)
    trained_model = position.train(rows, labels)

    stats = position._accumulate_stats_before(plays, cutoff_date)
    results = []
    for play in plays:
        if play["event_date"] < cutoff_date:
            continue
        features_row = stats.features_for(play["song_id"], play["event_date"])
        probabilities = position.predict_proba(trained_model, features_row)
        predicted_category = max(probabilities, key=probabilities.get)

        results.append(
            {
                "setlist_id": play["setlist_id"],
                "song_id": play["song_id"],
                "actual_category": play["category"],
                "predicted_category": predicted_category,
                "correct": predicted_category == play["category"],
            }
        )
        stats.observe(play)

    return results


def summarize_position_backtest(results: list[dict]) -> dict:
    """`mid` dominates real data (~81% of plays) -- raw accuracy alone would let a model that
    always predicts `mid` look deceptively good. Returns overall accuracy alongside recall per
    category (correctly predicted / actual occurrences), so the per-category signal survives
    class imbalance."""
    overall_accuracy = sum(r["correct"] for r in results) / len(results) if results else 0.0

    actual_counts: dict[str, int] = {}
    correct_counts: dict[str, int] = {}
    for r in results:
        category = r["actual_category"]
        actual_counts[category] = actual_counts.get(category, 0) + 1
        if r["correct"]:
            correct_counts[category] = correct_counts.get(category, 0) + 1

    recall_by_category = {
        category: correct_counts.get(category, 0) / count for category, count in actual_counts.items()
    }

    return {"overall_accuracy": overall_accuracy, "recall_by_category": recall_by_category}


def backtest_next_show_date(conn, holdout_shows: int = 10) -> list[dict]:
    """Holds out the last `holdout_shows` chronological shows, trains on everything strictly
    before the earliest held-out show's date, and for each held-out show predicts the gap
    since the previous one, walking the accumulator forward through held-out shows as it
    goes."""
    dates = next_show_date._ordered_show_dates(conn)
    if len(dates) <= holdout_shows:
        raise ValueError(
            f"Not enough setlists ({len(dates)}) to hold out {holdout_shows} for backtesting"
        )

    test_dates = dates[-holdout_shows:]
    cutoff_date = test_dates[0]

    rows, labels = next_show_date.build_training_rows(conn, before_date=cutoff_date)
    trained_model = next_show_date.train(rows, labels)

    stats = next_show_date._accumulate_stats_before(dates, cutoff_date)
    results = []
    for event_date in test_dates:
        features_row = stats.features_for()
        predicted_gap = next_show_date.predict_gap_days(trained_model, features_row)
        actual_gap = (event_date - stats.last_event_date).days
        predicted_date = stats.last_event_date + timedelta(days=round(predicted_gap))

        results.append(
            {
                "event_date": event_date.isoformat(),
                "actual_gap_days": actual_gap,
                "predicted_gap_days": predicted_gap,
                "absolute_error_days": abs(predicted_gap - actual_gap),
                "predicted_date": predicted_date.isoformat(),
            }
        )
        stats.observe(event_date)

    return results


def summarize_next_show_date_backtest(results: list[dict]) -> dict:
    """Median alongside the mean -- a single held-out show landing right after a real
    multi-month gap could otherwise dominate the MAE and misrepresent typical accuracy."""
    errors = [r["absolute_error_days"] for r in results]
    return {
        "mae_days": sum(errors) / len(errors) if errors else 0.0,
        "median_absolute_error_days": statistics.median(errors) if errors else 0.0,
    }
