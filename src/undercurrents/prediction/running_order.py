"""Predicting the running order of the next show: not which songs, but in what sequence.

This is a different question from `prediction.features`/`model`, which ranks every song by
the probability that it appears at all. Here the model is asked to write out the set from
the first song to the last, and the answer is judged as a sequence.

The network is the GRU already benchmarked in `benchmarks.sequence`, reused rather than
reimplemented. What is new is the decoding and, more importantly, the honesty of the
measurement. The benchmark scores the GRU with teacher forcing: at every position it is
handed the real songs played so far and asked only for the next one. A page that prints a
predicted running order cannot do that, because at prediction time there is no real prefix
to hand it. It has to run free, feeding its own guesses back in, so one early mistake
propagates through the rest of the set. Free-running accuracy is therefore much lower than
teacher-forced accuracy, and it is the free-running number this module reports, because it
is the one that describes what the page actually shows.
"""

from datetime import date

import numpy as np

from undercurrents.benchmarks import data as benchmark_data
from undercurrents.benchmarks import sequence

DEFAULT_HOLDOUT_SHOWS = 60


# --------------------------------------------------------------------------- training


def train(sequences: list[dict]) -> dict:
    """Trains the GRU and returns a bundle that survives a round trip through joblib.

    The trained `torch` module is not stored directly. Only its state dict (plain tensors)
    and the vocabulary are, so the model can be rebuilt by `build_gru` on load. That keeps
    the saved file independent of this module's class definitions.
    """
    song_ids, index = sequence._vocab(sequences)
    model, max_len = sequence.train_gru(sequences, len(song_ids), index)
    return {
        "song_ids": song_ids,
        "index": index,
        "max_len": max_len,
        "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
        "trained_on_shows": len(sequences),
    }


def restore(bundle: dict):
    """Rebuilds the network from a bundle. Kept separate from `train` so the API can load a
    persisted bundle without importing anything about how it was fitted."""
    import torch  # noqa: F401  (imported for its side effect of being available to the model)

    model = sequence.build_gru(len(bundle["song_ids"]))
    model.load_state_dict(bundle["state_dict"])
    model.eval()
    return model


# --------------------------------------------------------------------------- decoding


def _scores(model, max_len: int, prefix: list[int]) -> np.ndarray:
    return sequence.gru_scores(model, max_len, prefix)


def decode(bundle: dict, length: int, model=None, seed: list[int] | None = None) -> list[dict]:
    """Greedy free-running decode of `length` songs.

    At each step the model scores every song in the vocabulary from the sequence built so
    far, songs already placed tonight are removed from the running, and the highest
    remaining one is taken. `confidence` is that song's share of the probability mass left
    among the songs still available, which is the quantity the choice was actually made on.
    A raw softmax value over the full vocabulary would understate it by counting songs that
    were never candidates at that position.
    """
    model = model or restore(bundle)
    song_ids = bundle["song_ids"]
    max_len = bundle["max_len"]

    prefix: list[int] = list(seed or [])
    order: list[dict] = []
    # only songs not already in the seed can still be placed
    length = max(0, min(int(length), len(song_ids) - len(prefix)))

    seeded = len(prefix)
    for position in range(seeded + 1, seeded + length + 1):
        scores = np.array(_scores(model, max_len, prefix), dtype=np.float64)
        scores[prefix] = -np.inf  # the band does not repeat a song inside one show
        available = scores[np.isfinite(scores)]
        total = float(available.sum()) if available.size else 0.0
        choice = int(np.argmax(scores))
        order.append(
            {
                "position": position,
                "song_id": song_ids[choice],
                "confidence": round(float(scores[choice]) / total, 4) if total > 0 else 0.0,
            }
        )
        prefix.append(choice)

    return order


# --------------------------------------------------------------------------- baselines


def _markov_bundle(sequences: list[dict]) -> dict:
    song_ids, index = sequence._vocab(sequences)
    return {
        "song_ids": song_ids,
        "index": index,
        "chain": sequence.train_markov(sequences, len(song_ids), index),
    }


def _decode_markov(bundle: dict, length: int, seed: list[int] | None = None) -> list[int]:
    chain = bundle["chain"]
    prefix: list[int] = list(seed or [])
    seeded = len(prefix)
    for _ in range(min(length, len(bundle["song_ids"]) - seeded)):
        scores = np.array(sequence.markov_scores(chain, prefix), dtype=np.float64).copy()
        scores[prefix] = -np.inf
        prefix.append(int(np.argmax(scores)))
    return prefix[seeded:]


def _decode_most_played(sequences: list[dict], index: dict[int, int], length: int) -> list[int]:
    """The flattest baseline there is: the N most played songs, in descending play count,
    the same set every night. It exists because a sequence model that cannot beat it is not
    telling you anything you could not read off a leaderboard."""
    counts: dict[int, int] = {}
    for show in sequences:
        for song_id in show["songs"]:
            if song_id in index:
                counts[index[song_id]] = counts.get(index[song_id], 0) + 1
    ranked = sorted(counts, key=lambda i: -counts[i])
    return ranked[:length]


# --------------------------------------------------------------------------- backtest


def _score_order(predicted: list[int], actual: list[int]) -> tuple[int, int]:
    """Songs correctly included, and songs correctly placed at the exact position."""
    included = len(set(predicted) & set(actual))
    exact = sum(1 for p, a in zip(predicted, actual) if p == a)
    return included, exact


SEED_LENGTHS = (0, 1, 3, 5)


def backtest(conn, holdout_shows: int = DEFAULT_HOLDOUT_SHOWS) -> dict:
    """Trains on everything before the last `holdout_shows` shows, then asks each method to
    write out the rest of each held-out set.

    The sweep over seed lengths is the point. With no seed the model has to invent the whole
    night from nothing and does badly, worse than a static list of the most played songs.
    Handed the real first few songs it does much better, because that is the regime the
    benchmark measured: the GRU's strength is continuing a set, not conjuring one. Reporting
    only the flattering end of that range would misdescribe the page, so every seed length
    is reported, baselines included, scored on the songs after the seed.
    """
    sequences = benchmark_data.load_sequences(conn)
    train_sequences, test_sequences = benchmark_data.split(sequences, holdout_shows)

    bundle = train(train_sequences)
    model = restore(bundle)
    index = bundle["index"]
    markov = _markov_bundle(train_sequences)
    most_played_ranking = _decode_most_played(train_sequences, index, len(index))

    runs = []
    for seed_length in SEED_LENGTHS:
        totals = {"gru": [0, 0], "markov": [0, 0], "most_played": [0, 0]}
        songs_total = 0
        shows_scored = 0

        for show in test_sequences:
            actual = [index[s] for s in show["songs"] if s in index]
            if len(actual) <= seed_length:
                continue  # nothing left to predict once the seed covers the whole set
            seed, remaining = actual[:seed_length], actual[seed_length:]
            length = len(remaining)
            songs_total += length
            shows_scored += 1

            gru_order = [
                index[entry["song_id"]]
                for entry in decode(bundle, length, model=model, seed=list(seed))
            ]
            markov_order = _decode_markov(markov, length, seed=list(seed))
            # the static list, minus anything the seed already used up
            static = [s for s in most_played_ranking if s not in seed][:length]

            for name, predicted in (
                ("gru", gru_order), ("markov", markov_order), ("most_played", static)
            ):
                included, exact = _score_order(predicted, remaining)
                totals[name][0] += included
                totals[name][1] += exact

        def summarise(name: str) -> dict:
            included, exact = totals[name]
            return {
                "songs_included": round(included / songs_total, 4) if songs_total else 0.0,
                "exact_position": round(exact / songs_total, 4) if songs_total else 0.0,
            }

        gru = summarise("gru")
        baselines = {"markov": summarise("markov"), "most_played": summarise("most_played")}
        best = max(b["songs_included"] for b in baselines.values())
        runs.append(
            {
                "seed_length": seed_length,
                "shows_scored": shows_scored,
                "songs_scored": songs_total,
                "model": gru,
                "baselines": {
                    "markov": {"name": "first-order Markov, same decode", **baselines["markov"]},
                    "most_played": {
                        "name": "the most played songs, every night",
                        **baselines["most_played"],
                    },
                },
                "songs_included_delta": round(gru["songs_included"] - best, 4),
                "winner": (
                    "model" if gru["songs_included"] > best
                    else ("tie" if gru["songs_included"] == best else "baseline")
                ),
            }
        )

    wins = [r for r in runs if r["winner"] == "model"]
    return {
        "task": "the rest of tonight's set, in order, given the songs played so far",
        "train_shows": len(train_sequences),
        "test_shows": len(test_sequences),
        "runs": runs,
        "model_beats_baselines_from_seed": min((r["seed_length"] for r in wins), default=None),
        "production": _backtest_production_seed(
            bundle, model, index, test_sequences, most_played_ranking
        ),
    }


PRODUCTION_SEED_SONGS = 3


def _backtest_production_seed(bundle, model, index, test_sequences, most_played_ranking) -> dict:
    """The setup the page actually runs in, scored on its own terms.

    Every run in the sweep above hands the model the real opening of the show it is being
    scored on. Before a show has happened nobody has that, so the page seeds with the opening
    of the *previous* show instead. Those seeded songs are then guesses about tonight like any
    other, so here they are scored as predictions rather than given for free, and the whole
    proposed set is compared against the whole real one.

    `opener_repeat_rate` is the assumption laid bare: how often the next show really does open
    with the same song. It is what separates the sweep's flattering numbers from this one.
    """
    songs_total = 0
    hits = {"gru": [0, 0], "most_played": [0, 0]}
    opener_repeats = 0
    comparisons = 0

    for previous, show in zip(test_sequences, test_sequences[1:]):
        actual = [index[s] for s in show["songs"] if s in index]
        previous_songs = [index[s] for s in previous["songs"] if s in index]
        if not actual or not previous_songs:
            continue

        seed = previous_songs[:PRODUCTION_SEED_SONGS]
        length = len(actual)
        songs_total += length
        comparisons += 1
        if actual[0] == previous_songs[0]:
            opener_repeats += 1

        decoded = [index[e["song_id"]] for e in decode(bundle, max(0, length - len(seed)), model=model, seed=list(seed))]
        proposed = (seed + decoded)[:length]
        for name, predicted in (("gru", proposed), ("most_played", most_played_ranking[:length])):
            included, exact = _score_order(predicted, actual)
            hits[name][0] += included
            hits[name][1] += exact

    def summarise(name: str) -> dict:
        included, exact = hits[name]
        return {
            "songs_included": round(included / songs_total, 4) if songs_total else 0.0,
            "exact_position": round(exact / songs_total, 4) if songs_total else 0.0,
        }

    gru = summarise("gru")
    baseline = summarise("most_played")
    return {
        "seed": "the opening of the previous show, scored as a prediction like the rest",
        "shows_scored": comparisons,
        "songs_scored": songs_total,
        "opener_repeat_rate": round(opener_repeats / comparisons, 4) if comparisons else 0.0,
        "model": gru,
        "baseline": {"name": "the most played songs, every night", **baseline},
        "songs_included_delta": round(gru["songs_included"] - baseline["songs_included"], 4),
        "winner": (
            "model" if gru["songs_included"] > baseline["songs_included"]
            else ("tie" if gru["songs_included"] == baseline["songs_included"] else "baseline")
        ),
    }


# --------------------------------------------------------------------------- serving


def build_training_sequences(conn, before_date: date | None = None) -> list[dict]:
    sequences = benchmark_data.load_sequences(conn)
    if before_date is None:
        return sequences
    cutoff = before_date.isoformat()
    return [s for s in sequences if s["event_date"] < cutoff]


def recent_show_prefix(conn, songs: int = 3) -> list[dict]:
    """The opening songs of the most recent show, the natural seed for a prediction made
    before anyone has heard tonight's set."""
    sequences = benchmark_data.load_sequences(conn)
    if not sequences:
        return []
    latest = sequences[-1]
    return [{"song_id": song_id} for song_id in latest["songs"][:songs]]
