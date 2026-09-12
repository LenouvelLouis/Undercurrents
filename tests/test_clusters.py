import numpy as np

from undercurrents.clustering.clusters import (
    compute_cluster_labels,
    store_setlist_clusters,
    store_song_clusters,
)
from undercurrents.storage import db


def _seed_setlists(conn, setlist_ids):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    song = SetlistSongEntry(1, 1, "Elephant", False, False, None, False, None)
    for setlist_id in setlist_ids:
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=setlist_id, event_date="2019-01-01", last_updated_source="x",
                url="https://x", artist=artist, venue=venue, tour=None, songs=[song],
            ),
        )


def _two_blob_embedding():
    rng = np.random.default_rng(0)
    blob_a = rng.normal(loc=(0, 0), scale=0.1, size=(10, 2))
    blob_b = rng.normal(loc=(10, 10), scale=0.1, size=(10, 2))
    return np.vstack([blob_a, blob_b])


def test_compute_cluster_labels_separates_distinct_blobs():
    embedding = _two_blob_embedding()
    labels = compute_cluster_labels(embedding, min_cluster_size=3)
    assert len(set(labels[:10])) == 1
    assert len(set(labels[10:])) == 1
    assert labels[0] != labels[10]


def test_store_setlist_clusters_round_trips(tmp_conn):
    _seed_setlists(tmp_conn, ["setlist-a", "setlist-b"])
    embedding = np.array([[1.0, 2.0], [3.0, 4.0]])
    labels = np.array([0, 1])
    store_setlist_clusters(tmp_conn, ["setlist-a", "setlist-b"], embedding, labels)

    rows = tmp_conn.execute(
        "SELECT setlist_id, x, y, cluster_id FROM setlist_clusters ORDER BY setlist_id"
    ).fetchall()
    assert [dict(r) for r in rows] == [
        {"setlist_id": "setlist-a", "x": 1.0, "y": 2.0, "cluster_id": 0},
        {"setlist_id": "setlist-b", "x": 3.0, "y": 4.0, "cluster_id": 1},
    ]


def test_store_setlist_clusters_replaces_previous_run(tmp_conn):
    _seed_setlists(tmp_conn, ["setlist-a", "setlist-b"])
    embedding = np.array([[1.0, 2.0]])
    labels = np.array([0])
    store_setlist_clusters(tmp_conn, ["setlist-a"], embedding, labels)
    store_setlist_clusters(tmp_conn, ["setlist-b"], embedding, labels)

    rows = tmp_conn.execute("SELECT setlist_id FROM setlist_clusters").fetchall()
    assert [r["setlist_id"] for r in rows] == ["setlist-b"]


def test_store_song_clusters_round_trips(tmp_conn):
    song_id = db.upsert_song(tmp_conn, "Elephant")
    tmp_conn.commit()
    embedding = np.array([[5.0, 6.0]])
    labels = np.array([-1])
    store_song_clusters(tmp_conn, [song_id], embedding, labels)

    row = tmp_conn.execute(
        "SELECT song_id, x, y, cluster_id FROM song_clusters"
    ).fetchone()
    assert dict(row) == {"song_id": song_id, "x": 5.0, "y": 6.0, "cluster_id": -1}
