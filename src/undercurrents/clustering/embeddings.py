import numpy as np
import umap

RANDOM_STATE = 42
DEFAULT_N_NEIGHBORS = 15


def compute_2d_embedding(matrix: np.ndarray, n_neighbors: int = DEFAULT_N_NEIGHBORS) -> np.ndarray:
    """Projects `matrix` (n_samples, n_features) to 2D with a fixed random seed, so two runs
    on unchanged data produce the same coordinates. `n_neighbors` is capped below n_samples
    so this also works on the small inputs used in tests."""
    n_samples = matrix.shape[0]
    effective_neighbors = max(2, min(n_neighbors, n_samples - 1))
    # UMAP's default "spectral" initialization computes n_components+1 eigenvectors of an
    # n_samples x n_samples graph; when n_samples is that small or smaller, scipy's sparse
    # eigensolver can't satisfy k < N and raises. Only real-world consequence is on tiny
    # inputs (small test fixtures here), not the ~150-1000 row matrices this is run on.
    init = "random" if n_samples <= 4 else "spectral"
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=effective_neighbors,
        random_state=RANDOM_STATE,
        n_jobs=1,
        init=init,
    )
    return reducer.fit_transform(matrix)
