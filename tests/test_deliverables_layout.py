"""Layout guard for the deliverables/ prose reorg (ticket 0226).

Each paper/slide deck is its own Quarto project under `deliverables/<x>/` with a
self-contained `_quarto.yml`; shared assets live in `deliverables/_shared/` and
are referenced by `../_shared/...`. This guard pins that structure:

1. No root `_quarto*.yml` exclusion-mask profile files survive.
2. The old flat `content/` tree is gone (or empty).
3. Each of the 9 deliverable folders has a `_quarto.yml` declaring a project.
4. No bare shared-asset reference (`figures/`, `tables/`, `_includes/`,
   `bibliography/` not prefixed `../_shared/`) remains in any deliverable
   `.qmd` or shared `_includes` fragment — includes resolve relative to the top
   rendering doc, so every such path must carry the `../_shared/` prefix.
5. Every render rule targets its PDF/DOCX next to the source under
   `deliverables/<x>/`; none targets the retired `output/` tree. Quarto's
   single-file render ignores a project output-dir, so the Make target must
   equal the file quarto actually writes (next to the .qmd) for Make to verify
   it.

Fast tier (pure-Python, no subprocess): a lexical structure ratchet.
"""

import glob
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DELIVERABLES = os.path.join(REPO_ROOT, "deliverables")

DELIVERABLE_FOLDERS = [
    "manuscript",
    "data-paper",
    "agentic",
    "multilayer",
    "corpus-report",
    "technical-report",
    "zoo",
    "slides-gide",
    "slides-eshet",
]

# A reference to a shared-asset directory, captured after a markdown/LaTeX/YAML
# lead-in so incidental prose mentions of the word are not flagged.
_SHARED_REF = re.compile(
    r"(?:\]\(|\{\{<\s*include\s+|\{|:\s*)"
    r"(?P<path>(?:\.\./)?[\w./_-]*?(?:figures|tables|_includes|bibliography)/[\w./_-]*)"
)


# A Make render rule: the target (first token, left of `:`) is a PDF/DOCX file.
_RENDER_TARGET = re.compile(r"^(?P<t>[\w./-]+\.(?:pdf|docx))\s*:")

# Makefiles that carry render rules (top-level + concern .mk + the manuscript's).
_MAKEFILES = (
    [os.path.join(REPO_ROOT, "Makefile")]
    + glob.glob(os.path.join(REPO_ROOT, "*.mk"))
    + [os.path.join(DELIVERABLES, "manuscript", "manuscript.mk")]
)


def test_no_root_quarto_masks():
    """The root exclusion-mask profile files must be gone."""
    masks = glob.glob(os.path.join(REPO_ROOT, "_quarto*.yml"))
    assert not masks, f"root _quarto*.yml mask files must not exist: {masks}"


def test_render_targets_next_to_source():
    """Every render rule targets deliverables/<x>/<doc>.{pdf,docx}, never output/.

    Quarto's single-file render writes next to the source and ignores a project
    output-dir, so a rule whose target is `output/content/<doc>.pdf` silently
    produces nothing at that path while `make` still returns 0. Pinning the
    target under `deliverables/<x>/` makes the target equal the real output so
    Make verifies it.
    """
    per_deliverable = re.compile(r"^deliverables/[^/]+/[\w-]+\.(?:pdf|docx)$")
    offenders = []
    for mkpath in _MAKEFILES:
        if not os.path.isfile(mkpath):
            continue
        with open(mkpath, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if line.startswith("\t"):  # recipe line
                    continue
                m = _RENDER_TARGET.match(line)
                if not m:
                    continue
                target = m.group("t")
                rel = os.path.relpath(mkpath, REPO_ROOT)
                if target.startswith("output/"):
                    offenders.append(f"{rel}:{lineno}: targets retired output/ tree: {target}")
                elif not per_deliverable.match(target):
                    offenders.append(f"{rel}:{lineno}: render target not under deliverables/<x>/: {target}")
    assert not offenders, "render rules must write next to source:\n" + "\n".join(offenders)


def test_content_tree_gone_or_empty():
    """The old flat content/ tree must be gone (or hold no files)."""
    content = os.path.join(REPO_ROOT, "content")
    if not os.path.isdir(content):
        return
    files = [
        os.path.join(dp, f)
        for dp, _dn, fns in os.walk(content)
        for f in fns
    ]
    assert not files, f"content/ still holds files after the reorg: {files}"


def test_each_deliverable_has_quarto_project():
    """Each deliverable folder declares its own Quarto project."""
    for folder in DELIVERABLE_FOLDERS:
        qy = os.path.join(DELIVERABLES, folder, "_quarto.yml")
        assert os.path.isfile(qy), f"missing {folder}/_quarto.yml"
        with open(qy, encoding="utf-8") as f:
            assert "project:" in f.read(), f"{folder}/_quarto.yml lacks a project: block"


def _bare_shared_refs(path):
    """Lines in `path` that reference a shared asset without the ../_shared/ prefix."""
    hits = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            for m in _SHARED_REF.finditer(line):
                p = m.group("path")
                if "slides-assets" in p:
                    continue
                if not p.startswith("../_shared/"):
                    hits.append((lineno, line.rstrip()))
    return hits


def test_no_bare_shared_asset_paths():
    """Shared-asset references carry the ../_shared/ prefix (no bare figures/ etc.)."""
    targets = glob.glob(os.path.join(DELIVERABLES, "*", "*.qmd"))
    targets += glob.glob(
        os.path.join(DELIVERABLES, "_shared", "_includes", "**", "*.md"),
        recursive=True,
    )
    offenders = []
    for path in targets:
        for lineno, line in _bare_shared_refs(path):
            offenders.append(f"{os.path.relpath(path, REPO_ROOT)}:{lineno}: {line}")
    assert not offenders, (
        "bare shared-asset references (must be ../_shared/<suffix>):\n"
        + "\n".join(offenders)
    )
