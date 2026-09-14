"""Write a deterministic source migration candidate without transferring ownership."""

import argparse
import gzip
import json
import os
import tempfile
from pathlib import Path

from script_io_args import parse_io_args, validate_io

from jetp._observatory_bundle import _protect_output
from jetp._source_crosswalk import SCHEMA_VERSION, migrate_sources


def _release_inputs(root: Path, output: Path) -> tuple[Path, ...]:
    """Protect every release file except a recognized previous candidate output."""
    replaceable = False
    if output.is_file():
        try:
            payload = output.read_bytes()
            if output.suffix == '.gz':
                payload = gzip.decompress(payload)
            previous = json.loads(payload)
            replaceable = (isinstance(previous, dict)
                           and previous.get('schema_version') == SCHEMA_VERSION
                           and previous.get('admission_status') == 'unadmitted_candidate')
        except (OSError, ValueError, EOFError, UnicodeError):
            pass
    return tuple(path for path in (root / 'data/jetp/releases').rglob('*')
                 if path.is_file() and not (path == output and replaceable))


def write_crosswalk(root: Path, output: Path, *, source_root: Path | None = None) -> dict:
    """Validate a complete candidate before atomically replacing its single artifact."""
    root, output = Path(root).resolve(), Path(output).resolve()
    source_root = Path(source_root or root).resolve()
    if not (output.suffix == '.json' or output.name.endswith('.json.gz')):
        raise ValueError('Candidate output must end in .json or .json.gz')
    _protect_output(root, output, inputs=_release_inputs(root, output))
    _protect_output(source_root, output, inputs=_release_inputs(source_root, output))
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
