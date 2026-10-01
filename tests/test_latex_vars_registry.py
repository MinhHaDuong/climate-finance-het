"""The LaTeX macro emitter remains available to document consumers."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS / "analysis"))

from _vars_registry import (
    LATEX_DOC_VARS,
    LATEX_DOC_VARS_FILE,
    write_latex_vars,
)
from build_latex_vars import write_registered_latex_vars

pytestmark = pytest.mark.domain_writing

def test_latex_macro_emitter_escapes_tex_special_delimiters(tmp_path: Path):
    target = tmp_path / "vars.tex"
    write_latex_vars({"source_note": r"a\b{c}"}, str(target))

    assert r"\newcommand{\SourceNote}{a\textbackslash{}b\{c\}}" in target.read_text(
        encoding="utf-8"
    )


def test_registered_latex_vars_write_below_requested_output(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(LATEX_DOC_VARS, "example", {"source_note": "verified"})
    monkeypatch.setitem(LATEX_DOC_VARS_FILE, "example", "example-vars.tex")
    write_registered_latex_vars(tmp_path)

    for document, values in LATEX_DOC_VARS.items():
        rendered = (tmp_path / document / f"{document}-vars.tex").read_text()
        for key, value in values.items():
            assert rf"\newcommand{{\{latex_macro_name(key)}}}{{{value}}}" in rendered
