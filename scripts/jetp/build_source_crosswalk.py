"""Write a deterministic source migration candidate without transferring ownership."""

import argparse
import gzip
import json
import os
import tempfile
from pathlib import Path

from script_io_args import parse_io_args, validate_io

from jetp._observatory_bundle import _protect_output
from jetp._source_crosswalk import migrate_sources


def write_crosswalk(root: Path, output: Path, *, source_root: Path | None = None) -> dict:
    """Validate a complete candidate before atomically replacing its single artifact."""
    root, output = Path(root).resolve(), Path(output).resolve()
    source_root = Path(source_root or root).resolve()
    protected = tuple((root / 'data/jetp/releases').glob('*.zip'))
    _protect_output(root, output, inputs=protected)
    _protect_output(source_root, output, inputs=tuple((source_root / 'data/jetp/releases').glob('*.zip')))
    result = migrate_sources(root, source_root=source_root)
    payload = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()
    if output.suffix == '.gz':
        payload = gzip.compress(payload, mtime=0)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return result


def main():
    """Accept explicit checkout, byte recovery root and candidate output paths."""
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args(extra)
    inputs = io_args.input or []
    if len(inputs) != 1:
        parser.error('requires --input CHECKOUT_ROOT')
    validate_io(output=io_args.output, inputs=inputs)
    write_crosswalk(Path(inputs[0]), Path(io_args.output), source_root=args.source_root)


if __name__ == '__main__':
    main()
