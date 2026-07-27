"""Shared scan of Quarto `{{< meta >}}` macros and the metadata that resolves them.

Quarto exits 0 on a macro naming a key no metadata declares. It writes the
literal `?meta:key` into the rendered document and warns on stderr, and nothing
downstream reads either — so the defect reaches the page and only a human
reading the finished PDF can see it (ticket 0363).

Two guards cover that failure: a static resolver that answers from the files on
disk, and a render oracle that asks Quarto itself. Both need the same three
answers — which documents exist, which keys each uses across its include tree,
and which keys its metadata actually declares — so those live here and the two
guards agree on what "a document's keys" means.

Support module, not a test module: `tests/_*.py` is this repo's flat helper
surface (`_source_roots.py`, `_gfm_render.py`).
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

META_RE = re.compile(r"\{\{<\s*meta\s+([^\s>]+?)\s*>\}\}")
INCLUDE_RE = re.compile(r"\{\{<\s*include\s+(\S+?)\s*>\}\}")
_FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\s*?\n", re.S)

#: The literal Quarto substitutes for a macro whose key it cannot resolve.
PLACEHOLDER = "?meta:"
#: The stderr line Quarto emits alongside it.
WARNING = "Unknown meta key"

#: Front-matter keys Quarto consumes as its own configuration and does not
#: expose to a `{{< meta >}}` macro. Being present in the header is therefore
#: not the same as being resolvable, and counting them as declared would let a
#: macro naming one pass the static guard while rendering `?meta:`.
#:
#: Established by probing every front-matter key of all 11 deliverables against
#: a real render: these three were refused in every document that carries them,
#: and the other twelve resolved. That makes it a verified floor over the keys
#: in use, not a transcription of Quarto's reserved list —
#: `test_quarto_still_refuses_the_reserved_keys` re-renders it so a Quarto
#: upgrade cannot silently change the answer.
QUARTO_REFUSES = frozenset({"format", "metadata-files", "number-sections"})


def deliverable_qmds() -> list[Path]:
    """Every rendering document, discovered rather than listed.

    Auto-discovery is the point: a hardcoded list silently stops covering the
    document someone adds next, which is the failure mode this guard exists to
    prevent.
    """
    return sorted(REPO_ROOT.glob("deliverables/*/*.qmd"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_mapping(path: Path) -> dict:
    """Load a metadata file, insisting it is a mapping.

    `set()` over a YAML list yields its *elements* as declared keys, and over a
    bare scalar yields its *characters* — either way the static guard declares
    keys nobody wrote and reports a false all-clear. A real render fails loudly
    on such a file, so only the toolchain-free tier needs this check, and that
    is the tier meant to work where the render cannot.
    """
    loaded = yaml.safe_load(_read(path))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path}: a metadata file must be a YAML mapping, got "
            f"{type(loaded).__name__}"
        )
    return loaded


def front_matter(qmd: Path) -> dict:
    """The document's YAML header, or an empty mapping if it has none."""
    match = _FRONT_MATTER_RE.match(_read(qmd))
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def source_files(qmd: Path) -> tuple[list[Path], list[str]]:
    """Return (the document and every file it includes, unresolvable includes).

    Includes are followed transitively and every path — nested ones included —
    resolves against the **root document's** directory, not against the file
    that contains it. Joining each include against its own directory is the
    natural implementation and it is wrong: it misses every nested include
    (`.claude/rules/architecture.md`, ticket 0359, where writing it that way
    produced 13 confident false positives).

    Some generated tables under `_shared/tables/` are gitignored — others are
    deliberately tracked, for the clean-room build — so a fresh worktree
    legitimately lacks a few includes. Those are returned rather than raised,
    so the caller decides whether a partial scan is good enough.
    """
    base = qmd.parent
    found: list[Path] = []
    unresolved: list[str] = []
    seen: set[Path] = set()
    queue = [qmd.resolve()]
    while queue:
        current = queue.pop()
        if current in seen or not current.is_file():
            continue
        seen.add(current)
        found.append(current)
        for spec in INCLUDE_RE.findall(_read(current)):
            candidate = base / spec
            if candidate.is_file():
                queue.append(candidate.resolve())
            else:
                unresolved.append(spec)
    return found, unresolved


def meta_keys_used(qmd: Path) -> set[str]:
    """Every key named by a `{{< meta >}}` macro in the document's include tree."""
    files, _ = source_files(qmd)
    return {key for f in files for key in META_RE.findall(_read(f))}


def declared_keys(qmd: Path) -> set[str]:
    """Every key Quarto can resolve: the header's own, plus its metadata files.

    Reading the generated `*-vars.yml` is the whole point — the older guard in
    `test_doc_vars_completeness.py` checks prose against the `DOC_VARS` dict in
    `compute_vars.py`, one layer above the artifact Quarto actually loads.

    Keys in `QUARTO_REFUSES` are excluded wherever they come from: Quarto keeps
    them for itself, so a header carrying `format:` does not make
    `{{< meta format >}}` resolve.
    """
    header = front_matter(qmd)
    keys = set(header)
    files = header.get("metadata-files") or []
    if isinstance(files, str):
        files = [files]
    for spec in files:
        path = qmd.parent / spec
        if path.is_file():
            keys |= set(_load_mapping(path))
    return keys - QUARTO_REFUSES


def unresolved_meta_keys(qmd: Path) -> set[str]:
    """Keys the document asks for that nothing declares — each one a `?meta:`."""
    return meta_keys_used(qmd) - declared_keys(qmd)


def require_quarto() -> None:
    """Skip the calling test where the Quarto toolchain is absent."""
    if shutil.which("quarto") is None:
        pytest.skip("quarto not available on this machine")


def render_to_markdown(qmd: Path) -> subprocess.CompletedProcess:
    """Render `qmd` through Quarto, returning the completed process.

    Markdown rather than the document's own PDF format: shortcodes resolve in a
    Lua filter ahead of writer selection, so both formats resolve identically
    while only one needs a LaTeX run — 2–8 s per document, ~1 min for the whole
    tier. `--output -` writes to stdout, so no rendered document lands beside a
    tracked source (Quarto still writes its gitignored `.quarto/` cache).
    `--no-execute` keeps the render off the compute path entirely.
    """
    return subprocess.run(
        ["quarto", "render", qmd.name, "--to", "markdown", "--no-execute", "--output", "-"],
        cwd=qmd.parent, capture_output=True, text=True, check=False,
    )
