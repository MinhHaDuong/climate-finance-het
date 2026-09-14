"""Frozen case adjudications; changes require source review, not automated inference."""

import argparse
import csv
import hashlib
import json
import pathlib

parser = argparse.ArgumentParser(
    description="Rebuild frozen documentary adjudications and anomaly table offline."
)
parser.add_argument("--output", type=pathlib.Path, required=True)
parser.add_argument("--bundle", type=pathlib.Path, required=True)
parser.add_argument("--xml", type=pathlib.Path, required=True)
parser.add_argument("--config", type=pathlib.Path, required=True)
args = parser.parse_args()
out = args.output
bundle = args.bundle
read = lambda n: list(csv.DictReader((out / n).open()))


def write(name, rows):
    with (out / name).open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


log = read("acquisition-log.csv")
cases = json.loads((out / "cases.json").read_text())
units = read("units.csv")
u = {r["unit_id"]: r for r in units}


def ev(
    i, claim, issuer, url, title, date, section, paraphrase, contrary, path, limitations
):
    p = pathlib.Path(path)
    return dict(
        evidence_id=i,
        claim=claim,
        issuer=issuer,
        url=url,
        title=title,
        source_date=date,
        section=section,
        faithful_paraphrase=paraphrase,
        contrary_evidence=contrary,
        archive_path=path,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        limitations=limitations,
    )


xml = str(args.xml)
evidence = [
    ev(
        "E_XML",
        "Distinct BMZ KfW-linked activities and raw source labels",
        "BMZ",
        "https://teamwork.bmz.de/pub/bscw.cgi/2018133/DE-1-BMZ-RecipientCountry.xml",
        "BMZ IATI export",
        "2026-09-02",
        "iati-activity identified by iati-identifier; transactions indexed within activity",
        "4036 distinct activities with exact participating-org ref XM-DAC-5-2. Current records have equal planned/actual starts; payment reporting stamps are preserved.",
        "Closed records are present; this is not proof of complete retention.",
        xml,
        "One current snapshot; unit is activity, not loan or historical census.",
    )
]
for index, claim, title, date, section, paraphrase, contrary, limit in [
    (
        5,
        "Published inclusion scope",
        "KfW transparency ranking",
        "2020-06-24",
        "IATI scope paragraph",
        "BMZ projects contracted since January 2013 plus those underway at that date are in the described publication scope.",
        "Current transparency page abbreviates scope to contracted since 2013.",
        "Historical statement retrieved now, not independently observed 2020 snapshot; cancellation/removal and implementation fidelity unknown.",
    ),
    (
        6,
        "Current project database scope",
        "Transparency",
        "",
        "Project Database",
        "Database describes contractually agreed projects since 2013.",
        "2020 statement includes ongoing-at-2013 projects.",
        "No complete dated 2018 roster; broader transparency portal and BMZ activity export have different scope.",
    ),
    (
        7,
        "BMZ mandate and monthly publication",
        "BMZ Transparenzportal",
        "2024-04-12",
        "Projektdaten / Transparenz konkret",
        "BMZ publishes monthly project information financed or cofinanced by BMZ.",
        "Public financing totals and project fields are not independently dated stage events.",
        "No transaction aggregation or first-payment completeness definition.",
    ),
    (
        8,
        "Monthly overwrite semantics",
        "BMZ Projektdaten (IATI-Meldung)",
        "",
        "Dataset description",
        "Catalogue says bilateral BMZ data are updated and overwritten at least monthly.",
        "Catalogue metadata date differs from XML generation timestamp.",
        "No independently archived past population or retained/removed-record reconciliation.",
    ),
    (
        13,
        "Mandatory Morocco identity",
        "Windprogramm Marokko (IKLU) Phase III",
        "",
        "project facts / Nummer 32652",
        "Official detail page linked directly from the exact IATI record identifies project 32652 with BMZ mandate and wind sector.",
        "The page reports active status; current status is not historical membership.",
        "No validated signature or first-payment date; no identity join to other wind phases.",
    ),
    (
        14,
        "Mandatory India identity",
        "Himachal Pradesh forest ecosystems",
        "",
        "project facts / Nummer 30347",
        "Official detail page linked directly from exact IATI record identifies 30347 with BMZ mandate and environment sector.",
        "Current active status does not validate a historical pending risk set.",
        "No signature or payment-date definition.",
    ),
    (
        16,
        "Sample rank2 documentary identity",
        "Ex post evaluation – Albania",
        "2016",
        "page 1 project identifiers; subsequent efficiency discussion",
        "Evaluation explicitly lists 2003 66 617 within Project A and discusses two power-supply phases separately from transmission Project B.",
        "Combined phases and project totals must not be assigned to a single IATI activity.",
        "Document supports identity and retrospective evaluation, not a complete contract roster or exact first-payment clock.",
    ),
]:
    r = next(r for r in log if int(r["unit"]) == index)
    evidence.append(
        ev(
            f"E{index:02d}",
            claim,
            "GovData/BMZ" if index == 8 else "BMZ" if index == 7 else "KfW",
            r["url_or_query"],
            title,
            date,
            section,
            paraphrase,
            contrary,
            r["archive_path"],
            limit,
        )
    )
write("evidence.csv", evidence)
rows = []
anomalies = []
for k, v in cases.items():
    role = v["selection"]["role"]
    rank = v["selection"]["rank"]
    attempt = next((r for r in log if k in r["purpose"]), None)
    if k == "DE-1-199170366":
        attempt = next(r for r in log if r["unit"] == "11")
    if k == "DE-1-199370321":
        attempt = next(r for r in log if r["unit"] == "12")
    retrieved = k in ["DE-1-201366764", "DE-1-201365154", "DE-1-200366617"]
    eid = {
        "DE-1-201366764": "E13",
        "DE-1-201365154": "E14",
        "DE-1-200366617": "E16",
    }.get(k, "E_XML")
    rows.append(
        dict(
            unit_id=k,
            role=role,
            rank=rank,
            local_xml="present",
            local_independent_document_before_pilot="absent",
            xml_document_links="present_leads_only",
            external_attempt="attempted" if attempt else "not_attempted",
            acquisition_unit=attempt["unit"] if attempt else "",
            retrieved_exact_identity_document="yes" if retrieved else "no",
            stage_clock_validated="no",
            evidence_ids=eid,
            disposition="Identity verified; stage clocks unresolved"
            if retrieved
            else (
                "No exact-ID original returned"
                if attempt
                else "Stopped after historical denominator and period-definition gaps; reserved verification tranche retained"
            ),
        )
    )
    dates = v["dates"]
    transactions = v["transactions"]
    payments = [t for t in transactions if t["type"] == "3"]
    start = next(d["iso-date"] for d in dates if d["type"] == "2")
    first = min((t["date"] for t in payments), default="")
    anomalies.append(
        dict(
            unit_id=k,
            kind="challenge" if role == "challenge" else "document_coverage",
            source_value=f"start_proxy={start}; earliest_reported_payment_stamp={first}",
            disposition="unresolved",
            reason="Earlier payment coverage and start/contract semantics unknown; never infer first-payment bounds",
            evidence_ids=eid,
        )
    )
for kind, source, reason in [
    (
        "source_status_conflict",
        "DE-1-201366764 XML end 2021-12-01 versus page aktiv",
        "Preserve both snapshots and distinct publisher status meanings; no lifecycle harmonization",
    ),
    (
        "pooled_evaluation",
        "DE-1-200366617 alongside 199865841 and training in Project A",
        "Evaluation identity confirmed but pooled financial totals and timings cannot be attributed to this activity",
    ),
    (
        "duplicate_exports",
        "Country/Region same SHA256",
        "One archived object; do not double count 4036 activities",
    ),
    (
        "equal_starts",
        "4036 planned/actual identical",
        "Original planned start not independently observed; zero delay unsupported",
    ),
    (
        "historical_roster",
        "MA/IN calendar 2018",
        "No complete dated official financing-contract roster acquired; denominator unknown",
    ),
    (
        "periodicity",
        "annual/quarter-end/2026-08-26",
        "Distribution consistent with reporting aggregation but period boundaries and completeness unvalidated",
    ),
    (
        "missing_payment",
        "387 records without type-3 entry",
        "Missing entries do not establish zero payment",
    ),
    (
        "lost_visibility",
        "one snapshot",
        "Disappearance not observed; count unavailable, not zero",
    ),
    (
        "protocol_deviation",
        "XML preview before directory hash check",
        "First 35 lines previewed; full bundles matched before profile and sample freeze",
    ),
    (
        "query_amendment",
        "initial site.domain operator omitted colon",
        "Units 9–12 used explicit site: syntax; initial four units retained and charged",
    ),
]:
    anomalies.append(
        dict(
            unit_id="",
            kind=kind,
            source_value=source,
            disposition="resolved_mapping"
            if kind in ["duplicate_exports", "equal_starts", "missing_payment"]
            else "unresolved",
            reason=reason,
            evidence_ids="E_XML",
        )
    )
for e in read("events.csv"):
    if e["stage"] == "negative_correction":
        anomalies.append(
            dict(
                unit_id=e["unit_id"],
                kind="negative_correction",
                source_value=f"{e['raw_field']}: {e['raw_value']} {e['amount_raw']}",
                disposition="unresolved",
                reason="Correction meaning undocumented; no cancellation inferred",
                evidence_ids="E_XML",
            )
        )
write("document-coverage.csv", rows)
write("anomalies.csv", anomalies)
manifest = json.loads((out / "input-manifest.json").read_text())
manifest["freeze_sha"] = "5a307735"
manifest["local_inputs"] = [
    r for r in manifest["local_inputs"] if r["path"] != str(args.config)
]
manifest["local_inputs"].append(
    {
        "path": str(args.config),
        "sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
    }
)
manifest["archive_xml_sha256"] = hashlib.sha256(
    pathlib.Path(xml).read_bytes()
).hexdigest()
(out / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
manifest = [
    dict(
        path=str(p),
        bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    )
    for p in sorted(bundle.iterdir())
    if p.is_file() and p.name != "sha256-manifest.json"
]
(out / "source-byte-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(bundle / "sha256-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
