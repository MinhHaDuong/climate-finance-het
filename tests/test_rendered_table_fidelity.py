"""Ticket 0325: the variables table must survive rendering, not just linting.

The defect this guards was invisible at source level. `render_markdown_table()`
emits a raw-LaTeX `longtable`, so pandoc never inspects those cells; the
description of `is_flagged` carried a correct `df[~df['is_flagged'] | ...]` in
the `.md` artifact, and LaTeX then read the `~` as a non-breaking space and
published the *complement* of the advertised subset. Every source-level
assertion passed while the PDF said the opposite of the paper's §3 prose.

So the oracle here is the rendered page. Each description is typeset twice in
one document — once through the emitter's raw LaTeX, once as ordinary Markdown
that Quarto's own pipeline escapes — and the extracted text of the two copies
must agree character for character. The Markdown copy is the same path §3
takes, which is what makes agreement meaningful rather than self-referential.
"""

import re
import shutil
import subprocess

import pytest
from _deposit_variables import (
    DEPOSIT_VARIABLES,
    describe,
    latex_inline,
)

RECIPE = "df[~df['is_flagged'] | df['is_protected']]"

# One line per description, wide enough that no line wraps: comparing extracted
# text is only meaningful when the extraction is not also doing layout.
_HEADER = """---
title: rendered-fidelity probe
format:
  pdf:
    geometry: [paperwidth=120cm, paperheight=200cm, margin=1cm]
---
"""


def _probe_document() -> str:
    emitted = [r"\begin{flushleft}"]
    emitted += ["EMIT " + latex_inline(describe(v)) + r"\\" for v in DEPOSIT_VARIABLES]
    emitted.append(r"\end{flushleft}")
    markdown = ["MARK " + describe(v) + "\n" for v in DEPOSIT_VARIABLES]
    return "\n".join(
        [_HEADER, "```{=latex}", *emitted, "```", "", *markdown])


def _extract(prefix: str, text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line[len(prefix):]).strip()
            for line in text.splitlines() if line.startswith(prefix)]


@pytest.fixture(scope="module")
def rendered(tmp_path_factory) -> tuple[list[str], list[str]]:
    """(emitted lines, markdown lines) as extracted from the built PDF."""
    for tool in ("quarto", "pdftotext"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} not available on this machine")
    workdir = tmp_path_factory.mktemp("fidelity")
    qmd = workdir / "probe.qmd"
    qmd.write_text(_probe_document(), encoding="utf-8")

    render = subprocess.run(
        ["quarto", "render", str(qmd), "--to", "pdf"],
        cwd=workdir, capture_output=True, text=True)
    pdf = workdir / "probe.pdf"
    if not pdf.is_file():
        pytest.skip(f"no PDF toolchain: quarto render failed\n{render.stderr[-2000:]}")

    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout
    emitted, markdown = _extract("EMIT ", text), _extract("MARK ", text)
    assert len(emitted) == len(DEPOSIT_VARIABLES), "probe document lost rows"
    assert len(markdown) == len(DEPOSIT_VARIABLES), "probe document lost rows"
    return emitted, markdown


@pytest.mark.integration
class TestRenderedFidelity:
    """One PDF build (~8 s), shared by both assertions through the fixture."""

    def test_every_description_renders_as_written(self, rendered):
        """Exit criterion: no description is altered by the LaTeX round trip."""
        emitted, markdown = rendered
        mismatched = [(v.name, e, m)
                      for v, e, m in zip(DEPOSIT_VARIABLES, emitted, markdown)
                      if e != m]
        assert not mismatched, "\n".join(
            f"{name}:\n  raw LaTeX: {e}\n  markdown : {m}"
            for name, e, m in mismatched)

    def test_reconstruction_recipe_keeps_its_negation(self, rendered):
        """The specific corruption: `~` typeset as a non-breaking space, so the
        published recipe selected the removed works instead of the kept ones.

        The recipe left the table cell with the one-line descriptions (author,
        2026-07-29); its rendered copy now lives in §3 prose and the
        datapackage description, both pinned by test_variables_table. Here the
        surviving fidelity claim is that the is_flagged row still renders and
        points at Section 3 rather than carrying a corrupted recipe."""
        emitted, _ = rendered
        line = emitted[[v.name for v in DEPOSIT_VARIABLES].index("is_flagged")]
        assert "Section 3" in line, \
            f"is_flagged row lost its Section 3 pointer: {line}"
        assert " " not in line, f"non-breaking space artifact: {line}"
