"""The live JETP LaTeX papers receive macros from the document registry."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS / "analysis"))

from _vars_registry import (
    LATEX_DOC_VARS,
    LATEX_DOC_VARS_FILE,
    latex_macro_name,
    write_latex_vars,
)


def test_each_jetp_latex_document_has_a_generated_witness_macro():
    """The skeleton proves the macro plumbing before empirical keys arrive."""
    assert set(LATEX_DOC_VARS) == {"jetp-mesure", "jetp-econpol"}
    assert set(LATEX_DOC_VARS) == set(LATEX_DOC_VARS_FILE)
    assert latex_macro_name("jetp_data_status") == "JetpDataStatus"

    for document, values in LATEX_DOC_VARS.items():
        rendered = Path(LATEX_DOC_VARS_FILE[document]).read_text(encoding="utf-8")
        for key, value in values.items():
            assert rf"\newcommand{{\{latex_macro_name(key)}}}{{{value}}}" in rendered


def test_latex_macro_emitter_escapes_tex_special_delimiters(tmp_path: Path):
    target = tmp_path / "vars.tex"
    write_latex_vars({"source_note": r"a\b{c}"}, str(target))

    assert r"\newcommand{\SourceNote}{a\textbackslash{}b\{c\}}" in target.read_text(
        encoding="utf-8"
    )
