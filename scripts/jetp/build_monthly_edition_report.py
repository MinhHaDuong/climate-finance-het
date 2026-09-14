"""Write a reviewed monthly-edition comparison or static release history."""

import argparse
import json
from pathlib import Path

from script_io_args import parse_io_args, validate_io
from jetp._monthly_editions import compare_editions, release_history


def main():
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('compare', 'history'), required=True)
    parser.add_argument('--releases', type=Path)
    args = parser.parse_args(extra)
    validate_io(output=io_args.output, inputs=io_args.input)
    if args.mode == 'compare':
        if len(io_args.input or []) != 2:
            parser.error('compare requires --input PREVIOUS CURRENT')
        report = compare_editions(*(json.loads(path.read_text()) for path in io_args.input))
    else:
        if io_args.input or not args.releases:
            parser.error('history requires --releases and no --input')
        report = release_history(args.releases)
    io_args.output.parent.mkdir(parents=True, exist_ok=True)
    io_args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
