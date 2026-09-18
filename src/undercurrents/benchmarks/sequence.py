"""Next-song-in-the-set prediction: a GRU against the first-order Markov chain.

The app's Transition Graph already answers "what follows song X" with a first-order Markov
chain built from counted transitions. That is the baseline here, and it is a strong one:
setlists repeat heavily, so knowing only the previous song already gets you a long way. The
GRU's claim is that the whole prefix of tonight's set carries more signal than its last
song alone. This module tests that claim and reports whichever way it falls.

Both models get the same constraint at prediction time: a song already played tonight is
masked out. The band effectively never repeats a song within a show, so allowing repeats
would penalise both models for the same irrelevant reason. Applying it to both keeps the
comparison fair rather than flattering either one.
"""

import numpy as np

SEED = 42
EMBED_DIM = 64
HIDDEN_DIM = 128
EPOCHS = 60
BATCH_SIZE = 32
LEARNING_RATE = 3e-3


def _vocab(sequences: list[dict]) -> tuple[list[int], dict[int, int]]:
    song_ids = sorted({sid for s in sequences for sid in s["songs"]})
    return song_ids, {sid: i for i, sid in enumerate(song_ids)}


# --------------------------------------------------------------------------- baseline


def train_markov(train_sequences: list[dict], n_songs: int, index: dict[int, int]) -> dict:
    """Counted transitions plus a counted opener distribution, with add-one smoothing so an
    unseen pair scores above zero instead of being impossible."""
    transitions = np.ones((n_songs, n_songs), dtype=np.float64)
    openers = np.ones(n_songs, dtype=np.float64)
    for show in train_sequences:
        songs = [index[s] for s in show["songs"] if s in index]
        if not songs:
            continue
        openers[songs[0]] += 1
        for a, b in zip(songs, songs[1:]):
            transitions[a, b] += 1
    transitions /= transitions.sum(axis=1, keepdims=True)
    openers /= openers.sum()
    return {"transitions": transitions, "openers": openers}


def markov_scores(model: dict, prefix: list[int]) -> np.ndarray:
    if not prefix:
        return model["openers"]
    return model["transitions"][prefix[-1]]


# --------------------------------------------------------------------------- GRU


def build_gru(n_songs: int):
    """The network itself, built at module level rather than inside `train_gru` so that a
    trained model can be reconstructed from a saved state dict. `prediction.running_order`
    relies on that to serve the model from the API without retraining on every request."""
    import torch.nn as nn

    class NextSongGRU(nn.Module):
        def __init__(self):
            super().__init__()
            # index 0 is a dedicated start token, so the model can score the opener from an
            # empty prefix the same way it scores any later position.
            self.embed = nn.Embedding(n_songs + 1, EMBED_DIM)
            self.gru = nn.GRU(EMBED_DIM, HIDDEN_DIM, batch_first=True)
            self.out = nn.Linear(HIDDEN_DIM, n_songs)

        def forward(self, x):
            emb = self.embed(x)
            _, hidden = self.gru(emb)
            return self.out(hidden[-1])

    return NextSongGRU()


def train_gru(train_sequences: list[dict], n_songs: int, index: dict[int, int]):
    import torch

    torch.manual_seed(SEED)

    examples = []
    for show in train_sequences:
        songs = [index[s] for s in show["songs"] if s in index]
        for i in range(len(songs)):
            prefix = [0] + [s + 1 for s in songs[:i]]
            examples.append((prefix, songs[i]))
    if not examples:
        raise ValueError("No training examples could be built from these sequences")

    max_len = max(len(p) for p, _ in examples)
    padded = np.zeros((len(examples), max_len), dtype=np.int64)
    targets = np.zeros(len(examples), dtype=np.int64)
    for row, (prefix, target) in enumerate(examples):
        padded[row, max_len - len(prefix):] = prefix  # left pad, so the last step is real
        targets[row] = target

    model = build_gru(n_songs)
    optimiser = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn = torch.nn.CrossEntropyLoss()
    x_all = torch.from_numpy(padded)
    y_all = torch.from_numpy(targets)

    generator = torch.Generator().manual_seed(SEED)
    model.train()
    for _ in range(EPOCHS):
        order = torch.randperm(len(examples), generator=generator)
        for start in range(0, len(examples), BATCH_SIZE):
            batch = order[start:start + BATCH_SIZE]
            optimiser.zero_grad()
            loss = loss_fn(model(x_all[batch]), y_all[batch])
            loss.backward()
            optimiser.step()
    model.eval()
    return model, max_len


def gru_scores(model, max_len: int, prefix: list[int]) -> np.ndarray:
    import torch

    tokens = [0] + [s + 1 for s in prefix]
    tokens = tokens[-max_len:]
    padded = np.zeros((1, max_len), dtype=np.int64)
    padded[0, max_len - len(tokens):] = tokens
    with torch.no_grad():
        logits = model(torch.from_numpy(padded))
    return torch.softmax(logits, dim=1).numpy()[0]


# --------------------------------------------------------------------------- scoring


def _evaluate(score_fn, test_sequences: list[dict], index: dict[int, int], n_songs: int) -> dict:
    top1 = top5 = total = 0
    for show in test_sequences:
        songs = [index[s] for s in show["songs"] if s in index]
        played: list[int] = []
        for target in songs:
            scores = np.array(score_fn(played), dtype=np.float64).copy()
            # same mask for every model: a song already played tonight is not a candidate
            for already in played:
                scores[already] = -np.inf
            ranked = np.argsort(-scores)
            if ranked[0] == target:
                top1 += 1
            if target in ranked[:5]:
                top5 += 1
            total += 1
            played.append(target)
    if total == 0:
        return {"top_1_accuracy": 0.0, "top_5_accuracy": 0.0, "predictions": 0}
    return {
        "top_1_accuracy": round(top1 / total, 4),
        "top_5_accuracy": round(top5 / total, 4),
        "predictions": total,
    }


def run(train_sequences: list[dict], test_sequences: list[dict]) -> dict:
    song_ids, index = _vocab(train_sequences)
    n_songs = len(song_ids)

    markov = train_markov(train_sequences, n_songs, index)
    baseline = _evaluate(lambda prefix: markov_scores(markov, prefix), test_sequences, index, n_songs)

    model, max_len = train_gru(train_sequences, n_songs, index)
    neural = _evaluate(lambda prefix: gru_scores(model, max_len, prefix), test_sequences, index, n_songs)

    delta = round(neural["top_1_accuracy"] - baseline["top_1_accuracy"], 4)
    return {
        "task": "next song in the set, given everything played so far tonight",
        "vocabulary": n_songs,
        "train_shows": len(train_sequences),
        "test_shows": len(test_sequences),
        "baseline": {"name": "first-order Markov chain", **baseline},
        "model": {
            "name": f"GRU (embed {EMBED_DIM}, hidden {HIDDEN_DIM}, {EPOCHS} epochs)",
            **neural,
        },
        "top_1_delta": delta,
        "winner": "model" if delta > 0 else ("tie" if delta == 0 else "baseline"),
    }
