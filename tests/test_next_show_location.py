from datetime import date

from undercurrents.prediction import next_show_location
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, country, tour_id=None):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id=f"v-{country}", name="V", city="C", state=None, country=country)
    song = SetlistSongEntry(1, 1, "A", False, False, None, False, None)
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=[song],
    )
    db.save_setlist(conn, normalized)
    if tour_id is not None:
        conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
        conn.commit()


def test_ordered_setlists_with_country_includes_every_setlist_regardless_of_songs(tmp_conn):
    conn = tmp_conn
    _setlist(conn, "s1", "2020-01-01", "Country A")
    _setlist(conn, "s2", "2020-01-05", "Country B")

    setlists = next_show_location._ordered_setlists_with_country(conn)

    assert [s["id"] for s in setlists] == ["s1", "s2"]
    assert [s["country"] for s in setlists] == ["Country A", "Country B"]
    assert setlists[0]["event_date"] == date(2020, 1, 1)


def test_country_stats_features_for_after_first_observation():
    stats = next_show_location.CountryStats()
    stats.observe({"tour_id": None, "country": "Country A", "event_date": date(2020, 1, 1)})

    features = stats.features_for("Country A", tour_id=None, current_date=date(2020, 1, 2))

    assert features["country_frequency"] == 1.0
    assert features["tour_country_frequency"] == 1.0  # falls back to country_frequency, no tour
    assert features["is_last_show_country"] == 1.0
    assert features["current_country_streak"] == 1.0
    assert features["days_since_country_last_visited"] == 1.0
    assert features["shows_since_country_last_visited"] == 0.0


def test_country_stats_known_country_ids_grows_as_countries_are_observed():
    stats = next_show_location.CountryStats()
    assert stats.known_country_ids() == set()

    stats.observe({"tour_id": None, "country": "Country A", "event_date": date(2020, 1, 1)})
    assert stats.known_country_ids() == {"Country A"}

    stats.observe({"tour_id": None, "country": "Country B", "event_date": date(2020, 1, 5)})
    assert stats.known_country_ids() == {"Country A", "Country B"}


def test_country_stats_streak_resets_when_a_different_country_is_observed():
    stats = next_show_location.CountryStats()
    stats.observe({"tour_id": None, "country": "Country A", "event_date": date(2020, 1, 1)})
    stats.observe({"tour_id": None, "country": "Country A", "event_date": date(2020, 1, 3)})
    stats.observe({"tour_id": None, "country": "Country B", "event_date": date(2020, 1, 6)})

    features_a = stats.features_for("Country A", tour_id=None, current_date=date(2020, 1, 7))
    features_b = stats.features_for("Country B", tour_id=None, current_date=date(2020, 1, 7))

    assert features_a["current_country_streak"] == 0.0  # broken by the Country B show
    assert features_b["current_country_streak"] == 1.0
    assert features_a["is_last_show_country"] == 0.0
    assert features_b["is_last_show_country"] == 1.0


def test_country_stats_tour_country_frequency_uses_tour_history_when_available():
    stats = next_show_location.CountryStats()
    stats.observe({"tour_id": 1, "country": "Country A", "event_date": date(2020, 1, 1)})
    stats.observe({"tour_id": 1, "country": "Country A", "event_date": date(2020, 1, 5)})
    stats.observe({"tour_id": 2, "country": "Country B", "event_date": date(2020, 1, 10)})

    with_tour_history = stats.features_for("Country A", tour_id=1, current_date=date(2020, 1, 11))
    unobserved_tour = stats.features_for("Country A", tour_id=99, current_date=date(2020, 1, 11))

    assert with_tour_history["tour_country_frequency"] == 1.0  # tour 1 was 100% Country A
    # tour 99 has no observed shows -> falls back to global country_frequency (2/3)
    assert unobserved_tour["tour_country_frequency"] == unobserved_tour["country_frequency"]


def _seed_three_countries(conn):
    """s1 (2020-01-01, Country A, tour 1), s2 (2020-02-01, Country B, tour 1),
    s3 (2020-03-01, Country A, tour 2)."""
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour One', 2020, 2020)")
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (2, 'Tour Two', 2020, 2020)")
    conn.commit()
    _setlist(conn, "s1", "2020-01-01", "Country A", tour_id=1)
    _setlist(conn, "s2", "2020-02-01", "Country B", tour_id=1)
    _setlist(conn, "s3", "2020-03-01", "Country A", tour_id=2)


def test_build_training_rows_emits_one_row_per_known_country_per_later_setlist(tmp_conn):
    _seed_three_countries(tmp_conn)

    rows, labels = next_show_location.build_training_rows(tmp_conn)

    # s1: nothing known yet -> 0 rows. s2: {A} known -> 1 row. s3: {A, B} known -> 2 rows.
    assert len(rows) == 3
    assert len(labels) == 3


def test_build_training_rows_computes_correct_labels(tmp_conn):
    _seed_three_countries(tmp_conn)

    rows, labels = next_show_location.build_training_rows(tmp_conn)

    # Row order: s2's row (candidate A), then s3's rows (candidates A, B -- sorted order).
    s2_a, s3_a, s3_b = rows
    label_s2_a, label_s3_a, label_s3_b = labels

    assert label_s2_a == 0  # s2 is actually Country B, candidate was A
    assert label_s3_a == 1  # s3 is actually Country A
    assert label_s3_b == 0  # s3 is not Country B


def test_build_training_rows_respects_before_date_cutoff(tmp_conn):
    _seed_three_countries(tmp_conn)

    rows, labels = next_show_location.build_training_rows(tmp_conn, before_date=date(2020, 3, 1))

    # Only s1 (0 rows) and s2 (1 row) are strictly before 2020-03-01.
    assert len(rows) == 1


def test_build_prediction_features_covers_all_countries_known_before_reference_date(tmp_conn):
    _seed_three_countries(tmp_conn)

    result = next_show_location.build_prediction_features(tmp_conn, date(2020, 4, 1))

    assert set(result) == {"Country A", "Country B"}
    for country_features in result.values():
        assert set(country_features) == {
            "country_frequency", "tour_country_frequency", "is_last_show_country",
            "current_country_streak", "days_since_country_last_visited",
            "shows_since_country_last_visited",
        }


def test_build_prediction_features_uses_supplied_tour_id(tmp_conn):
    _seed_three_countries(tmp_conn)

    with_tour = next_show_location.build_prediction_features(tmp_conn, date(2020, 4, 1), tour_id=1)
    without_tour = next_show_location.build_prediction_features(tmp_conn, date(2020, 4, 1), tour_id=None)

    # Tour 1 (s1, s2) was Country A once and Country B once -> 50% each.
    assert with_tour["Country A"]["tour_country_frequency"] == 0.5
    # Without a tour hint, falls back to global country_frequency (also computed, not hardcoded).
    assert without_tour["Country A"]["tour_country_frequency"] == without_tour["Country A"]["country_frequency"]


def test_train_and_predict_proba_favors_the_more_frequent_country():
    rows = [
        {"country_frequency": 0.8, "tour_country_frequency": 0.8, "is_last_show_country": 1.0,
         "current_country_streak": 5.0, "days_since_country_last_visited": 1.0,
         "shows_since_country_last_visited": 0.0},
        {"country_frequency": 0.2, "tour_country_frequency": 0.2, "is_last_show_country": 0.0,
         "current_country_streak": 0.0, "days_since_country_last_visited": 100.0,
         "shows_since_country_last_visited": 5.0},
    ] * 10
    labels = [1, 0] * 10

    trained = next_show_location.train(rows, labels)
    probabilities = next_show_location.predict_proba(
        trained,
        {
            "Country A": rows[0],
            "Country B": rows[1],
        },
    )

    assert probabilities["Country A"] > probabilities["Country B"]
    assert 0.0 <= probabilities["Country A"] <= 1.0
    assert 0.0 <= probabilities["Country B"] <= 1.0
