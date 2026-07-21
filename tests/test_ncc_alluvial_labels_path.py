"""plot_ncc_alluvial.py must read cluster_labels.json alongside --input.

Regression pin for ticket 0265: the script gated its primary tab_alluvial.csv
read on --input but read the secondary cluster_labels.json unconditionally from
the module-level DERIVED_TABLES_DIR constant. When --input redirects the data
elsewhere (test harness, companion-paper variant), the labels file was looked
up in the wrong place. This is the same bug shape fixed for plot_fig_alluvial.py
and plot_fig2_composition.py in ticket 0262 (PR #1049).

The test points --input at a tmp directory holding both files and points
CLIMATE_FINANCE_DATA (hence DERIVED_TABLES_DIR) at an EMPTY tree. Buggy code
falls back to DERIVED_TABLES_DIR, fails to find cluster_labels.json, and exits
non-zero. Fixed code derives the labels dir from the --input path and succeeds.
"""

import json
import os
import subprocess
import sys

import pytest
from _source_roots import source_root_env

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
SCRIPT = os.path.join(SCRIPTS_DIR, "figures", "plot_ncc_alluvial.py")

# Minimal valid alluvial table: period (index) x cluster columns 0..3, counts.
_ALLUVIAL_CSV = (
    "period,0,1,2,3\n"
    "1990-2006,10,5,3,2\n"
    "2007-2014,4,12,6,8\n"
    "2015-2025,2,7,15,9\n"
)
_CLUSTER_LABELS = {"0": "Finance", "1": "Policy", "2": "Adaptation", "3": "Markets"}


@pytest.mark.integration
def test_cluster_labels_read_from_input_dir(tmp_path):
    """--input redirects both tab_alluvial.csv and cluster_labels.json reads."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "tab_alluvial.csv").write_text(_ALLUVIAL_CSV)
    (input_dir / "cluster_labels.json").write_text(json.dumps(_CLUSTER_LABELS))

    # DERIVED_TABLES_DIR resolves under CLIMATE_FINANCE_DATA/derived/tables.
    # Point it at an EMPTY tree: a buggy fallback there cannot find the labels.
    empty_data = tmp_path / "empty_data"
    (empty_data / "derived" / "tables").mkdir(parents=True)

    output = tmp_path / "fig_ncc_alluvial.png"
    env = source_root_env({
        **os.environ,
        "CLIMATE_FINANCE_DATA": str(empty_data),
        "MPLBACKEND": "Agg",
        "SOURCE_DATE_EPOCH": "0",
    })
    result = subprocess.run(
        [
            sys.executable, SCRIPT,
            "--output", str(output),
            "--input", str(input_dir / "tab_alluvial.csv"),
        ],
        capture_output=True, text=True, env=env, timeout=120,
    )

    assert result.returncode == 0, (
        "plot_ncc_alluvial.py failed with --input redirected away from "
        f"DERIVED_TABLES_DIR (labels not read alongside --input?):\n{result.stderr}"
    )
    assert output.exists(), "expected output figure was not written"
