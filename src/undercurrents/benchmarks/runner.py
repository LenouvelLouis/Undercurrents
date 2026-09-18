"""Runs every benchmark and writes one JSON the API can serve.

Results are stored rather than computed per request: training a GRU on each page load would
be absurd, and a stored file also means the numbers shown in the app are exactly the ones
produced by a dated run, not something that quietly drifts.
"""

import json
from datetime import datetime
from pathlib import Path

from undercurrents.benchmarks import data, item2vec, sequence, tabular

DEFAULT_OUTPUT = Path("data/models/benchmarks.json")


def run_all(conn, holdout_shows: int = data.DEFAULT_HOLDOUT_SHOWS) -> dict:
    sequences = data.load_sequences(conn)
    train_sequences, test_sequences = data.split(sequences, holdout_shows)
    names = data.song_names(conn)

    results: dict = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "holdout_shows": holdout_shows,
        "total_shows": len(sequences),
        "split_note": (
            "Chronological split: the most recent shows are held out. Never random, so no "
            "model is scored on a show earlier than one it trained on."
        ),
    }

    results["sequence"] = sequence.run(train_sequences, test_sequences)

    song_ids = sorted({sid for s in train_sequences for sid in s["songs"]})
    index = {sid: i for i, sid in enumerate(song_ids)}
    vectors = item2vec.train(train_sequences, song_ids, index)
    results["item2vec"] = {
        "task": "song embeddings learned from setlist co-occurrence",
        "dimensions": item2vec.EMBED_DIM,
        "songs": len(song_ids),
        "train_shows": len(train_sequences),
        "note": (
            "Trained on the training split only. Distinct from the stored UMAP map, which "
            "projects counted co-occurrence to 2D for display rather than fitting vectors."
        ),
        "neighbours": item2vec.neighbours(vectors, song_ids, names),
    }

    split_date = datetime.strptime(test_sequences[0]["event_date"], "%Y-%m-%d").date()
    try:
        results["tabular"] = tabular.run(conn, split_date)
    except ValueError as exc:
        results["tabular"] = {"error": str(exc)}

    return results


def write(results: dict, output: Path = DEFAULT_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return output


def load(output: Path = DEFAULT_OUTPUT) -> dict | None:
    if not output.exists():
        return None
    return json.loads(output.read_text(encoding="utf-8"))
