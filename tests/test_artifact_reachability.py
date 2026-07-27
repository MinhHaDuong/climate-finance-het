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

Fast tier: pure-Python lexical scan, no subprocess, no heavy import.
"""

import glob
import os
import re

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
    """Every Makefile fragment that can name an artifact path."""
    paths = [os.path.join(REPO_ROOT, "Makefile"), os.path.join(REPO_ROOT, "paths.mk")]
    paths += sorted(glob.glob(os.path.join(REPO_ROOT, "scripts", "analysis", "*.mk")))
    paths += sorted(glob.glob(os.path.join(DELIVERABLES, "*", "*.mk")))
    return [p for p in paths if os.path.isfile(p)]


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


# Deliberate exceptions, repo-relative path -> reason. Filled by the green step.
ALLOWED: dict[str, str] = {}


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
