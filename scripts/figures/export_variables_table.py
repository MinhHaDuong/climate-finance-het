"""Generate the variables-description table for the data paper (ticket 0279).

Renders the climate_finance_corpus.csv column contract declared in
scripts/deposit_variables.py as a Quarto pipe table (@tbl-variables).
export_deposit.py enforces the same contract at write time, so this table
cannot drift from the shipped CSV.

Usage:
    uv run python scripts/figures/export_variables_table.py \
        --output deliverables/_shared/tables/tab_variables.md
"""

from deposit_variables import render_markdown_table
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("export_variables_table")


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)

    with open(io_args.output, "w", encoding="utf-8") as f:
        f.write(render_markdown_table())
    log.info("Wrote %s", io_args.output)


if __name__ == "__main__":
    main()
