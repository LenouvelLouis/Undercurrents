import pytest

from undercurrents.clustering import stats
from undercurrents.storage import db
from tests.test_features import _make_setlist


def test_song_frequency_by_year_counts_per_year(tmp_conn):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    def make(setlist_id, year):
        artist = Artist(id="a1", name="Tame Impala", mbid="a1")
        venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
        song = SetlistSongEntry(1, 1, "Elephant", False, False, None, False, None)
        return NormalizedSetlist(
            id=setlist_id, event_date=f"{year}-01-01", last_updated_source="x",
            url="https://x", artist=artist, venue=venue, tour=None, songs=[song],
        )

    db.save_setlist(tmp_conn, make("s1", 2015))
    db.save_setlist(tmp_conn, make("s2", 2015))
    db.save_setlist(tmp_conn, make("s3", 2016))

    song_id = db.get_song_id_by_name(tmp_conn, "Elephant")
    result = stats.song_frequency_by_year(tmp_conn, song_id)

    assert result == {2015: 2, 2016: 1}


def test_cluster_summary_reports_size_date_range_and_top_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Elephant", "Nangs"])
    _make_setlist(tmp_conn, "s2", ["Elephant", "Nangs"])
    _make_setlist(tmp_conn, "s3", ["Loser"])

    elephant_id = db.get_song_id_by_name(tmp_conn, "Elephant")
    nangs_id = db.get_song_id_by_name(tmp_conn, "Nangs")

    db.replace_setlist_clusters(
        tmp_conn,
        [("s1", 0.0, 0.0, 0), ("s2", 0.1, 0.1, 0), ("s3", 9.0, 9.0, 1)],
    )

    summaries = stats.cluster_summary(tmp_conn)

    cluster_0 = next(s for s in summaries if s["cluster_id"] == 0)
    assert cluster_0["size"] == 2
    assert cluster_0["date_start"] == "2019-01-01"
    assert cluster_0["date_end"] == "2019-01-01"
    assert set(cluster_0["top_song_ids"]) >= {elephant_id, nangs_id}


def _setlist(conn, setlist_id, event_date, song_names, tour_id=None):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
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
    if tour_id is not None:
        conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
        conn.commit()


def test_show_number_in_tour_counts_chronologically(tmp_conn):
    tmp_conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    tmp_conn.commit()
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"], tour_id=1)
    _setlist(tmp_conn, "s2", "2020-02-01", ["A"], tour_id=1)
    _setlist(tmp_conn, "s3", "2020-03-01", ["A"], tour_id=1)

    assert stats.show_number_in_tour(tmp_conn, "s1") == 1
    assert stats.show_number_in_tour(tmp_conn, "s2") == 2
    assert stats.show_number_in_tour(tmp_conn, "s3") == 3


def test_show_number_in_tour_is_none_without_a_tour(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])

    assert stats.show_number_in_tour(tmp_conn, "s1") is None


def test_show_number_in_tour_is_none_for_unknown_setlist(tmp_conn):
    assert stats.show_number_in_tour(tmp_conn, "does-not-exist") is None


def test_average_setlist_length_by_year(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A", "B"])
    _setlist(tmp_conn, "s2", "2020-02-01", ["A", "B", "C", "D"])
    _setlist(tmp_conn, "s3", "2021-01-01", ["A"])

    assert stats.average_setlist_length_by_year(tmp_conn) == {2020: 3.0, 2021: 1.0}


def test_average_setlist_length_by_year_excludes_setlists_with_no_songs_logged(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A", "B"])
    _setlist(tmp_conn, "s2", "2020-02-01", [])  # a data gap, not a real 0-song show

    assert stats.average_setlist_length_by_year(tmp_conn) == {2020: 2.0}


def test_average_relative_position(tmp_conn):
    # s1: A at position 1 of 2 -> 0.5. s2: A at position 4 of 4 -> 1.0. Average: 0.75.
    _setlist(tmp_conn, "s1", "2020-01-01", ["A", "B"])
    _setlist(tmp_conn, "s2", "2020-02-01", ["B", "C", "D", "A"])

    song_id = db.get_song_id_by_name(tmp_conn, "A")
    assert stats.average_relative_position(tmp_conn, song_id) == 0.75


def test_average_relative_position_none_for_never_played_song(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    fake_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    assert stats.average_relative_position(tmp_conn, fake_id) is None


def _seed_tour_with_two_legs(conn):
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()
    # Leg 1: 2020-01-01, 01-03, 01-05 (gaps of 2 days). Leg 2: 2020-03-01, 03-03 (gap of ~55
    # days from the last leg-1 show, then 2 days within the leg).
    for setlist_id, event_date in [
        ("s1", "2020-01-01"), ("s2", "2020-01-03"), ("s3", "2020-01-05"),
        ("s4", "2020-03-01"), ("s5", "2020-03-03"),
    ]:
        _setlist(conn, setlist_id, event_date, ["A"], tour_id=1)


def test_tour_leg_number_splits_on_a_large_gap(tmp_conn):
    _seed_tour_with_two_legs(tmp_conn)

    assert stats.tour_leg_number(tmp_conn, "s1") == 1
    assert stats.tour_leg_number(tmp_conn, "s2") == 1
    assert stats.tour_leg_number(tmp_conn, "s3") == 1
    assert stats.tour_leg_number(tmp_conn, "s4") == 2
    assert stats.tour_leg_number(tmp_conn, "s5") == 2


def test_tour_leg_number_none_without_a_tour(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    assert stats.tour_leg_number(tmp_conn, "s1") is None


def test_consecutive_setlist_similarity_computes_jaccard_index(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A", "B"])
    _setlist(tmp_conn, "s2", "2020-01-02", ["A", "B", "C"])  # 2 shared, 3 total -> 2/3
    _setlist(tmp_conn, "s3", "2020-01-03", ["D"])  # 0 shared, 4 total -> 0.0

    results = {r["setlist_id"]: r["similarity_to_previous"] for r in stats.consecutive_setlist_similarity(tmp_conn)}

    assert "s1" not in results  # no predecessor
    assert results["s2"] == pytest.approx(2 / 3)
    assert results["s3"] == pytest.approx(0.0)


def test_consecutive_setlist_similarity_is_one_for_identical_setlists(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A", "B"])
    _setlist(tmp_conn, "s2", "2020-01-02", ["A", "B"])

    results = {r["setlist_id"]: r["similarity_to_previous"] for r in stats.consecutive_setlist_similarity(tmp_conn)}

    assert results["s2"] == pytest.approx(1.0)


def test_consecutive_setlist_similarity_skips_setlists_with_no_songs_logged(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-01-02", [])  # data gap, excluded like elsewhere
    _setlist(tmp_conn, "s3", "2020-01-03", ["A"])

    results = {r["setlist_id"]: r["similarity_to_previous"] for r in stats.consecutive_setlist_similarity(tmp_conn)}

    assert "s2" not in results
    assert results["s3"] == pytest.approx(1.0)  # compared against s1, not the skipped s2


def test_current_consecutive_streak_counts_back_from_most_recent_show(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-01-02", ["B"])  # breaks the streak
    _setlist(tmp_conn, "s3", "2020-01-03", ["A"])
    _setlist(tmp_conn, "s4", "2020-01-04", ["A"])

    song_id = db.get_song_id_by_name(tmp_conn, "A")
    assert stats.current_consecutive_streak(tmp_conn, song_id) == 2


def test_current_consecutive_streak_is_zero_if_absent_from_latest_show(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-01-02", ["B"])

    song_id = db.get_song_id_by_name(tmp_conn, "A")
    assert stats.current_consecutive_streak(tmp_conn, song_id) == 0


def test_current_consecutive_streak_zero_for_never_played_song(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    fake_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    assert stats.current_consecutive_streak(tmp_conn, fake_id) == 0


def test_longest_consecutive_streak_finds_the_longest_run_anywhere(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-01-02", ["A"])
    _setlist(tmp_conn, "s3", "2020-01-03", ["A"])
    _setlist(tmp_conn, "s4", "2020-01-04", ["B"])  # breaks it
    _setlist(tmp_conn, "s5", "2020-01-05", ["A"])
    _setlist(tmp_conn, "s6", "2020-01-06", ["A"])

    song_id = db.get_song_id_by_name(tmp_conn, "A")
    assert stats.longest_consecutive_streak(tmp_conn, song_id) == 3


def test_longest_consecutive_streak_zero_for_never_played_song(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    fake_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    assert stats.longest_consecutive_streak(tmp_conn, fake_id) == 0


def test_cluster_song_entropy_is_zero_for_a_fully_predictable_cluster(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Elephant"])
    _make_setlist(tmp_conn, "s2", ["Elephant"])
    db.replace_setlist_clusters(tmp_conn, [("s1", 0.0, 0.0, 0), ("s2", 0.1, 0.1, 0)])

    entropy = stats.cluster_song_entropy(tmp_conn)

    assert entropy[0] == pytest.approx(0.0)


def test_cluster_song_entropy_is_one_bit_for_a_fifty_fifty_split(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Elephant"])
    _make_setlist(tmp_conn, "s2", ["Nangs"])
    db.replace_setlist_clusters(tmp_conn, [("s1", 0.0, 0.0, 0), ("s2", 0.1, 0.1, 0)])

    entropy = stats.cluster_song_entropy(tmp_conn)

    assert entropy[0] == pytest.approx(1.0)


def test_cluster_song_entropy_empty_when_no_clusters(tmp_conn):
    assert stats.cluster_song_entropy(tmp_conn) == {}


def test_show_number_in_leg_resets_per_leg(tmp_conn):
    _seed_tour_with_two_legs(tmp_conn)

    assert stats.show_number_in_leg(tmp_conn, "s1") == 1
    assert stats.show_number_in_leg(tmp_conn, "s2") == 2
    assert stats.show_number_in_leg(tmp_conn, "s3") == 3
    assert stats.show_number_in_leg(tmp_conn, "s4") == 1
    assert stats.show_number_in_leg(tmp_conn, "s5") == 2
