from undercurrents.orchestrator import facts
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, song_names):
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


def test_total_show_count(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-02-01", ["B"])
    assert facts.total_show_count(tmp_conn) == 2


def test_date_range(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-03-15", ["B"])
    assert facts.date_range(tmp_conn) == ("2020-01-01", "2020-03-15")


def test_date_range_none_when_no_setlists(tmp_conn):
    assert facts.date_range(tmp_conn) is None


def test_most_played_song(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A", "B"])
    _setlist(tmp_conn, "s2", "2020-02-01", ["A"])
    assert facts.most_played_song(tmp_conn) == ("A", 2)


def test_most_played_song_none_when_no_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    assert facts.most_played_song(tmp_conn) is None


def test_last_played_date(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["A"])
    _setlist(tmp_conn, "s2", "2020-03-01", ["A"])
    song_id = db.get_song_id_by_name(tmp_conn, "A")
    assert facts.last_played_date(tmp_conn, song_id) == "2020-03-01"


def test_last_played_date_includes_merged_variant_plays(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _setlist(tmp_conn, "s1", "2020-01-01", ["Canonical"])
    _setlist(tmp_conn, "s2", "2020-05-01", ["Variant"])
    canonical_id = db.get_song_id_by_name(tmp_conn, "Canonical")
    variant_id = db.get_song_id_by_name(tmp_conn, "Variant")
    db.set_song_canonical(tmp_conn, variant_id, canonical_id)

    assert facts.last_played_date(tmp_conn, canonical_id) == "2020-05-01"


def test_last_played_date_none_for_never_played_song(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    fake_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()
    assert facts.last_played_date(tmp_conn, fake_id) is None
