from datetime import date

from undercurrents.prediction import features
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


def _seed_three_setlists(conn):
    """s1 (2020-01-01, tour 1, cluster 10): {Song A, Song B}
    s2 (2020-02-01, tour 1, cluster 20): {Song A}
    s3 (2020-03-01, tour 2, cluster 20): {Song B}"""
    db.ensure_songs_clustering_columns(conn)
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour One', 2020, 2020)")
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (2, 'Tour Two', 2020, 2020)")
    conn.commit()

    _setlist(conn, "s1", "2020-01-01", ["Song A", "Song B"], tour_id=1)
    _setlist(conn, "s2", "2020-02-01", ["Song A"], tour_id=1)
    _setlist(conn, "s3", "2020-03-01", ["Song B"], tour_id=2)

    db.replace_setlist_clusters(
        conn,
        [("s1", 0.0, 0.0, 10), ("s2", 0.0, 0.0, 20), ("s3", 0.0, 0.0, 20)],
    )
    return {
        "A": db.get_song_id_by_name(conn, "Song A"),
        "B": db.get_song_id_by_name(conn, "Song B"),
    }


def test_build_training_rows_emits_one_row_per_known_song_per_later_setlist(tmp_conn):
    ids = _seed_three_setlists(tmp_conn)

    rows, labels = features.build_training_rows(tmp_conn)

    # s1: nothing known yet -> 0 rows. s2: {A, B} known -> 2 rows. s3: {A, B} known -> 2 rows.
    assert len(rows) == 4
    assert len(labels) == 4


def test_build_training_rows_computes_correct_frequencies_and_labels(tmp_conn):
    ids = _seed_three_setlists(tmp_conn)

    rows, labels = features.build_training_rows(tmp_conn)

    # Rows are emitted in setlist chronological order, then by ascending song id within a
    # setlist (song ids reflect insertion order: A=lower id, B=higher id since s1 inserts A
    # before B). The first 2 rows are s2's (A, then B); the last 2 are s3's.
    s2_row_a, s2_row_b, s3_row_a, s3_row_b = rows
    label_s2_a, label_s2_b, label_s3_a, label_s3_b = labels

    # At s2 (tour 1, after only s1 observed): A and B both played once in 1 prior setlist.
    assert s2_row_a["global_frequency"] == 1.0
    assert s2_row_a["tour_frequency"] == 1.0  # tour 1 has 1 prior setlist, A was in it
    assert s2_row_a["cluster_frequency"] == 1.0  # last cluster (10) had A
    assert s2_row_a["country_frequency"] == 1.0  # s1 (the only prior setlist) was in "Country"
    assert label_s2_a == 1  # A is played in s2
    assert label_s2_b == 0  # B is not played in s2

    # At s3 (tour 2, after s1+s2 observed): A played in 2/2 priors, B played in 1/2.
    assert s3_row_a["global_frequency"] == 1.0
    assert s3_row_b["global_frequency"] == 0.5
    # tour 2 has 0 prior setlists -> both fall back to global_frequency
    assert s3_row_a["tour_frequency"] == s3_row_a["global_frequency"]
    assert s3_row_b["tour_frequency"] == s3_row_b["global_frequency"]
    # last cluster (20, from s2) never had B -> cluster_frequency 0 for B
    assert s3_row_b["cluster_frequency"] == 0.0
    assert label_s3_a == 0  # A is not played in s3
    assert label_s3_b == 1  # B is played in s3


def test_build_training_rows_respects_before_date_cutoff(tmp_conn):
    _seed_three_setlists(tmp_conn)

    rows, labels = features.build_training_rows(tmp_conn, before_date=date(2020, 3, 1))

    # Only setlists strictly before 2020-03-01 are processed: s1 (0 rows) and s2 (2 rows).
    assert len(rows) == 2


def test_build_prediction_features_covers_all_songs_known_before_reference_date(tmp_conn):
    _seed_three_setlists(tmp_conn)

    result = features.build_prediction_features(tmp_conn, reference_date=date(2020, 4, 1))

    ids = {db.get_song_id_by_name(tmp_conn, "Song A"), db.get_song_id_by_name(tmp_conn, "Song B")}
    assert set(result) == ids
    for song_features in result.values():
        assert set(song_features) == {
            "global_frequency", "tour_frequency", "cluster_frequency", "country_frequency",
            "shows_since_last_played", "days_since_last_played",
            "current_streak", "cluster_entropy",
            "is_holiday", "duration_minutes",
        }


def test_build_prediction_features_uses_supplied_tour_id(tmp_conn):
    _seed_three_setlists(tmp_conn)
    song_a = db.get_song_id_by_name(tmp_conn, "Song A")

    with_tour = features.build_prediction_features(tmp_conn, date(2020, 4, 1), tour_id=1)
    without_tour = features.build_prediction_features(tmp_conn, date(2020, 4, 1), tour_id=None)

    # Tour 1 had A in both of its setlists (100%); without a tour hint it falls back to A's
    # global frequency (2/2 = 1.0 too here, so assert equality with the *fallback* value
    # directly rather than a numeric literal, keeping the test tied to the real computation).
    assert with_tour[song_a]["tour_frequency"] == 1.0
    assert without_tour[song_a]["tour_frequency"] == without_tour[song_a]["global_frequency"]


def test_build_prediction_features_uses_supplied_country(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["Song A"])  # country "Country" (helper default)

    def _second_country_setlist(conn, setlist_id, event_date, song_names):
        from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

        artist = Artist(id="a1", name="Tame Impala", mbid="a1")
        venue = Venue(id="v2", name="V2", city="C2", state=None, country="Other Country")
        songs = [
            SetlistSongEntry(i + 1, 1, name, False, False, None, False, None)
            for i, name in enumerate(song_names)
        ]
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=setlist_id, event_date=event_date, last_updated_source="x",
                url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=songs,
            ),
        )

    _second_country_setlist(tmp_conn, "s2", "2020-02-01", ["Song B"])
    song_a = db.get_song_id_by_name(tmp_conn, "Song A")

    same_country = features.build_prediction_features(tmp_conn, date(2020, 4, 1), country="Country")
    other_country = features.build_prediction_features(tmp_conn, date(2020, 4, 1), country="Other Country")
    no_country = features.build_prediction_features(tmp_conn, date(2020, 4, 1), country=None)

    # "Country" had 1 setlist, and A was in it -> 100% country_frequency there.
    assert same_country[song_a]["country_frequency"] == 1.0
    # "Other Country" had 1 setlist, and A was NOT in it -> 0% country_frequency there.
    assert other_country[song_a]["country_frequency"] == 0.0
    # With no country hint, falls back to global_frequency (A played in 1 of 2 setlists).
    assert no_country[song_a]["country_frequency"] == no_country[song_a]["global_frequency"] == 0.5


def test_build_prediction_features_uses_known_song_duration(tmp_conn):
    ids = _seed_three_setlists(tmp_conn)
    db.ensure_songs_enrichment_columns(tmp_conn)
    song_a = db.get_song_id_by_name(tmp_conn, "Song A")
    song_b = db.get_song_id_by_name(tmp_conn, "Song B")
    db.set_song_metadata(tmp_conn, song_a, release_date=None, duration_ms=240000, genre_tags="[]")
    # Song B is left unenriched -> its duration must be imputed with A's known value (the only
    # known one here), not left null/zero.

    result = features.build_prediction_features(tmp_conn, date(2020, 4, 1))

    assert result[song_a]["duration_minutes"] == 4.0  # 240000ms = 4 minutes
    assert result[song_b]["duration_minutes"] == 4.0  # imputed with the only known value


def test_build_prediction_features_duration_imputation_defaults_to_zero_when_none_known(tmp_conn):
    _seed_three_setlists(tmp_conn)
    song_a = db.get_song_id_by_name(tmp_conn, "Song A")

    result = features.build_prediction_features(tmp_conn, date(2020, 4, 1))

    assert result[song_a]["duration_minutes"] == 0.0


def test_build_training_rows_marks_holidays_using_the_setlist_own_country(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-07-03", ["Song A"])  # not a holiday yet
    # United States isn't accepted by name in this test fixture's country ("Country"), so use
    # a real supported country name directly for a deterministic holiday check.
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v-us", name="V", city="C", state=None, country="United States")
    song = SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)
    db.save_setlist(
        tmp_conn,
        NormalizedSetlist(
            id="s2", event_date="2020-07-04", last_updated_source="x",
            url="https://x/s2", artist=artist, venue=venue, tour=None, songs=[song],
        ),
    )

    rows, _ = features.build_training_rows(tmp_conn)

    # Row for "Song A" scored against s2 (2020-07-04, US Independence Day).
    assert rows[-1]["is_holiday"] == 1.0


def test_build_prediction_features_is_holiday_false_for_unsupported_country(tmp_conn):
    _seed_three_setlists(tmp_conn)  # venue country is "Country", unsupported by `holidays`
    song_a = db.get_song_id_by_name(tmp_conn, "Song A")

    result = features.build_prediction_features(tmp_conn, date(2020, 7, 4), country="Country")

    assert result[song_a]["is_holiday"] == 0.0
