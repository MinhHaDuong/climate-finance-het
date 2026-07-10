"""Duration-ratchet guard + heavy-import auto-mark (ticket 0216).

Two enforcement layers keep heavy tests off the fast inner loop
(`make check-fast` = `-m "not slow and not integration and not adherence"`):

1. **Auto-mark** — a collection-time hook (in ``conftest.py``) marks every test
   whose module statically imports a heavy dependency (dcor / torch / ot /
   sentence_transformers / matplotlib) with ``slow``. This is the robust fix for
   the dcor import tax: ``import dcor`` costs ~7s (numba JIT, no disk cache) and
   is paid once per xdist worker, attaching to whichever dcor test runs first —
   so per-test marking is whack-a-mole. Marking every dcor-importing module in
   one stroke is deterministic.

2. **Ratchet** — this file's ``adherence`` test reads the per-test durations
   recorded on the last run and fails if any *fast-path* test (one carrying none
   of slow/integration/adherence) exceeds the budget. This backstops heavy
   *compute* that no heavy *import* reveals.

The pure detection/selection logic lives in ``tests/_tier_autoscan.py`` so both
this test and ``conftest.py`` share one implementation, and so the logic is unit
-testable without spinning a real collection.
"""

import os

import pytest
from _tier_autoscan import (
    HEAVY_MODULES,
    fast_path_violations,
    file_has_heavy_import,
    heavy_imports_in_source,
    load_durations,
    load_ratchet_config,
)

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Layer 1 — heavy-import detection (pure, fast tier)
# ---------------------------------------------------------------------------


class TestHeavyImportDetection:
    def test_detects_plain_import(self):
        assert heavy_imports_in_source("import dcor") == {"dcor"}

    def test_detects_from_import(self):
        assert heavy_imports_in_source("from matplotlib import pyplot") == {
            "matplotlib"
        }

    def test_detects_dotted_import(self):
        assert heavy_imports_in_source("import matplotlib.pyplot as plt") == {
            "matplotlib"
        }

    def test_detects_lazy_import_in_function_body(self):
        src = "def f():\n    import torch\n    return torch\n"
        assert heavy_imports_in_source(src) == {"torch"}

    def test_ot_word_boundary_no_false_positive(self):
        # `ot` must not match inside another module name.
        assert heavy_imports_in_source("import other_module") == set()
        assert heavy_imports_in_source("from otherpkg import x") == set()

    def test_ot_matches_exact(self):
        assert heavy_imports_in_source("import ot") == {"ot"}

    def test_torch_word_boundary(self):
        # `import torchvision` must not be read as `torch`.
        assert heavy_imports_in_source("import torchvision") == set()

    def test_pure_source_has_no_heavy_import(self):
        assert heavy_imports_in_source("import os\nimport numpy as np\n") == set()

    def test_all_heavy_modules_named(self):
        # Guard the canonical list against silent shrinkage.
        assert set(HEAVY_MODULES) == {
            "dcor",
            "torch",
            "ot",
            "sentence_transformers",
            "matplotlib",
        }

    def test_real_dcor_test_file_flagged(self):
        # test_divergence.py lazy-imports dcor inside test bodies.
        assert file_has_heavy_import(os.path.join(TESTS_DIR, "test_divergence.py"))

    def test_this_file_not_flagged(self):
        # This ratchet file imports nothing heavy — it must stay on the fast path.
        assert not file_has_heavy_import(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Layer 2 — ratchet selection logic (pure, fast tier)
# ---------------------------------------------------------------------------


class TestRatchetLogic:
    def test_flags_unmarked_fast_path_test_over_budget(self):
        records = [
            {"nodeid": "tests/test_x.py::test_heavy", "duration": 10.0, "markers": []},
            {"nodeid": "tests/test_x.py::test_light", "duration": 0.5, "markers": []},
        ]
        violations = fast_path_violations(records, budget=5.0)
        assert [nodeid for nodeid, _ in violations] == [
            "tests/test_x.py::test_heavy"
        ]
        assert violations[0][1] == 10.0

    def test_passes_when_over_budget_test_is_slow(self):
        records = [
            {
                "nodeid": "tests/test_x.py::test_heavy",
                "duration": 10.0,
                "markers": ["slow"],
            }
        ]
        assert fast_path_violations(records, budget=5.0) == []

    def test_passes_when_over_budget_test_is_integration(self):
        records = [
            {"nodeid": "n", "duration": 10.0, "markers": ["integration"]},
        ]
        assert fast_path_violations(records, budget=5.0) == []

    def test_passes_when_over_budget_test_is_adherence(self):
        records = [
            {"nodeid": "n", "duration": 10.0, "markers": ["adherence"]},
        ]
        assert fast_path_violations(records, budget=5.0) == []

    def test_under_budget_never_flags(self):
        records = [
            {"nodeid": "n", "duration": 4.9, "markers": []},
        ]
        assert fast_path_violations(records, budget=5.0) == []


class TestRatchetConfig:
    def test_budget_from_config_is_positive_float(self):
        cfg = load_ratchet_config()
        assert isinstance(cfg["budget_seconds"], float)
        assert cfg["budget_seconds"] > 0
        assert cfg["durations_file"]


# ---------------------------------------------------------------------------
# Layer 2 — the live ratchet (adherence tier)
# ---------------------------------------------------------------------------


@pytest.mark.adherence
def test_fast_path_within_budget():
    """Fail if any fast-path test on the last recorded run exceeded the budget.

    Cold-start: skip (never error) when no durations file exists yet — the guard
    activates only once `make test-durations` has recorded timings.
    """
    cfg = load_ratchet_config()
    budget = cfg["budget_seconds"]
    data = load_durations()
    if data is None:
        pytest.skip(
            f"no durations file ({cfg['durations_file']}) yet — "
            "run `make test-durations` to record fast-path timings"
        )
    violations = fast_path_violations(data["records"], budget=budget)
    if violations:
        lines = "\n".join(
            f"  {nodeid}  ({dur:.2f}s)" for nodeid, dur in violations
        )
        pytest.fail(
            f"{len(violations)} fast-path test(s) exceed the {budget:.1f}s budget.\n"
            f"{lines}\n"
            "Fix: give each a slower tier — `@pytest.mark.slow` (heavy compute / "
            "real data / heavy dep) or `@pytest.mark.integration` (spawns a "
            "subprocess). A heavy *import* is auto-marked; this is heavy *compute*."
        )
