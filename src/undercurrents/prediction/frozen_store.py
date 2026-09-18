import json
from datetime import date, datetime
from pathlib import Path

import joblib

from undercurrents.prediction import (
    comeback,
    encore,
    evaluate,
    features,
    model,
    next_show_date,
    next_show_location,
    position,
    running_order,
    setlist_length,
)

DEFAULT_MODELS_DIR = "data/models"

# Predictor key -> (module providing build_training_rows, module providing train). Every
# predictor module exposes the identical `build_training_rows(conn, before_date) -> (rows,
# labels)` / `train(rows, labels) -> model` shape (see the design spec's "Key constraint
# verified" section), so one generic helper below drives all five instead of duplicating the
# tiered load/train/persist logic per predictor. Modules (not bound function references) are
# stored so the lookup happens at call time via attribute access -- matching how agent.py
# already calls these (`module.function(...)`), which is what lets tests monkeypatch a
# module's `train`/`build_training_rows` attribute and have it actually take effect.
_PREDICTOR_MODULES = {
    "next_show": (features, model),
    "setlist_length": (setlist_length, setlist_length),
    "position_category": (position, position),
    "next_show_date": (next_show_date, next_show_date),
    "next_show_country": (next_show_location, next_show_location),
    "encore": (encore, encore),
    "comeback": (comeback, comeback),
}

# Backtests that are far too slow to compute inside a request. Each is a (module, filename)
# pair; the result is a plain dict cached as JSON next to the models.
_BACKTESTS = {
    "encore": (encore, "encore_backtest.json"),
    "comeback": (comeback, "comeback_backtest.json"),
    "running_order": (running_order, "running_order_backtest.json"),
}


class FrozenModelStore:
    """Three-tier cache (memory -> disk -> train-and-persist) for the prediction models used
    by the live API. Training itself is always delegated to each predictor module's existing
    `build_training_rows`/`train` functions -- this class only decides *whether* to call them.
    """

    def __init__(self, models_dir: str | Path = DEFAULT_MODELS_DIR):
        self.models_dir = Path(models_dir)
        self._cache: dict[str, object] = {}

    def _model_path(self, key: str) -> Path:
        return self.models_dir / f"{key}.joblib"

    def _get_or_train_model(self, key: str, conn):
        if key in self._cache:
            return self._cache[key]

        path = self._model_path(key)
        if path.exists():
            # joblib.load deserializes via pickle, which can execute arbitrary code from an
            # untrusted file. Safe here: the only producer of this file is this same class's
            # train_all()/_get_or_train_model(), run locally against this project's own
            # database -- never a network download or user upload.
            trained_model = joblib.load(path)
        else:
            build_module, train_module = _PREDICTOR_MODULES[key]
            rows, labels = build_module.build_training_rows(conn, before_date=date.today())
            trained_model = train_module.train(rows, labels)
            self.models_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(trained_model, path)

        self._cache[key] = trained_model
        return trained_model

    def get_next_show_model(self, conn):
        return self._get_or_train_model("next_show", conn)

    def get_setlist_length_model(self, conn):
        return self._get_or_train_model("setlist_length", conn)

    def get_position_category_model(self, conn):
        return self._get_or_train_model("position_category", conn)

    def get_next_show_date_model(self, conn):
        return self._get_or_train_model("next_show_date", conn)

    def get_next_show_country_model(self, conn):
        return self._get_or_train_model("next_show_country", conn)

    def get_encore_model(self, conn):
        return self._get_or_train_model("encore", conn)

    def get_comeback_model(self, conn):
        return self._get_or_train_model("comeback", conn)

    def get_running_order_bundle(self, conn):
        """The GRU takes around three minutes to fit, so it is never trained inside a
        request: it is loaded from disk, and only trained here if the file is missing,
        which happens once on a fresh checkout."""
        key = "running_order"
        if key in self._cache:
            return self._cache[key]

        path = self._model_path(key)
        if path.exists():
            bundle = joblib.load(path)
        else:
            bundle = running_order.train(running_order.build_training_sequences(conn))
            self.models_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(bundle, path)

        self._cache[key] = bundle
        return bundle

    def get_backtest(self, key: str, conn) -> dict:
        """Cached backtest results. Computing one means retraining on a held-out split, so
        the JSON on disk is the normal source and recomputation is the fallback."""
        cache_key = f"{key}_backtest"
        if cache_key in self._cache:
            return self._cache[cache_key]

        module, filename = _BACKTESTS[key]
        path = self.models_dir / filename
        if path.exists():
            stats = json.loads(path.read_text())
        else:
            stats = module.backtest(conn)
            self.models_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(stats))

        self._cache[cache_key] = stats
        return stats

    def get_next_date_backtest_stats(self, conn, holdout_shows: int = 10) -> dict:
        key = "next_date_backtest"
        if key in self._cache:
            return self._cache[key]

        path = self.models_dir / "next_date_backtest.json"
        if path.exists():
            stats = json.loads(path.read_text())
        else:
            results = evaluate.backtest_next_show_date(conn, holdout_shows=holdout_shows)
            stats = evaluate.summarize_next_show_date_backtest(results)
            self.models_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(stats))

        self._cache[key] = stats
        return stats

    def train_all(self, conn) -> dict:
        """Unconditionally retrains every model plus the next-date backtest stats, overwriting
        whatever is cached in memory or on disk. This is what the `train-models` CLI command
        calls after new data has been ingested."""
        self._cache.clear()
        self.models_dir.mkdir(parents=True, exist_ok=True)

        for key, (build_module, train_module) in _PREDICTOR_MODULES.items():
            rows, labels = build_module.build_training_rows(conn, before_date=date.today())
            trained_model = train_module.train(rows, labels)
            joblib.dump(trained_model, self._model_path(key))
            self._cache[key] = trained_model

        results = evaluate.backtest_next_show_date(conn, holdout_shows=10)
        stats = evaluate.summarize_next_show_date_backtest(results)
        (self.models_dir / "next_date_backtest.json").write_text(json.dumps(stats))
        self._cache["next_date_backtest"] = stats

        metadata = {"trained_at": datetime.now().isoformat()}
        (self.models_dir / "metadata.json").write_text(json.dumps(metadata))

        return {"models": list(_PREDICTOR_MODULES), "backtest": stats, "metadata": metadata}

    def train_slow(self, conn) -> dict:
        """The GRU and the three held-out backtests, kept apart from `train_all` on purpose.

        Everything in `train_all` fits in well under a second and needs only a handful of
        shows. This takes minutes, because it trains a sequence model twice over (once to
        serve, once on a reduced history to score it honestly) and replays every held-out
        show. Bundling the two would have made the ordinary retrain unusable, and would have
        made it fail outright on a database too small to hold anything out, which is exactly
        the situation a fresh install is in.

        A backtest that cannot run for want of data is recorded as skipped rather than
        raised: the models it would have scored are still worth having.
        """
        self.models_dir.mkdir(parents=True, exist_ok=True)

        bundle = running_order.train(running_order.build_training_sequences(conn))
        joblib.dump(bundle, self._model_path("running_order"))
        self._cache["running_order"] = bundle

        completed, skipped = [], {}
        for key, (module, filename) in _BACKTESTS.items():
            try:
                result = module.backtest(conn)
            except ValueError as error:
                skipped[key] = str(error)
                continue
            (self.models_dir / filename).write_text(json.dumps(result))
            self._cache[f"{key}_backtest"] = result
            completed.append(key)

        return {
            "sequence_model": "running_order",
            "trained_on_shows": bundle["trained_on_shows"],
            "backtests": completed,
            "skipped": skipped,
        }
