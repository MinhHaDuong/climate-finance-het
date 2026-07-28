"""Phase outputs are tracked so that the next phase can build.

Ticket 0348. The writing workpackage renders from handoff artifacts on disk —
no uv, no corpus, Quarto and a LaTeX engine only, as each `deliverables/*/*.mk`
header states. That property holds only if every artifact a render target
depends on is carried by git. It did not: the three generated `*-vars.yml`
files were gitignored, so a fresh clone could not render any of the three
documents without first running Phase 2, which needs uv and the DVC corpus.

The guard is on the *class*, not on three filenames: any future handoff
artifact wired into a writing-side Makefile and left untracked trips it.
"""

import os
import re
import subprocess
import sys

import pytest
import yaml
from _mk_discovery import mk_fragments
from utils import BASE_DIR

# Make's PYTHONPATH carries `scripts` and the package source root, not
# `scripts/analysis`, so every test importing a compute_* module inserts it
# itself. Omitting this makes the import succeed or fail by collection order.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))

from compute_vars import DOC_VARS, DOC_VARS_FILE

# Paths a render rule can name. Deliberately excludes the rendered PDF/DOCX,
# which are regenerable outputs rather than inputs and stay ignored.
ARTIFACT_RE = re.compile(r"deliverables/[\w./-]+\.(?:yml|yaml|md|csv|png|bib)")


def _writing_makefiles():
    """The per-deliverable render fragments, via the shared discovery helper.

    Enumerating `.mk` files by hand is itself a guarded defect (ticket 0248):
    hand-rolled globs drift apart when fragments move. `mk_fragments()` is the
    single source of truth, filtered here to the Phase-3 render fragments.
    """
    return [p for p in mk_fragments() if p.parent.parent.name == "deliverables"]


def _is_tracked(relpath):
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relpath],
        cwd=BASE_DIR, capture_output=True,
    )
    return result.returncode == 0


@pytest.mark.adherence
@pytest.mark.integration
def test_vars_files_are_tracked():
    """Every -vars.yml a writing Makefile consumes must be in git."""
    untracked = []
    for mk in _writing_makefiles():
        body = mk.read_text(encoding="utf-8")
        for path in sorted(set(ARTIFACT_RE.findall(body))):
            if not path.endswith("-vars.yml"):
                continue
            if not os.path.isfile(os.path.join(BASE_DIR, path)):
                continue  # not built here; nothing to assert about
            if not _is_tracked(path):
                untracked.append(f"{mk.name} -> {path}")
    assert not untracked, (
        "handoff artifacts consumed by a writing-side Makefile are not tracked, "
        "so a fresh clone cannot render: " + "; ".join(untracked)
    )


@pytest.mark.adherence
@pytest.mark.parametrize("doc", sorted(DOC_VARS))
def test_tracked_vars_file_carries_every_declared_variable(doc):
    """Tracking the file is not enough — it must hold what the prose asks for.

    Now that the writing workpackage renders from the committed `*-vars.yml`
    rather than regenerating it, a variable added to DOC_VARS and to the prose
    but never written back to the artifact renders as an empty macro on a
    clean clone. Nothing else catches that: `test_doc_vars_complete` compares
    prose against DOC_VARS, and the tracking guard above only checks that the
    file exists in git (ticket 0329, after 0348 made these files handoff
    artifacts).
    """
    path = DOC_VARS_FILE[doc]
    if not os.path.isfile(path):
        pytest.skip(f"{path} not built here")
    with open(path, encoding="utf-8") as fh:
        present = yaml.safe_load(fh) or {}
    missing = [k for k in DOC_VARS[doc] if k not in present]
    assert not missing, (
        f"{os.path.basename(path)} is missing {len(missing)} variable(s) "
        f"declared for {doc}: {missing}. Regenerate it with `make stats` and "
        "commit the result — the render reads this file, not compute_vars.py."
    )


@pytest.mark.adherence
def test_vars_files_are_not_gitignored():
    """A tracked file can still be listed in .gitignore; catch the re-add.

    Tracking survives a stray ignore line — git keeps honouring the index — so
    this failure mode is silent until someone clones fresh or the file is
    removed and restored. Checking the ignore rules directly closes that gap.
    """
    with open(os.path.join(BASE_DIR, ".gitignore"), encoding="utf-8") as fh:
        rules = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    offenders = [r for r in rules if r.endswith("-vars.yml") and not r.startswith("!")]
    assert not offenders, (
        f".gitignore excludes handoff artifacts: {offenders} - Phase outputs are "
        "tracked so that the next phase can build"
    )
