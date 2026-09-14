"""Offline, bounded FCDO documentary feasibility. No network or canonical writes."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

COUNTRIES = ("AL", "MA", "IN", "SN", "ZA", "ID", "VN")
LANDMARKS = {
    "ZA": ("2020-12-31", "2021-09-28", "2021-11-01"),
    "ID": ("2021-12-31", "2022-03-15", "2022-11-14"),
    "VN": ("2021-12-31", "2022-03-15", "2022-12-13"),
    "SN": ("2021-12-31", "2022-03-15", "2023-06-21"),
}
SNAPSHOT = "2026-09-14"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structured(record, field):
    values = record.get("json." + field, [])
    if isinstance(values, str):
        values = [values]
    return [json.loads(v) if isinstance(v, str) else v for v in values]


def clocks(record, parent=None):
    # Parent is accepted to make the forbidden inheritance explicit in tests.
    dates = structured(record, "activity-date")
    transactions = structured(record, "transaction")
    result = {"actual_start": "", "earliest_observed_expenditure": "",
              "earliest_observed_transfer": "", "first_spending": "",
              "approved_unsigned": "unknown"}
    starts = sorted({d["iso-date"] for d in dates if str(d.get("type")) == "2"})
    if len(starts) == 1:
        result["actual_start"] = starts[0]
    for code, key in [("4", "earliest_observed_expenditure"),
                      ("3", "earliest_observed_transfer")]:
        observed = [t["transaction-date"]["iso-date"] for t in transactions
                    if str(t.get("transaction-type", {}).get("code")) == code
                    and float(t.get("value", 0)) > 0]
        result[key] = min(observed, default="")
    return result


def country(record):
    values = sorted(set(record.get("recipient_country_code", [])))
    if len(values) == 1:
        return values[0]
    return "multi-country" if values else "regional-or-unspecified"


def sector(record):
    # The frozen catalogue omitted vocabulary; DAC-looking codes are insufficient.
    entries = structured(record, "sector")
    if not entries or any(str(v.get("vocabulary")) != "1" for v in entries):
        return "mixed-or-unmapped"
    energy = [23000 <= int(v["code"]) <= 23999 for v in entries]
    return "energy" if all(energy) else "non-energy" if not any(energy) else "mixed-or-unmapped"


def write_csv(path, rows, fields=None):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def selection(records):
    challenge = {d["iati_identifier"] for d in records
                 if d["hierarchy"] == 1 and d.get("activity_status_code") == "1"}
    challenge.update(["GB-1-112151", "GB-1-112151-101"])
    strata = defaultdict(list)
    for d in records:
        if d["hierarchy"] == 1 and country(d) in COUNTRIES and d["iati_identifier"] not in challenge:
            key = (country(d), sector(d), str(d.get("default_finance_type_code", "missing")))
            strata[key].append(d)
    ordered = []
    for members in strata.values():
        members.sort(key=lambda d: d["iati_identifier"])
    for turn in range(max(map(len, strata.values()), default=0)):
        for key in sorted(strata):
            if turn < len(strata[key]):
                ordered.append((key, strata[key][turn]))
    rows = []
    for rank, (key, d) in enumerate(ordered, 1):
        rows.append(dict(case_id=d["iati_identifier"], country=key[0], source_unit="programme",
                         role="sample", stratum="|".join(key), rank=rank,
                         selected=str(rank <= 12).lower(),
                         selection_reason="frozen lexicographic stratum round robin; no status/date filter",
                         baseline_alternatives=json.dumps(LANDMARKS, sort_keys=True)))
    indexed = {d["iati_identifier"]: d for d in records}
    for ident in sorted(challenge):
        d = indexed[ident]
        rows.append(dict(case_id=ident, country=country(d),
                         source_unit="programme" if d["hierarchy"] == 1 else "component",
                         role="challenge", stratum="mandatory", rank="", selected="true",
                         selection_reason="mandatory known failure-mode challenge; excluded from sample N",
                         baseline_alternatives=json.dumps(LANDMARKS, sort_keys=True)))
    return rows


def load_records(path):
    return json.loads(path.read_text())["response"]["docs"]


def run(archive, output, new_archive=None):
    output.mkdir(parents=True, exist_ok=True)
    raw = archive / "us-uk"
    records = load_records(raw / "fcdo-catalogue.json")
    assert len(records) == len({d["iati_identifier"] for d in records}) == 25282
    assert Counter(d["hierarchy"] for d in records) == {1: 7327, 2: 17955}
    selected = selection(records)
    write_csv(output / "selection.csv", selected)
    detailed = {}
    sources = {}
    for name in ("fcdo-112151.json", "fcdo-112151-101.json", "fcdo-400397.json"):
        for d in load_records(raw / name):
            detailed[d["iati_identifier"]] = d
            sources[d["iati_identifier"]] = raw / name
    if new_archive:
        for path in sorted(new_archive.glob("activity-*.json")):
            for d in load_records(path):
                detailed[d["iati_identifier"]] = d
                sources[d["iati_identifier"]] = path
    units, events, evidence = [], [], []
    catalogue = raw / "fcdo-catalogue.json"
    evidence.append(dict(evidence_id="catalogue", claim="complete acquired response; not historical census",
                         issuer="FCDO", url="https://fcdo.iati.cloud/search/activity/",
                         title_date="GB-GOV-1 catalogue; acquired 2026-09-14", page_section="response.docs",
                         paraphrase="25282 distinct activity IDs, with separate hierarchy 1 and 2 units",
                         contrary_evidence="no independent inclusion, cancellation or retention history",
                         archive_path="data/jetp/audit-evidence/0735-round3/us-uk/fcdo-catalogue.json",
                         sha256=sha(catalogue), limitations="limited fl projection; sector vocabulary and finance code omitted"))
    for ident, path in sorted(sources.items()):
        bundle = "0735-round3/us-uk/" + path.name if path.parent == raw else "0739-pilot/" + path.name
        evidence.append(dict(evidence_id=ident, claim="structured activity dates, relations and documentary pointers",
                             issuer="FCDO", url="https://fcdo.iati.cloud/search/activity/?fl=*&format=json&q=iati_identifier:" + ident,
                             title_date=ident + "; acquired 2026-09-14", page_section="response.docs[0].json.*",
                             paraphrase="Activity dates retain their type; document links are pointers, not validated documents",
                             contrary_evidence="current status and old events do not establish historical membership",
                             archive_path="data/jetp/audit-evidence/" + bundle, sha256=sha(path),
                             limitations="source-reported dates; no legal financing identity or complete earlier payment coverage"))
    selected_ids = {r["case_id"] for r in selected if r["selected"] == "true"}
    for d in sorted(records, key=lambda d: d["iati_identifier"]):
        ident = d["iati_identifier"]
        detail = detailed.get(ident, {})
        parents = [r["ref"] for r in structured(detail, "related-activity") if str(r.get("type")) == "1"]
        units.append(dict(unit_id=ident, parent_ids="|".join(parents),
                          source_unit="programme" if d["hierarchy"] == 1 else "component",
                          country=country(d), country_raw="|".join(d.get("recipient_country_code", [])),
                          related_ids_raw="|".join(d.get("related_activity_ref", [])),
                          sector_raw="|".join(d.get("sector_code", [])), sector_mapped=sector(detail),
                          instrument_raw=str(detail.get("default_finance_type_code", "")),
                          instrument_mapped="unknown", snapshot=SNAPSHOT,
                          observation_status="observed_current_snapshot", raw_status=d.get("activity_status_code", ""),
                          identity_confidence="exact source ID; parent only from structured relation",
                          evidence_id=ident if detail else "catalogue"))
        dates = structured(detail, "activity-date")
        for number, date in enumerate(dates):
            stage = {"1": "planned_start", "2": "actual_start", "3": "planned_end", "4": "actual_end"}.get(str(date.get("type")), "unknown")
            events.append(event(ident, stage, "json.activity-date[" + str(number) + "]", date,
                                date.get("iso-date", ""), "day", ident, "source_reported_activity_date", ""))
        if not dates:
            events.append(event(ident, "actual_start", "activity_date_type;activity_date_iso_date", "", "", "",
                                "catalogue", "unvalidated", "structured dates unavailable; parallel arrays not paired"))
        for number, transaction in enumerate(structured(detail, "transaction")):
            events.append(event(ident, "transaction_type_" + str(transaction["transaction-type"]["code"]),
                                "json.transaction[" + str(number) + "]", transaction,
                                transaction.get("transaction-date", {}).get("iso-date", ""),
                                "reported date; aggregated period where described", ident,
                                "observed_accounting_entry_not_first_payment", ""))
        if ident in selected_ids:
            for stage in ("approval", "signature", "procurement", "first_spending"):
                events.append(event(ident, stage, "", "", "", "", ident if detail else "catalogue",
                                    "unvalidated", "no independently validated stage document / earlier coverage"))
    write_csv(output / "units.csv", units)
    write_csv(output / "events.csv", events)
    write_csv(output / "evidence.csv", evidence)
    coverage = []
    groups = defaultdict(list)
    for unit in units:
        groups[(unit["country"], unit["sector_mapped"], unit["instrument_raw"], unit["source_unit"])].append(unit)
    for (ctry, sec, instrument, source_unit), members in sorted(groups.items()):
        coverage.append(dict(lender="FCDO", country=ctry, sector=sec, instrument=instrument or "missing",
                             entry_cohort="unknown_or_unvalidated", baseline="current_snapshot", stage="catalogue_presence",
                             unit=source_unit, count_kind="observed", count=len(members), missing_count="",
                             lost_visibility_count="", calendar_coverage=SNAPSHOT,
                             denominator_rule="complete acquired export at hierarchy; no replication of multi-country records",
                             evidence_ids="catalogue", reason="retention and historical loss unknown"))
        if ctry not in COUNTRIES:
            continue
        for target, cutoffs in LANDMARKS.items():
            for label, cutoff in zip(("early_calendar", "before_discussions", "before_declaration"), cutoffs, strict=True):
                for stage in ("actual_start", "approval", "signature", "procurement", "first_spending"):
                    observed = [clocks(detailed.get(u["unit_id"], {}))["actual_start"] for u in members] if stage == "actual_start" else [""] * len(members)
                    for kind in ("retrospective", "member", "pending"):
                        supported = kind == "retrospective" and stage == "actual_start"
                        coverage.append(dict(lender="FCDO", country=ctry, sector=sec, instrument=instrument or "missing",
                                             entry_cohort="source_reported_only", baseline=target + ":" + label + ":" + cutoff,
                                             stage=stage, unit=source_unit, count_kind=kind,
                                             count=sum(bool(d) and d <= cutoff for d in observed) if supported else "",
                                             missing_count=sum(not d for d in observed), lost_visibility_count="",
                                             calendar_coverage="single 2026-09-14 snapshot; earlier reported dates only",
                                             denominator_rule="all acquired group records; comparators aligned to each target calendar",
                                             evidence_ids="catalogue", reason="no historical census/pending evidence; current start is not approval"))
    write_csv(output / "coverage.csv", coverage)
    cohorts = Counter((u["country"], u["source_unit"], clocks(detailed.get(u["unit_id"], {}))["actual_start"][:4] or "unvalidated_or_missing") for u in units)
    write_csv(output / "entry-cohorts.csv", [dict(country=k[0], unit=k[1], stage="actual_start",
                cohort=k[2], count=v, validation="source reported, not document validated") for k, v in sorted(cohorts.items())])
    docs = []
    for row in selected:
        if row["selected"] != "true":
            continue
        detail = detailed.get(row["case_id"], {})
        links = structured(detail, "document-link")
        for stage in ("approval", "procurement", "start"):
            docs.append(dict(case_id=row["case_id"], role=row["role"], source_unit=row["source_unit"], stage=stage,
                             structured_record_available=str(bool(detail)).lower(), linked_documents=len(links) if detail else "",
                             local_stage_document="not_established", attempted="false", retrieved="false", validates_stage="false",
                             observation="pointers_only" if links else "no_links_in_payload" if detail else "not_attempted",
                             missingness_reason="consult document-assessment.csv for fetched originals; no automatic title-to-stage inference"))
    write_csv(output / "document-coverage.csv", docs)
    profile = dict(records=len(records), hierarchy=dict(Counter(d["hierarchy"] for d in records)),
                   status_by_hierarchy={str(h): dict(Counter(d.get("activity_status_code") for d in records if d["hierarchy"] == h)) for h in (1, 2)},
                   sample_candidates=sum(r["role"] == "sample" for r in selected), sample_selected=sum(r["role"] == "sample" and r["selected"] == "true" for r in selected),
                   challenge_programmes=sum(r["role"] == "challenge" and r["source_unit"] == "programme" for r in selected),
                   challenge_components=1, detailed_records=len(detailed), frozen_sector="mixed-or-unmapped: catalogue omitted vocabulary",
                   frozen_instrument="missing: catalogue projection omitted finance type")
    (output / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")


def event(ident, stage, field, raw, date, precision, evidence, validation, missing):
    return dict(unit_id=ident, stage=stage, raw_field=field, raw_value=json.dumps(raw, sort_keys=True) if raw != "" else "",
                normalized_date=date, interval_start="", interval_end="", precision=precision,
                source_coverage="current snapshot; no independent prior coverage", source_version=SNAPSHOT,
                validation_status=validation, evidence_id=evidence, missingness_reason=missing)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="0735-round3 archive directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--new-archive", type=Path)
    args = parser.parse_args()
    run(args.input, args.output, args.new_archive)
