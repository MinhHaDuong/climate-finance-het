"""Index the archived copies staged beside the local observatory preview.

The observatory's pages link an archived copy only where the server holds it
(ticket 0915). They learn which copies it holds from ``documents/index.json``,
which this script writes from the files actually staged under
``deliverables/jetp-observatory/documents/objects``: the site-relative path of
each, in the form the registry's ``local_path`` uses. ``documents/`` is
untracked, so the public bundle never carries the index and its pages never
draw an archived link.

Run by ``make jetp-observatory-documents``; never part of the JSON build.
"""

import argparse
import json
import os
from pathlib import Path

from utils import get_logger

log = get_logger("build_documents_index")


def staged_objects(documents: Path) -> list[str]:
    """Every staged file under ``objects/``, as ``documents/objects/...``.

    Symlinks are followed: where reflinks are unsupported, ``objects`` is a
    link to the DVC checkout rather than a copy of it.
    """
    root = documents / "objects"
    found = []
    for directory, _, files in os.walk(root, followlinks=True):
        for name in files:
            relative = (Path(directory) / name).relative_to(documents)
            found.append("documents/" + relative.as_posix())
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path,
                        default=Path("deliverables/jetp-observatory/documents"),
                        help="the staged documents directory")
    parser.add_argument("--output", type=Path, default=None,
                        help="index path (default: <documents>/index.json)")
    args = parser.parse_args()
    if args.documents.is_symlink():
        # The old fallback linked the whole directory to data/jetp/documents:
        # an index written through it would land in the DVC checkout.
        parser.error(f"{args.documents} is a symlink; run make jetp-observatory-refresh")
    output = args.output or args.documents / "index.json"
    objects = staged_objects(args.documents)
    output.write_text(json.dumps({"objects": objects}, indent=0) + "\n", encoding="utf-8")
    log.info("Indexed %d staged copies in %s", len(objects), output)


if __name__ == "__main__":
    main()
