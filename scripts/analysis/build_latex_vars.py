"""Write the committed macro handoffs for the live JETP LaTeX papers."""

import argparse
import os
from pathlib import Path

from _vars_registry import LATEX_DOC_VARS, LATEX_DOC_VARS_FILE, write_latex_vars


def write_registered_latex_vars(output_dir: Path) -> None:
    """Write every registered JETP macro file below *output_dir*."""
    for document, values in LATEX_DOC_VARS.items():
        path = output_dir / document / Path(LATEX_DOC_VARS_FILE[document]).name
        os.makedirs(path.parent, exist_ok=True)
        write_latex_vars(values, str(path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="root directory containing the registered JETP deliverables",
    )
    args = parser.parse_args()
    write_registered_latex_vars(args.output)


if __name__ == "__main__":
    main()
