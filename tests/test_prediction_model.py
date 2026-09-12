from undercurrents.prediction import model

ALWAYS_PLAYED = {
    "global_frequency": 1.0, "tour_frequency": 1.0, "cluster_frequency": 1.0,
    "shows_since_last_played": 0.0, "days_since_last_played": 10.0,
}
NEVER_PLAYED = {
    "global_frequency": 0.0, "tour_frequency": 0.0, "cluster_frequency": 0.0,
    "shows_since_last_played": 50.0, "days_since_last_played": 500.0,
}


def test_train_and_predict_proba_ranks_always_played_above_never_played():
    rows = [ALWAYS_PLAYED, NEVER_PLAYED] * 20
    labels = [1, 0] * 20

    trained = model.train(rows, labels)
    probabilities = model.predict_proba(trained, {1: ALWAYS_PLAYED, 2: NEVER_PLAYED})

    assert probabilities[1] > probabilities[2]
    assert 0.0 <= probabilities[1] <= 1.0
    assert 0.0 <= probabilities[2] <= 1.0


def test_predict_proba_preserves_input_song_ids():
    rows = [ALWAYS_PLAYED, NEVER_PLAYED] * 20
    labels = [1, 0] * 20
    trained = model.train(rows, labels)

    probabilities = model.predict_proba(trained, {42: ALWAYS_PLAYED, 7: NEVER_PLAYED})

    assert set(probabilities) == {42, 7}
