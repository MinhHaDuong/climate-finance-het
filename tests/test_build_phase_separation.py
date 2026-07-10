"""Phase-2/Phase-3 separation for the writing workpackages (tickets 0131, 0237).

The harness Build rule requires that a writing-side build produce a deliverable
from handoff artifacts alone — no `uv run`, no data fetch. Two things enforce it:

1. The manuscript's small, byte-stable writing-facing deliverables (3 PNGs +
   tab_venues.md) are git-tracked, so a fresh worktree has them without running
   Phase 2 or pulling corpus data.
2. A standalone `manuscript.mk` renders the PDF/DOCX with prerequisites limited
   to committed prose + deliverables — no Phase-1 data dependency.

Ticket 0237 generalizes (2): each deliverable owns a Phase-3 render `.mk`
(render-only), the analysis concern `.mk` stay pure Phase-2, and no single `.mk`
mixes the two. The phase-purity guard below classifies each `.mk` by RECIPE —
a `quarto render` recipe or `.pdf:`/`.docx:` target marks Phase-3 render; a
`scripts/(analyze_|compute_|plot_|export_|summarize_|build_het)` recipe marks
Phase-2 compute — and fails any file that carries both.
"""

import glob
import os
import re
import subprocess

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
MANUSCRIPT_MK = os.path.join(REPO_ROOT, "deliverables", "manuscript", "manuscript.mk")

# ── Phase-purity guard (ticket 0237) ─────────────────────────────────────────
# Classify by RECIPE, not by any target-string convention.
_RENDER_RECIPE_RE = re.compile(r"quarto\s+render")
_RENDER_TARGET_RE = re.compile(r"^[\w./$()-]+\.(?:pdf|docx)\s*:", re.MULTILINE)
_PHASE2_RECIPE_RE = re.compile(
    r"scripts/(?:analyze_|compute_|plot_|export_|summarize_|build_het)"
)


def _has_render(text: str) -> bool:
    return bool(_RENDER_RECIPE_RE.search(text) or _RENDER_TARGET_RE.search(text))


def _has_phase2(text: str) -> bool:
    return bool(_PHASE2_RECIPE_RE.search(text))


def _all_mk_files() -> list[str]:
    """Every build fragment: root paths.mk + Phase-2 analysis concern .mk under
    scripts/analysis/ (relocated by ticket 0239) + per-deliverable render .mk."""
    files = glob.glob(os.path.join(REPO_ROOT, "*.mk"))
    files += glob.glob(os.path.join(REPO_ROOT, "scripts", "analysis", "*.mk"))
    files += glob.glob(os.path.join(REPO_ROOT, "deliverables", "*", "*.mk"))
    return sorted(files)


@pytest.mark.adherence
@pytest.mark.parametrize("mkpath", _all_mk_files())
def test_mk_file_is_single_phase(mkpath):
    """No .mk may carry BOTH a Phase-3 render recipe and a Phase-2 compute recipe."""
    with open(mkpath, encoding="utf-8") as f:
        text = f.read()
    render, phase2 = _has_render(text), _has_phase2(text)
    assert not (render and phase2), (
        f"{os.path.relpath(mkpath, REPO_ROOT)} mixes a Phase-3 render recipe "
        f"(quarto render / .pdf|.docx target) with a Phase-2 compute recipe "
        f"(scripts/analyze_|compute_|plot_|export_|summarize_|build_het). "
        f"Render and compute must live in separate .mk (ticket 0237)."
    )


@pytest.mark.adherence
def test_phase_purity_guard_has_teeth(tmp_path):
    """The guard must trip on a fabricated mixed .mk and pass a single-kind one."""
    render_only = "foo.pdf: foo.qmd\n\tquarto render $< --to pdf\n"
    compute_only = "bar.csv: baz.py\n\t$(PYTHON) scripts/compute_bar.py --output $@\n"
    mixed = render_only + compute_only

    # Mixed file: both detectors fire → the parametrized guard would fail on it.
    assert _has_render(mixed) and _has_phase2(mixed)

    # Single-kind files: exactly one detector fires.
    assert _has_render(render_only) and not _has_phase2(render_only)
    assert _has_phase2(compute_only) and not _has_render(compute_only)

    # Round-trip through disk so the guard's file read is exercised.
    p = tmp_path / "mixed.mk"
    p.write_text(mixed)
    with open(p, encoding="utf-8") as f:
        disk = f.read()
    assert _has_render(disk) and _has_phase2(disk)

# The manuscript's writing-facing deliverables — what manuscript.qmd actually
# consumes via ![](../_shared/figures/...) and
# {{< include ../_shared/tables/tab_venues.md >}}.
MANUSCRIPT_DELIVERABLES = [
    "deliverables/_shared/figures/fig_bars_v1.png",
    "deliverables/_shared/figures/fig_composition.png",
    "deliverables/_shared/figures/fig_breaks.png",
    "deliverables/_shared/tables/tab_venues.md",
]

# Tokens that betray a Phase-1/data dependency leaking into the writing build.
DATA_TOKENS = ["$(REFINED)", "$(DATA_DIR)", "refined_works", "data/"]


@pytest.mark.integration
@pytest.mark.parametrize("path", MANUSCRIPT_DELIVERABLES)
def test_deliverable_is_git_tracked(path):
    """Each manuscript deliverable must be tracked by git (like deliverables/_shared/_includes/)."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{path} is not git-tracked; a clean-room writing build cannot find it. "
        f"git ls-files said: {result.stderr.strip()}"
    )


def test_manuscript_mk_exists():
    assert os.path.isfile(MANUSCRIPT_MK), "manuscript.mk missing at deliverables/manuscript/"


def test_manuscript_pdf_rule_has_no_data_prereq():
    """The manuscript.pdf rule (prereqs + recipe) must not reference Phase-1 data."""
    with open(MANUSCRIPT_MK) as f:
        text = f.read()

    # Isolate the deliverables/manuscript/manuscript.pdf rule block (prereq line + recipe).
    lines = text.splitlines()
    block = []
    in_rule = False
    for line in lines:
        if line.startswith("deliverables/manuscript/manuscript.pdf:"):
            in_rule = True
            block.append(line)
            continue
        if in_rule:
            # Recipe lines are tab-indented; a non-indented, non-blank line ends it.
            if line and not line[0].isspace():
                break
            block.append(line)
    assert block, "deliverables/manuscript/manuscript.pdf rule not found in manuscript.mk"

    rule_text = "\n".join(block)
    for token in DATA_TOKENS:
        assert token not in rule_text, (
            f"manuscript.pdf rule references Phase-1 data token {token!r}: "
            f"the writing build must depend on committed deliverables only.\n{rule_text}"
        )
