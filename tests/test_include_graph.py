"""Guard the Quarto include graph (ticket 0290).

Two failure modes, one walker:

1. **Orphans.** A file under ``deliverables/_shared/_includes/`` that no
   deliverable reaches is dead prose. It still gets maintained by mechanical
   sweeps, still carries claims that may have been retracted elsewhere, and
   misleads readers into believing a document says something it does not
   (ticket 0286: an orphan's figure reference convinced a session the
   manuscript carried a figure it never had).

2. **Stale dependency sets.** ``paths.mk`` declares one ``*_INCLUDES`` variable
   per document, used as Make prerequisites of that document's render rule.
   Hand-maintained, they drift: before 0290 the technical report's set listed
   six includes the .qmd had stopped including and omitted the whole 19-file
   zoo tree it does include, so editing a method write-up did not rebuild the
   report.

Include paths resolve against the ROOT document's directory at every level of
recursion, not against the file doing the including — see
``.claude/rules/architecture.md``. A walker that rebases on each file's own
directory misses every nested include and reports it as an orphan.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DELIVERABLES = REPO / "deliverables"
INCLUDES_DIR = DELIVERABLES / "_shared" / "_includes"
PATHS_MK = REPO / "paths.mk"

INCLUDE_RE = re.compile(r"\{\{<\s*include\s+([^>}]+?)\s*>\}\}")

# Include files kept on purpose although no deliverable renders them yet.
# An entry is a promise that something will consume it — keep the ticket
# reference so a stale exemption is visible.
ALLOWED_ORPHANS = {
    # Split out of bibliometric-context.md by 0289; staged for the data-paper
    # resubmission response (0283), not yet wired into data-paper.qmd.
    "prior-mappings.md": "0283",
}

# Document → the paths.mk variable holding its include closure.
DOC_INCLUDE_VARS = {
    "manuscript/manuscript.qmd": "MANUSCRIPT_INCLUDES",
    "manuscript/manuscript-Gide.qmd": "GIDE_INCLUDES",
    "corpus-report/corpus-report.qmd": "CORPUS_REPORT_INCLUDES",
    "data-paper/data-paper.qmd": "DATAPAPER_INCLUDES",
    "technical-report/technical-report.qmd": "TECHREP_INCLUDES",
    "multilayer/multilayer-detection.qmd": "MULTILAYER_INCLUDES",
    "multilayer/multilayer-detection-techrep.qmd": "MULTILAYER_TECHREP_INCLUDES",
    "zoo/breakpoint-detect-method-zoo.qmd": "ZOO_INCLUDES",
}


def deliverable_docs() -> list[Path]:
    return sorted(DELIVERABLES.glob("*/*.qmd"))


def include_closure(root: Path) -> set[Path]:
    """Every file ``root`` includes, transitively, as repo-relative paths.

    ``base`` stays the root document's directory through the whole recursion —
    that is how Quarto resolves nested includes.
    """
    base = root.parent
    found: set[Path] = set()

    def walk(doc: Path) -> None:
        try:
            text = doc.read_text()
        except OSError:
            return  # generated table not yet built; its path is still a prereq
        for match in INCLUDE_RE.finditer(text):
            target = (base / match.group(1).strip()).resolve()
            rel = target.relative_to(REPO)
            if rel in found:
                continue
            found.add(rel)
            walk(target)

    walk(root)
    return found


def make_var(name: str) -> set[Path]:
    """Read a ``NAME := a \\\n b`` list out of paths.mk, expanding $(REFS)."""
    text = PATHS_MK.read_text()
    match = re.search(
        rf"^{re.escape(name)}\s*:=(.*?)(?=^\s*$|^[A-Z_]+\s*:=)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match, f"{name} not defined in paths.mk"
    body = match.group(1).replace("\\\n", " ")
    body = re.sub(r"#.*", "", body)
    entries: set[Path] = set()
    for token in body.split():
        ref = re.fullmatch(r"\$\((\w+)\)", token)
        if ref:
            entries |= make_var(ref.group(1))
        else:
            entries.add(Path(token))
    return entries


def test_no_orphaned_includes():
    """Every shared include is reachable from at least one deliverable."""
    reached: set[Path] = set()
    for doc in deliverable_docs():
        reached |= include_closure(doc)

    on_disk = {p.relative_to(REPO) for p in INCLUDES_DIR.rglob("*.md")}
    orphans = {p for p in on_disk - reached if p.name not in ALLOWED_ORPHANS}

    assert not orphans, (
        "Unreferenced include(s) — embed in a deliverable, move to conception/, "
        "delete (git keeps the content), or add to ALLOWED_ORPHANS with a "
        f"ticket: {sorted(str(p) for p in orphans)}"
    )


def test_allowed_orphans_are_still_orphans():
    """An exemption expires once the file is actually wired in."""
    reached: set[Path] = set()
    for doc in deliverable_docs():
        reached |= include_closure(doc)

    redundant = [name for name in ALLOWED_ORPHANS if any(p.name == name for p in reached)]
    assert not redundant, (
        f"ALLOWED_ORPHANS entries are now referenced; drop them: {redundant}"
    )


def test_allowed_orphans_exist():
    """An exemption for a deleted file is dead config."""
    missing = [name for name in ALLOWED_ORPHANS if not (INCLUDES_DIR / name).exists()]
    assert not missing, f"ALLOWED_ORPHANS names a file that is gone: {missing}"


@pytest.mark.parametrize("doc_rel,var", sorted(DOC_INCLUDE_VARS.items()))
def test_paths_mk_matches_include_closure(doc_rel: str, var: str):
    """A render's Make prerequisites are exactly what the document includes."""
    doc = DELIVERABLES / doc_rel
    assert doc.exists(), f"{doc_rel} listed in DOC_INCLUDE_VARS but missing"

    actual = include_closure(doc)
    declared = make_var(var)

    assert declared == actual, (
        f"{var} is out of sync with {doc_rel}.\n"
        f"  declared but not included: {sorted(str(p) for p in declared - actual)}\n"
        f"  included but not declared: {sorted(str(p) for p in actual - declared)}"
    )


def test_every_doc_with_includes_has_an_include_var():
    """A document that includes anything declares it as Make prerequisites.

    Docs that include nothing (the agentic paper, the slide decks) need no
    variable; the check starts applying the moment one gains an include.
    """
    unmapped = sorted(
        str(doc.relative_to(DELIVERABLES))
        for doc in deliverable_docs()
        if include_closure(doc) and str(doc.relative_to(DELIVERABLES)) not in DOC_INCLUDE_VARS
    )
    assert not unmapped, (
        "Document(s) with includes but no paths.mk include set — add a "
        f"*_INCLUDES variable and map it in DOC_INCLUDE_VARS: {unmapped}"
    )
