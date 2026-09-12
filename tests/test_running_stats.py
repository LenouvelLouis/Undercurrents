from datetime import date

from undercurrents.prediction.features import RunningStats


def _setlist(tour_id, cluster_id, songs, event_date):
    return {
        "tour_id": tour_id,
        "cluster_id": cluster_id,
        "songs": set(songs),
        "event_date": event_date,
    }


def test_known_song_ids_reflects_observed_songs():
    stats = RunningStats()
    assert stats.known_song_ids() == set()

    stats.observe(_setlist(1, 10, {"A", "B"}, date(2020, 1, 1)))
    assert stats.known_song_ids() == {"A", "B"}


def test_features_for_tracks_global_tour_and_cluster_frequency():
    stats = RunningStats()
    stats.observe(_setlist(tour_id=1, cluster_id=10, songs={"A", "B"}, event_date=date(2020, 1, 1)))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 2, 1))
    assert features["global_frequency"] == 1.0
    assert features["tour_frequency"] == 1.0
    assert features["cluster_frequency"] == 1.0
    assert features["shows_since_last_played"] == 0.0
    assert features["days_since_last_played"] == 31.0


def test_features_for_falls_back_to_global_frequency_for_unseen_tour():
    stats = RunningStats()
    stats.observe(_setlist(tour_id=1, cluster_id=10, songs={"A"}, event_date=date(2020, 1, 1)))

    features = stats.features_for("A", tour_id=999, current_date=date(2020, 2, 1))
    assert features["tour_frequency"] == features["global_frequency"] == 1.0


def test_features_for_falls_back_to_global_frequency_for_null_tour():
    stats = RunningStats()
    stats.observe(_setlist(tour_id=1, cluster_id=10, songs={"A"}, event_date=date(2020, 1, 1)))

    features = stats.features_for("A", tour_id=None, current_date=date(2020, 2, 1))
    assert features["tour_frequency"] == features["global_frequency"] == 1.0


def test_features_for_uses_most_recently_observed_cluster():
    stats = RunningStats()
    stats.observe(_setlist(tour_id=1, cluster_id=10, songs={"A"}, event_date=date(2020, 1, 1)))
    stats.observe(_setlist(tour_id=1, cluster_id=20, songs={"B"}, event_date=date(2020, 2, 1)))

    # last_cluster_id is now 20 (from the most recently observed setlist), which never
    # co-occurred with "A" — so "A"'s cluster_frequency is 0, not its own historical cluster.
    features = stats.features_for("A", tour_id=1, current_date=date(2020, 3, 1))
    assert features["cluster_frequency"] == 0.0


def test_features_for_unknown_song_has_zero_frequency_and_no_recency():
    stats = RunningStats()
    stats.observe(_setlist(tour_id=1, cluster_id=10, songs={"A"}, event_date=date(2020, 1, 1)))

    features = stats.features_for("never-played", tour_id=1, current_date=date(2020, 2, 1))
    assert features["global_frequency"] == 0.0
    assert features["shows_since_last_played"] is None
    assert features["days_since_last_played"] is None


def test_features_for_before_any_observation_is_all_zero():
    stats = RunningStats()
    features = stats.features_for("A", tour_id=1, current_date=date(2020, 1, 1))
    assert features["global_frequency"] == 0.0
    assert features["tour_frequency"] == 0.0
    assert features["cluster_frequency"] == 0.0
