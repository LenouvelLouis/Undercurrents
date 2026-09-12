from datetime import date

from undercurrents.prediction.agent import PredictionAgent
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, song_names, tour_id):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    songs = [
        SetlistSongEntry(i + 1, 1, name, name == "Encore Song", False, None, False, None)
        for i, name in enumerate(song_names)
    ]
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=songs,
    )
    db.save_setlist(conn, normalized)
    conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
    conn.commit()


def _seed_history(conn):
    db.ensure_songs_clustering_columns(conn)
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()

    dates = ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01", "2020-05-01", "2020-06-01"]
    for i, event_date in enumerate(dates):
        songs = ["Common Song", "Encore Song"] if i % 2 == 0 else ["Common Song", "Rare Song"]
        _setlist(conn, f"s{i}", event_date, songs, tour_id=1)

    rows = [(f"s{i}", float(i), float(i), i % 2) for i in range(len(dates))]
    db.replace_setlist_clusters(conn, rows)


def test_predict_next_show_returns_all_known_songs_sorted_by_probability(tmp_conn):
    _seed_history(tmp_conn)

    predictions = PredictionAgent().predict_next_show(tmp_conn, reference_date=date(2020, 7, 1))

    song_names = {db.get_song_id_by_name(tmp_conn, n) for n in ["Common Song", "Encore Song", "Rare Song"]}
    assert {p.song_id for p in predictions} == song_names
    probabilities = [p.probability for p in predictions]
    assert probabilities == sorted(probabilities, reverse=True)


def test_predict_next_show_defaults_reference_date_to_today(tmp_conn):
    _seed_history(tmp_conn)

    predictions = PredictionAgent().predict_next_show(tmp_conn)  # must not raise
    assert len(predictions) == 3


def test_predict_encore_probability_reflects_historical_ratio(tmp_conn):
    _seed_history(tmp_conn)
    encore_song_id = db.get_song_id_by_name(tmp_conn, "Encore Song")

    probability = PredictionAgent().predict_encore_probability(tmp_conn, encore_song_id)

    assert probability == 1.0  # every time it was played, it was in the encore


def test_predict_encore_probability_is_zero_for_never_played_song(tmp_conn):
    _seed_history(tmp_conn)
    fake_song_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    probability = PredictionAgent().predict_encore_probability(tmp_conn, fake_song_id)

    assert probability == 0.0
