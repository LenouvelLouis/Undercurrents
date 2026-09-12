from undercurrents.orchestrator import retrieval
from undercurrents.orchestrator.intent import ClassifiedIntent, Intent
from undercurrents.storage import db


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


def test_retrieve_fact_includes_overview_and_mentioned_song(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["Elephant"])

    result = retrieval.retrieve(
        tmp_conn, ClassifiedIntent(Intent.FACT, mentioned_song_name="Elephant")
    )

    assert result.intent == Intent.FACT
    assert result.data["total_shows"] == 1
    assert result.data["mentioned_song"] == "Elephant"
    assert result.data["mentioned_song_last_played"] == "2020-01-01"


def test_retrieve_fact_without_mentioned_song_omits_song_fields(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["Elephant"])

    result = retrieval.retrieve(tmp_conn, ClassifiedIntent(Intent.FACT))

    assert "mentioned_song" not in result.data


def test_retrieve_prediction_returns_ranked_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    conn = tmp_conn
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()
    dates = ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01"]
    cluster_rows = []
    for i, event_date in enumerate(dates):
        # Alternate with a rarely-played song so the training labels aren't all 1 (a single
        # always-played song leaves LogisticRegression with only one class to learn from).
        songs = ["Common Song"] if i % 2 == 0 else ["Common Song", "Rare Song"]
        _setlist(conn, f"s{i}", event_date, songs, tour_id=1)
        cluster_rows.append((f"s{i}", 0.0, 0.0, 0))
    db.replace_setlist_clusters(conn, cluster_rows)

    result = retrieval.retrieve(conn, ClassifiedIntent(Intent.PREDICT))

    assert result.intent == Intent.PREDICT
    assert len(result.data["top_predictions"]) > 0
    assert result.data["top_predictions"][0]["song_name"] == "Common Song"


def test_retrieve_cluster_summary_includes_song_names(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["Elephant"])
    _setlist(tmp_conn, "s2", "2020-02-01", ["Elephant"])
    db.replace_setlist_clusters(tmp_conn, [("s1", 0.0, 0.0, 0), ("s2", 0.1, 0.1, 0)])

    result = retrieval.retrieve(tmp_conn, ClassifiedIntent(Intent.CLUSTER))

    assert result.intent == Intent.CLUSTER
    assert len(result.data["clusters"]) == 1
    assert result.data["clusters"][0]["top_songs"] == ["Elephant"]


def test_retrieve_chat_returns_empty_data(tmp_conn):
    result = retrieval.retrieve(tmp_conn, ClassifiedIntent(Intent.CHAT))
    assert result.intent == Intent.CHAT
    assert result.data == {}
