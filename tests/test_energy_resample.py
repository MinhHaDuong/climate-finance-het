"""Cached S2 resampling must reproduce the original CPU statistics."""

import os
import sys

import dcor
import numpy as np

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "analysis"))

from compute_divergence_bootstrap import bootstrap_one_window
from compute_divergence_subsampled import subsample_one_window
from _permutation_io import permutation_test


def _samples():
    rng = np.random.RandomState(19)
    return rng.randn(7, 4), rng.randn(9, 4) + 0.3


def test_cached_energy_bootstrap_matches_original_replicates():
    from _energy_resample import bootstrap_energy

    x, y = _samples()
    expected = bootstrap_one_window(x, y, dcor.energy_distance, 12, 42)
    actual = bootstrap_energy(x, y, 12, 42)
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)


def test_cached_energy_permutations_match_original_rng_sequence():
    from _energy_resample import permutation_energy

    x, y = _samples()
    expected = permutation_test(x, y, dcor.energy_distance, 12, np.random.RandomState(42))
    actual = permutation_energy(x, y, 12, np.random.RandomState(42))
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)


def test_cached_energy_subsample_matches_original_replicates():
    from _energy_resample import subsample_energy

    x, y = _samples()
    expected = subsample_one_window(x, y, dcor.energy_distance, 12, 42, 2008, 3)
    actual = subsample_energy(x, y, 12, 42, 2008, 3)
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)
