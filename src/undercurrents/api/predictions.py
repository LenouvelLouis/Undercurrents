import os
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException

from undercurrents.api.dependencies import get_conn
from undercurrents.prediction.agent import PredictionAgent
from undercurrents.prediction.frozen_store import FrozenModelStore

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

agent = PredictionAgent()
store = FrozenModelStore(models_dir=os.environ.get("UNDERCURRENTS_MODELS_DIR", "data/models"))

DATE_HOLDOUT_SHOWS = 10


def _run_or_503(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError:
        raise HTTPException(status_code=503, detail="Not enough data to generate a prediction yet")


@router.get("/next-setlist")
def get_next_setlist(tour_id: int | None = None, country: str | None = None, conn=Depends(get_conn)):
    trained_model = _run_or_503(store.get_next_show_model, conn)
    predictions = agent.predict_next_show(
        conn, tour_id=tour_id, country=country, trained_model=trained_model
    )
    return [
        {"song_id": p.song_id, "song_name": p.song_name, "probability": p.probability}
        for p in predictions
    ]


@router.get("/setlist-length")
def get_setlist_length(tour_id: int | None = None, country: str | None = None, conn=Depends(get_conn)):
    trained_model = _run_or_503(store.get_setlist_length_model, conn)
    predicted = agent.predict_setlist_length(
        conn, tour_id=tour_id, country=country, trained_model=trained_model
    )
    return {"predicted_songs": round(predicted, 1)}


@router.get("/song-role/{song_id}")
def get_song_role(song_id: int, conn=Depends(get_conn)):
    row = conn.execute("SELECT name FROM songs WHERE id = ?", (song_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Song not found")

    trained_model = _run_or_503(store.get_position_category_model, conn)
    probabilities = agent.predict_position_category(conn, song_id, trained_model=trained_model)
    return {"song_id": song_id, "song_name": row["name"], "probabilities": probabilities}


@router.get("/next-date")
def get_next_date(conn=Depends(get_conn)):
    trained_model = _run_or_503(store.get_next_show_date_model, conn)
    predicted = agent.predict_next_show_date(conn, trained_model=trained_model)
    days_from_today = (predicted - date_type.today()).days

    mae_days = 0.0
    median_days = 0.0
    try:
        summary = store.get_next_date_backtest_stats(conn, holdout_shows=DATE_HOLDOUT_SHOWS)
        mae_days = summary["mae_days"]
        median_days = summary["median_absolute_error_days"]
    except ValueError:
        pass

    return {
        "predicted_date": predicted.isoformat(),
        "days_from_today": days_from_today,
        "mae_days": round(mae_days, 1),
        "median_absolute_error_days": round(median_days, 1),
    }


@router.get("/next-country")
def get_next_country(tour_id: int | None = None, conn=Depends(get_conn)):
    trained_model = _run_or_503(store.get_next_show_country_model, conn)
    predictions = agent.predict_next_show_country(conn, tour_id=tour_id, trained_model=trained_model)
    return [{"country": p.country, "probability": p.probability} for p in predictions]
