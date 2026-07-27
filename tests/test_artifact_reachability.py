"""Reachability guard for generated artifacts under `deliverables/_shared/` (ticket 0359).

`make` builds includes, tables and figures into `deliverables/_shared/`. Nothing
checked that a document still consumes them, so a prose cut silently left the
build graph producing artifacts for nobody: 0332's §4 cut orphaned
`fig_sem_composition.png`, and the 0226/0240 deliverables reorg orphaned the
whole flat `_includes/*.md` layer. This guard makes the next such orphaning fail
a test instead of accumulating.

## Two edge types, two checks

An artifact reaches a reader over two different edges, and each check owns one:

1. **Includes** — strict transitive reachability. A shared `_includes/**/*.md`
   must be reachable from one of the deliverable `.qmd` roots by following
   `{{< include >}}` directives.
2. **Figures and markdown tables** — displayed by *some* prose file in the
   corpus (a root `.qmd` or a shared include). Whether that prose file is itself
   reachable is check 1's business.

The split avoids reporting one root cause twice: 13 further figures are
displayed only from the 17 unreachable includes. Reporting them here as well
would triple the noise for a single finding, and would hide the real property —
that when ticket 0290 settles those includes, those 13 figures newly fail check
2 and force their own follow-up.

## The trap this resolver must not fall into

Quarto resolves a `{{< include >}}` path against the **top rendering document's**
directory, not against the file that contains the directive (see
`.claude/rules/architecture.md`). So the walk carries the *root's* directory as
base through every level of recursion. Joining each include against its own
directory is the natural implementation and it is wrong: a 2026-07-27 sweep
written that way returned 13 confident false positives, all of
`_includes/zoo/*.md`, which `_includes/techrep-zoo.md` reaches as
`../_shared/_includes/zoo/…` from the zoo deliverable's folder.
`test_nested_zoo_includes_are_reachable` pins that so the trap cannot return.

## Artifact universes, and why each is chosen that way

Each universe must be identical on a fresh checkout and on a fully built tree —
a guard whose verdict depends on whether `make` has run is worthless.

- Includes: every `_includes/**/*.md` on disk. All are committed handoff
  artifacts; no build step writes one.
- Figures / markdown tables: every such path named literally in a Makefile or
  `.mk`. Most are gitignored and regenerable, so the filesystem is not a stable
  universe; the build graph is. Dynamic outputs whose filenames are computed at
  run time (`fig_lexical_tfidf_{year}.png`, tracked by `.lexical_tfidf.stamp`)
  are outside any static universe and outside this guard.
- CSV and JSON artifacts are excluded: scripts read them, documents do not.

Adherence tier: a build-graph contract, like every other `_mk_discovery` consumer
(`test_build_phase_separation`, `test_mk_discovery_unified`,
`test_handoff_artifacts_tracked`). Cost is fast-tier — a pure-Python lexical scan,
no subprocess, no heavy import — but `make lint` is the gate built to run rule
guards, and this one is invisible there unless marked.
"""

import glob
import os
import re

import pytest
from _mk_discovery import all_makefiles

pytestmark = pytest.mark.adherence

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DELIVERABLES = os.path.join(REPO_ROOT, "deliverables")
SHARED = os.path.join(DELIVERABLES, "_shared")

# `{{< include path >}}` — Quarto's include shortcode.
_INCLUDE_RE = re.compile(r"\{\{<\s*include\s+([^\s>]+)\s*>\}\}")
# `![caption](path)` — markdown image.
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
# `\includegraphics[opts]{path}` — raw LaTeX, used by the slide decks.
_GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")

# Artifact paths as they appear in the build graph.
_MK_FIGURE_RE = re.compile(r"deliverables/_shared/figures/[\w.-]+\.png")
_MK_TABLE_RE = re.compile(r"deliverables/_shared/tables/[\w.-]+\.md")


def _deliverable_roots():
    """The top rendering documents: one `.qmd` per deliverable folder."""
    return sorted(glob.glob(os.path.join(DELIVERABLES, "*", "*.qmd")))


def _makefiles():
    """Every Makefile fragment that can name an artifact path.

    Shared discovery (ticket 0248): a `.mk` relocation updates one list, and this
    guard cannot silently narrow its universe — which would turn a real orphan
    into a false green.
    """
    return [str(p) for p in all_makefiles() if p.is_file()]


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _includes_in(text):
    return [m.group(1) for m in _INCLUDE_RE.finditer(text)]


def _assets_in(text):
    return [m.group(1) for m in _IMAGE_RE.finditer(text)] + [
        m.group(1) for m in _GRAPHICS_RE.finditer(text)
    ]


def _reachable_includes():
    """Absolute paths of shared includes reachable from some deliverable root.

    The base directory stays the ROOT document's directory at every depth — see
    the module docstring. Changing that to the including file's directory is the
    known defect this guard exists to avoid.
    """
    reached = set()
    for root in _deliverable_roots():
        base = os.path.dirname(root)
        queue = [root]
        seen = {os.path.normpath(root)}
        while queue:
            current = queue.pop()
            if not os.path.isfile(current):
                continue
            for rel in _includes_in(_read(current)):
                target = os.path.normpath(os.path.join(base, rel))
                reached.add(target)
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
    return reached


def _all_shared_includes():
    return sorted(glob.glob(os.path.join(SHARED, "_includes", "**", "*.md"), recursive=True))


def _displayed_basenames():
    """Basenames of every asset any prose file in the corpus references.

    The corpus is the deliverable roots plus every shared include — reachable or
    not. Check 1 owns whether the referencing include is itself reachable.
    """
    names = set()
    for path in _deliverable_roots() + _all_shared_includes():
        text = _read(path)
        for rel in _assets_in(text) + _includes_in(text):
            names.add(os.path.basename(rel))
    return names


def _declared(pattern):
    """Artifact paths (repo-relative) named literally in the build graph."""
    found = set()
    for mk in _makefiles():
        found |= {m.group(0) for m in pattern.finditer(_read(mk))}
    return found


def _rel(path):
    return os.path.relpath(path, REPO_ROOT)


# ── Allowlist ────────────────────────────────────────────────────────────────
# Repo-relative artifact path -> why it is built and consumed by no document.
#
# Every entry states a real reason and, where one exists, the ticket that will
# settle it. `test_allowlist_has_no_redundant_entries` deletes the exemption's
# cover the moment an artifact becomes reachable again, so this cannot rot into
# a permanent "ignore these" list.

_FLAT_INCLUDE_REASON = (
    "Leftover of the 0226/0240 deliverables reorg: the technical report now "
    "composes only _includes/techrep/, so the whole flat _includes/*.md layer "
    "fell out of every document at once. Disposition (delete / relocate to "
    "conception/ / re-embed) is ticket 0290's, and its action 2 sends any "
    "include not clearly superseded by the techrep/ set to the author. This "
    "guard is 0290's action 3; it does not pre-empt its action 1."
)

_UNSETTLED_REASON = (
    "Built by make, displayed by no prose file, disposition undecided. "
    "Deleting a committed artifact together with its Make rules while the data "
    "paper is mid-R&R is an author call, not a sweep's. Tracked with the "
    "flat-include audit in ticket 0290."
)

ALLOWED: dict[str, str] = {
    # ── The 17 flat shared includes — see _FLAT_INCLUDE_REASON, ticket 0290 ──
    "deliverables/_shared/_includes/agentic-workflow.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/alluvial-diagram.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/bibliometric-context.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/bimodality-analysis.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/changepoint-analysis.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/citation-genealogy.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/clustering-comparison.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/cop-topic-structure.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/core-vs-full-analysis.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/core-vs-full.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/embedding-generation.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/pca-scatter.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/prior-mappings.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/structural-breaks.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/tab2_poles.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/tab_traditions.md": _FLAT_INCLUDE_REASON,
    "deliverables/_shared/_includes/temporal-structure.md": _FLAT_INCLUDE_REASON,
    # ── Figures: deliberate, with a stated consumer outside the render graph ──
    "deliverables/_shared/figures/fig_global_map_cocitation.png": (
        "Companion artifact, committed but embedded nowhere by design "
        "(ticket 0307, R1-14): the data paper carries the direct-citation map, "
        "the co-citation map backs the reviewer response. The intent is pinned "
        "by tests/test_global_map.py:175, which asserts the basename is absent "
        "from the data paper source."
    ),
    "deliverables/_shared/figures/fig_traditions_pre2008_citers.png": (
        "Citer-limited variant of fig_traditions built for the RDJ4HSS R1-14 "
        "response (ticket 0286); its consumer is "
        "deliverables/data-paper/revision-rdj26561/r1-14-network-response.md, "
        "a revision record rather than a rendered deliverable."
    ),
    "deliverables/_shared/figures/fig_ncc_alluvial.png": (
        "NCC_FIGS is declared analysis-only at Makefile:136 — the four fig_ncc_* "
        "figures reproduce the analysis in Nature Climate Change house format "
        "for comparison (docs/ncc-pipeline-audit.md) and were never meant for a "
        "deliverable."
    ),
    "deliverables/_shared/figures/fig_ncc_bimodality.png": (
        "See fig_ncc_alluvial.png — analysis-only NCC_FIGS set, Makefile:136."
    ),
    "deliverables/_shared/figures/fig_ncc_core_comparison.png": (
        "See fig_ncc_alluvial.png — analysis-only NCC_FIGS set, Makefile:136."
    ),
    "deliverables/_shared/figures/fig_ncc_divergence.png": (
        "See fig_ncc_alluvial.png — analysis-only NCC_FIGS set, Makefile:136."
    ),
    "deliverables/_shared/figures/fig_sem_composition.png": (
        "Orphaned on 2026-07-27 when ticket 0332 cut the data paper's §4 "
        "semantic-cluster paragraph. Kept rather than deleted: the paper is "
        "mid-R&R and §4 may be revisited in round 2, so retiring the figure "
        "with its lit-confirmations.mk rules is reversible-only-once and "
        "belongs to the author. The backing tab_sem_composition.csv and the "
        "clustering behind tab_sem6_assignments.csv stay either way — §1's "
        "literature-confirmation bullet depends on them."
    ),
    # ── Figures and tables with no consumer and no decision yet ───────────────
    # These are standalone rules outside every *_FIGS render list, so `make
    # figures` does not even build them; they run on demand from their own
    # targets.
    "deliverables/_shared/figures/fig_breakpoints_core.png": _UNSETTLED_REASON,
    "deliverables/_shared/figures/fig_k_sensitivity.png": _UNSETTLED_REASON,
    "deliverables/_shared/figures/fig_venue_concentration.png": _UNSETTLED_REASON,
    # These two sit in TECHREP_FIGS, so `make figures` builds them, yet the
    # technical report displays neither — their prose consumers were in the flat
    # include layer above.
    "deliverables/_shared/figures/fig_communities.png": _UNSETTLED_REASON,
    "deliverables/_shared/figures/fig_traditions.png": _UNSETTLED_REASON,
    "deliverables/_shared/tables/tab_core_venues_top10.md": _UNSETTLED_REASON,
    # ── Markdown tables consumed by something other than a document ──────────
    "deliverables/_shared/tables/codebook.md": (
        "Ships in the Zenodo deposit, not in a paper: "
        "build/build_datapaper_archive.sh:47 copies it into data/products/ of "
        "the reproducibility archive, where README-datapaper.md documents it as "
        "the data dictionary. Correct as-is."
    ),
    "deliverables/_shared/tables/tab_venues_fr_caption.md": (
        "A build input, not a rendered fragment: manuscript.mk:62-63 "
        "concatenates it onto tab_venues.md to produce tab_venues_fr.md, which "
        "manuscript-Gide.qmd does include. Correct as-is."
    ),
}


def test_nested_zoo_includes_are_reachable():
    """Nested includes resolve against the ROOT document's directory.

    `_includes/zoo/*.md` are reached only through `_includes/techrep-zoo.md`,
    which names them `../_shared/_includes/zoo/…` — a path that resolves from
    the zoo deliverable's folder, not from `_includes/`. A resolver that joins
    each include against its own directory reports all 18 as orphans. This test
    is the regression pin for that defect; it must fail loudly if the base ever
    stops being the root's directory.
    """
    reached = _reachable_includes()
    zoo = sorted(glob.glob(os.path.join(SHARED, "_includes", "zoo", "*.md")))
    assert zoo, "no zoo includes found — the fixture this test pins has moved"
    missing = [_rel(p) for p in zoo if p not in reached]
    assert not missing, (
        "nested zoo includes reported unreachable — the resolver is resolving "
        "include paths against the including file's directory instead of the "
        "root document's:\n" + "\n".join(missing)
    )


def test_shared_includes_are_reachable():
    """Every shared include is reachable from a deliverable, or allowlisted."""
    reached = _reachable_includes()
    orphans = [
        _rel(p)
        for p in _all_shared_includes()
        if p not in reached and _rel(p) not in ALLOWED
    ]
    assert not orphans, (
        f"{len(orphans)} shared include(s) reachable from no deliverable .qmd. "
        "Re-embed, delete, or add to ALLOWED with the reason:\n" + "\n".join(orphans)
    )


def test_declared_figures_are_displayed():
    """Every figure the build graph declares is displayed by some prose file."""
    orphans = sorted(
        p
        for p in _declared(_MK_FIGURE_RE)
        if os.path.basename(p) not in _displayed_basenames() and p not in ALLOWED
    )
    assert not orphans, (
        f"{len(orphans)} figure(s) built by make and displayed by no prose file. "
        "Embed, drop the rule, or add to ALLOWED with the reason:\n" + "\n".join(orphans)
    )


def test_declared_markdown_tables_are_included():
    """Every markdown table the build graph declares is included somewhere."""
    orphans = sorted(
        p
        for p in _declared(_MK_TABLE_RE)
        if os.path.basename(p) not in _displayed_basenames() and p not in ALLOWED
    )
    assert not orphans, (
        f"{len(orphans)} markdown table(s) built by make and included by no prose "
        "file. Include, drop the rule, or add to ALLOWED with the reason:\n"
        + "\n".join(orphans)
    )


def test_allowlist_has_no_redundant_entries():
    """An allowlist entry that is no longer orphaned must be removed.

    Without this the allowlist rots into a permanent exemption list: an artifact
    re-embedded by a later ticket would keep its exemption and the guard would
    stop covering it.
    """
    reached = _reachable_includes()
    displayed = _displayed_basenames()
    declared = _declared(_MK_FIGURE_RE) | _declared(_MK_TABLE_RE)
    on_disk = {_rel(p) for p in _all_shared_includes()}

    redundant, unknown = [], []
    for entry in ALLOWED:
        if entry in on_disk:
            if os.path.join(REPO_ROOT, entry) in reached:
                redundant.append(f"{entry} — now reachable from a deliverable")
        elif entry in declared:
            if os.path.basename(entry) in displayed:
                redundant.append(f"{entry} — now displayed by a prose file")
        else:
            unknown.append(entry)

    assert not redundant, (
        "allowlist entries that are no longer orphaned — delete them:\n"
        + "\n".join(redundant)
    )
    assert not unknown, (
        "allowlist entries naming no shared include and no build-graph artifact "
        "(typo, or the artifact was deleted) — delete them:\n" + "\n".join(unknown)
    )
