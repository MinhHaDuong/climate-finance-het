"""Guard: `paths.mk` answers "which artifacts does this deliverable need?"
correctly, and nothing under `deliverables/_shared/` is built for nobody
(ticket 0359).

`paths.mk` is both the reader's answer to that question and the render rules'
prerequisite lists, so a stale entry costs twice: it misinforms, and it makes a
PDF depend on a file its document stopped using while missing one it opens. The
answer drifts silently — a prose cut orphans a figure, a rewrite drops eleven
includes, a document grows a figure nobody declared.

The checks all key on one fact: what a deliverable renders is its `.qmd` files
plus their transitive `{{< include >}}` closure.

- **figures, declared -> rendered**: every figure in a `*_FIGS` variable is
  embedded by at least one deliverable that variable answers for, or carries a
  `# not-embedded:` marker in paths.mk saying why.
- **figures, rendered -> declared**: every generated figure a mapped
  deliverable embeds appears in one of its variables, so a render rule keyed on
  the variable really covers the document.
- **includes, both ways**: each `*_INCLUDES` variable equals the shared files
  its document actually composes.
- **nothing built for nobody**: every tracked shared include and Markdown table
  is reachable from some deliverable, or listed in
  `config/unrendered-artifacts.txt` with its reason.

The two figure directions are not one check on one map: the zoo lists serve
three documents, and the multilayer supplement embeds only the six methods it
discusses, so a figure is declared-and-rendered when *some* consumer embeds it,
while a document is covered when *its own* variables name everything it opens.

The markers and the allowlist are the load-bearing part. Without them the guard
would either fail forever on the deliberately-built-but-unembedded artifacts or
be deleted.
"""

import os
import re
import subprocess

import pytest
from _mk_discovery import mk_fragments

BASE = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PATHS_MK = os.path.join(BASE, "paths.mk")
DELIVERABLES = os.path.join(BASE, "deliverables")
ALLOWLIST = os.path.join(BASE, "config", "unrendered-artifacts.txt")
FIGURES_REL = "_shared/figures/"

# Which deliverable folders each figure variable answers for. A deliverable
# absent from this map is not covered by the figure checks: `agentic` declares
# no figure set because it embeds none.
FIG_VAR_DELIVERABLES = {
    "MANUSCRIPT_FIGS": ("manuscript",),
    "DATAPAPER_FIGS": ("data-paper",),
    "CORPUS_REPORT_FIGS": ("corpus-report",),
    "TECHREP_FIGS": ("technical-report",),
    "MULTILAYER_FIGS": ("multilayer",),
    "SLIDES_FIGS": ("slides-eshet", "slides-gide"),
    # One entry per method, embedded by the zoo and the technical report in
    # full and by the multilayer supplement for the six methods it discusses.
    "ZOO_SCHEMATICS": ("zoo", "technical-report", "multilayer"),
    "ZOO_RESULT_FIGS": ("zoo", "technical-report", "multilayer"),
}

# Figure lists that answer for no single deliverable, with the reason.
UNMAPPED_FIG_VARS = {
    "ORPHANED_FIGS": "built, embedded nowhere, disposition pending ticket 0290",
}

# Figure sets `make figures` deliberately skips, with the reason. TECHREP_FIGS
# expands to the two zoo lists, so it inherits their exclusion.
NOT_IN_ALL_FIGS = {
    "ZOO_SCHEMATICS": "needs the full divergence and null-model pipeline",
    "ZOO_RESULT_FIGS": "needs the full divergence and null-model pipeline",
    "TECHREP_FIGS": "expands to the two zoo lists",
}

# Deliverables whose render rule is expected to name the figure variable. The
# slide decks are rendered by hand and own no .mk, so they declare figures
# without wiring them.
NO_RENDER_RULE = ("slides-eshet", "slides-gide")

# Which .qmd each include list is the prerequisite set for. The list must equal
# the union of those roots' closures.
INCLUDE_VAR_ROOTS = {
    "MANUSCRIPT_INCLUDES": ("manuscript/manuscript.qmd",),
    # The Gide variant composes the French-caption table, not the English one,
    # so it owns a list rather than sharing MANUSCRIPT_INCLUDES (ticket 0290).
    "GIDE_INCLUDES": ("manuscript/manuscript-Gide.qmd",),
    "CORPUS_REPORT_INCLUDES": ("corpus-report/corpus-report.qmd",),
    "TECHREP_INCLUDES": ("technical-report/technical-report.qmd",),
    "DATAPAPER_INCLUDES": ("data-paper/data-paper.qmd",),
    "MULTILAYER_INCLUDES": ("multilayer/multilayer-detection.qmd",),
    "MULTILAYER_TECHREP_INCLUDES": ("multilayer/multilayer-detection-techrep.qmd",),
    "ZOO_INCLUDES": ("zoo/breakpoint-detect-method-zoo.qmd",),
}

# Shared trees whose tracked files must be reachable from some deliverable.
# Only Markdown is checked: a .csv under tables/ is read by a script, not
# composed by Quarto, so include reachability is the wrong question for it.
REACHABLE_TREES = ("deliverables/_shared/_includes", "deliverables/_shared/tables")

INCLUDE_RE = re.compile(r"\{\{<\s*include\s+([^>\s]+)\s*>\}\}")
# Only figures reached through the shared figures dir are pipeline output;
# a slide deck's local logo is not something paths.mk should declare.
GENERATED_PNG_RE = re.compile(re.escape(FIGURES_REL) + r"([\w.-]+\.png)")
# A marker's reason runs to the end of its comment block: continuation lines are
# indented under the `#`, so capture them too rather than judging the reason on
# its first line alone.
NOT_EMBEDDED_RE = re.compile(
    r"^#\s*not-embedded:\s*([\w.-]+\.png)\s*(?:—|--)\s*(\S.*(?:\n#\s{2,}.*)*)",
    re.M)
ALLOWLIST_RE = re.compile(r"^(\S+)\s*(?:—|--)\s*(\S.*)$", re.M)


def _read(path):
    with open(path) as fh:
        return fh.read()


def _make_variables(text):
    """Parse `NAME := value` assignments, honouring `\\` continuations.

    Comment lines are dropped first: a `#` inside a continued assignment would
    comment out the continuation itself, so paths.mk never carries one.

    The separators are `[ \\t]`, never `\\s`: `\\s` matches a newline, so on an
    empty assignment (`FOO :=`) a `\\s*` would run past the line end and hand
    back the *next* line's text as this variable's value, silently losing that
    variable too.
    """
    text = "\n".join(ln for ln in text.splitlines()
                     if not ln.lstrip().startswith("#"))
    text = re.sub(r"\\\n", " ", text)
    return dict(re.findall(r"^(\w+)[ \t]*:?=[ \t]*(.*)$", text, re.M))


def _expand(value, variables, depth=0):
    """Substitute `$(NAME)` references, as `:=` does at parse time."""
    if depth > 5:
        return value

    def sub(match):
        return _expand(variables.get(match.group(1), ""), variables, depth + 1)

    return re.sub(r"\$\((\w+)\)", sub, value)


VARIABLES = _make_variables(_read(PATHS_MK))


def _var_paths(name):
    """A paths.mk variable as a list of repo-relative paths."""
    return [os.path.normpath(p)
            for p in _expand(VARIABLES.get(name, ""), VARIABLES).split()]


def _figure_vars():
    """paths.mk variables whose value is a list of shared figures."""
    out = {}
    for name in VARIABLES:
        entries = _expand(VARIABLES[name], VARIABLES).split()
        if entries and all(FIGURES_REL in e for e in entries):
            out[name] = [os.path.basename(e) for e in entries]
    return out


def _closure(qmd):
    """Every shared file `qmd` composes, and the text it all renders as.

    Quarto resolves `{{< include >}}` paths relative to the *top* rendering
    document, so nested includes are joined against the .qmd's directory, not
    their own (deliverables/_shared/_includes/techrep-zoo.md is the case that
    makes the difference).

    A referenced include counts as composed even when absent from disk: three
    of the tables are generated by `make corpus-tables` and are missing from a
    fresh worktree. Recursion stops there, which is exact — a file that does
    not exist composes nothing further.

    Known boundary: the scan is not fence-aware, so an `{{< include >}}` shown
    as an example inside a code block would read as a real edge. No document
    has one today (checked across every .qmd and shared include), and the
    failure mode is benign — a spurious edge marks an artifact reachable, never
    the reverse — so this stays a regex rather than a Markdown parser.
    """
    root = os.path.join(DELIVERABLES, qmd)
    top = os.path.dirname(root)
    seen, pending, refs, text = set(), [root], set(), []
    while pending:
        current = os.path.normpath(pending.pop())
        if current in seen:
            continue
        seen.add(current)
        if not os.path.isfile(current):
            continue
        text.append(_read(current))
        for target in INCLUDE_RE.findall(text[-1]):
            resolved = os.path.normpath(os.path.join(top, target))
            refs.add(os.path.relpath(resolved, BASE))
            pending.append(resolved)
    return refs, "\n".join(text)


def _roots(deliverable):
    folder = os.path.join(DELIVERABLES, deliverable)
    return [os.path.join(deliverable, f)
            for f in sorted(os.listdir(folder)) if f.endswith(".qmd")]


def _tracked(tree):
    """Tracked Markdown under `tree` — git, not disk.

    Disk would be machine-dependent: most of these artifacts are build output
    and a fresh worktree holds only the committed handoff subset.
    """
    out = subprocess.run(["git", "ls-files", tree], cwd=BASE,
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split() if p.endswith(".md")]


FIG_VARS = _figure_vars()
NOT_EMBEDDED = dict(NOT_EMBEDDED_RE.findall(_read(PATHS_MK)))
ALLOWED = dict(ALLOWLIST_RE.findall(
    "\n".join(ln for ln in _read(ALLOWLIST).splitlines()
              if ln.strip() and not ln.startswith("#"))))

ALL_DELIVERABLES = sorted(
    d for d in os.listdir(DELIVERABLES)
    if d != "_shared" and os.path.isdir(os.path.join(DELIVERABLES, d)))
CLOSURES = {q: _closure(q) for d in ALL_DELIVERABLES for q in _roots(d)}
RENDERED = {d: "\n".join(CLOSURES[q][1] for q in _roots(d))
            for d in ALL_DELIVERABLES}
ALL_RENDERED = "\n".join(RENDERED.values())
REACHED = {p for refs, _ in CLOSURES.values() for p in refs}
DELIVERABLES_COVERED = sorted(
    {d for ds in FIG_VAR_DELIVERABLES.values() for d in ds})


@pytest.mark.adherence
@pytest.mark.parametrize("variable", sorted(FIG_VAR_DELIVERABLES))
def test_declared_figures_are_rendered(variable):
    """Nothing in a figure set is dead weight."""
    consumers = FIG_VAR_DELIVERABLES[variable]
    orphans = [f for f in FIG_VARS.get(variable, [])
               if f not in NOT_EMBEDDED
               and not any(f in RENDERED[d] for d in consumers)]
    assert not orphans, (
        f"{variable} names figures none of {list(consumers)} renders: "
        f"{orphans}. Move each to the variable of the deliverable that renders "
        f"it, drop it, or add a `# not-embedded: <file> — <reason>` marker in "
        f"paths.mk."
    )


@pytest.mark.adherence
@pytest.mark.parametrize("deliverable", DELIVERABLES_COVERED)
def test_rendered_figures_are_declared(deliverable):
    """A render rule keyed on the variables really covers the document."""
    variables = [v for v, ds in FIG_VAR_DELIVERABLES.items()
                 if deliverable in ds]
    declared = {f for v in variables for f in FIG_VARS.get(v, [])}
    used = set(GENERATED_PNG_RE.findall(RENDERED[deliverable]))
    assert not used - declared, (
        f"{deliverable} renders figures no variable declares: "
        f"{sorted(used - declared)}. Add them to {'/'.join(variables)}."
    )


@pytest.mark.adherence
@pytest.mark.parametrize("variable", sorted(INCLUDE_VAR_ROOTS))
def test_declared_includes_match_the_document(variable):
    """An include list is exactly what its document composes.

    Both directions matter and they fail differently: a surplus entry makes the
    PDF rebuild on a file the document dropped, a missing one makes it not
    rebuild when a live include changes.
    """
    declared = set(_var_paths(variable))
    composed = set()
    for root in INCLUDE_VAR_ROOTS[variable]:
        composed |= CLOSURES[root][0]
    assert not declared - composed, (
        f"{variable} declares includes the document does not compose: "
        f"{sorted(declared - composed)}. Drop them."
    )
    assert not composed - declared, (
        f"{variable} omits includes the document composes: "
        f"{sorted(composed - declared)}. Add them — the render rule uses this "
        f"list as its prerequisites."
    )


# `integration` alongside `adherence` on the two tests that shell out to git,
# matching tests/test_handoff_artifacts_tracked.py. Both markers are wanted:
# `make lint` selects on adherence, and the subprocess is what keeps these out
# of the fast tier.
@pytest.mark.adherence
@pytest.mark.integration
@pytest.mark.parametrize("tree", REACHABLE_TREES)
def test_shared_artifacts_are_reachable(tree):
    """Nothing under _shared/ is maintained for a document that dropped it."""
    orphans = sorted(p for p in _tracked(tree)
                     if p not in REACHED and p not in ALLOWED)
    assert not orphans, (
        f"{tree} holds files no deliverable composes: {orphans}. Include one "
        f"from a .qmd, delete it, or add it to config/unrendered-artifacts.txt "
        f"with the reason it is built for nobody."
    )


@pytest.mark.adherence
@pytest.mark.integration
def test_allowlist_entries_are_earned():
    """The allowlist is an exception list, not a mute skip-list."""
    tracked = {p for tree in REACHABLE_TREES for p in _tracked(tree)}
    for path, reason in sorted(ALLOWED.items()):
        assert path in tracked, (
            f"config/unrendered-artifacts.txt lists {path}, which is not a "
            f"tracked Markdown file under {' or '.join(REACHABLE_TREES)} — "
            f"drop the entry.")
        assert path not in REACHED, (
            f"config/unrendered-artifacts.txt lists {path}, but a deliverable "
            f"now composes it. Drop the entry.")
        assert len(reason.split()) >= 5, (
            f"{path} needs a real reason, got {reason!r}.")


@pytest.mark.adherence
def test_every_figure_variable_is_accounted_for():
    """A new figure list cannot escape the guard by being unmapped."""
    stray = sorted(set(FIG_VARS) - set(FIG_VAR_DELIVERABLES)
                   - set(UNMAPPED_FIG_VARS))
    assert not stray, (
        f"paths.mk figure lists mapped to no deliverable: {stray}. Add them to "
        f"FIG_VAR_DELIVERABLES, or to UNMAPPED_FIG_VARS with a reason."
    )


@pytest.mark.adherence
def test_every_include_variable_is_accounted_for():
    """Same, for include lists — a new one is checked or it is not there."""
    stray = sorted(n for n in VARIABLES
                   if n.endswith("_INCLUDES") and n not in INCLUDE_VAR_ROOTS)
    assert not stray, (
        f"paths.mk include lists mapped to no document: {stray}. Add them to "
        f"INCLUDE_VAR_ROOTS."
    )


@pytest.mark.adherence
def test_every_document_with_includes_has_a_variable():
    """The other direction: a document cannot escape by having no variable.

    The check above catches a *variable* nobody mapped. This catches a
    *document* nobody declared: it composes includes, so its render rule needs
    them as prerequisites, but no `*_INCLUDES` list names it and both include
    checks skip it silently. A document that composes nothing (the agentic
    paper, the slide decks) needs no list, and the check starts applying the
    moment it gains its first include. Ported from ticket 0290's guard, the one
    direction this file did not already cover.
    """
    mapped = {root for roots in INCLUDE_VAR_ROOTS.values() for root in roots}
    unmapped = sorted(q for q, (refs, _) in CLOSURES.items()
                      if refs and q not in mapped)
    assert not unmapped, (
        f"Document(s) composing includes that no paths.mk list declares: "
        f"{unmapped}. Add a *_INCLUDES variable and map it in "
        f"INCLUDE_VAR_ROOTS — otherwise the render rule misses them."
    )


@pytest.mark.adherence
def test_not_embedded_markers_are_earned():
    """A marker names a declared figure that is still embedded nowhere."""
    declared = {f for figs in FIG_VARS.values() for f in figs}
    for fig, reason in sorted(NOT_EMBEDDED.items()):
        assert fig in declared, (
            f"`# not-embedded: {fig}` names no figure in any paths.mk "
            f"variable — drop the marker.")
        assert fig not in ALL_RENDERED, (
            f"`# not-embedded: {fig}` is stale: a deliverable now renders it. "
            f"Drop the marker.")
        assert len(reason.split()) >= 3, (
            f"`# not-embedded: {fig}` needs a real reason, got {reason!r}.")


@pytest.mark.adherence
def test_orphaned_figures_are_really_orphaned():
    """ORPHANED_FIGS is a holding pen, not a place to park a live figure."""
    live = [f for f in FIG_VARS.get("ORPHANED_FIGS", []) if f in ALL_RENDERED]
    assert not live, (
        f"ORPHANED_FIGS entries a deliverable renders: {live}. Move them to "
        f"that deliverable's figure set.")


@pytest.mark.adherence
def test_all_figs_builds_every_declared_figure():
    """`make figures` covers every figure set except the stated exceptions."""
    all_figs = _make_variables(_read(os.path.join(BASE, "Makefile")))["ALL_FIGS"]
    built = set(re.findall(r"\$\((\w+)\)", all_figs))
    expected = set(FIG_VAR_DELIVERABLES) | set(UNMAPPED_FIG_VARS)
    missing = sorted(expected - set(NOT_IN_ALL_FIGS) - built)
    assert not missing, f"ALL_FIGS omits figure sets: {missing}"
    surplus = sorted(built & set(NOT_IN_ALL_FIGS))
    assert not surplus, (
        f"ALL_FIGS pulls in sets `make figures` is meant to skip: {surplus} "
        f"({'; '.join(NOT_IN_ALL_FIGS[v] for v in surplus)})."
    )


@pytest.mark.adherence
@pytest.mark.parametrize("variable", sorted(FIG_VAR_DELIVERABLES))
def test_render_rules_depend_on_their_figures(variable):
    """A deliverable's render rule takes its figures as prerequisites.

    Three rules did not before 0359, so a rebuilt figure left the PDF stale.

    The check is on the *expanded* prerequisites, not on the variable name: the
    technical report reaches the zoo figures through `$(TECHREP_FIGS)` and the
    manuscript's clean-room .mk names its files literally, having no paths.mk
    to include. Both are correct, and only expansion sees that.
    """
    for deliverable in FIG_VAR_DELIVERABLES[variable]:
        if deliverable in NO_RENDER_RULE:
            continue
        folder = os.path.join(DELIVERABLES, deliverable)
        local = dict(VARIABLES)
        prerequisites = []
        for path in mk_fragments():
            if os.path.dirname(str(path)) != folder:
                continue
            text = _read(str(path))
            local.update(_make_variables(text))
            prerequisites += [ln.split(":", 1)[1]
                              for ln in re.sub(r"\\\n", " ", text).splitlines()
                              if ".pdf:" in ln]
        wired = _expand(" ".join(prerequisites), local)
        missing = [f for f in FIG_VARS.get(variable, []) if f not in wired]
        assert not missing, (
            f"{deliverable}'s render rule does not depend on {missing} from "
            f"$({variable}), so the PDF does not rebuild when they change.")
