"""Cached S2 resampling must reproduce the original CPU statistics."""

import os
import sys

import numpy as np
import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "analysis"))

from _permutation_io import permutation_test
from compute_divergence_bootstrap import bootstrap_one_window
from compute_divergence_subsampled import subsample_one_window

pytestmark = pytest.mark.wp_corpus

def _samples(dtype):
    rng = np.random.RandomState(19)
    return rng.randn(7, 4).astype(dtype), (rng.randn(9, 4) + 0.3).astype(dtype)


def _tolerance(dtype):
    # dcor sums float32 distances in float32; cached BLAS uses float64.
    return 2e-5 if dtype is np.float32 else 1e-10


def _original_statistic(tmp_path, monkeypatch):
    # dcor's Numba cache needs a writable locator in the read-only shared env.
    monkeypatch.setenv("NUMBA_CACHE_DIR", str(tmp_path))
    import dcor

    return dcor.energy_distance


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_cached_energy_bootstrap_matches_original_replicates(dtype, tmp_path, monkeypatch):
    from _energy_resample import bootstrap_energy

    x, y = _samples(dtype)
    expected = bootstrap_one_window(x, y, _original_statistic(tmp_path, monkeypatch), 12, 42)
    actual = bootstrap_energy(x, y, 12, 42)
    np.testing.assert_allclose(actual, expected, rtol=_tolerance(dtype), atol=_tolerance(dtype))


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_cached_energy_permutations_match_original_rng_sequence(dtype, tmp_path, monkeypatch):
    from _energy_resample import permutation_energy

    x, y = _samples(dtype)
    expected = permutation_test(
        x, y, _original_statistic(tmp_path, monkeypatch), 12, np.random.RandomState(42)
    )
    actual = permutation_energy(x, y, 12, np.random.RandomState(42))
    np.testing.assert_allclose(actual, expected, rtol=_tolerance(dtype), atol=_tolerance(dtype))


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_cached_energy_subsample_matches_original_replicates(dtype, tmp_path, monkeypatch):
    from _energy_resample import subsample_energy

    x, y = _samples(dtype)
    expected = subsample_one_window(
        x, y, _original_statistic(tmp_path, monkeypatch), 12, 42, 2008, 3
    )
    actual = subsample_energy(x, y, 12, 42, 2008, 3)
    np.testing.assert_allclose(actual, expected, rtol=_tolerance(dtype), atol=_tolerance(dtype))
