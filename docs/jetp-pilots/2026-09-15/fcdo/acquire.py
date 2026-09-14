"""Explicit single-request acquisition with a cumulative cap; never follows redirects."""

import argparse
import csv
import datetime
import hashlib
import urllib.error
import urllib.request
from pathlib import Path

FIELDS = [
    "unit",
    "route",
    "case_id",
    "purpose",
    "url",
    "status",
    "retrieved",
    "bytes",
    "sha256",
    "archive_path",
    "error",
]


def acquire(url, name, case, purpose, route, output, log):
    rows = list(csv.DictReader(log.open())) if log.exists() else []
    if len(rows) >= 20:
        raise RuntimeError("FCDO cap exhausted")
    output.mkdir(parents=True, exist_ok=True)
    row = dict(zip(FIELDS, [""] * len(FIELDS), strict=True))
    row.update(
        unit=len(rows) + 1,
        route=route,
        case_id=case,
        purpose=purpose,
        url=url,
        retrieved=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "Climate-finance-history-research/0739"}
        )
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=35
        ) as response:
            payload = response.read()
            row["status"] = response.status
        (output / name).write_bytes(payload)
        row.update(
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            archive_path="data/jetp/audit-evidence/0739-pilot/" + name,
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        row.update(status=getattr(exc, "code", "failed"), error=str(exc))
    rows.append(row)
    with log.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(row["unit"], case, row["status"], row["bytes"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("url", "name", "case", "purpose", "route", "output", "log"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    acquire(
        args.url,
        args.name,
        args.case,
        args.purpose,
        args.route,
        Path(args.output),
        Path(args.log),
    )
