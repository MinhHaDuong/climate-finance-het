"""Write a complete baseline/candidate archive or a semantic comparison report."""

import argparse
import json
from pathlib import Path

from script_io_args import parse_io_args, validate_io

from jetp._observatory_bundle import (
    build_candidate,
    freeze_bundle,
    restore_bundle,
    write_comparison,
)


def main():
    """Keep one invocation to one explicitly named output artifact."""
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('freeze', 'candidate', 'diff', 'restore'), required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--include-sources', action='store_true')
    parser.add_argument('--intentional', type=Path)
    args = parser.parse_args(extra)
    validate_io(output=io_args.output, inputs=io_args.input)
    inputs = io_args.input or []
    if args.mode == 'restore':
        if len(inputs) != 1:
            parser.error('restore requires --input BUNDLE')
        restore_bundle(inputs[0], io_args.output)
    elif args.mode == 'diff':
        if len(inputs) != 2:
            parser.error('diff requires --input ACCEPTED CANDIDATE')
        evidence = json.loads(args.intentional.read_text()) if args.intentional else {}
        write_comparison(args.root, *inputs, io_args.output, intentional_paths=evidence,
                         extra_inputs=(args.intentional,) if args.intentional else ())
    elif args.mode == 'candidate':
        if len(inputs) != 1:
            parser.error('candidate requires --input ACCEPTED')
        build_candidate(args.root, io_args.output, accepted=inputs[0], source_root=args.source_root,
                        include_sources=args.include_sources)
    else:
        freeze_bundle(args.root, io_args.output, source_root=args.source_root,
                      include_sources=args.include_sources)


if __name__ == '__main__':
    main()
