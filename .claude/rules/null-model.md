---
paths:
  - "scripts/compute_null_model.py"
  - "scripts/_permutation_accel.py"
  - "scripts/analysis/divergence.mk"
---

# Architecture — null model acceleration

Split from `architecture.md` (pipeline phases, Phase-2 rules, artifact homes); siblings: `deliverables.md`, `data-location.md`, `openalex-corpus.md`, `null-model.md`.

## Null model acceleration

The permutation null models in `scripts/compute_null_model.py` use three complementary acceleration strategies, all in `scripts/_permutation_accel.py`:

- **GPU-vectorized permutations** for `S2_energy` and `S1_MMD`: the pairwise distance / kernel matrix is computed once on GPU, then all permutation statistics are batched in a single matmul (`stats = -((C @ D) * C).sum(dim=1)`). Auto-detected when CUDA is available.
- **Precomputed TF-IDF** for `L1`: the vectorizer runs once per window; permutations only reshuffle row indices into the sparse matrix — eliminating redundant `vectorizer.transform()` calls per (year, window).
- **CPU parallel via joblib** across (year, window) pairs for `G2_spectral`, `G9_community`, and `L2`. Default `n_jobs=1` at the API boundary preserves test determinism; the CLI exposes `--n-jobs` (`-1` = all cores) for production runs.

The Makefile knob is `NJOBS` (in `scripts/analysis/divergence.mk`). Default `-1` uses all cores — fine for a single method, oversubscribes under `make -jN`. When composing with `-j`, pass `NJOBS ≈ cores/N` (e.g. on 24 cores: `make -j4 NJOBS=6 null-model`). End-to-end on padme: ~3h → ~7min.
