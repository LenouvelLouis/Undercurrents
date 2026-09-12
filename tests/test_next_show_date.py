import math
from datetime import date

from undercurrents.prediction import next_show_date
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    song = SetlistSongEntry(1, 1, "A", False, False, None, False, None)
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=[song],
    )
    db.save_setlist(conn, normalized)


def test_ordered_show_dates_includes_every_setlist_regardless_of_songs(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01")
    _setlist(conn, "s2", "2020-01-05")

    dates = next_show_date._ordered_show_dates(conn)

    assert dates == [date(2020, 1, 1), date(2020, 1, 5)]


def test_gap_stats_features_for_with_no_prior_shows_returns_zero_fallbacks():
    stats = next_show_date.GapStats()

    features = stats.features_for()

    assert features["last_gap_days"] == 0.0
    assert features["recent_avg_gap_days"] == 0.0
    assert features["current_leg_avg_gap_days"] == 0.0
    assert features["show_number_in_current_leg"] == 0.0
    assert features["days_since_leg_started"] == 0.0
    assert features["global_avg_gap_days"] == 0.0


def test_gap_stats_tracks_a_single_leg_when_gaps_stay_under_the_threshold():
    stats = next_show_date.GapStats()
    stats.observe(date(2020, 1, 1))
    stats.observe(date(2020, 1, 3))  # gap 2, within threshold
    stats.observe(date(2020, 1, 6))  # gap 3, within threshold

    features = stats.features_for()

    assert features["last_gap_days"] == 3.0
    assert features["recent_avg_gap_days"] == 2.5  # mean(2, 3)
    assert features["current_leg_avg_gap_days"] == 2.5  # both gaps are in the same leg
    assert features["show_number_in_current_leg"] == 3.0
    assert features["days_since_leg_started"] == 5.0  # Jan 1 -> Jan 6
    assert features["global_avg_gap_days"] == 2.5


def test_gap_stats_starts_a_new_leg_when_a_gap_exceeds_the_threshold():
    stats = next_show_date.GapStats()
    stats.observe(date(2020, 1, 1))
    stats.observe(date(2020, 1, 3))  # gap 2, leg 1
    stats.observe(date(2020, 3, 1))  # gap 58, exceeds 14-day threshold -> new leg

    features = stats.features_for()

    assert features["show_number_in_current_leg"] == 1.0  # new leg just started
    assert features["current_leg_avg_gap_days"] == features["recent_avg_gap_days"]  # no internal gap yet
    assert features["days_since_leg_started"] == 0.0  # leg started on the last observed show itself


def test_build_training_rows_skips_the_first_show_and_log_transforms_labels(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01")
    _setlist(conn, "s2", "2020-01-04")  # gap 3

    rows, labels = next_show_date.build_training_rows(conn)

    assert len(rows) == 1  # first show contributes no row
    assert labels == [math.log1p(3)]


def test_build_prediction_features_returns_the_anchor_date(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01")
    _setlist(conn, "s2", "2020-01-04")

    features, anchor_date = next_show_date.build_prediction_features(conn, date(2020, 6, 1))

    assert anchor_date == date(2020, 1, 4)
    assert features["last_gap_days"] == 3.0


def test_build_prediction_features_raises_when_no_show_exists_before_as_of_date(tmp_conn):
    try:
        next_show_date.build_prediction_features(tmp_conn, date(2020, 1, 1))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_train_and_predict_gap_days_inverts_the_log_transform():
    rows = [{name: 1.0 for name in next_show_date.FEATURE_ORDER}] * 20
    labels = [math.log1p(3.0)] * 20

    trained = next_show_date.train(rows, labels)
    predicted = next_show_date.predict_gap_days(trained, {name: 1.0 for name in next_show_date.FEATURE_ORDER})

    assert 2.0 <= predicted <= 4.0
