from datetime import date, timedelta

from undercurrents.prediction import evaluate
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, song_names, tour_id, cluster_id):
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
    conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
    conn.commit()
    return cluster_id


def _seed_two_alternating_modes(conn, n_pairs=15):
    """Builds `2 * n_pairs` setlists alternating between two sharply distinct, cluster-
    separable modes: mode X (cluster 1, tour 1) always plays {Song A, Song B}; mode Y
    (cluster 2, tour 2) always plays {Song C, Song D}. `cluster_frequency` alone should let
    the model separate them almost perfectly."""
    db.ensure_songs_clustering_columns(conn)
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Mode X Tour', 2020, 2020)")
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (2, 'Mode Y Tour', 2020, 2020)")
    conn.commit()

    cluster_rows = []
    current_date = date(2020, 1, 1)
    for i in range(n_pairs):
        _setlist(conn, f"x{i}", current_date.isoformat(), ["Song A", "Song B"], tour_id=1, cluster_id=1)
        cluster_rows.append((f"x{i}", 0.0, 0.0, 1))
        current_date += timedelta(days=10)

        _setlist(conn, f"y{i}", current_date.isoformat(), ["Song C", "Song D"], tour_id=2, cluster_id=2)
        cluster_rows.append((f"y{i}", 1.0, 1.0, 2))
        current_date += timedelta(days=10)

    db.replace_setlist_clusters(conn, cluster_rows)


def test_backtest_achieves_high_accuracy_on_a_cluster_separable_pattern(tmp_conn):
    _seed_two_alternating_modes(tmp_conn, n_pairs=15)

    results = evaluate.backtest(tmp_conn, holdout_shows=6)

    assert len(results) == 6
    mean_accuracy = sum(r["top_n_accuracy"] for r in results) / len(results)
    assert mean_accuracy >= 0.9


def test_backtest_raises_when_holdout_exceeds_available_setlists(tmp_conn):
    _seed_two_alternating_modes(tmp_conn, n_pairs=2)

    try:
        evaluate.backtest(tmp_conn, holdout_shows=1000)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_backtest_setlist_length_returns_one_result_per_held_out_show(tmp_conn):
    _seed_two_alternating_modes(tmp_conn, n_pairs=15)

    results = evaluate.backtest_setlist_length(tmp_conn, holdout_shows=6)

    assert len(results) == 6
    for r in results:
        assert set(r) == {"setlist_id", "event_date", "actual_length", "predicted_length", "absolute_error"}
        assert r["absolute_error"] == abs(r["predicted_length"] - r["actual_length"])


def test_backtest_setlist_length_raises_when_holdout_exceeds_available_setlists(tmp_conn):
    _seed_two_alternating_modes(tmp_conn, n_pairs=2)

    try:
        evaluate.backtest_setlist_length(tmp_conn, holdout_shows=1000)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_backtest_position_category_returns_one_result_per_held_out_play(tmp_conn):
    _seed_two_alternating_modes(tmp_conn, n_pairs=15)

    results = evaluate.backtest_position_category(tmp_conn, holdout_shows=6)

    assert len(results) > 0
    for r in results:
        assert set(r) == {"setlist_id", "song_id", "actual_category", "predicted_category", "correct"}
        assert r["correct"] == (r["predicted_category"] == r["actual_category"])


def test_backtest_position_category_raises_when_holdout_exceeds_available_setlists(tmp_conn):
    _seed_two_alternating_modes(tmp_conn, n_pairs=2)

    try:
        evaluate.backtest_position_category(tmp_conn, holdout_shows=1000)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_summarize_position_backtest_computes_overall_accuracy_and_per_category_recall():
    results = [
        {"setlist_id": "s1", "song_id": 1, "actual_category": "opener", "predicted_category": "opener", "correct": True},
        {"setlist_id": "s1", "song_id": 2, "actual_category": "mid", "predicted_category": "mid", "correct": True},
        {"setlist_id": "s2", "song_id": 3, "actual_category": "encore", "predicted_category": "mid", "correct": False},
        {"setlist_id": "s2", "song_id": 4, "actual_category": "mid", "predicted_category": "mid", "correct": True},
    ]

    summary = evaluate.summarize_position_backtest(results)

    assert summary["overall_accuracy"] == 0.75
    assert summary["recall_by_category"]["opener"] == 1.0
    assert summary["recall_by_category"]["mid"] == 1.0
    assert summary["recall_by_category"]["encore"] == 0.0
