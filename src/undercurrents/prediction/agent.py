from dataclasses import dataclass
from datetime import date

from undercurrents.clustering.features import variant_song_ids
from undercurrents.prediction import features, model
from undercurrents.storage import db


def _play_count_matching(conn, song_id: int, condition_sql: str) -> tuple[int, int]:
    """Returns (total_plays, matching_plays) across every variant of `song_id` (see
    `variant_song_ids`), where `condition_sql` is a boolean SQL expression over the
    `setlist_songs` alias `ss`."""
    matching_ids = variant_song_ids(conn, song_id)
    if not matching_ids:
        return 0, 0
    placeholders = ",".join("?" * len(matching_ids))
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total, SUM(CASE WHEN {condition_sql} THEN 1 ELSE 0 END) AS matching
        FROM setlist_songs ss
        WHERE ss.song_id IN ({placeholders})
        """,
        matching_ids,
    ).fetchone()
    return row["total"], row["matching"] or 0


@dataclass(frozen=True)
class SongPrediction:
    song_id: int
    song_name: str
    probability: float


class PredictionAgent:
    def predict_next_show(
        self, conn, reference_date: date | None = None, tour_id: int | None = None
    ) -> list[SongPrediction]:
        if reference_date is None:
            reference_date = date.today()

        rows, labels = features.build_training_rows(conn, before_date=reference_date)
        trained_model = model.train(rows, labels)

        feature_by_song = features.build_prediction_features(conn, reference_date, tour_id=tour_id)
        probabilities = model.predict_proba(trained_model, feature_by_song)

        song_names = {row["id"]: row["name"] for row in db.get_all_songs(conn)}
        predictions = [
            SongPrediction(song_id=song_id, song_name=song_names[song_id], probability=probability)
            for song_id, probability in probabilities.items()
        ]
        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions

    def predict_encore_probability(self, conn, song_id: int) -> float:
        total, matching = _play_count_matching(conn, song_id, "ss.is_encore = 1")
        return matching / total if total else 0.0

    def predict_opener_probability(self, conn, song_id: int) -> float:
        total, matching = _play_count_matching(conn, song_id, "ss.position = 1")
        return matching / total if total else 0.0

    def predict_closer_probability(self, conn, song_id: int) -> float:
        condition = (
            "ss.position = (SELECT MAX(ss2.position) FROM setlist_songs ss2 "
            "WHERE ss2.setlist_id = ss.setlist_id)"
        )
        total, matching = _play_count_matching(conn, song_id, condition)
        return matching / total if total else 0.0
