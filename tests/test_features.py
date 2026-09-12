from undercurrents.clustering import features
from undercurrents.storage import db


def _make_setlist(conn, setlist_id, song_names):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="artist-1", name="Tame Impala", mbid="artist-1")
    venue = Venue(id="venue-1", name="Some Venue", city="Perth", state="WA", country="Australia")
    songs = [
        SetlistSongEntry(
            position=i + 1,
            set_number=1,
            song_name=name,
            is_encore=False,
            is_cover=False,
            cover_artist_name=None,
            is_tape=False,
            info=None,
        )
        for i, name in enumerate(song_names)
    ]
    normalized = NormalizedSetlist(
        id=setlist_id,
        event_date="2019-01-01",
        last_updated_source="2019-01-01T00:00:00.000+0000",
        url=f"https://example.com/{setlist_id}",
        artist=artist,
        venue=venue,
        tour=None,
        songs=songs,
    )
    db.save_setlist(conn, normalized)


def test_build_setlist_song_matrix_excludes_flagged_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Elephant", "Intro"])
    intro_id = db.get_song_id_by_name(tmp_conn, "Intro")
    db.set_song_excluded(tmp_conn, intro_id)

    setlist_ids, song_ids, matrix = features.build_setlist_song_matrix(tmp_conn)

    assert setlist_ids == ["s1"]
    elephant_id = db.get_song_id_by_name(tmp_conn, "Elephant")
    assert song_ids == [elephant_id]
    assert matrix.shape == (1, 1)
    assert matrix[0, 0] == 1.0


def test_build_setlist_song_matrix_merges_canonical_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Halcyon + On + On"])
    _make_setlist(tmp_conn, "s2", ["Halcyon And On And On"])
    canonical_id = db.get_song_id_by_name(tmp_conn, "Halcyon + On + On")
    variant_id = db.get_song_id_by_name(tmp_conn, "Halcyon And On And On")
    db.set_song_canonical(tmp_conn, variant_id, canonical_id)

    setlist_ids, song_ids, matrix = features.build_setlist_song_matrix(tmp_conn)

    assert song_ids == [canonical_id]
    assert matrix.shape == (2, 1)
    assert matrix[0, 0] == 1.0
    assert matrix[1, 0] == 1.0


def test_build_setlist_song_matrix_drops_setlists_with_no_remaining_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Intro"])
    intro_id = db.get_song_id_by_name(tmp_conn, "Intro")
    db.set_song_excluded(tmp_conn, intro_id)

    setlist_ids, song_ids, matrix = features.build_setlist_song_matrix(tmp_conn)

    assert setlist_ids == []
    assert song_ids == []
    assert matrix.shape == (0, 0)


def test_build_song_cooccurrence_matrix_counts_shared_setlists(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Elephant", "Nangs"])
    _make_setlist(tmp_conn, "s2", ["Elephant", "Nangs"])
    _make_setlist(tmp_conn, "s3", ["Elephant"])

    song_ids, matrix = features.build_song_cooccurrence_matrix(tmp_conn)

    elephant_idx = song_ids.index(db.get_song_id_by_name(tmp_conn, "Elephant"))
    nangs_idx = song_ids.index(db.get_song_id_by_name(tmp_conn, "Nangs"))
    assert matrix[elephant_idx, nangs_idx] == 2
    assert matrix[elephant_idx, elephant_idx] == 0
