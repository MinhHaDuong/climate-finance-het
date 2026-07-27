"""No `{{< meta >}}` macro reaches a rendered deliverable unresolved (ticket 0363).

Quarto exits 0 when a macro names a key its metadata does not declare, writes
the literal `?meta:key` into the document, and warns only on stderr. Every
number a referee checks in the data paper is behind that mechanism, and until
this suite its only gate was someone remembering to look at the finished PDF.

Two guards, deliberately different in what they trust:

* the **render oracle** asks Quarto — the authority on its own resolution — and
  reads the output it actually produced. It needs the toolchain and the
  generated includes, so it is `integration` and skips where either is absent.
* the **static resolver** answers from the files on disk, against the generated
  `*-vars.yml` rather than the `DOC_VARS` dict one layer above it. It needs
  nothing, so it runs in the fast loop and covers every machine — including the
  fresh worktrees where the render guard skips.

Both are proved able to fail, on a document written to be broken, before either
is trusted on a real one — the invariant ticket 0327 paid for.
"""

import pytest
from _qmd_meta import (
    PLACEHOLDER,
    QUARTO_REFUSES,
    WARNING,
    declared_keys,
    deliverable_qmds,
    meta_keys_used,
    render_to_markdown,
    require_quarto,
    source_files,
    unresolved_meta_keys,
)

#: Documents known to render `?meta:` placeholders today, with the ticket that
#: fixes each. The static guard marks these `strict`, so the entry fails the
#: suite once the document is fixed and a stale exemption cannot outlive the
#: defect it names.
KNOWN_UNRESOLVED = {
    # corpus-report reads technical-report-vars.yml but is absent from
    # compute_vars.DOC_VARS, so it has no vars file of its own: 12 distinct
    # keys, 22 occurrences, all rendering as placeholders. Ticket 0357 owns the
    # registry gap itself. (0322 is adjacent, not the fix — its action 2 covers
    # the verify_*/complete_* vars, a different set of keys.)
    "corpus-report": "ticket 0357 — corpus-report is outside the vars registry",
}


def _params(strict=True):
    """Discovered documents, each carrying its own known-defect mark.

    `strict` belongs to the static guard alone. A `pytest.skip()` raised inside
    a strict xfail reports SKIPPED, not XPASS, so a guard that can skip cannot
    be relied on to self-destruct when the defect is fixed — and the render
    guard skips wherever a gitignored generated include is absent, which is the
    ordinary fresh-worktree case. The static guard has no skip path, so it
    carries the strict mark and the self-destruct property for both.
    """
    out = []
    for qmd in deliverable_qmds():
        marks = []
        if qmd.stem in KNOWN_UNRESOLVED:
            marks.append(pytest.mark.xfail(strict=strict, reason=KNOWN_UNRESOLVED[qmd.stem]))
        out.append(pytest.param(qmd, marks=marks, id=qmd.stem))
    return out


def _broken_document(tmp_path, key="absent_key"):
    """A minimal Quarto document naming one declared key and one undeclared."""
    (tmp_path / "probe-vars.yml").write_text('declared_key: "1,234"\n', encoding="utf-8")
    qmd = tmp_path / "probe.qmd"
    qmd.write_text(
        "---\n"
        'title: "Probe"\n'
        "metadata-files: [probe-vars.yml]\n"
        "---\n\n"
        "Declared: {{< meta declared_key >}}. Undeclared: {{< meta " + key + " >}}.\n",
        encoding="utf-8",
    )
    return qmd


# --------------------------------------------------------------------------
# The static resolver
# --------------------------------------------------------------------------

def test_static_resolver_flags_an_undeclared_key(tmp_path):
    """Red first: the resolver must see the defect on a document built to have it."""
    qmd = _broken_document(tmp_path)
    assert unresolved_meta_keys(qmd) == {"absent_key"}


def test_static_resolver_reads_the_generated_vars_file(tmp_path):
    """A key resolves *because the vars file declares it*, not because a dict does.

    Deleting the artifact Quarto loads must be enough to make the same document
    fail — otherwise the guard is reading something one layer removed, which is
    exactly the gap that let 0363 through.
    """
    qmd = _broken_document(tmp_path)
    assert "declared_key" not in unresolved_meta_keys(qmd)
    (tmp_path / "probe-vars.yml").unlink()
    assert "declared_key" in unresolved_meta_keys(qmd)


@pytest.mark.parametrize("qmd", _params())
def test_no_deliverable_uses_an_undeclared_meta_key(qmd):
    """Every `{{< meta X >}}` in a deliverable resolves against its metadata."""
    unresolved = unresolved_meta_keys(qmd)
    assert not unresolved, (
        f"{qmd.name}: {len(unresolved)} macro key(s) nothing declares, each of "
        f"which renders as `{PLACEHOLDER}key`: {sorted(unresolved)}"
    )


def test_discovery_finds_the_deliverables():
    """A glob that matches nothing parametrizes nothing, and pytest calls that a pass.

    Every guard below is parametrized over `deliverable_qmds()`, so renaming
    `deliverables/` — this repo has renamed a deliverable directory before —
    would remove all three at once, silently and with exit 0. The data paper is
    named outright because its 77 macro keys are why this suite exists.
    """
    found = deliverable_qmds()
    assert found, "no deliverable .qmd discovered — has deliverables/ moved?"
    assert "data-paper" in {qmd.stem for qmd in found}, (
        f"the data paper is not among the discovered documents: "
        f"{sorted(qmd.stem for qmd in found)}"
    )


@pytest.mark.parametrize("qmd", [pytest.param(q, id=q.stem) for q in deliverable_qmds()])
def test_document_scan_is_not_silently_empty(qmd):
    """The scan reaches the document's own text and its metadata.

    A resolver that reads nothing reports nothing unresolved and passes forever.
    Missing *includes* are tolerated — `_shared/tables/*.md` is generated and
    gitignored, so a fresh worktree legitimately lacks some — but a document
    that yields no source file at all, or a metadata-files declaration that
    resolves to no keys, means the scan itself broke.
    """
    files, _ = source_files(qmd)
    assert qmd.resolve() in files, f"{qmd.name}: scan did not reach the document itself"
    if meta_keys_used(qmd):
        assert declared_keys(qmd), f"{qmd.name}: uses meta macros but declares no keys"


# --------------------------------------------------------------------------
# The render oracle
# --------------------------------------------------------------------------

@pytest.mark.integration
def test_render_oracle_flags_an_undeclared_key(tmp_path):
    """Pins Quarto's failure mode, which is the reason this suite exists.

    Exit 0 is asserted deliberately: it is why no build step catches this, and
    if a future Quarto starts failing the render instead, this test says so.
    """
    require_quarto()
    result = render_to_markdown(_broken_document(tmp_path))
    assert result.returncode == 0, f"expected a silent failure, got:\n{result.stderr}"
    assert f"{PLACEHOLDER}absent_key" in result.stdout
    assert WARNING in result.stderr
    assert "1,234" in result.stdout, "the declared key should still resolve"


@pytest.mark.integration
def test_quarto_still_refuses_the_reserved_keys(tmp_path):
    """Every key in `QUARTO_REFUSES` is one a real render still refuses.

    The static resolver subtracts this set, so an entry that Quarto *started*
    exposing would make it under-declare and report a false positive, while a
    newly-reserved key absent from the set would let a real `?meta:` through.
    Rendering the set is the only thing that can tell either way.
    """
    require_quarto()
    keys = sorted(QUARTO_REFUSES)
    (tmp_path / "probe-vars.yml").write_text("declared_key: ok\n", encoding="utf-8")
    body = "\n".join(f"K{k.replace('-', '')}: {{{{< meta {k} >}}}}" for k in keys)
    qmd = tmp_path / "reserved.qmd"
    qmd.write_text(
        "---\n"
        'title: "Reserved"\n'
        "metadata-files: [probe-vars.yml]\n"
        "number-sections: true\n"
        "format: html\n"
        f"---\n\n{body}\n",
        encoding="utf-8",
    )
    result = render_to_markdown(qmd)
    assert result.returncode == 0, f"probe failed to render:\n{result.stderr}"
    exposed = [k for k in keys if f"{PLACEHOLDER}{k}" not in result.stdout]
    assert not exposed, (
        f"Quarto now exposes {exposed} to a meta macro; drop them from "
        f"QUARTO_REFUSES or the static resolver reports false positives"
    )


@pytest.mark.integration
@pytest.mark.parametrize("qmd", _params(strict=False))
def test_rendered_deliverable_has_no_meta_placeholder(qmd):
    """Ask Quarto itself: nothing it produced carries a `?meta:` placeholder."""
    require_quarto()
    _, missing = source_files(qmd)
    if missing:
        pytest.skip(f"generated include not built: {missing[0]} (run `make corpus-tables`)")
    result = render_to_markdown(qmd)
    assert result.returncode == 0, f"{qmd.name} failed to render:\n{result.stderr}"
    placeholders = sorted({
        line for line in result.stdout.split() if PLACEHOLDER in line
    })
    assert not placeholders, (
        f"{qmd.name}: rendered output carries unresolved macros: {placeholders}"
    )
    assert WARNING not in result.stderr, (
        f"{qmd.name}: Quarto warned about an unknown meta key:\n{result.stderr}"
    )
