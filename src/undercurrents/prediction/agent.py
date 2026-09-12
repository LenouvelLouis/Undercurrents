from dataclasses import dataclass
from datetime import date

from undercurrents.prediction import features, model
from undercurrents.storage import db


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
        row = conn.execute(
            "SELECT COUNT(*) AS total, SUM(is_encore) AS encores FROM setlist_songs WHERE song_id = ?",
            (song_id,),
        ).fetchone()
        if not row["total"]:
            return 0.0
        return (row["encores"] or 0) / row["total"]
