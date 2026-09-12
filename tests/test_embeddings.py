import numpy as np

from undercurrents.clustering.embeddings import compute_2d_embedding


def _random_matrix(n_samples=20, n_features=8, seed=0):
    rng = np.random.default_rng(seed)
    return rng.random((n_samples, n_features))


def test_compute_2d_embedding_returns_expected_shape():
    matrix = _random_matrix()
    embedding = compute_2d_embedding(matrix)
    assert embedding.shape == (20, 2)


def test_compute_2d_embedding_is_reproducible_with_fixed_seed():
    matrix = _random_matrix()
    embedding_1 = compute_2d_embedding(matrix)
    embedding_2 = compute_2d_embedding(matrix)
    np.testing.assert_allclose(embedding_1, embedding_2)


def test_compute_2d_embedding_handles_small_inputs():
    matrix = _random_matrix(n_samples=4, n_features=3)
    embedding = compute_2d_embedding(matrix)
    assert embedding.shape == (4, 2)
