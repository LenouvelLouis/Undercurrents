"""Learned song embeddings: skip-gram with negative sampling over setlists.

Each setlist is treated as a sentence and each song as a word, so two songs end up close
when they keep turning up in the same sets. This is a different object from the UMAP map
the clustering pipeline already stores: UMAP projects a counted co-occurrence matrix down
to 2D for display, while these vectors are fitted by gradient descent and live in a higher
dimensional space, which is what makes nearest-neighbour queries meaningful.

It is trained on the training split only, so the neighbours it reports are not informed by
the shows held out for scoring.
"""

import numpy as np

SEED = 42
EMBED_DIM = 48
EPOCHS = 120
NEGATIVES = 8
LEARNING_RATE = 5e-3
BATCH_PAIRS = 512


def train(train_sequences: list[dict], song_ids: list[int], index: dict[int, int]):
    import torch
    import torch.nn as nn

    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)

    # Every unordered pair within a setlist is a positive example: within a set there is no
    # meaningful "window", the whole night is the context.
    pairs = []
    for show in train_sequences:
        songs = sorted({index[s] for s in show["songs"] if s in index})
        for i, a in enumerate(songs):
            for b in songs[i + 1:]:
                pairs.append((a, b))
                pairs.append((b, a))
    if not pairs:
        raise ValueError("No co-occurring song pairs in the training split")

    pairs_arr = np.array(pairs, dtype=np.int64)
    n_songs = len(song_ids)

    # Negative sampling follows the unigram^0.75 distribution, the usual choice: it draws
    # frequent songs often enough to be informative without letting them dominate.
    counts = np.bincount(pairs_arr[:, 0], minlength=n_songs).astype(np.float64)
    noise = counts ** 0.75
    noise = noise / noise.sum()

    centre = nn.Embedding(n_songs, EMBED_DIM)
    context = nn.Embedding(n_songs, EMBED_DIM)
    nn.init.normal_(centre.weight, std=0.1)
    nn.init.normal_(context.weight, std=0.1)
    optimiser = torch.optim.Adam(list(centre.parameters()) + list(context.parameters()), lr=LEARNING_RATE)

    for _ in range(EPOCHS):
        order = rng.permutation(len(pairs_arr))
        for start in range(0, len(order), BATCH_PAIRS):
            batch = pairs_arr[order[start:start + BATCH_PAIRS]]
            a = torch.from_numpy(batch[:, 0])
            b = torch.from_numpy(batch[:, 1])
            negatives = torch.from_numpy(
                rng.choice(n_songs, size=(len(batch), NEGATIVES), p=noise)
            )

            optimiser.zero_grad()
            v_a = centre(a)
            positive = torch.sum(v_a * context(b), dim=1)
            negative = torch.bmm(context(negatives), v_a.unsqueeze(2)).squeeze(2)
            loss = (
                -torch.nn.functional.logsigmoid(positive).mean()
                - torch.nn.functional.logsigmoid(-negative).mean()
            )
            loss.backward()
            optimiser.step()

    vectors = centre.weight.detach().numpy()
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def neighbours(vectors: np.ndarray, song_ids: list[int], names: dict[int, str], top_k: int = 6) -> list[dict]:
    """Cosine nearest neighbours for every song, from the normalised vectors."""
    similarity = vectors @ vectors.T
    np.fill_diagonal(similarity, -np.inf)
    results = []
    for i, song_id in enumerate(song_ids):
        ranked = np.argsort(-similarity[i])[:top_k]
        results.append(
            {
                "song_id": song_id,
                "song_name": names.get(song_id, "Unknown"),
                "neighbours": [
                    {
                        "song_id": song_ids[j],
                        "song_name": names.get(song_ids[j], "Unknown"),
                        "similarity": round(float(similarity[i][j]), 4),
                    }
                    for j in ranked
                ],
            }
        )
    return results
