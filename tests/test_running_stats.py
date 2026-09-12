from datetime import date

import pytest

from undercurrents.prediction.features import RunningStats


def _setlist(tour_id, cluster_id, songs, event_date, country=None):
    return {
        "tour_id": tour_id,
        "cluster_id": cluster_id,
        "songs": set(songs),
        "event_date": event_date,
        "country": country,
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


def test_current_streak_increments_while_played_and_resets_when_skipped():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A", "B"}, date(2020, 1, 1)))
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 2)))  # B skipped here
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 3)))

    features_a = stats.features_for("A", tour_id=1, current_date=date(2020, 1, 4))
    features_b = stats.features_for("B", tour_id=1, current_date=date(2020, 1, 4))
    assert features_a["current_streak"] == 3.0
    assert features_b["current_streak"] == 0.0


def test_current_streak_is_one_for_a_brand_new_song_on_its_debut():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 1)))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 1, 2))
    assert features["current_streak"] == 1.0


def test_current_streak_is_zero_for_never_played_song():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 1)))

    features = stats.features_for("never-played", tour_id=1, current_date=date(2020, 1, 2))
    assert features["current_streak"] == 0.0


def test_cluster_entropy_is_zero_when_current_cluster_has_a_single_song():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 1)))
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 2)))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 1, 3))
    assert features["cluster_entropy"] == pytest.approx(0.0)


def test_cluster_entropy_is_one_bit_for_an_even_two_song_split():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 1)))
    stats.observe(_setlist(1, 10, {"B"}, date(2020, 1, 2)))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 1, 3))
    assert features["cluster_entropy"] == pytest.approx(1.0)


def test_cluster_entropy_is_zero_before_any_observation():
    stats = RunningStats()
    features = stats.features_for("A", tour_id=1, current_date=date(2020, 1, 1))
    assert features["cluster_entropy"] == 0.0


def test_features_for_tracks_country_frequency():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A", "B"}, date(2020, 1, 1), country="Australia"))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 2, 1), country="Australia")
    assert features["country_frequency"] == 1.0


def test_features_for_falls_back_to_global_frequency_for_unseen_country():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 1), country="Australia"))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 2, 1), country="France")
    assert features["country_frequency"] == features["global_frequency"] == 1.0


def test_features_for_falls_back_to_global_frequency_for_null_country():
    stats = RunningStats()
    stats.observe(_setlist(1, 10, {"A"}, date(2020, 1, 1), country="Australia"))

    features = stats.features_for("A", tour_id=1, current_date=date(2020, 2, 1), country=None)
    assert features["country_frequency"] == features["global_frequency"] == 1.0
