"""The JETP LaTeX renderer rejects warnings that leave broken references."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_latex_log import assert_clean_log


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
