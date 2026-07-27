"""Shared `.mk` discovery for the build-guard tests (ticket 0248).

One place enumerates every Makefile fragment the pipeline `-include`s, so a
future `.mk` relocation updates a single list and no guard can silently narrow
its coverage. This closes the class defect that ticket 0239 surfaced: five
guards each hand-rolled a fixed-directory glob union that drifted apart when
fragments moved.

`<repo>` is resolved from this file's own location, so the helper is correct in
any worktree.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# `$(NAME)` or `${NAME}`; automatic variables ($@, $<) are deliberately left
# alone — they only appear in recipes, which this module never reads.
_VAR = re.compile(r"\$[({]([A-Za-z_][A-Za-z0-9_]*)[)}]")
# `NAME := value` and its `=`, `?=`, `+=` siblings, at column zero.
_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::=|\?=|\+=|=)\s*(.*?)\s*$")
# A rule line `target [target…]: prereqs`, at column zero (recipes are indented).
# The `(?!=)` lookahead is what separates `target:` from an `NAME :=` assignment.
_RULE = re.compile(r"^([^\s#][^:=]*):(?!=)")
_CONTINUATION = re.compile(r"\\\n[ \t]*")


def mk_fragments() -> list[Path]:
    """Every `-include`d build fragment, sorted for stable parametrized test IDs.

    Covers the three homes a `.mk` fragment can live in:
      - repo-root ``*.mk`` (``paths.mk``, the shared variable interface);
      - ``scripts/analysis/*.mk`` (Phase-2 analysis concerns, relocated by 0239);
      - ``deliverables/*/*.mk`` (per-deliverable Phase-3 render fragments).

    Excludes the top-level ``Makefile`` — use :func:`all_makefiles` for that.
    """
    fragments = list(REPO_ROOT.glob("*.mk"))
    fragments += list((REPO_ROOT / "scripts" / "analysis").glob("*.mk"))
    fragments += list((REPO_ROOT / "deliverables").glob("*/*.mk"))
    return sorted(fragments)


def all_makefiles(include_main: bool = True) -> list[Path]:
    """Every Makefile the build reads: the top-level ``Makefile`` plus fragments.

    Pass ``include_main=False`` for a guard that asserts a property of the
    ``-include``d *fragments* alone — e.g. single-phase purity, since the main
    ``Makefile`` legitimately wires both render and compute concerns.
    """
    files = mk_fragments()
    if include_main:
        files = [REPO_ROOT / "Makefile"] + files
    return files


def makefile_constants(files: list[Path] | None = None) -> dict[str, str]:
    """`NAME` → fully expanded value, read across `files` (default: all of them).

    Fragments share one namespace at build time (`paths.mk` is `-include`d by
    the main Makefile and by each per-deliverable one), so resolving a target
    written in one file often needs a constant defined in another. First
    definition wins, and `all_makefiles()` puts the top-level Makefile first.

    `files` is a parameter rather than a fixed union because the right scope is
    the caller's: `tests/test_phase_layout.py` deliberately reads the main
    Makefile alone, since widening its constant set would widen what it flags.
    """
    raw: dict[str, str] = {}
    for path in all_makefiles() if files is None else files:
        text = _CONTINUATION.sub(" ", path.read_text(encoding="utf-8"))
        for line in text.splitlines():
            assignment = _ASSIGN.match(line)
            if assignment:
                raw.setdefault(assignment.group(1), assignment.group(2))

    def expand(value: str, seen: frozenset[str]) -> str:
        def repl(match: re.Match) -> str:
            name = match.group(1)
            if name in raw and name not in seen:
                return expand(raw[name], seen | {name})
            return match.group(0)  # undefined, or self-referential: leave as-is
        return _VAR.sub(repl, value)

    return {name: expand(value, frozenset({name})) for name, value in raw.items()}


def expand_vars(token: str, constants: dict[str, str]) -> str:
    """Substitute `$(NAME)` references in `token`; unknown names pass through."""
    return _VAR.sub(lambda m: constants.get(m.group(1), m.group(0)), token)


def rule_targets() -> dict[str, str]:
    """Every declared Make target → the `<makefile>:<line>` that declares it.

    Targets are resolved through :func:`makefile_constants`, so a rule written
    as `$(GIDE_VENUES_FR):` is discovered under its real path. Grouped-target
    rules (`a.csv b.md &:`) contribute each target; the `&` token resolves to
    itself and is harmless to any suffix-filtering caller.
    """
    constants = makefile_constants()
    targets: dict[str, str] = {}
    for path in all_makefiles():
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, 1):
            rule = _RULE.match(line)
            if not rule:
                continue
            for token in rule.group(1).split():
                targets.setdefault(
                    expand_vars(token, constants),
                    f"{path.relative_to(REPO_ROOT)}:{lineno}",
                )
    return targets


def generated_markdown_targets() -> dict[str, str]:
    """Generated Markdown artifacts → the rule that builds each (ticket 0340).

    Every `.md` the build produces, discovered from the build rather than
    listed: an emitter added tomorrow is covered by whichever guard calls this,
    with no edit to that guard.
    """
    return {t: origin for t, origin in rule_targets().items() if t.endswith(".md")}
