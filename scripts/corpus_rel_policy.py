"""Import approved local-only policy abstentions with honest native absence (2011).

--input is the registered immutable scope manifest, --archive-root holds its
native decision/input/failure artifacts, and --pool must match the approved
snapshot. --output is the append-only policy provenance table. --table and
--dimensions are explicitly bound canonical append targets. discipline_only
writes no ICF or facet row; no model call or public proof is fabricated.
"""
import argparse
import json
import sys
from pathlib import Path

import _icf_screen as ics
import _rel_facet_io as fio
import _rel_policy as policy
import yaml
from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("corpus_rel_policy")
ROOT = Path(__file__).resolve().parents[1]


def import_dispositions(records: list[dict], context: dict, *, table: str, dimensions: str,
                        output: str, run_id: str, labelled_at: str, machine: str,
                        new_table: bool = False) -> dict:
    """Preflight all append batches; never replace an assessed selected judgment."""
    labels = ics.read_table(table)
    dims = ics.read_table(dimensions, ics.DIMENSIONS)
    dispositions, icf_rows, dim_rows = policy.build_rows(records, context, labels, dims, run_id, labelled_at, machine)
    fresh_policy = not Path(output).exists()
    if fresh_policy and not new_table and any(r["labeller"] == "policy" for r in labels + dims):
        raise ValueError("policy table missing although canonical policy judgments exist; fetch it before importing")
    batches = [(output, dispositions, policy.SCHEMA, new_table or fresh_policy),
               (dimensions, dim_rows, ics.DIMENSIONS, new_table)]
    if icf_rows:
        batches.append((table, icf_rows, ics.ICF, new_table))
    result = fio.append_batches(batches)
    return {"scope": context["scope"], "dispositions": len(dispositions),
            "icf_rows": len(icf_rows), "dimension_rows": len(dim_rows),
            "appended_skipped": result, "native_model_answers": 0}


def main(argv=None):
    io, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=sorted(policy.SCOPES), required=True)
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--dimensions", required=True)
    parser.add_argument("--config", default=str(ROOT / "config/rel_local_policy_v1.yaml"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--labelled-at", required=True, help="stable disposition timestamp")
    parser.add_argument("--machine", default="padme")
    parser.add_argument("--new-table", action="store_true")
    args = parser.parse_args(extra)
    try:
        if not io.input or len(io.input) != 1:
            raise ValueError("--input must name exactly one approved policy scope manifest")
        validate_io(io.output, [*io.input, args.pool, args.config])
        ics.require_table(args.table)
        with open(args.config, encoding="utf-8") as fh:
            registry = yaml.safe_load(fh)
        records, context = policy.load_context(io.input[0], args.archive_root, args.pool, args.scope, registry)
        result = import_dispositions(records, context, table=args.table, dimensions=args.dimensions,
                                     output=io.output, run_id=args.run_id, labelled_at=args.labelled_at,
                                     machine=args.machine, new_table=args.new_table)
    except (ValueError, OSError, ics.IcfScreenError) as exc:
        log.error("%s", exc)
        return 1
    log.info("policy import %s", json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
