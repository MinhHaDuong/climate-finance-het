"""Verify DOC_VARS lists every {{< meta >}} variable, and that prose says where it lives.

Scans each .qmd and its {{< include >}}'d files for {{< meta X >}} shortcodes,
then checks that every variable X appears in the DOC_VARS mapping for that
document. Prevents silent empty-string rendering when a new variable is
added to prose but not registered in compute_vars.py.

This checks prose against the `DOC_VARS` dict — a source-to-source check that
catches a new variable before anyone regenerates the vars file. It is one layer
above the artifact Quarto loads, so it cannot see a key that leaves `DOC_VARS`
correct but the generated YAML short; `test_render_placeholders.py` closes
that side (ticket 0363). The shortcode scan is shared between the two.
"""

import os
import re
import sys

import pytest
from _qmd_meta import deliverable_qmds, meta_keys_used

# Allow importing from scripts/analysis/ (not on the pytest pythonpath roots)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))  # 0257
from compute_vars import DOC_VARS

#: Documents whose vars file is hand-maintained, so compute_vars must not own
#: them. `manuscript-vars.yml` is pinned to the v1.0 submission values and the
#: manuscript and its Gide variant both load it.
#:
#: An exemption that no longer applies is itself a defect, so
#: `test_no_pinned_document_is_also_generated` fails if one of these appears in
#: DOC_VARS — the entry cannot rot into a mute skip.
PINNED_DOCS = frozenset({"manuscript", "manuscript-Gide"})


def _qmd_path(doc_name):
    """Locate a doc's .qmd under its deliverable folder (folder name may differ)."""
    for qmd in deliverable_qmds():
        if qmd.stem == doc_name:
            return qmd
    return None


@pytest.mark.parametrize("doc_name", list(DOC_VARS.keys()))
def test_doc_vars_complete(doc_name):
    """Every {{< meta X >}} in doc + includes must appear in DOC_VARS."""
    qmd_path = _qmd_path(doc_name)
    if qmd_path is None:
        pytest.skip(f"{doc_name}.qmd not found")

    used = meta_keys_used(qmd_path)
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
    if qmd_path is None:
        pytest.skip(f"{doc_name}.qmd not found")

    used = meta_keys_used(qmd_path)
    declared = set(DOC_VARS[doc_name])
    extra = declared - used
    assert not extra, (
        f"{doc_name}: {len(extra)} variable(s) in DOC_VARS but unused in prose: "
        f"{sorted(extra)}"
    )


def test_every_document_using_macros_is_registered():
    """Discover the documents from disk, not from the registry being checked.

    Both guards above are parametrized over `DOC_VARS`, so a document the
    registry never heard of is checked in neither direction — and it still
    renders, because Quarto resolves whatever its shared vars file happens to
    carry and writes `?meta:key` for the rest at exit 0. corpus-report sat in
    that blind spot with 12 unresolved keys until ticket 0357. Keying off the
    documents that exist is what makes the next unregistered one loud.
    """
    unregistered = sorted(
        qmd.stem
        for qmd in deliverable_qmds()
        if meta_keys_used(qmd) and qmd.stem not in DOC_VARS and qmd.stem not in PINNED_DOCS
    )
    assert not unregistered, (
        f"{len(unregistered)} document(s) use {{{{< meta >}}}} macros but are "
        f"absent from compute_vars.DOC_VARS: {unregistered}. Register each one "
        f"with the variables its prose uses, or add it to PINNED_DOCS if its "
        f"vars file is hand-maintained."
    )


def test_registered_documents_exist_on_disk():
    """The registry must not name a document that has been renamed or removed.

    `_qmd_path` skips when it finds nothing, so a stale DOC_VARS entry would
    otherwise turn both guards above into silent skips rather than failures.
    """
    orphaned = sorted(doc for doc in DOC_VARS if _qmd_path(doc) is None)
    assert not orphaned, (
        f"DOC_VARS names {len(orphaned)} document(s) with no .qmd under "
        f"deliverables/: {orphaned}"
    )


def test_no_pinned_document_is_also_generated():
    """A document cannot have both a pinned and a generated vars file."""
    both = sorted(PINNED_DOCS & set(DOC_VARS))
    assert not both, (
        f"{both} are listed as hand-maintained but compute_vars also generates "
        f"their variables — drop them from PINNED_DOCS"
    )


#: Prose files that describe the registry to a reader or an editor. Each is a
#: propagation target: a change to where `DOC_VARS` lives has to reach them, and
#: nothing but a check makes that happen.
REGISTRY_PROSE = [
    "README.md",
    "docs/ncc-pipeline-audit.md",
    ".claude/rules/architecture.md",
]

#: Where `DOC_VARS` is actually defined. `compute_vars` re-exports it, so an
#: instruction that says otherwise still *works* — which is exactly why it
#: survives: following it lands the editor in a file that no longer holds the
#: dict (ticket 0357).
REGISTRY_MODULE = "_vars_registry.py"

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

#: "the DOC_VARS dictionary in compute_vars.py", "compute_vars.py's DOC_VARS",
#: and their near neighbours — prose that points an editor at the re-export.
_WRONG_HOME = re.compile(
    r"DOC_VARS[^.\n]{0,60}\bcompute_vars\.py|compute_vars\.py[^.\n]{0,60}\bDOC_VARS"
)


def _prose(name):
    path = os.path.join(_REPO_ROOT, name)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("name", REGISTRY_PROSE)
def test_prose_points_at_the_module_that_defines_the_registry(name):
    """Prose naming DOC_VARS must send an editor to the registry, not the re-export."""
    offenders = [
        f"  {name}:{i}  {line.strip()}"
        for i, line in enumerate(_prose(name).splitlines(), 1)
        if _WRONG_HOME.search(line)
    ]
    assert not offenders, (
        f"{name} tells the reader DOC_VARS lives in compute_vars.py; it is "
        f"defined in scripts/analysis/{REGISTRY_MODULE} and only re-exported "
        f"there, so following this lands in the wrong file:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("name", REGISTRY_PROSE)
def test_prose_does_not_call_a_registered_document_unregistered(name):
    """A fixed defect described as open is worse than no description at all.

    The README carried "**corpus-report is live in intent but not in fact.** It
    is absent from `compute_vars.DOC_VARS`" for as long as that was true, and
    would have carried it afterwards too. Registration is machine-checkable, so
    the claim should be.

    Scoped to the paragraph, not to a character window: in the real text the
    document name and the word "absent" sat on different lines with a sentence
    boundary between them, which is precisely what a proximity regex misses. A
    first draft of this guard used one and passed the replayed defect.
    """
    for para in re.split(r"\n\s*\n", _prose(name)):
        if "absent from" not in para:
            continue
        named = sorted(doc for doc in DOC_VARS if doc in para)
        assert not named, (
            f"{name} has a paragraph saying {named} are absent from the "
            f"registry, but DOC_VARS registers them — the prose describes a "
            f"defect that is fixed:\n  {' '.join(para.split())[:300]}"
        )


def test_the_registry_prose_scan_is_not_vacuous():
    """Every named file must exist and mention the registry, or the scan is blind."""
    for name in REGISTRY_PROSE:
        text = _prose(name)
        assert "DOC_VARS" in text, (
            f"{name} no longer mentions DOC_VARS — drop it from REGISTRY_PROSE "
            f"or the two scans above pass on it for free"
        )
