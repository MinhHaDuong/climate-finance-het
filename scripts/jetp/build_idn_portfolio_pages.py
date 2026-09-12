# WARNING: AI-generated, not human-reviewed
"""Build reconciled records from archived Indonesia JETP programme profiles.

The official portfolio stores one page per grant programme and one financing
table row per donor modality.  This extractor preserves the portal's own
amounts separately from the 2025 Progress Report events so rounding and source
differences remain visible rather than being silently overwritten.
"""

import argparse
import csv
import re
from html.parser import HTMLParser
from pathlib import Path

from script_io_args import parse_io_args, validate_io

OUTPUT_FIELDS = (
    "country",
    "project_id",
    "source_id",
    "document_sha256",
    "title",
    "period",
    "ipg_entity",
    "beneficiary",
    "implementing_partner",
    "specific_focus",
    "modality",
    "financing_type",
    "financing_source",
    "financing_intermediary",
    "amount_home_currency",
    "amount_home",
    "amount_usd",
    "part_of_jetp_pledge",
    "matched_event_id",
    "report_currency_home",
    "report_amount_home",
    "reconciliation_status",
    "notes",
)

FIELD_LABELS = {
    "ipg_entity": "IPG Country / Entity",
    "beneficiary": "Beneficiary",
    "implementing_partner": "Implementing Partner",
    "specific_focus": "Specific Focus",
}

MODALITY_PATTERN = re.compile(r"Modality\s+[A-Z0-9]+")
AMOUNT_PATTERN = re.compile(r"([A-Z]{3})\s+([0-9][0-9,.]*)")


class _VisibleTextParser(HTMLParser):
    """Collect normalized visible strings without a third-party dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        value = " ".join(data.split())
        if value:
            self.values.append(value)


def _value_after(values: list[str], label: str) -> str:
    try:
        return values[values.index(label) + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError(f"missing portfolio field: {label}") from exc


def _parse_amount(value: str) -> tuple[str, str]:
    match = AMOUNT_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"invalid portfolio amount: {value}")
    currency, amount = match.groups()
    return currency, amount.replace(",", "")


def parse_portfolio_html(html: str) -> list[dict[str, str]]:
    """Return one normalized observation per financing modality."""
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    values = parser.values

    try:
        category_index = values.index("Grants/TA")
        title = values[category_index + 1]
        period = values[category_index + 2]
    except (ValueError, IndexError) as exc:
        raise ValueError("missing Grants/TA programme heading") from exc

    shared = {
        field: _value_after(values, label) for field, label in FIELD_LABELS.items()
    }
    rows: list[dict[str, str]] = []
    for index, value in enumerate(values):
        if not MODALITY_PATTERN.fullmatch(value):
            continue
        try:
            currency, amount_home = _parse_amount(values[index + 4])
            usd_currency, amount_usd = _parse_amount(values[index + 5])
            if usd_currency != "USD":
                raise ValueError(f"expected USD amount, found {values[index + 5]}")
            rows.append(
                {
                    "title": title,
                    "period": period,
                    **shared,
                    "modality": value,
                    "financing_type": values[index + 1],
                    "financing_source": values[index + 2],
                    "financing_intermediary": values[index + 3],
                    "amount_home_currency": currency,
                    "amount_home": amount_home,
                    "amount_usd": amount_usd,
                    "part_of_jetp_pledge": values[index + 6],
                }
            )
        except IndexError as exc:
            raise ValueError(f"incomplete financing row: {value}") from exc
    if not rows:
        raise ValueError(f"no financing modality found for {title}")
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _latest_material(manifest: list[dict[str, str]], source_id: str) -> dict[str, str]:
    for row in reversed(manifest):
        if row["source_id"] == source_id and row["storage_path"] and row["sha256"]:
            return row
    raise ValueError(f"no material manifest row for {source_id}")


def _matching_event(
    observation: dict[str, str], events: list[dict[str, str]]
) -> dict[str, str]:
    candidates = [
        row for row in events if row["project_id"] == observation["project_id"]
    ]
    if not candidates:
        raise ValueError(f"no report event for {observation['project_id']}")
    if len(candidates) == 1:
        return candidates[0]

    donor = observation["financing_source"].removeprefix("IPG - ")
    donor_matches = [row for row in candidates if row["funder"].startswith(donor)]
    if len(donor_matches) != 1:
        raise ValueError(
            f"cannot resolve modality donor {donor!r} for {observation['project_id']}"
        )
    return donor_matches[0]


def build_observations(
    sources_path: Path,
    manifest_path: Path,
    events_path: Path,
    storage_root: Path,
) -> list[dict[str, str]]:
    """Build source-addressed modality rows and reconcile report amounts."""
    sources = [
        row
        for row in _read_csv(sources_path)
        if row["country"] == "IDN" and row["source_id"].startswith("idn-portfolio-")
    ]
    manifest = _read_csv(manifest_path)
    events = [
        row
        for row in _read_csv(events_path)
        if row["country"] == "IDN"
        and row["source_id"] == "idn-jetp-progress-report-2025"
        and row["project_id"].startswith("idn-grant-")
    ]

    output: list[dict[str, str]] = []
    for source in sources:
        material = _latest_material(manifest, source["source_id"])
        html = (storage_root / material["storage_path"]).read_text(encoding="utf-8")
        for parsed in parse_portfolio_html(html):
            observation = {
                "country": "IDN",
                "project_id": source["project_id"],
                "source_id": source["source_id"],
                "document_sha256": material["sha256"],
                **parsed,
            }
            event = _matching_event(observation, events)
            exact = (
                observation["amount_home_currency"] == event["currency_original"]
                and observation["amount_home"] == event["amount_original"]
            )
            status = "matched" if exact else "amount_mismatch"
            note = (
                "Portal home-currency amount equals the 2025 Progress Report event"
                if exact
                else "Portal and 2025 Progress Report home-currency values differ; "
                "both are preserved"
            )
            output.append(
                {
                    **observation,
                    "matched_event_id": event["event_id"],
                    "report_currency_home": event["currency_original"],
                    "report_amount_home": event["amount_original"],
                    "reconciliation_status": status,
                    "notes": note,
                }
            )
    return output


def main(argv: list[str] | None = None) -> None:
    """Write the canonical Indonesia portfolio-observation ledger."""
    io_args, extra = parse_io_args(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", required=True)
    args = parser.parse_args(extra)
    if not io_args.input or len(io_args.input) != 3:
        parser.error("--input requires sources, manifest and events, in that order")
    validate_io(output=io_args.output, inputs=io_args.input)

    rows = build_observations(
        Path(io_args.input[0]),
        Path(io_args.input[1]),
        Path(io_args.input[2]),
        Path(args.storage_root),
    )
    output = Path(io_args.output)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
