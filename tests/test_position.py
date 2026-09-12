from datetime import date

from undercurrents.prediction import position
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, songs, tour_id=None):
    """`songs` is a list of (name, is_encore) tuples, in position order."""
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    db.ensure_songs_clustering_columns(conn)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    entries = [
        SetlistSongEntry(i + 1, 1, name, is_encore, False, None, False, None)
        for i, (name, is_encore) in enumerate(songs)
    ]
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=entries,
    )
    db.save_setlist(conn, normalized)
    if tour_id is not None:
        conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
        conn.commit()


def test_categorize_prioritizes_encore_over_opener_and_closer():
    assert position._categorize(position=1, max_position=1, is_encore=True) == "encore"
    assert position._categorize(position=1, max_position=5, is_encore=False) == "opener"
    assert position._categorize(position=5, max_position=5, is_encore=False) == "closer"
    assert position._categorize(position=5, max_position=5, is_encore=True) == "encore"
    assert position._categorize(position=3, max_position=5, is_encore=False) == "mid"


def test_ordered_song_plays_categorizes_a_real_setlist(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01", [
        ("Opener Song", False),
        ("Mid Song", False),
        ("Closer Not Encore", False),
    ])
    _setlist(conn, "s2", "2020-02-01", [
        ("Opener Song", False),
        ("Mid Song", False),
        ("Encore Song", True),
    ])

    plays = position._ordered_song_plays(conn)

    categories_s1 = {p["song_id"]: p["category"] for p in plays if p["setlist_id"] == "s1"}
    categories_s2 = {p["song_id"]: p["category"] for p in plays if p["setlist_id"] == "s2"}
    opener_id = db.get_song_id_by_name(conn, "Opener Song")
    mid_id = db.get_song_id_by_name(conn, "Mid Song")
    closer_id = db.get_song_id_by_name(conn, "Closer Not Encore")
    encore_id = db.get_song_id_by_name(conn, "Encore Song")

    assert categories_s1[opener_id] == "opener"
    assert categories_s1[mid_id] == "mid"
    assert categories_s1[closer_id] == "closer"
    assert categories_s2[encore_id] == "encore"  # last song AND encore -> encore wins


def test_position_stats_features_for_never_played_song_mirrors_global_rates():
    stats = position.PositionStats()
    stats.observe({"setlist_id": "s1", "event_date": date(2020, 1, 1), "song_id": 1, "category": "opener"})
    stats.observe({"setlist_id": "s1", "event_date": date(2020, 1, 1), "song_id": 2, "category": "mid"})

    features = stats.features_for(song_id=999, current_date=date(2020, 2, 1))  # never played

    assert features["own_opener_rate"] == features["global_opener_rate"]
    assert features["own_closer_rate"] == features["global_closer_rate"]
    assert features["own_encore_rate"] == features["global_encore_rate"]
    assert features["times_played_before"] == 0.0
    assert features["days_since_last_played"] == 0.0
    assert features["global_opener_rate"] == 0.5  # 1 of 2 observed plays was an opener


def test_position_stats_observe_updates_own_rate_and_recency():
    stats = position.PositionStats()
    stats.observe({"setlist_id": "s1", "event_date": date(2020, 1, 1), "song_id": 1, "category": "opener"})
    stats.observe({"setlist_id": "s2", "event_date": date(2020, 1, 15), "song_id": 1, "category": "opener"})
    stats.observe({"setlist_id": "s3", "event_date": date(2020, 2, 1), "song_id": 1, "category": "mid"})

    features = stats.features_for(song_id=1, current_date=date(2020, 3, 1))

    assert features["times_played_before"] == 3.0
    assert features["own_opener_rate"] == 2 / 3
    assert features["own_closer_rate"] == 0.0
    assert features["days_since_last_played"] == 29.0  # Feb 1 -> Mar 1


def test_position_stats_recent_own_rate_reflects_a_recent_role_shift_not_lifetime_average():
    stats = position.PositionStats()
    # Song 1 was "mid" for a long stretch, then recently became the opener every night --
    # own_opener_rate (lifetime) should stay low, but recent_own_opener_rate should catch it.
    for i in range(30):
        stats.observe({"setlist_id": f"old{i}", "event_date": date(2020, 1, i + 1), "song_id": 1, "category": "mid"})
    for i in range(20):  # exactly RECENT_WINDOW plays, so the window holds only these
        stats.observe({"setlist_id": f"new{i}", "event_date": date(2020, 3, i + 1), "song_id": 1, "category": "opener"})

    features = stats.features_for(song_id=1, current_date=date(2020, 4, 1))

    assert features["own_opener_rate"] == 20 / 50  # lifetime average stays much lower
    assert features["recent_own_opener_rate"] == 1.0  # last 20 (the window) are all "opener"


def test_position_stats_recent_own_rate_falls_back_to_global_when_never_played():
    stats = position.PositionStats()
    stats.observe({"setlist_id": "s1", "event_date": date(2020, 1, 1), "song_id": 1, "category": "encore"})

    features = stats.features_for(song_id=999, current_date=date(2020, 2, 1))

    assert features["recent_own_opener_rate"] == features["global_opener_rate"]
    assert features["recent_own_encore_rate"] == features["global_encore_rate"]


def test_build_training_rows_emits_one_row_per_play_with_correct_labels(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01", [("A", False), ("B", True)])

    rows, labels = position.build_training_rows(conn)

    assert len(rows) == 2
    assert sorted(labels) == ["encore", "opener"]


def test_build_prediction_features_for_a_known_song(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01", [("A", False), ("B", True)])
    song_a = db.get_song_id_by_name(conn, "A")

    features = position.build_prediction_features(conn, song_a, reference_date=date(2020, 6, 1))

    assert features["own_opener_rate"] == 1.0
    assert features["times_played_before"] == 1.0


def test_train_and_predict_proba_returns_a_distribution_over_all_observed_categories():
    rows = [
        {name: 1.0 for name in position.FEATURE_ORDER},
        {name: 0.0 for name in position.FEATURE_ORDER},
        {name: 0.5 for name in position.FEATURE_ORDER},
    ] * 10
    labels = ["opener", "mid", "encore"] * 10

    trained = position.train(rows, labels)
    probabilities = position.predict_proba(trained, {name: 1.0 for name in position.FEATURE_ORDER})

    assert set(probabilities) == {"opener", "mid", "encore"}
    assert abs(sum(probabilities.values()) - 1.0) < 1e-6
