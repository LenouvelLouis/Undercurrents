import json
import os
import sqlite3
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException

from undercurrents.api.dependencies import get_conn
from undercurrents.prediction import comeback, encore, running_order
from undercurrents.prediction.agent import PredictionAgent
from undercurrents.prediction.frozen_store import FrozenModelStore
from undercurrents.storage import db

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


@router.get("/setlist-duration")
def get_setlist_duration(
    tour_id: int | None = None, country: str | None = None, conn=Depends(get_conn)
):
    """Runtime of the next show in minutes.

    This is a derivation, not a separate trained model, and the response says so: the
    existing length model gives an expected song count, the songs the setlist model ranks
    highest supply their real stored durations, and the two are multiplied. Both inputs
    are real; the product is an estimate, which is why `method` and the coverage figures
    are returned alongside it rather than a bare number. The historical block is measured,
    not estimated: it only counts shows where every performed song has a known duration.
    """
    durations = db.get_song_durations_ms(conn)
    if not durations:
        raise HTTPException(
            status_code=503, detail="No song durations stored yet; run the enrichment step"
        )

    length_model = _run_or_503(store.get_setlist_length_model, conn)
    predicted_songs = agent.predict_setlist_length(
        conn, tour_id=tour_id, country=country, trained_model=length_model
    )

    setlist_model = _run_or_503(store.get_next_show_model, conn)
    ranked = agent.predict_next_show(
        conn, tour_id=tour_id, country=country, trained_model=setlist_model
    )

    # Average over the songs actually expected to be played, so a set of long songs reads
    # longer than a set of short ones instead of every show getting the catalogue mean.
    expected_count = max(1, int(round(predicted_songs)))
    expected_durations = [
        durations[p.song_id] for p in ranked[:expected_count] if p.song_id in durations
    ]
    basis = "expected setlist"
    if not expected_durations:
        expected_durations = list(durations.values())
        basis = "whole catalogue"
    mean_song_ms = sum(expected_durations) / len(expected_durations)

    # Measured runtimes, restricted to shows with no missing duration so the sum is a real
    # total rather than a partial one.
    complete = conn.execute(
        """
        SELECT SUM(s.duration_ms) / 60000.0 AS minutes
        FROM setlist_songs ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.is_tape = 0
        GROUP BY ss.setlist_id
        HAVING SUM(CASE WHEN s.duration_ms IS NULL THEN 1 ELSE 0 END) = 0
        """
    ).fetchall()
    measured = sorted(row["minutes"] for row in complete)

    coverage = conn.execute(
        """
        SELECT SUM(CASE WHEN s.duration_ms IS NOT NULL THEN 1 ELSE 0 END) AS known,
               COUNT(*) AS total
        FROM setlist_songs ss
        JOIN songs s ON s.id = ss.song_id
        WHERE ss.is_tape = 0
        """
    ).fetchone()
    known, total = coverage["known"] or 0, coverage["total"] or 0

    shows_total = conn.execute("SELECT COUNT(*) AS n FROM setlists").fetchone()["n"]

    median = None
    if measured:
        mid = len(measured) // 2
        median = measured[mid] if len(measured) % 2 else (measured[mid - 1] + measured[mid]) / 2

    return {
        "predicted_minutes": round(predicted_songs * mean_song_ms / 60000, 1),
        "predicted_songs": round(predicted_songs, 1),
        "mean_song_minutes": round(mean_song_ms / 60000, 2),
        "duration_basis": basis,
        "method": "expected song count x mean duration of the expected songs",
        "measured_mean_minutes": round(sum(measured) / len(measured), 1) if measured else None,
        "measured_median_minutes": round(median, 1) if median is not None else None,
        "measured_shows": len(measured),
        "shows_total": shows_total,
        "duration_coverage": round(known / total, 4) if total else None,
    }


def _song_names(conn) -> dict[int, str]:
    return {row["id"]: row["name"] for row in db.get_all_songs(conn)}


@router.get("/running-order")
def get_running_order(
    length: int | None = None, seed_songs: str | None = None, conn=Depends(get_conn)
):
    """The rest of tonight's set, in order, given the songs already played.

    Distinct from `/next-setlist`, which ranks the catalogue by the probability each song
    appears somewhere in the set and says nothing about sequence.

    The seed matters, and the response is explicit about where it came from. Asked to invent
    a whole night from nothing the model does badly, worse than a static list of the most
    played songs; handed the real opening songs it does considerably better, which is the
    regime it was trained for. With no `seed_songs` given there is no real prefix to use, so
    the opening of the most recent show stands in for one, and the response says so rather
    than presenting it as knowledge about tonight.
    """
    bundle = _run_or_503(store.get_running_order_bundle, conn)
    stats = store.get_backtest("running_order", conn)
    index = bundle["index"]

    if seed_songs:
        requested = [int(part) for part in seed_songs.split(",") if part.strip()]
        seed_ids = [song_id for song_id in requested if song_id in index]
        seed_source = "the songs you gave"
    else:
        seed_ids = [entry["song_id"] for entry in running_order.recent_show_prefix(conn, songs=3)]
        seed_ids = [song_id for song_id in seed_ids if song_id in index]
        seed_source = "the opening of the most recent show, standing in for tonight's"

    seed_indices = [index[song_id] for song_id in seed_ids]

    if length is None:
        length_model = _run_or_503(store.get_setlist_length_model, conn)
        from undercurrents.prediction import setlist_length

        features = setlist_length.build_prediction_features(conn, date_type.today())
        predicted_length = int(round(setlist_length.predict(length_model, features)))
        length_source = "predicted by the setlist-length model"
    else:
        predicted_length = int(length)
        length_source = "given"

    remaining = max(1, predicted_length - len(seed_indices))
    names = _song_names(conn)
    order = running_order.decode(bundle, remaining, seed=seed_indices)

    return {
        "length": predicted_length,
        "length_source": length_source,
        "seed_length": len(seed_indices),
        "seed_source": seed_source,
        "seed": [
            {
                "position": i + 1,
                "song_id": song_id,
                "song_name": names.get(song_id, f"song {song_id}"),
                "confidence": 1.0,
            }
            for i, song_id in enumerate(seed_ids)
        ],
        "order": [
            {**entry, "song_name": names.get(entry["song_id"], f"song {entry['song_id']}")}
            for entry in order
        ],
        "trained_on_shows": bundle["trained_on_shows"],
        "accuracy": stats,
    }


@router.get("/encore")
def get_encore(top_n: int = 10, conn=Depends(get_conn)):
    """Ranked encore candidates, using whichever method the backtest's validation window
    chose. The full method comparison travels with the response so the page can show what
    the choice cost or gained."""
    stats = store.get_backtest("encore", conn)
    method = stats["chosen_method"]
    trained_model = _run_or_503(store.get_encore_model, conn) if method == "model" else None

    names = _song_names(conn)
    candidates = encore.predict_next_by_method(conn, method, trained_model, top_n=top_n)
    return {
        "method": method,
        "method_name": encore.METHOD_NAMES[method],
        "candidates": [
            {**c, "song_name": names.get(c["song_id"], f"song {c['song_id']}")} for c in candidates
        ],
        "accuracy": stats,
    }


@router.get("/comeback")
def get_comeback(top_n: int = 15, conn=Depends(get_conn)):
    """Songs absent from the most recent show, ranked by how likely they are to return at
    the next one."""
    stats = store.get_backtest("comeback", conn)
    method = stats["chosen_method"]
    trained_model = _run_or_503(store.get_comeback_model, conn) if method == "model" else None

    names = _song_names(conn)
    candidates = comeback.predict_next_by_method(conn, method, trained_model, top_n=top_n)
    return {
        "method": method,
        "method_name": comeback.METHOD_NAMES[method],
        "candidates": [
            {**c, "song_name": names.get(c["song_id"], f"song {c['song_id']}")} for c in candidates
        ],
        "accuracy": stats,
    }


@router.get("/backtests")
def get_backtests(conn=Depends(get_conn)):
    """The three held-out backtests in one place, so the Models page can show every
    model-against-baseline result together rather than scattering them across the pages that
    happen to use each one.

    Served from the stored JSON. A backtest that has not been run yet is reported as absent
    rather than computed here: each one retrains on a reduced history and replays dozens of
    shows, which is minutes of work, not a request.
    """
    from pathlib import Path

    models_dir = Path(os.environ.get("UNDERCURRENTS_MODELS_DIR", "data/models"))
    results, missing = {}, []
    for key, filename in (
        ("running_order", "running_order_backtest.json"),
        ("encore", "encore_backtest.json"),
        ("comeback", "comeback_backtest.json"),
    ):
        path = models_dir / filename
        if path.exists():
            results[key] = json.loads(path.read_text())
        else:
            missing.append(key)

    return {
        "backtests": results,
        "missing": missing,
        "command": "uv run python -m undercurrents.prediction.cli train-models --with-sequence",
    }


@router.get("/benchmarks")
def get_benchmarks():
    """Stored results of the last `undercurrents.benchmarks.cli run`.

    Served from disk rather than recomputed: training a GRU per request would be absurd, and
    a dated file also means the app shows exactly the numbers a given run produced instead of
    something that drifts silently between page loads.
    """
    from pathlib import Path

    from undercurrents.benchmarks import runner

    models_dir = Path(os.environ.get("UNDERCURRENTS_MODELS_DIR", "data/models"))
    results = runner.load(models_dir / "benchmarks.json")
    if results is None:
        raise HTTPException(
            status_code=404,
            detail="No benchmark run found. Run: uv run python -m undercurrents.benchmarks.cli run",
        )
    return results


@router.get("/show-type")
def get_show_type(conn=Depends(get_conn)):
    """Festival slot or headline show next, with the method chosen on validation folds and
    the test score it earned. Needs `show_format` (derived.cli build)."""
    from undercurrents.prediction import show_type

    try:
        backtest = store.get_backtest("show_type", conn)
    except (ValueError, sqlite3.OperationalError) as error:
        raise HTTPException(status_code=503, detail=f"Show types not available yet: {error}")
    prediction = show_type.predict_next(conn, backtest["chosen_method"])
    return {**prediction, "accuracy": backtest}


@router.get("/model-health")
def get_model_health(conn=Depends(get_conn)):
    """How honest the setlist model's probabilities are, from the walk-forward replay: a
    calibration table, the Brier score, accuracy per show and per year next to a popularity
    baseline. Every number comes from shows the model had not been trained on."""
    try:
        replay = store.get_backtest("replay", conn)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error))
    shows = replay["shows"]
    # nights with a thin recorded setlist (TV spots, partial transcriptions) swing between 0%
    # and 100% on one song and say nothing about the model, so the extremes skip them
    full = [s for s in shows if s["played"] >= 8]
    worst = sorted(full, key=lambda s: s["accuracy"])[:5]
    best_margin = sorted(full, key=lambda s: s["accuracy"] - s["baseline_accuracy"], reverse=True)[:5]
    unseen_by_year: dict[str, list[int]] = {}
    for s in shows:
        tally = unseen_by_year.setdefault(s["event_date"][:4], [0, 0])
        tally[0] += len(s["unseen_songs"])
        tally[1] += s["played"]
    by_year = {
        year: {**stats, "new_song_share": round(unseen_by_year[year][0] / unseen_by_year[year][1], 4) if unseen_by_year[year][1] else 0.0}
        for year, stats in replay["by_year"].items()
    }
    return {
        "method": replay["method"],
        "refit_every": replay["refit_every"],
        "warm_up_shows": replay["warm_up_shows"],
        "shows_scored": replay["shows_scored"],
        "mean_accuracy": replay["mean_accuracy"],
        "mean_baseline_accuracy": replay["mean_baseline_accuracy"],
        "brier_score": replay["brier_score"],
        "calibration": replay["calibration"],
        "by_year": by_year,
        "series": [
            {"setlist_id": s["setlist_id"], "event_date": s["event_date"], "accuracy": s["accuracy"], "baseline": s["baseline_accuracy"]}
            for s in shows
        ],
        "hardest_nights": [
            {"setlist_id": s["setlist_id"], "event_date": s["event_date"], "accuracy": s["accuracy"], "played": s["played"], "unseen_songs": len(s["unseen_songs"])}
            for s in worst
        ],
        "biggest_wins_over_baseline": [
            {"setlist_id": s["setlist_id"], "event_date": s["event_date"], "accuracy": s["accuracy"], "baseline": s["baseline_accuracy"]}
            for s in best_margin
        ],
    }
