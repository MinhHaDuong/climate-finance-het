"""Write the bounded provenance sidecar for a complete static observatory site."""

import argparse
import json
from pathlib import Path

import yaml

from jetp._publication import reported_position_sidecar

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')


def build(root, output, *, data_directory=None):
    """Build only from the matching country payload bytes already selected for release."""
    root = Path(root)
    data = Path(data_directory or output.parent)
    config = yaml.safe_load((root / 'config/jetp_observatory.yaml').read_text())
    countries = {code: json.loads((data / f'{code}.json').read_text()) for code in COUNTRIES}
    result = reported_position_sidecar(config, countries)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-directory', type=Path)
    args = parser.parse_args()
    build(args.root, args.output, data_directory=args.data_directory)


if __name__ == '__main__':
    main()
