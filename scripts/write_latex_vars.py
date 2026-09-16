"""Write the committed macro handoffs for the live JETP LaTeX papers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "analysis"))

from _vars_registry import LATEX_DOC_VARS, LATEX_DOC_VARS_FILE, write_latex_vars


def main() -> None:
    for document, values in LATEX_DOC_VARS.items():
        path = LATEX_DOC_VARS_FILE[document]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_latex_vars(values, path)


if __name__ == "__main__":
    main()
