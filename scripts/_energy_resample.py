"""CPU S2 resampling using one distance matrix per year and window.

Energy distance is ``-c.T @ D @ c`` for signed group weights ``c``.  The
same pairwise distances are reused for every bootstrap, permutation, and
equal-size subsample replicate.  Seeds and draws match the original loops.
"""

import numpy as np
from scipy.spatial.distance import cdist


def _distance_matrix(x, y):
    pooled = np.vstack((x, y))
    return cdist(pooled, pooled, metric="euclidean")


def _statistics(distance, weights):
    return -np.einsum("ij,ij->i", weights @ distance, weights)


def _weights(n_before, n_after, before_indices, after_indices):
    weights = np.zeros(n_before + n_after, dtype=np.float64)
    weights[:n_before] = np.bincount(before_indices, minlength=n_before) / len(before_indices)
    weights[n_before:] = -np.bincount(after_indices, minlength=n_after) / len(after_indices)
    return weights


def bootstrap_energy(x, y, k, seed):
    """Return K S2 bootstrap values with the original per-replicate seeds."""
    n_before, n_after = len(x), len(y)
    distance = _distance_matrix(x, y)
    weights = np.empty((k, n_before + n_after), dtype=np.float64)
    for i in range(k):
        rng = np.random.RandomState(seed + i)
        before = rng.choice(n_before, n_before, replace=True)
        after = rng.choice(n_after, n_after, replace=True)
        weights[i] = _weights(n_before, n_after, before, after)
    return _statistics(distance, weights).tolist()


def permutation_energy(x, y, n_perm, rng):
    """Return the original five null-model statistics using cached distances."""
    n_before, n_after = len(x), len(y)
    n = n_before + n_after
    distance = _distance_matrix(x, y)
    observed_weights = _weights(n_before, n_after, np.arange(n_before), np.arange(n_after))
    observed = float(_statistics(distance, observed_weights[None, :])[0])

    indices = np.arange(n)
    weights = np.empty((n_perm, n), dtype=np.float64)
    for i in range(n_perm):
        rng.shuffle(indices)
        weights[i].fill(0.0)
        weights[i, indices[:n_before]] = 1.0 / n_before
        weights[i, indices[n_before:]] = -1.0 / n_after

    null_stats = _statistics(distance, weights)
    null_mean = float(np.mean(null_stats))
    null_std = float(np.std(null_stats))
    z = (observed - null_mean) / null_std if null_std > 0 else 0.0
    p = float(np.mean(null_stats >= observed))
    return observed, null_mean, null_std, z, p


def subsample_energy(x, y, r_replicates, seed, year, window):
    """Return equal-size S2 subsample values using the original RNG streams."""
    from _divergence_io import _make_subsample_rng

    n_before, n_after = len(x), len(y)
    n = min(n_before, n_after)
    distance = _distance_matrix(x, y)
    weights = np.empty((r_replicates, n_before + n_after), dtype=np.float64)
    for i in range(r_replicates):
        rng = _make_subsample_rng(seed, year, window, i)
        before = rng.choice(n_before, n, replace=False) if n_before > n else np.arange(n_before)
        after = rng.choice(n_after, n, replace=False) if n_after > n else np.arange(n_after)
        weights[i] = _weights(n_before, n_after, before, after)
    return _statistics(distance, weights).tolist()
