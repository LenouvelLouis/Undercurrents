from dataclasses import dataclass
from datetime import date, timedelta

from undercurrents.clustering.features import variant_song_ids
from undercurrents.prediction import (
    features,
    model,
    next_show_date,
    next_show_location,
    position,
    setlist_length,
)
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


@dataclass(frozen=True)
class CountryPrediction:
    country: str
    probability: float


class PredictionAgent:
    def predict_next_show(
        self,
        conn,
        reference_date: date | None = None,
        tour_id: int | None = None,
        country: str | None = None,
    ) -> list[SongPrediction]:
        if reference_date is None:
            reference_date = date.today()

        rows, labels = features.build_training_rows(conn, before_date=reference_date)
        trained_model = model.train(rows, labels)

        feature_by_song = features.build_prediction_features(
            conn, reference_date, tour_id=tour_id, country=country
        )
        probabilities = model.predict_proba(trained_model, feature_by_song)

        song_names = {row["id"]: row["name"] for row in db.get_all_songs(conn)}
        predictions = [
            SongPrediction(song_id=song_id, song_name=song_names[song_id], probability=probability)
            for song_id, probability in probabilities.items()
        ]
        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions

    def predict_setlist_length(
        self,
        conn,
        reference_date: date | None = None,
        tour_id: int | None = None,
        country: str | None = None,
    ) -> float:
        if reference_date is None:
            reference_date = date.today()

        rows, labels = setlist_length.build_training_rows(conn, before_date=reference_date)
        trained_model = setlist_length.train(rows, labels)

        prediction_features = setlist_length.build_prediction_features(
            conn, reference_date, tour_id=tour_id, country=country
        )
        return setlist_length.predict(trained_model, prediction_features)

    def predict_position_category(
        self, conn, song_id: int, reference_date: date | None = None
    ) -> dict[str, float]:
        if reference_date is None:
            reference_date = date.today()

        rows, labels = position.build_training_rows(conn, before_date=reference_date)
        trained_model = position.train(rows, labels)

        prediction_features = position.build_prediction_features(conn, song_id, reference_date)
        return position.predict_proba(trained_model, prediction_features)

    def predict_next_show_date(self, conn, as_of_date: date | None = None) -> date:
        if as_of_date is None:
            as_of_date = date.today()

        rows, labels = next_show_date.build_training_rows(conn, before_date=as_of_date)
        trained_model = next_show_date.train(rows, labels)

        prediction_features, anchor_date = next_show_date.build_prediction_features(conn, as_of_date)
        predicted_gap = next_show_date.predict_gap_days(trained_model, prediction_features)
        return anchor_date + timedelta(days=round(predicted_gap))

    def predict_next_show_country(
        self, conn, reference_date: date | None = None, tour_id: int | None = None
    ) -> list[CountryPrediction]:
        if reference_date is None:
            reference_date = date.today()

        rows, labels = next_show_location.build_training_rows(conn, before_date=reference_date)
        trained_model = next_show_location.train(rows, labels)

        feature_by_country = next_show_location.build_prediction_features(
            conn, reference_date, tour_id=tour_id
        )
        probabilities = next_show_location.predict_proba(trained_model, feature_by_country)

        predictions = [
            CountryPrediction(country=country, probability=probability)
            for country, probability in probabilities.items()
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
