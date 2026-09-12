from undercurrents.clustering import clusters, embeddings, features, title_resolution
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


class FakeMbidClient:
    def __init__(self):
        self.calls = 0

    def get(self, path, params):
        self.calls += 1
        return 200, {"recordings": []}


def _setlist(setlist_id, song_names):
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    songs = [
        SetlistSongEntry(i + 1, 1, name, False, False, None, False, None)
        for i, name in enumerate(song_names)
    ]
    return NormalizedSetlist(
        id=setlist_id, event_date="2019-01-01", last_updated_source="x",
        url="https://x", artist=artist, venue=venue, tour=None,
        songs=songs,
    )


def test_full_pipeline_resolves_filters_and_clusters(tmp_conn):
    db.save_setlist(tmp_conn, _setlist("s1", ["Elephant", "Halcyon + On + On", "Intro"]))
    db.save_setlist(tmp_conn, _setlist("s2", ["Elephant", "Halcyon And On And On"]))
    db.save_setlist(tmp_conn, _setlist("s3", ["Nangs"]))

    client = FakeMbidClient()
    title_resolution.resolve_song_titles(tmp_conn, client)

    intro_id = db.get_song_id_by_name(tmp_conn, "Intro")
    intro_row = tmp_conn.execute(
        "SELECT excluded_from_clustering FROM songs WHERE id = ?", (intro_id,)
    ).fetchone()
    assert intro_row["excluded_from_clustering"] == 1

    canonical_id = db.get_song_id_by_name(tmp_conn, "Halcyon + On + On")
    variant_id = db.get_song_id_by_name(tmp_conn, "Halcyon And On And On")
    variant_row = tmp_conn.execute(
        "SELECT canonical_song_id FROM songs WHERE id = ?", (variant_id,)
    ).fetchone()
    assert variant_row["canonical_song_id"] == canonical_id

    setlist_ids, song_ids, matrix = features.build_setlist_song_matrix(tmp_conn)
    assert set(setlist_ids) == {"s1", "s2", "s3"}
    assert intro_id not in song_ids

    embedding = embeddings.compute_2d_embedding(matrix)
    labels = clusters.compute_cluster_labels(embedding, min_cluster_size=2)
    clusters.store_setlist_clusters(tmp_conn, setlist_ids, embedding, labels)

    stored = tmp_conn.execute("SELECT COUNT(*) AS c FROM setlist_clusters").fetchone()["c"]
    assert stored == 3
