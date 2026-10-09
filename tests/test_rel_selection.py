"""Only an attributed append occurrence loses scientific selection eligibility."""

import csv
import hashlib
import importlib
import io
import json
from pathlib import Path

import _icf_screen as raw
import _rel_view as view
import pytest

pytestmark = pytest.mark.domain_corpus
METHOD = "rel-occurrence-quarantine-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def row_bytes(row, schema=raw.ICF):
    stream = io.StringIO(newline="")
    csv.DictWriter(stream, schema.columns, lineterminator="\n").writerow(row)
    return stream.getvalue().encode()


def label(key, value, run):
    return {"work_key": key, "openalex_id": key.split(":")[1], "stage": "2",
            "labeller": "llm", "model": "native", "prompt_sha256": "abc", "run_id": run,
            "machine": "padme", "label": value, "doc_type": "research", "why": "native evidence",
            "labelled_at": "2026-10-01", "source": "native.jsonl"}


def fixture_registry(tmp_path):
    table = tmp_path / "icf_screen.csv"
    raw.append_new(str(table), [label("openalex:W1", "icf", "original-A"),
                                label("openalex:W2", "out", "original-B")], new_table=True)
    baseline = tmp_path / "baseline.csv"
    baseline.write_bytes(table.read_bytes())
    Path(raw.manifest_path(str(baseline))).write_bytes(Path(raw.manifest_path(str(table))).read_bytes())
    source = raw.read_table(str(table))[0]
    copied = dict(source, work_key="openalex:W2")
    raw.append_new(str(table), [copied], "t1654 exact identity migration")
    target = raw.read_table(str(table))[2]
    events = [json.loads(line) for line in Path(raw.manifest_path(str(table))).read_text().split("\n") if line]
    migration = {"mapping": {"openalex:W1": "openalex:W2"},
                 "tables": {"icf_screen": {"appended": 1, "skipped": 0}}}
    provenance = tmp_path / "migration.jsonl"
    provenance.write_bytes(canonical(migration) + b"\n")
    mapping = tmp_path / "mapping.json"
    mapping.write_bytes(canonical(migration["mapping"]))
    occurrence = {"source_ordinal": 1, "target_ordinal": 3,
                  "source_work_key": source["work_key"], "target_work_key": target["work_key"],
                  "source_raw_row_sha256": digest(row_bytes(source)), "target_raw_row_sha256": digest(row_bytes(target)),
                  "source_fields_sha256": digest(canonical(source)), "target_fields_sha256": digest(canonical(target)),
                  "baseline_target_multiplicity": 0, "prefix_target_multiplicity": 1,
                  "source_multiplicity": 1, "append_event_ordinal": 2,
                  "append_event_sha256": digest(canonical(events[1])),
                  "migration_record_ordinal": 1, "migration_record_sha256": digest(canonical(migration)),
                  "disposition": "exclude_migration_copy", "reason": "unauthorized_selection_precedence"}
    evidence = tmp_path / "evidence.json"
    evidence.write_bytes(canonical({"method": METHOD, "occurrences": [{"table": "icf_screen", **occurrence}]}))
    approval = tmp_path / "approval.json"
    approval.write_bytes(canonical({"method": METHOD, "evidence_sha256": digest(evidence.read_bytes()),
                                   "approved_occurrences": [{"table": "icf_screen", **occurrence}]}))
    artifact = lambda p: {"path": p.name, "sha256": digest(p.read_bytes())}
    registry = {"version": METHOD, "artifact_root": ".", "serialization": "utf8-csv-raw-and-canonical-json-v1",
                "evidence": artifact(evidence), "approval": artifact(approval), "mapping": artifact(mapping),
                "migration": artifact(provenance), "tables": [{"name": "icf_screen", "path": table.name,
                "schema_columns": raw.ICF.columns, "id_column": raw.ICF.id_column,
                "baseline": artifact(baseline), "baseline_manifest": artifact(Path(raw.manifest_path(str(baseline)))),
                "prefix": {"bytes": len(table.read_bytes()), "rows": 3, "sha256": digest(table.read_bytes())},
                "manifest_prefix": {"bytes": len(Path(raw.manifest_path(str(table))).read_bytes()),
                                    "sha256": digest(Path(raw.manifest_path(str(table))).read_bytes())},
                "occurrences": [occurrence]}]}
    reg_path = tmp_path / "quarantine.json"
    reg_path.write_bytes(canonical(registry))
    config = {"method": METHOD, "registry": str(reg_path), "registry_sha256": digest(reg_path.read_bytes())}
    return table, registry, reg_path, config


def effective(table, config):
    try:
        module = importlib.import_module("_rel_selection")
    except ModuleNotFoundError:
        return raw.read_table(str(table))
    return module.read_effective_table(str(table), selection=config)


def test_only_proven_migration_occurrence_is_ineligible_and_raw_append_stays_raw(tmp_path):
    table, _, _, config = fixture_registry(tmp_path)
    before = table.read_bytes(), Path(raw.manifest_path(str(table))).read_bytes()
    original = raw.read_table(str(table))
    eligible = effective(table, config)
    assert eligible == original[:2]
    assert view.work_status(original[1:], {})["status"] == "icf"
    assert view.work_status(eligible[1:], {})["status"] == "out"
    assert raw.append_new(str(table), [dict(original[2])]) == (0, 1)
    assert (table.read_bytes(), Path(raw.manifest_path(str(table))).read_bytes()) == before
