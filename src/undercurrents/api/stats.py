from fastapi import APIRouter, Depends

from undercurrents.api.dependencies import get_conn
from undercurrents.prediction import evaluate

router = APIRouter(prefix="/api/stats", tags=["stats"])

HOLDOUT_SHOWS = 10


def _safe_mean(fn, key, *, conn, holdout_shows):
    """Safely compute mean from backtest results; returns None if insufficient data."""
    try:
        results = fn(conn, holdout_shows=holdout_shows)
        return sum(r[key] for r in results) / len(results)
    except ValueError:
        return None


@router.get("/overview")
def get_overview(conn=Depends(get_conn)):
    concerts_row = conn.execute(
        "SELECT COUNT(*) AS c, MIN(event_date) AS min_d, MAX(event_date) AS max_d FROM setlists"
    ).fetchone()
    venues_row = conn.execute("SELECT COUNT(*) AS c FROM venues").fetchone()
    countries_row = conn.execute(
        "SELECT COUNT(DISTINCT country) AS c FROM venues WHERE country IS NOT NULL"
    ).fetchone()
    clusters_row = conn.execute(
        "SELECT COUNT(DISTINCT cluster_id) AS c FROM setlist_clusters"
    ).fetchone()

    setlist_accuracy = _safe_mean(
        evaluate.backtest, "top_n_accuracy", conn=conn, holdout_shows=HOLDOUT_SHOWS
    )
    length_mae = _safe_mean(
        evaluate.backtest_setlist_length, "absolute_error", conn=conn, holdout_shows=HOLDOUT_SHOWS
    )

    return {
        "concerts_logged": concerts_row["c"],
        "years_start": int(concerts_row["min_d"][:4]) if concerts_row["min_d"] else None,
        "years_end": int(concerts_row["max_d"][:4]) if concerts_row["max_d"] else None,
        "venues_mapped": venues_row["c"],
        "countries": countries_row["c"],
        "setlist_clusters": clusters_row["c"],
        "setlist_accuracy": round(setlist_accuracy, 4) if setlist_accuracy is not None else None,
        "length_mae_songs": round(length_mae, 3) if length_mae is not None else None,
    }
