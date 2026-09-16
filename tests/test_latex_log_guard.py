"""The JETP LaTeX renderer rejects warnings that leave broken references."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_latex_log import assert_clean_log


REPO = Path(__file__).resolve().parents[1]
TECTONIC = shutil.which("tectonic") or "/home/haduong/.local/bin/tectonic"


@pytest.mark.parametrize(
    "warning",
    [
        "LaTeX Warning: Reference `missing' on page 1 undefined on input line 4.",
        "LaTeX Warning: Citation `missing' on page 1 undefined on input line 5.",
        "! Undefined control sequence.",
    ],
)
def test_log_guard_rejects_unresolved_latex_warning(tmp_path: Path, warning: str):
    """A successful latexmk process is insufficient when its log is broken."""
    log = tmp_path / "broken.log"
    log.write_text(warning + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unresolved LaTeX"):
        assert_clean_log(log)


def test_log_guard_accepts_clean_log(tmp_path: Path):
    log = tmp_path / "clean.log"
    log.write_text("Output written on skeleton.pdf (1 page).\n", encoding="utf-8")

    assert_clean_log(log)


@pytest.mark.integration
def test_log_guard_rejects_an_actual_tex_unresolved_reference(tmp_path: Path):
    """The guard sees the warning emitted by a real TeX engine, not a fixture."""
    if not Path(TECTONIC).is_file():
        pytest.skip("tectonic is unavailable")
    source = tmp_path / "broken.tex"
    source.write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Broken reference: \\ref{missing-label}.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [TECTONIC, "-C", "-k", "--keep-logs", "-r", "2", source.name],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    with pytest.raises(ValueError, match="unresolved LaTeX"):
        assert_clean_log(tmp_path / "broken.log")


@pytest.mark.parametrize("document", ["jetp-mesure", "jetp-econpol"])
def test_latexmk_recipe_changes_to_the_source_directory(document: str):
    """Sibling macro and bibliography paths require latexmk's ``-cd`` mode."""
    recipe = (REPO / "deliverables" / document / f"{document}.mk").read_text(
        encoding="utf-8"
    )
    assert "-cd" in recipe
