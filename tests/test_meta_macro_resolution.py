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
  nothing, so it runs in the fast loop and covers every machine.

Both are proved able to fail, on a document written to be broken, before either
is trusted on a real one — the invariant ticket 0327 paid for.
"""

import pytest
from _qmd_meta import (
    PLACEHOLDER,
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
#: fixes each. `strict` is the point: the entry fails the suite once the
#: document is fixed, so a stale exemption cannot outlive the defect.
KNOWN_UNRESOLVED = {
    # corpus-report reads technical-report-vars.yml but is absent from
    # compute_vars.DOC_VARS, so it has no vars file of its own and renders 22
    # placeholders. Ticket 0322 action 2 owns registering its vars; ticket
    # 0357, filed on the branch of PR #1162 and not yet on main, states the
    # registry gap directly.
    "corpus-report": "tickets 0322 / 0357 — corpus-report is outside the vars registry",
}


def _params():
    """Discovered documents, each carrying its own known-defect mark."""
    out = []
    for qmd in deliverable_qmds():
        marks = []
        if qmd.stem in KNOWN_UNRESOLVED:
            marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_UNRESOLVED[qmd.stem]))
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
@pytest.mark.parametrize("qmd", _params())
def test_rendered_deliverable_has_no_meta_placeholder(qmd):
    """Ask Quarto itself: nothing it produced carries a `?meta:` placeholder."""
    require_quarto()
    _, missing = source_files(qmd)
    if missing:
        pytest.skip(f"generated include not built: {missing[0]} (run `make analysis`)")
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
