"""Build one immutable, offline JETP public-release archive."""

import argparse
from pathlib import Path

from jetp._public_release import build_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--input-git-sha', required=True)
    parser.add_argument('--cutoff', required=True)
    parser.add_argument('--prepared-on', required=True)
    parser.add_argument('--reviewer', required=True)
    args = parser.parse_args()
    build_release(args.root, args.output, edition=args.edition, input_git_sha=args.input_git_sha,
                  cutoff=args.cutoff, prepared_on=args.prepared_on, reviewer=args.reviewer)


if __name__ == '__main__':
    main()
