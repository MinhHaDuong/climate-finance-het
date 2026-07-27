"""Verify DOC_VARS in compute_vars.py lists every {{< meta >}} variable.

Scans each .qmd and its {{< include >}}'d files for {{< meta X >}} shortcodes,
then checks that every variable X appears in the DOC_VARS mapping for that
document. Prevents silent empty-string rendering when a new variable is
added to prose but not registered in compute_vars.py.

This checks prose against the `DOC_VARS` dict — a source-to-source check that
catches a new variable before anyone regenerates the vars file. It is one layer
above the artifact Quarto loads, so it cannot see a key that leaves `DOC_VARS`
correct but the generated YAML short; `test_meta_macro_resolution.py` closes
that side (ticket 0363). The shortcode scan is shared between the two.
"""

import glob
import os
import sys
from pathlib import Path

import pytest
from _qmd_meta import meta_keys_used

# Allow importing from scripts/analysis/ (not on the pytest pythonpath roots)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))  # 0257
from compute_vars import DOC_VARS

DELIVERABLES = os.path.join(os.path.dirname(__file__), "..", "deliverables")


def _qmd_path(doc_name):
    """Locate a doc's .qmd under its deliverable folder (folder name may differ)."""
    matches = glob.glob(os.path.join(DELIVERABLES, "*", f"{doc_name}.qmd"))
    return matches[0] if matches else None


@pytest.mark.parametrize("doc_name", list(DOC_VARS.keys()))
def test_doc_vars_complete(doc_name):
    """Every {{< meta X >}} in doc + includes must appear in DOC_VARS."""
    qmd_path = _qmd_path(doc_name)
    if not qmd_path or not os.path.isfile(qmd_path):
        pytest.skip(f"{qmd_path} not found")

    used = meta_keys_used(Path(qmd_path))
    declared = set(DOC_VARS[doc_name])
    missing = used - declared
    assert not missing, (
        f"{doc_name}: {len(missing)} variable(s) used in prose but not in DOC_VARS: "
        f"{sorted(missing)}"
    )


@pytest.mark.parametrize("doc_name", list(DOC_VARS.keys()))
def test_doc_vars_no_extras(doc_name):
    """DOC_VARS should not list variables that no shortcode uses (dead entries)."""
    qmd_path = _qmd_path(doc_name)
    if not qmd_path or not os.path.isfile(qmd_path):
        pytest.skip(f"{qmd_path} not found")

    used = meta_keys_used(Path(qmd_path))
    declared = set(DOC_VARS[doc_name])
    extra = declared - used
    assert not extra, (
        f"{doc_name}: {len(extra)} variable(s) in DOC_VARS but unused in prose: "
        f"{sorted(extra)}"
    )
