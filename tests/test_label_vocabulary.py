"""The TF-IDF label vocabulary has one home (ticket 0321).

`compute_clusters` labels semantic k-means clusters (alluvial panels);
`analyze_global_map` labels Louvain citation communities
(fig_global_map_direct nodes). Both score terms by TF-IDF distinctiveness over
the same corpus, so they have to suppress the same stopwords and collapse the
same acronyms — otherwise the two figures disagree about which terms
characterise a group of works.

They used to agree by `analyze_global_map` importing from `compute_clusters`,
which made a Tier-3 entry point into a library and broke the invariant the
`scripts/` reorg depends on (epic 0240). These tests pin the extraction: one
source, both consumers reading it, and no reintroduced local copy.
"""

import ast
import os

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

CONSUMERS = (
    os.path.join("analysis", "compute_clusters.py"),
    os.path.join("analysis", "analyze_global_map.py"),
)


def _source(rel):
    with open(os.path.join(SCRIPTS_DIR, rel)) as fh:
        return fh.read()


def _assigned_names(rel):
    """Module-level names a script binds, and functions it defines."""
    tree = ast.parse(_source(rel), filename=rel)
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def test_vocabulary_module_is_importable_and_populated():
    from _label_vocabulary import (
        ACRONYM_EXPANSIONS,
        LABEL_STOPWORDS,
        collapse_acronyms,
    )

    assert LABEL_STOPWORDS and ACRONYM_EXPANSIONS
    assert callable(collapse_acronyms)


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_imports_the_shared_vocabulary(rel):
    assert "from _label_vocabulary import" in _source(rel), (
        f"{rel} should read the label vocabulary from _label_vocabulary"
    )


@pytest.mark.parametrize("rel", CONSUMERS)
def test_consumer_keeps_no_local_copy(rel):
    """A local re-definition would silently drift from the shared one."""
    local = _assigned_names(rel) & {
        "LABEL_STOPWORDS", "ACRONYM_EXPANSIONS", "collapse_acronyms",
        "_collapse_acronyms",
    }
    assert not local, f"{rel} redefines {sorted(local)} instead of importing it"


def test_no_consumer_imports_from_the_other():
    """The dual-role hazard this extraction resolves: a Tier-3 entry point
    imported by another script is not safe to move between phase directories,
    which is the invariant the scripts/ reorg rests on."""
    for rel in CONSUMERS:
        src = _source(rel)
        assert "from compute_clusters import" not in src
        assert "from analyze_global_map import" not in src


def test_acronyms_collapse_so_a_term_is_not_split_across_spellings():
    from _label_vocabulary import collapse_acronyms

    assert collapse_acronyms("the clean development mechanism") == "the CDM"
    assert collapse_acronyms("Clean Development Mechanism") == "CDM"
    # A work already using the acronym is left as-is, so both spellings land
    # on the same term.
    assert collapse_acronyms("the CDM") == "the CDM"


def test_stopwords_cover_the_corpus_wide_terms():
    """"climate" and "finance" describe every work in the corpus, so they
    distinguish no group within it."""
    from _label_vocabulary import LABEL_STOPWORDS

    for term in ("climate", "finance", "carbon", "emissions"):
        assert term in LABEL_STOPWORDS
