import pytest

from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.prediction import comeback, encore
from undercurrents.storage import db


def _entry(position, name, encore_flag=False):
    return SetlistSongEntry(position, 1, name, encore_flag, False, None, False, None)


def _save(conn, setlist_id, event_date, songs):
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id,
            event_date=event_date,
            last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
            venue=Venue(id="v1", name="Venue", city="City", state=None, country="Country A"),
            tour=None,
            songs=songs,
        ),
    )


def _song(conn, name):
    return db.get_song_id_by_name(conn, name)


# --------------------------------------------------------------------------- encore


def test_encore_features_never_see_the_show_they_describe(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Main"), _entry(2, "Closer", encore_flag=True)])
    shows = encore.load_shows(tmp_conn)
    stats = encore.EncoreStats()
    stats.observe(shows[0])

    # After exactly one show, "Closer" has one encore out of one play. If features_for were
    # reading ahead into the next show, this would not hold.
    features = stats.features_for(_song(tmp_conn, "Closer"))
    assert features["encore_rate"] == 1.0
    assert features["encore_count"] == 1.0
    assert features["was_in_previous_encore"] == 1.0
    assert stats.features_for(_song(tmp_conn, "Main"))["was_in_previous_encore"] == 0.0


def test_encore_recent_rate_follows_the_window_not_the_lifetime(tmp_conn):
    # "Old" is encored once at the start and never again; "New" only lately. The lifetime
    # count cannot separate them once they are equal, but the recent window can.
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Old", encore_flag=True)])
    for i in range(2, 13):
        _save(tmp_conn, f"s{i}", f"2020-02-{i:02d}", [_entry(1, "New", encore_flag=True)])

    shows = encore.load_shows(tmp_conn)
    stats = encore.EncoreStats()
    for show in shows:
        stats.observe(show)

    old = stats.features_for(_song(tmp_conn, "Old"))
    new = stats.features_for(_song(tmp_conn, "New"))
    assert old["recent_encore_rate"] == 0.0
    assert new["recent_encore_rate"] > 0.9
    assert old["encore_count"] == 1.0


def test_encore_rejects_an_unknown_method(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A", encore_flag=True)])
    with pytest.raises(ValueError):
        encore.predict_next_by_method(tmp_conn, "wishful-thinking", None)


def test_encore_backtest_refuses_a_history_too_short_for_its_windows(tmp_conn):
    # One show cannot supply a test window plus three non-overlapping validation folds, and
    # quietly shrinking the windows to fit would make the reported accuracy meaningless.
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A", encore_flag=True)])
    with pytest.raises(ValueError, match="validation folds"):
        encore.backtest(tmp_conn, holdout_shows=60)


def test_comeback_backtest_refuses_a_history_too_short_for_its_windows(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A")])
    with pytest.raises(ValueError, match="validation folds"):
        comeback.backtest(tmp_conn, holdout_shows=60)


# --------------------------------------------------------------------------- comeback


def test_comeback_candidates_exclude_songs_played_at_the_last_show(tmp_conn):
    for i in range(1, 6):
        _save(tmp_conn, f"s{i}", f"2020-01-{i:02d}", [_entry(1, "Always"), _entry(2, "Sometimes")])
    _save(tmp_conn, "s6", "2020-01-06", [_entry(1, "Always")])

    shows = comeback.load_shows(tmp_conn)
    stats = comeback.ComebackStats()
    for show in shows:
        stats.observe(show)

    candidates = stats.candidate_song_ids()
    assert _song(tmp_conn, "Sometimes") in candidates
    # played last night, so by definition not a comeback candidate
    assert _song(tmp_conn, "Always") not in candidates


def test_comeback_candidates_need_a_minimum_history(tmp_conn):
    # "Once" is played a single time: too little history for "overdue" to mean anything.
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Once"), _entry(2, "Regular")])
    for i in range(2, 8):
        _save(tmp_conn, f"s{i}", f"2020-01-{i:02d}", [_entry(1, "Regular")])
    _save(tmp_conn, "s8", "2020-01-08", [_entry(1, "Filler")])

    stats = comeback.ComebackStats()
    for show in comeback.load_shows(tmp_conn):
        stats.observe(show)

    assert _song(tmp_conn, "Once") not in stats.candidate_song_ids()
    assert _song(tmp_conn, "Regular") in stats.candidate_song_ids()


def test_comeback_overdue_ratio_is_absence_over_usual_gap(tmp_conn):
    # Played at show indices 0, 2 and 4, so its usual gap is 2 shows. Eight shows have now
    # been seen, which puts the next one at index 8: four shows on from its last outing, or
    # twice its own rhythm. The distance is measured the same way the gaps themselves are,
    # as a difference of show indices, so the two are directly comparable.
    for i in range(1, 9):
        songs = [_entry(1, "Filler")]
        if i in (1, 3, 5):
            songs.append(_entry(2, "Rotating"))
        _save(tmp_conn, f"s{i}", f"2020-01-{i:02d}", songs)

    stats = comeback.ComebackStats()
    for show in comeback.load_shows(tmp_conn):
        stats.observe(show)

    features = stats.features_for(_song(tmp_conn, "Rotating"))
    assert features["mean_gap_shows"] == 2.0
    assert features["shows_since_last_play"] == 4.0
    assert features["overdue_ratio"] == pytest.approx(2.0)


def test_comeback_rejects_an_unknown_method(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A")])
    with pytest.raises(ValueError):
        comeback.predict_next_by_method(tmp_conn, "vibes", None)


def test_a_single_class_yields_a_constant_rather_than_a_crash():
    # A history where every row has the same label gives a classifier nothing to separate.
    # Fitting one is impossible, so the model degenerates to that one observed outcome.
    rows = [dict.fromkeys(encore.FEATURE_ORDER, 1.0) for _ in range(5)]
    model = encore.train(rows, [1] * 5)
    assert model["classifier"] is None
    assert encore.predict_proba(model, {7: rows[0], 9: rows[0]}) == {7: 1.0, 9: 1.0}

    rows = [dict.fromkeys(comeback.FEATURE_ORDER, 0.5) for _ in range(5)]
    model = comeback.train(rows, [0] * 5)
    assert comeback.predict_proba(model, {3: rows[0]}) == {3: 0.0}
