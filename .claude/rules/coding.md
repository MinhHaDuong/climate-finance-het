---
paths:
  - "scripts/**/*.py"
  - "tests/**/*.py"
  - "Makefile"
  - "dvc.yaml"
  - "pyproject.toml"
  - "config/**/*"
---

# Coding Rules (project-specific)

Generic coding rules are in `~/.claude/rules/coding.md`. This file adds project-specific conventions.

## Python

- **Centralize research parameters.** Constants belong in `config/analysis.yaml`, read via `load_analysis_config()`.
- **Logging**: `from utils import get_logger; log = get_logger("script_name")`.
- Torch extras: `--extra cpu` (doudou) or `--extra cu130` (padme).
- **Always `uv run`**: never bare `python3`, never `.venv/bin/python`. In Makefiles: inline `uv run python`. Deps in `pyproject.toml`.
- **Direct script runs need the source roots** (ticket 0253). `uv run python scripts/x.py` outside `make` only resolves `from utils import …` / `import openalex_corpus` when the two source roots are on `PYTHONPATH` — `make` exports them, a bare shell does not. Run scripts via `make`, or set `PYTHONPATH=scripts:libs/openalex-corpus/src` for the invocation. The rule: source roots (`scripts` + `libs/openalex-corpus/src`) are placed on the path in every execution context — pytest (pythonpath), make (export), test subprocesses (explicit env), containers (ENV), archive scripts/Makefiles — never assumed ambient.
- **Formatter strips unused imports**: add an import AND its first usage in the same Edit call. If split across calls, Read the file after adding the import to verify it survived the formatter. A PostToolUse warning "formatter modified the file" means check the import immediately.

## Testing

- **Mock os guards**: when mocking `pd.read_csv` on `pipeline_loaders`, also mock `os.path.exists` — `load_refined_works()` checks file existence before reading. Same pattern for any loader that guards with existence checks.
- **Sampling-semantics tests**: for any function named `bootstrap`, `permutation`, `resample`, `subsample`, or `monte_carlo`, schema + row-count assertions are insufficient. Assert the sampling distribution matches the function name (e.g., bootstrap: resample size == input size, duplicates expected across draws).

Typing policy — core modules must be fully typed, enforced by mypy in `test_script_hygiene.py::TestTypingCoreModules` (which owns the canonical module list). When touching a core module, annotations are required on new/changed functions. Do NOT type: `main()` bodies, plot scripts, DataFrame column access, one-off scripts.

### Test tiers — classify by cost, not mechanism (tickets 0213/0214)

Markers gate which `make` target runs a test. Pick the tier by **cost**, not by the mechanism it happens to use:

| Tier | Marker | Belongs here | Gate |
|------|--------|--------------|------|
| fast | *(none)* | pure-Python logic; pandas/numpy fine; **no** dcor/torch/ot/matplotlib, no subprocess, no lint | `make check-fast` |
| integration | `@pytest.mark.integration` | spawns a subprocess / drives a script / sleep-based timing | `make check` |
| slow | `@pytest.mark.slow` | network, real data, a heavy numerical dependency (dcor/torch/ot/sentence_transformers), or heavy compute | `make check` |
| adherence | `@pytest.mark.adherence` | ruff / mypy / hygiene / contracts | `make lint` |

`make check-fast` = `-m "not slow and not integration and not adherence"` (the inner loop — must stay pure logic). `make lint` = `-m adherence`. `make check` runs everything. No coverage is lost by moving a test to a slower tier — `make check` still runs it before every PR.

Two guards keep the fast tier honest (ticket 0216, owned by `tests/test_fast_path_budget.py` + `tests/conftest.py`):

- **Auto-mark** — a collection hook marks any test whose module imports a heavy dependency (dcor/torch/ot/sentence_transformers/matplotlib) `slow` automatically, so you rarely mark those by hand. `import dcor` alone costs ~7s (numba JIT), so this is the deterministic fix for the per-worker import tax.
- **Ratchet** — an `adherence` test fails if any fast-path test on the last recorded run exceeds the budget in `[tool.fast_path_ratchet]` (pyproject). Heavy *compute* that no heavy *import* reveals lands here: give it `slow` (heavy compute / real data) or `integration` (subprocess). Refresh timings with `make test-durations` (serial, so the budget measures true cost, not xdist contention).

## Testing

- Acceptance tests (e.g., `make corpus-validate`) are the top-level contract — never weaken without discussion.

## Build (Make)

- `make` builds all documents. `make manuscript` builds manuscript only. `make papers` builds the 3 companions. `make figures` regenerates all figures (byte-reproducible).
- Add `*.stamp` to `.gitignore` for sentinel stamps.
