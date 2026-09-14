"""Offline, conservative BMZ/KfW feasibility tables for ticket 0738.

Inputs are immutable audit XML; outputs are research diagnostics, never a
historical contract census. No network access or canonical ledger mutation.
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

from pipeline_loaders import load_analysis_config
from script_io_args import parse_io_args, validate_io

CONFIG = load_analysis_config()["jetp_kfw_pilot"]
COUNTRIES = set(CONFIG["countries"])
LANDMARKS = CONFIG["landmarks"]


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def parse_exports(payloads):
    """Deduplicate endpoints and IDs; reject disagreeing duplicate activities."""
    records, seen = {}, set()
    for payload in payloads:
        digest = hashlib.sha256(payload).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        for _, node in ET.iterparse(io.BytesIO(payload), events=["end"]):
            if node.tag != "iati-activity":
                continue
            if any(
                o.get("ref") == CONFIG["participant_ref"]
                for o in node.findall("participating-org")
            ):
                key = node.findtext("iati-identifier").strip()
                raw = ET.tostring(node)
                if key in records and ET.tostring(records[key]) != raw:
                    raise ValueError(f"Conflicting duplicate activity: {key}")
                records[key] = ET.fromstring(raw)
            node.clear()
    return records


def payment_event(key, day, value, locator):
    negative = Decimal(value) < 0
    return {
        "unit_id": key,
        "stage": "negative_correction" if negative else "observed_disbursement",
        "raw_field": locator,
        "raw_value": day,
        "amount_raw": value,
        "normalized_date": "",
        "interval_start": "",
        "interval_end": "",
        "first_payment_date": "",
        "precision": "reporting_stamp",
        "source_coverage": "current_snapshot_earlier_payment_coverage_unknown",
        "validation_status": "correction_meaning_unknown"
        if negative
        else "period_semantics_unverified",
        "evidence_id": "E_XML",
        "missingness_reason": "Earlier coverage and publisher period definitions absent",
    }


def select_sample(units, challenges, size=None):
    size = CONFIG["sample_size"] if size is None else size
    strata = {}
    for row in units:
        if row["country"] in COUNTRIES and row["unit_id"] not in challenges:
            key = (row["country"], row["sector"], row["instrument"])
            strata.setdefault(key, []).append(row["unit_id"])
    for values in strata.values():
        values.sort()
    ordered = []
    for depth in range(max(map(len, strata.values()), default=0)):
        for stratum in sorted(strata):
            if depth < len(strata[stratum]):
                ordered.append((strata[stratum][depth], stratum))
    return [
        dict(
            unit_id=key,
            country=s[0],
            source_unit="IATI activity",
            role="sample",
            stratum="|".join(s),
            rank=i,
            selected="true" if i <= size else "false",
            selection_reason="round_robin_strata_then_lexicographic_ID",
            baseline_alternatives=json.dumps(LANDMARKS, sort_keys=True),
        )
        for i, (key, s) in enumerate(ordered, 1)
    ]


def write_csv(path, rows, fields=None):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def unit_row(key, node, snapshot):
    countries = node.findall("recipient-country")
    regions = node.findall("recipient-region")
    country = (
        countries[0].get("code")
        if len(countries) == 1 and not regions
        else "REGIONAL_OR_MULTI"
    )
    sectors = node.findall("sector")
    dac = [
        int(s.get("code"))
        for s in sectors
        if s.get("vocabulary", "1") == "1" and s.get("code", "").isdigit()
    ]
    energy = [23000 <= code <= 23999 for code in dac]
    sector = (
        ("energy" if all(energy) else "non-energy")
        if energy and len(dac) == len(sectors) and len(set(energy)) == 1
        else "mixed-or-unmapped"
    )
    instrument = node.find("default-finance-type")
    raw_instrument = instrument.get("code") if instrument is not None else "missing"
    starts = {
        d.get("type"): d.get("iso-date", "") for d in node.findall("activity-date")
    }
    return dict(
        unit_id=key,
        parent_ids="|".join(r.get("ref", "") for r in node.findall("related-activity")),
        country=country,
        country_allocation=json.dumps(
            [dict(c.attrib) for c in countries + regions], sort_keys=True
        ),
        sector_raw="|".join(
            f"{s.get('vocabulary', '1')}:{s.get('code')}" for s in sectors
        ),
        sector=sector,
        instrument_raw=raw_instrument,
        instrument=raw_instrument,
        instrument_mapped="unharmonized",
        snapshot=snapshot,
        observation_status="observed_current",
        identity_confidence="exact_publisher_ID",
        source_status=node.find("activity-status").get("code"),
        start_proxy=starts.get("2", ""),
        validated_entry_cohort="",
        proxy_entry_cohort=starts.get("2", "")[:4],
        document_links="|".join(
            d.get("url", "") for d in node.findall("document-link")
        ),
    )


def events_for(key, node):
    events = []
    meanings = {
        "1": "planned_start",
        "2": "actual_start",
        "3": "planned_end",
        "4": "actual_end",
    }
    for d in node.findall("activity-date"):
        events.append(
            dict(
                unit_id=key,
                stage=meanings.get(d.get("type"), "unknown_date"),
                raw_field=f"activity-date[@type='{d.get('type')}']",
                raw_value=d.get("iso-date", ""),
                amount_raw="",
                normalized_date="",
                interval_start="",
                interval_end="",
                first_payment_date="",
                precision="source_day_label",
                source_coverage="current_snapshot",
                validation_status="administrative_semantics_unverified",
                evidence_id="E_XML",
                missingness_reason="Not a validated approval/signature/completion clock",
            )
        )
    for stage in ["approval", "signature", "first_payment"]:
        events.append(
            dict(
                unit_id=key,
                stage=stage,
                raw_field="",
                raw_value="",
                amount_raw="",
                normalized_date="",
                interval_start="",
                interval_end="",
                first_payment_date="",
                precision="unknown",
                source_coverage="unknown",
                validation_status="missing",
                evidence_id="E_XML",
                missingness_reason="No validated field or complete earlier coverage",
            )
        )
    for index, tx in enumerate(node.findall("transaction"), 1):
        code = tx.find("transaction-type").get("code")
        day = tx.find("transaction-date").get("iso-date", "")
        value = tx.findtext("value", "").strip()
        event = payment_event(key, day, value, f"transaction[{index}]/transaction-date")
        if code != "3":
            event.update(
                stage="outgoing_commitment"
                if code == "2"
                else f"transaction_type_{code}",
                precision="source_day_label",
                validation_status="not_validated_signature_or_approval",
                missingness_reason="Transaction code does not validate lender signature or approval date",
            )
        events.append(event)
    return events


def coverage_rows(units):
    rows = []
    groups = {}
    for unit in units:
        key = (
            unit["country"],
            unit["sector"],
            unit["instrument"],
            unit["proxy_entry_cohort"] or "missing",
        )
        groups.setdefault(key, []).append(unit)
    for (country, sector, instrument, cohort), members in sorted(groups.items()):
        if country not in COUNTRIES and country != "REGIONAL_OR_MULTI":
            continue
        for target, landmarks in LANDMARKS.items():
            for landmark in landmarks:
                eligible = [
                    u
                    for u in members
                    if u["start_proxy"] and u["start_proxy"] <= landmark
                ]
                for kind in ["retrospective", "member", "pending"]:
                    rows.append(
                        dict(
                            lender="KfW_BMZ",
                            country=country,
                            sector=sector,
                            instrument=instrument,
                            entry_cohort=f"proxy:{cohort}",
                            baseline=f"{target}:{landmark}",
                            stage="source_reported_actual_start",
                            unit="IATI activity",
                            count_kind=kind,
                            count=len(eligible) if kind == "retrospective" else "",
                            missing_count=sum(not u["start_proxy"] for u in members)
                            if kind == "retrospective"
                            else "",
                            lost_visibility_count="",
                            calendar_coverage="2026-09-02 snapshot; earlier visibility unknown",
                            denominator_rule="Current observed activities; proxy not contract cohort",
                            evidence_ids="E_XML",
                            unsupported_reason=""
                            if kind == "retrospective"
                            else "Historical inclusion and pending stage unknown",
                        )
                    )
    for country in sorted(COUNTRIES):
        for target, landmarks in LANDMARKS.items():
            for landmark in landmarks:
                for stage in ["approval", "signature", "first_payment"]:
                    for kind in ["retrospective", "member", "pending"]:
                        rows.append(
                            dict(
                                lender="KfW_BMZ",
                                country=country,
                                sector="ALL",
                                instrument="ALL",
                                entry_cohort="validated:unknown",
                                baseline=f"{target}:{landmark}",
                                stage=stage,
                                unit="IATI activity",
                                count_kind=kind,
                                count="",
                                missing_count="",
                                lost_visibility_count="",
                                calendar_coverage="unknown",
                                denominator_rule="Historical stage population unknown",
                                evidence_ids="E_XML",
                                unsupported_reason="No validated stage clock or historical denominator",
                            )
                        )
    return rows


def run(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    records = parse_exports([args.xml.read_bytes()])
    snapshot = ET.parse(args.xml).getroot().get("generated-datetime")
    units = [unit_row(k, node, snapshot) for k, node in sorted(records.items())]
    challenges = set(CONFIG["mandatory_ids"])
    for country in CONFIG["old_start_challenge_countries"]:
        challenges.add(
            min(
                u["unit_id"]
                for u in units
                if u["country"] == country
                and u["start_proxy"]
                and u["start_proxy"] < CONFIG["old_start_cutoff"]
            )
        )
    selection = select_sample(units, challenges)
    for key in sorted(challenges):
        u = next(u for u in units if u["unit_id"] == key)
        selection.append(
            dict(
                unit_id=key,
                country=u["country"],
                source_unit="IATI activity",
                role="challenge",
                stratum=f"{u['country']}|{u['sector']}|{u['instrument']}",
                rank="",
                selected="true",
                selection_reason="mandatory_ID_or_smallest_pre2013_start_proxy",
                baseline_alternatives=json.dumps(LANDMARKS, sort_keys=True),
            )
        )
    events = [e for key, node in sorted(records.items()) for e in events_for(key, node)]
    payments = [
        e
        for e in events
        if e["stage"] in {"observed_disbursement", "negative_correction"}
    ]
    summary = dict(
        distinct_activities=len(records),
        xml_sha256=sha256(args.xml),
        snapshot=snapshot,
        status=dict(Counter(u["source_status"] for u in units)),
        countries=dict(sorted(Counter(u["country"] for u in units).items())),
        instruments=dict(Counter(u["instrument"] for u in units)),
        identical_starts=sum(
            n.find("activity-date[@type='1']").get("iso-date")
            == n.find("activity-date[@type='2']").get("iso-date")
            for n in records.values()
        ),
        disbursement_entries=len(payments),
        negative_entries=sum(e["stage"] == "negative_correction" for e in payments),
        payment_stamps=dict(sorted(Counter(e["raw_value"] for e in payments).items())),
        challenge_ids=sorted(challenges),
        sample_candidates=len(selection) - len(challenges),
        xml_document_link_presence=sum(
            bool(
                next(u for u in units if u["unit_id"] == s["unit_id"])["document_links"]
            )
            for s in selection
            if s["role"] == "sample" and s["selected"] == "true"
        ),
    )
    for name, rows in [
        ("units", units),
        ("events", events),
        ("coverage", coverage_rows(units)),
        ("selection", selection),
    ]:
        write_csv(output / f"{name}.csv", rows)
    (output / "profile.json").write_text(json.dumps(summary, indent=2) + "\n")
    cases = {}
    for s in selection:
        if s["selected"] == "true":
            node = records[s["unit_id"]]
            cases[s["unit_id"]] = dict(
                selection=s,
                title=[n.text for n in node.findall("title/narrative")],
                dates=[dict(d.attrib) for d in node.findall("activity-date")],
                documents=[dict(d.attrib) for d in node.findall("document-link")],
                transactions=[
                    dict(
                        type=t.find("transaction-type").get("code"),
                        date=t.find("transaction-date").get("iso-date"),
                        value_date=t.find("value").get("value-date"),
                        amount=t.findtext("value"),
                    )
                    for t in node.findall("transaction")
                ],
            )
    (output / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


def main():
    io_args, extra = parse_io_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, required=True)
    args = parser.parse_args(extra)
    if io_args.input:
        parser.error("Use --xml to identify the immutable BMZ export")
    validate_io(output=io_args.output, inputs=[str(args.xml)])
    args.output = Path(io_args.output)
    run(args)


if __name__ == "__main__":
    main()
