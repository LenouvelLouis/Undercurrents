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
            "global_frequency", "tour_frequency", "cluster_frequency",
            "shows_since_last_played", "days_since_last_played",
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
