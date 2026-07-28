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

import re

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

#: Documents that render `?meta:` placeholders today, pinned to the exact keys.
#:
#: An `xfail` would be the obvious way to record a known defect and it is the
#: wrong one here: it says only "this document fails", so a *new* unresolved
#: key in the same document reports the identical `1 xfailed` and nothing
#: notices. Pinning the set instead makes the guard fail in both directions —
#: when a key is added, and when the fix lands and the set empties, at which
#: point the entry is deleted rather than left to rot.
#:
#: Empty since ticket 0357, which registered corpus-report in
#: `compute_vars.DOC_VARS` and so emptied the only entry this map ever held —
#: the 12 keys it read from the shared technical-report-vars.yml that nothing
#: declared. Leaving the map in place rather than deleting it keeps the
#: mechanism available for the next known-broken document, and keeps the
#: guard's both-directions behaviour: a new unresolved key fails here.
KNOWN_UNRESOLVED: dict[str, frozenset[str]] = {}

PLACEHOLDER_RE = re.compile(re.escape(PLACEHOLDER) + r"([A-Za-z0-9_.-]+)")


def _params():
    """Every discovered document, as a parametrize list."""
    return [pytest.param(qmd, id=qmd.stem) for qmd in deliverable_qmds()]


def _assert_matches_expectation(qmd, unresolved, where):
    """Compare an unresolved-key set against what this document is pinned to."""
    expected = KNOWN_UNRESOLVED.get(qmd.stem, frozenset())
    if unresolved == expected:
        return
    new = sorted(unresolved - expected)
    fixed = sorted(expected - unresolved)
    detail = []
    if new:
        detail.append(f"{len(new)} key(s) nothing declares, each rendering as "
                      f"`{PLACEHOLDER}key`: {new}")
    if fixed:
        detail.append(f"{len(fixed)} key(s) now resolve — drop them from "
                      f"KNOWN_UNRESOLVED: {fixed}")
    raise AssertionError(f"{qmd.name} ({where}): " + "; ".join(detail))


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


@pytest.mark.parametrize("bad", ['- a\n- b\n', 'just a string\n'])
def test_static_resolver_rejects_a_vars_file_that_is_not_a_mapping(tmp_path, bad):
    """A malformed vars file must fail loudly, not quietly declare nonsense.

    `set()` over a YAML list yields its elements; over a bare scalar, its
    characters. Either way every macro would look declared and the fast tier —
    the one that runs where no render can — would report an all-clear.
    """
    qmd = _broken_document(tmp_path)
    (tmp_path / "probe-vars.yml").write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        unresolved_meta_keys(qmd)


@pytest.mark.parametrize("qmd", _params())
def test_no_deliverable_uses_an_undeclared_meta_key(qmd):
    """Every `{{< meta X >}}` in a deliverable resolves against its metadata."""
    _assert_matches_expectation(qmd, unresolved_meta_keys(qmd), "static scan")


def test_discovery_finds_the_deliverables():
    """A glob that matches nothing parametrizes nothing, and pytest calls that a pass.

    Every guard below is parametrized over `deliverable_qmds()`, so renaming
    `deliverables/` — this repo has renamed a deliverable directory before —
    would remove all three at once, silently and with exit 0. The data paper is
    named outright because it resolves every number it reports through this
    mechanism, which is why the suite exists. No key count here: it moves with
    every ticket that converts a literal, and a suite about numbers rotting
    should not ship a rotting number of its own.
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
@pytest.mark.parametrize("qmd", _params())
def test_rendered_deliverable_has_no_meta_placeholder(qmd):
    """Ask Quarto itself: nothing it produced carries a `?meta:` placeholder."""
    require_quarto()
    _, missing = source_files(qmd)
    if missing:
        pytest.skip(f"generated include not built: {missing[0]} (run `make corpus-tables`)")
    result = render_to_markdown(qmd)
    assert result.returncode == 0, f"{qmd.name} failed to render:\n{result.stderr}"
    _assert_matches_expectation(
        qmd, set(PLACEHOLDER_RE.findall(result.stdout)), "rendered output"
    )
    if not KNOWN_UNRESOLVED.get(qmd.stem):
        assert WARNING not in result.stderr, (
            f"{qmd.name}: Quarto warned about an unknown meta key:\n{result.stderr}"
        )
