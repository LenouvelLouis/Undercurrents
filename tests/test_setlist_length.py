from datetime import date

from undercurrents.prediction import setlist_length
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, song_names, tour_id=None):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    songs = [
        SetlistSongEntry(i + 1, 1, name, False, False, None, False, None)
        for i, name in enumerate(song_names)
    ]
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=songs,
    )
    db.save_setlist(conn, normalized)
    if tour_id is not None:
        conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
        conn.commit()


def test_ordered_setlists_with_length_counts_raw_rows_and_skips_empty_setlists(tmp_conn):
    conn = tmp_conn
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()
    _setlist(conn, "s1", "2020-01-01", ["A", "B", "C"], tour_id=1)  # length 3
    _setlist(conn, "s2", "2020-02-01", [], tour_id=1)  # 0 setlist_songs rows -> excluded
    _setlist(conn, "s3", "2020-03-01", ["A"], tour_id=1)  # length 1

    result = setlist_length._ordered_setlists_with_length(conn)

    assert [row["id"] for row in result] == ["s1", "s3"]
    assert result[0]["length"] == 3
    assert result[1]["length"] == 1


def test_length_stats_features_for_with_no_prior_data_returns_zero_fallbacks(tmp_conn):
    stats = setlist_length.LengthStats()

    features = stats.features_for(tour_id=1, current_date=date(2020, 1, 1), country="Country")

    assert features["recent_avg_length"] == 0.0
    assert features["global_avg_length"] == 0.0
    assert features["tour_avg_length"] == 0.0
    assert features["country_avg_length"] == 0.0
    assert features["cluster_avg_length"] == 0.0
    assert features["show_number_in_tour"] == 1.0  # first show of tour 1
    assert features["days_since_last_show"] == 0.0
    assert features["is_holiday"] == 0.0


def test_length_stats_features_for_falls_back_to_zero_show_number_when_tour_unknown(tmp_conn):
    stats = setlist_length.LengthStats()

    features = stats.features_for(tour_id=None, current_date=date(2020, 1, 1), country=None)

    assert features["show_number_in_tour"] == 0.0


def test_length_stats_observe_updates_running_averages(tmp_conn):
    stats = setlist_length.LengthStats()
    stats.observe({
        "id": "s1", "event_date": date(2020, 1, 1), "tour_id": 1,
        "cluster_id": 10, "country": "Country", "length": 10,
    })
    stats.observe({
        "id": "s2", "event_date": date(2020, 2, 1), "tour_id": 1,
        "cluster_id": 10, "country": "Country", "length": 20,
    })

    features = stats.features_for(tour_id=1, current_date=date(2020, 3, 1), country="Country")

    assert features["global_avg_length"] == 15.0
    assert features["tour_avg_length"] == 15.0
    assert features["country_avg_length"] == 15.0
    assert features["cluster_avg_length"] == 15.0
    assert features["recent_avg_length"] == 15.0
    assert features["show_number_in_tour"] == 3.0  # 2 observed + this one
    assert features["days_since_last_show"] == 29.0  # Feb 1 -> Mar 1


def test_length_stats_recent_avg_length_truncates_to_last_five(tmp_conn):
    stats = setlist_length.LengthStats()
    lengths = [5, 10, 15, 20, 25, 100]  # only the last 5 (10..100) should count
    for i, length in enumerate(lengths):
        stats.observe({
            "id": f"s{i}", "event_date": date(2020, 1, i + 1), "tour_id": None,
            "cluster_id": None, "country": None, "length": length,
        })

    features = stats.features_for(tour_id=None, current_date=date(2020, 2, 1), country=None)

    assert features["recent_avg_length"] == (10 + 15 + 20 + 25 + 100) / 5


def test_length_stats_falls_back_to_global_when_tour_or_country_unseen(tmp_conn):
    stats = setlist_length.LengthStats()
    stats.observe({
        "id": "s1", "event_date": date(2020, 1, 1), "tour_id": 1,
        "cluster_id": None, "country": "Country A", "length": 10,
    })

    features = stats.features_for(tour_id=2, current_date=date(2020, 2, 1), country="Country B")

    assert features["tour_avg_length"] == 10.0  # tour 2 unseen -> falls back to global
    assert features["country_avg_length"] == 10.0  # Country B unseen -> falls back to global


def test_build_training_rows_emits_one_row_per_setlist_including_the_first(tmp_conn):
    conn = tmp_conn
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()
    _setlist(conn, "s1", "2020-01-01", ["A", "B"], tour_id=1)
    _setlist(conn, "s2", "2020-02-01", ["A", "B", "C"], tour_id=1)

    rows, labels = setlist_length.build_training_rows(conn)

    assert len(rows) == 2
    assert labels == [2.0, 3.0]
    assert rows[0]["global_avg_length"] == 0.0  # first setlist has no prior history


def test_build_training_rows_respects_before_date_cutoff(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01", ["A"])
    _setlist(conn, "s2", "2020-03-01", ["A", "B"])

    rows, labels = setlist_length.build_training_rows(conn, before_date=date(2020, 2, 1))

    assert len(rows) == 1
    assert labels == [1.0]


def test_build_prediction_features_uses_supplied_tour_and_country(tmp_conn):
    conn = tmp_conn
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()
    _setlist(conn, "s1", "2020-01-01", ["A", "B", "C", "D"], tour_id=1)

    result = setlist_length.build_prediction_features(
        conn, reference_date=date(2020, 6, 1), tour_id=1, country="Country"
    )

    assert result["tour_avg_length"] == 4.0
    assert result["country_avg_length"] == 4.0


def test_train_and_predict_returns_a_plausible_length():
    rows = [
        {name: 10.0 for name in setlist_length.FEATURE_ORDER},
        {name: 20.0 for name in setlist_length.FEATURE_ORDER},
    ] * 10
    labels = [10.0, 20.0] * 10

    trained = setlist_length.train(rows, labels)
    predicted = setlist_length.predict(trained, {name: 10.0 for name in setlist_length.FEATURE_ORDER})

    assert 5.0 <= predicted <= 15.0
