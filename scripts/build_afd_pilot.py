"""Offline AFD pilot: retain source observations without inventing outcomes.

Usage: python scripts/build_afd_pilot.py --input data/jetp/audit-evidence --output DIR
"""

import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from script_io_args import parse_io_args, validate_io

COUNTRIES = {
    "ALBANIE": "AL",
    "MAROC": "MA",
    "INDE": "IN",
    "SENEGAL": "SN",
    "AFRIQUE DU SUD": "ZA",
    "INDONESIE": "ID",
    "VIET-NAM": "VN",
}
BASELINES = {
    "ZA": ["2020-12-31", "2021-09-28", "2021-11-01"],
    "ID": ["2021-12-31", "2022-03-15", "2022-11-14"],
    "VN": ["2021-12-31", "2022-03-15", "2022-12-13"],
    "SN": ["2021-12-31", "2022-03-15", "2023-06-21"],
}
FIELDS = {
    "approval": "date_d_octroi",
    "signature": "date_de_signature_de_convention",
    "first_payment": "date_de_1er_versement_concours",
}


def reconcile(legacy, current):
    """Require exact financing identity; disappearance carries no outcome."""
    present = current and current.get("code_concours_simple") == legacy["id_concours"]
    stage = next(
        (
            s
            for s in ["first_payment", "signature", "approval"]
            if legacy.get(FIELDS[s])
        ),
        "unknown",
    )
    return {
        "observation_status": "retained" if present else "lost_visibility",
        "outcome": "unknown",
        "last_observed_stage": stage,
        "last_observed_snapshot": "legacy-retrieved-2026-09-14",
        "award": legacy.get("date_d_octroi"),
    }


def payment_observation(legacy_date, xml_dates):
    """No complete earlier coverage has been established for XML periods."""
    return {
        "date": legacy_date,
        "precision": "day" if legacy_date else "unknown",
        "interval": None,
        "observed_periods": xml_dates,
    }


def write_csv(path, rows):
    """Write explicit empty cells, never numerical missing-value sentinels."""
    if not rows:
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_inputs(root):
    """Validate immutable bundles before inspecting records."""
    expected = {
        "0735-round2": "6cd6406b227e6860cae66906cce21d9c.dir",
        "0735-round3": "4b1a54b98d1ff7df92afe3e7b95ec07e.dir",
    }
    hashes = {}
    for name, digest in expected.items():
        entries = []
        for path in sorted((root / name).rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                entries.append(
                    {
                        "md5": hashlib.md5(data).hexdigest(),
                        "relpath": path.relative_to(root / name).as_posix(),
                    }
                )
                hashes[str(path.relative_to(root))] = hashlib.sha256(data).hexdigest()
        actual = (
            hashlib.md5(json.dumps(entries, sort_keys=True).encode()).hexdigest()
            + ".dir"
        )
        if actual != digest:
            raise ValueError(f"Bundle mismatch {name}: {actual}")
    legacy = json.loads(
        (
            root
            / "0735-round2/f7d4454ff2f20926fe8407a5aaf101d2fe37537dfb17ffe55692bcc400851e87.json"
        ).read_text()
    )
    afd = root / "0735-round3/afd"
    portal = json.loads((afd / "les-concours-de-l-afd.json").read_text())
    xml = {}
    parents = set()
    for country in sorted(COUNTRIES.values()):
        path = afd / f"fr-afd-{country.lower()}.xml"
        tree = ET.parse(path)
        for activity in tree.getroot().findall("iati-activity"):
            identifier = activity.findtext("iati-identifier").removeprefix("FR-3-")
            if activity.get("hierarchy") == "1":
                parents.add(identifier)
                continue
            xml[identifier] = (activity, path.relative_to(root).as_posix(), country)
    return legacy, portal, xml, parents, hashes


def sector_stratum(activity):
    if activity is None:
        return "mixed-or-unmapped"
    codes = [
        s.get("code", "")
        for s in activity.findall("sector")
        if s.get("vocabulary", "1") == "1"
    ]
    if not codes or any(not s.isdigit() for s in codes):
        return "mixed-or-unmapped"
    energy = [23000 <= int(s) <= 23999 for s in codes]
    return (
        "energy"
        if all(energy)
        else ("non-energy" if not any(energy) else "mixed-or-unmapped")
    )


def find_anomalies(old, current, xml):
    anomalies = []
    for identifier, row in sorted(old.items()):
        kinds = []
        now = current.get(identifier)
        if now is None:
            kinds.append(
                (
                    "missing_portal",
                    "lost_visibility; outcome unknown; inclusion/retention history required",
                )
            )
        elif row.get(FIELDS["signature"]) != now.get(
            "min_transaction_transaction_date_iso_date"
        ):
            kinds.append(
                (
                    "signature_nonmatch",
                    "preserve both; dated exact financing contract required",
                )
            )
        award, signature = row.get(FIELDS["approval"]), row.get(FIELDS["signature"])
        if award and signature and award > signature:
            kinds.append(
                (
                    "award_signature_reversal",
                    "preserve order; approval meaning and legal instrument unresolved",
                )
            )
        if identifier in xml and not award:
            kinds.append(
                (
                    "missing_award_matched_xml",
                    "no value-date imputation; dated approval decision required",
                )
            )
        for kind, disposition in kinds:
            activity = xml.get(identifier, (None,))[0]
            values = (
                []
                if activity is None
                else [
                    t.find("value").get("value-date")
                    for t in activity.findall("transaction")
                    if t.find("transaction-type").get("code") == "2"
                ]
            )
            anomalies.append(
                {
                    "unit_id": identifier,
                    "kind": kind,
                    "legacy_award": award,
                    "legacy_signature": signature,
                    "portal_signature": None
                    if now is None
                    else now.get("min_transaction_transaction_date_iso_date"),
                    "xml_commitment_value_dates": "|".join(values),
                    "legacy_status": row.get("etat_du_projet"),
                    "parent_id": row["id_projet"],
                    "join": "exact financing ID only",
                    "disposition": disposition,
                    "evidence_id": "legacy|portal|" + xml[identifier][1]
                    if activity is not None
                    else "legacy|portal",
                }
            )
    return anomalies


def select_cases(old, xml, anomalies):
    challenge = {r["unit_id"] for r in anomalies}
    strata = defaultdict(list)
    for identifier, row in sorted(old.items()):
        country = COUNTRIES.get(row["pays_de_realisation"])
        if country and identifier not in challenge:
            activity = xml.get(identifier, (None,))[0]
            instrument = (
                ""
                if activity is None
                else activity.find("default-finance-type").get("code", "")
            )
            strata[(country, sector_stratum(activity), instrument or "missing")].append(
                identifier
            )
    order = []
    for cycle in range(max(map(len, strata.values()))):
        for stratum, ids in sorted(strata.items()):
            if cycle < len(ids):
                order.append((ids[cycle], stratum))
    selection = []
    for rank, (identifier, stratum) in enumerate(order, 1):
        selection.append(
            {
                "case_id": identifier,
                "country": stratum[0],
                "source_unit": "financing",
                "role": "sample",
                "stratum": "|".join(stratum),
                "rank": rank,
                "selected": rank <= 12,
                "selection_reason": "round-robin lexical strata; no event filtering",
                "baseline_alternatives": json.dumps(BASELINES, sort_keys=True),
            }
        )
    for identifier in sorted(challenge):
        row = old[identifier]
        selection.append(
            {
                "case_id": identifier,
                "country": COUNTRIES.get(
                    row["pays_de_realisation"], row["pays_de_realisation"]
                ),
                "source_unit": "financing",
                "role": "challenge",
                "stratum": "",
                "rank": "",
                "selected": True,
                "selection_reason": "|".join(
                    r["kind"] for r in anomalies if r["unit_id"] == identifier
                ),
                "baseline_alternatives": json.dumps(BASELINES, sort_keys=True),
            }
        )
    return selection


def build_observations(old, current, xml):
    units, events = [], []
    for identifier in sorted(set(old) | set(current) | set(xml)):
        row, now = old.get(identifier), current.get(identifier)
        activity, path, country = xml.get(identifier, (None, "", ""))
        label = (
            row["pays_de_realisation"]
            if row
            else now.get("recipient_country_narrative", "")
        )
        country = country or COUNTRIES.get(
            label,
            "regional" if label == "MULTI-PAYS" else "outside-diagnostic-or-unmapped",
        )
        instrument = (
            ""
            if activity is None
            else activity.find("default-finance-type").get("code", "")
        )
        sector = sector_stratum(activity)
        state = (
            reconcile(row, now)
            if row
            else {
                "observation_status": "current_only",
                "outcome": "unknown",
                "last_observed_stage": "",
                "last_observed_snapshot": "",
            }
        )
        units.append(
            {
                "unit_id": identifier,
                "parent_id": row["id_projet"]
                if row
                else now["iati_identifier"].removeprefix("FR-3-"),
                "country": country,
                "country_raw": label,
                "sector_raw": row.get("libelle_secteur_economique_cad_5", "")
                if row
                else now.get("sector_narrative", ""),
                "sector_mapped": sector,
                "instrument_raw": instrument,
                "instrument_label": row.get("groupe_de_produit", "")
                if row
                else now.get("groupe_de_produit", ""),
                "xml_sector_raw": ""
                if activity is None
                else "|".join(
                    x.get("vocabulary", "1") + ":" + x.get("code", "")
                    for x in activity.findall("sector")
                ),
                "legacy_aid_type_raw": row.get("valeur_fixe1", "") if row else "",
                "portal_aid_type_raw": now.get("default_aid_type_code", "")
                if now
                else "",
                "portal_operation_raw": now.get("groupe_d_operation", "")
                if now
                else "",
                "policy_investment": "unknown",
                "snapshot": "retrieved-2026-09-14",
                "legacy_present": row is not None,
                "portal_present": now is not None,
                "xml_present": activity is not None,
                "observation_status": state["observation_status"],
                "identity_confidence": "exact financing ID",
                "last_observed_stage": state["last_observed_stage"],
                "last_observed_snapshot": state["last_observed_snapshot"],
                "outcome": "unknown",
            }
        )

        def event(
            stage,
            field,
            value,
            evidence,
            precision="day",
            validation="source-reported; legal meaning unvalidated",
        ):
            events.append(
                {
                    "unit_id": identifier,
                    "stage": stage,
                    "raw_field": field,
                    "raw_value": value,
                    "normalized_date": value if precision != "amount" else None,
                    "interval": "",
                    "precision": precision if value else "unknown",
                    "source_coverage": "earlier completeness unknown",
                    "validation_status": validation,
                    "evidence_id": evidence,
                    "missingness_reason": ""
                    if value
                    else "not disclosed in source field",
                }
            )

        if row:
            for stage, field in FIELDS.items():
                event(stage, field, row.get(field), "legacy")
        if now:
            event(
                "signature",
                "min_transaction_transaction_date_iso_date",
                now.get("min_transaction_transaction_date_iso_date"),
                "portal",
            )
        if activity is not None:
            for date in activity.findall("activity-date"):
                event(
                    "activity_date_type_" + date.get("type"),
                    "activity-date",
                    date.get("iso-date"),
                    path,
                )
            for transaction in activity.findall("transaction"):
                kind = transaction.find("transaction-type").get("code")
                date = transaction.find("transaction-date").get("iso-date")
                value = transaction.find("value")
                event(
                    "commitment" if kind == "2" else "observed_payment_period",
                    "transaction-date",
                    date,
                    path,
                    "day" if kind == "2" else "reporting-period endpoint",
                    "first-payment time unknown"
                    if kind == "3"
                    else "source-reported signature proxy",
                )
                event(
                    "currency_conversion",
                    "value-date",
                    value.get("value-date"),
                    path,
                    validation="not an approval imputation",
                )
                event(
                    "transaction_value_type_" + kind,
                    "value",
                    value.text,
                    path,
                    precision="amount",
                    validation="reported amount; negative corrections preserved",
                )
    return units, events


def build_coverage(legacy, current, xml):
    coverage = []
    # Every landmark is applied to every diagnostic country for calendar alignment.
    for exposure, dates in BASELINES.items():
        for baseline in dates:
            for country in sorted(COUNTRIES.values()):
                subset = [
                    r
                    for r in legacy
                    if COUNTRIES.get(r["pays_de_realisation"]) == country
                ]
                groups = defaultdict(list)
                for row in subset:
                    act = xml.get(row["id_concours"], (None,))[0]
                    inst = (
                        "missing"
                        if act is None
                        else act.find("default-finance-type").get("code", "missing")
                    )
                    groups[(sector_stratum(act), inst)].append(row)
                for (sector, inst), records in sorted(groups.items()):
                    for stage, field in FIELDS.items():
                        cohorts = sorted(
                            {
                                (r.get(field) or "missing")[:4]
                                if r.get(field)
                                else "missing"
                                for r in records
                            }
                        )
                        for cohort in cohorts:
                            cohort_rows = [
                                r
                                for r in records
                                if ((r.get(field) or "")[:4] or "missing") == cohort
                            ]
                            for kind in ["retrospective", "member", "pending"]:
                                coverage.append(
                                    {
                                        "lender": "AFD",
                                        "country": country,
                                        "sector": sector,
                                        "instrument": inst,
                                        "entry_cohort": cohort,
                                        "baseline": exposure + ":" + baseline,
                                        "stage": stage,
                                        "unit": "financing",
                                        "count_kind": kind,
                                        "count": sum(
                                            bool(r.get(field)) and r[field] <= baseline
                                            for r in cohort_rows
                                        )
                                        if kind == "retrospective"
                                        else "",
                                        "missing_count": sum(
                                            not r.get(field) for r in cohort_rows
                                        ),
                                        "lost_visibility_count": sum(
                                            r["id_concours"] not in current
                                            for r in cohort_rows
                                        ),
                                        "calendar_coverage": "legacy source-reported dates; historical census unknown",
                                        "denominator_rule": "legacy disclosed cohort; stage dates unvalidated"
                                        if kind == "retrospective"
                                        else "unsupported: historical denominator/pending status unknown",
                                        "evidence_ids": "legacy|portal",
                                    }
                                )
    return coverage


def profile_exports(root, output, legacy, portal):
    """Profile complete acquired exports and keep source-specific cohorts."""
    afd = root / "0735-round3/afd"
    projects = json.loads((afd / "les-projets-de-l-afd.json").read_text())
    transactions = json.loads((afd / "les-transactions-de-l-afd.json").read_text())
    profile = {
        "project_rows": len(projects),
        "transaction_rows": len(transactions),
        "transaction_types": dict(
            Counter(
                str(r.get("transaction_transaction_type_code")) for r in transactions
            )
        ),
        "negative_values": sum(
            float(r.get("transaction_value_text") or 0) < 0 for r in transactions
        ),
        "portal_country_labels": dict(
            Counter(str(r.get("recipient_country_narrative")) for r in portal)
        ),
        "legacy_country_labels": dict(
            Counter(str(r.get("pays_de_realisation")) for r in legacy)
        ),
        "legacy_product_labels": dict(
            Counter(str(r.get("groupe_de_produit")) for r in legacy)
        ),
        "portal_product_labels": dict(
            Counter(str(r.get("groupe_de_produit")) for r in portal)
        ),
        "portal_aid_type_codes": dict(
            Counter(str(r.get("default_aid_type_code")) for r in portal)
        ),
        "limitations": "Dates are reported proxies; no legally validated historical cohort. Missing/unmapped countries remain explicit.",
    }
    (output / "full-export-profile.json").write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n"
    )
    cohorts = []
    for source, records, fields, country_field in [
        ("legacy", legacy, FIELDS, "pays_de_realisation"),
        (
            "portal",
            portal,
            {"signature": "min_transaction_transaction_date_iso_date"},
            "recipient_country_narrative",
        ),
    ]:
        for stage, field in fields.items():
            counts = Counter(
                (
                    str(r.get(country_field) or "missing"),
                    str(r.get("groupe_de_produit") or "missing"),
                    (r.get(field) or "missing")[:4] if r.get(field) else "missing",
                )
                for r in records
            )
            for (country, instrument, cohort), count in sorted(counts.items()):
                cohorts.append(
                    {
                        "source": source,
                        "country_raw": country,
                        "instrument_raw": instrument,
                        "stage": stage,
                        "cohort": cohort,
                        "count": count,
                        "validation": "source-reported; legal date unvalidated",
                        "unit": "financing",
                    }
                )
    write_csv(output / "source-cohorts.csv", cohorts)


def run(root, output):
    legacy, portal, xml, parents, hashes = load_inputs(root)
    output.mkdir(parents=True, exist_ok=True)
    current = {r["code_concours_simple"]: r for r in portal}
    old = {r["id_concours"]: r for r in legacy}
    profile_exports(root, output, legacy, portal)
    anomalies = find_anomalies(old, current, xml)
    selection = select_cases(old, xml, anomalies)
    units, events = build_observations(old, current, xml)
    coverage = build_coverage(legacy, current, xml)
    write_csv(output / "selection.csv", selection)
    write_csv(output / "anomalies.csv", anomalies)
    write_csv(output / "units.csv", units)
    write_csv(output / "events.csv", events)
    write_csv(output / "coverage.csv", coverage)
    (output / "country-label-mapping.json").write_text(
        json.dumps(COUNTRIES, indent=2, sort_keys=True) + "\n"
    )
    counts = {
        "legacy": len(legacy),
        "portal": len(portal),
        "xml_financings": len(xml),
        "xml_parents": len(parents),
        "legacy_diagnostic": sum(r["pays_de_realisation"] in COUNTRIES for r in legacy),
        "legacy_xml_overlap": len(set(old) & set(xml)),
        "anomalies": dict(Counter(r["kind"] for r in anomalies)),
        "candidate_count": sum(r["role"] == "sample" for r in selection),
        "sample": [
            r["case_id"] for r in selection if r["role"] == "sample" and r["selected"]
        ],
    }
    (output / "calculations.json").write_text(
        json.dumps(counts, indent=2, sort_keys=True) + "\n"
    )
    (output / "archive-hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    )


def main():
    args, extra = parse_io_args()
    if extra or not args.input or len(args.input) != 1:
        raise ValueError("Supply exactly one archive root with --input")
    validate_io(args.output, args.input)
    run(Path(args.input[0]), Path(args.output))


if __name__ == "__main__":
    main()
