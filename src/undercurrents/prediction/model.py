import numpy as np
from sklearn.linear_model import LogisticRegression

FEATURE_ORDER = [
    "global_frequency",
    "tour_frequency",
    "cluster_frequency",
    "shows_since_last_played",
    "days_since_last_played",
]


def _to_matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def train(rows: list[dict], labels: list[int]) -> LogisticRegression:
    model = LogisticRegression(max_iter=1000)
    model.fit(_to_matrix(rows), np.array(labels))
    return model


def predict_proba(model: LogisticRegression, feature_dicts_by_song: dict[int, dict]) -> dict[int, float]:
    song_ids = list(feature_dicts_by_song)
    matrix = _to_matrix([feature_dicts_by_song[song_id] for song_id in song_ids])
    positive_class_index = list(model.classes_).index(1)
    probabilities = model.predict_proba(matrix)[:, positive_class_index]
    return dict(zip(song_ids, probabilities))
