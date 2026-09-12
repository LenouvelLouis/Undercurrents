import numpy as np
from sklearn.cluster import HDBSCAN

from undercurrents.storage import db

DEFAULT_MIN_CLUSTER_SIZE = 5


def compute_cluster_labels(
    embedding: np.ndarray, min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE
) -> np.ndarray:
    clusterer = HDBSCAN(min_cluster_size=min_cluster_size, copy=False)
    return clusterer.fit_predict(embedding)


def store_setlist_clusters(
    conn, setlist_ids: list[str], embedding: np.ndarray, labels: np.ndarray
) -> None:
    rows = [
        (setlist_id, float(x), float(y), int(cluster_id))
        for setlist_id, (x, y), cluster_id in zip(setlist_ids, embedding, labels)
    ]
    db.replace_setlist_clusters(conn, rows)


def store_song_clusters(
    conn, song_ids: list[int], embedding: np.ndarray, labels: np.ndarray
) -> None:
    rows = [
        (song_id, float(x), float(y), int(cluster_id))
        for song_id, (x, y), cluster_id in zip(song_ids, embedding, labels)
    ]
    db.replace_song_clusters(conn, rows)
