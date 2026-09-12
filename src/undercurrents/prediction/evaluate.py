from undercurrents.prediction import features, model


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
    results = []
    for setlist in test_setlists:
        feature_by_song = {
            song_id: stats.features_for(song_id, setlist["tour_id"], setlist["event_date"])
            for song_id in stats.known_song_ids()
        }
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
