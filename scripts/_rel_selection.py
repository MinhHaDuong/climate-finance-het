"""Explicit scientific eligibility of proven migration-copy occurrences.

Raw append verification/uniqueness stays in _icf_screen. Operator-approved
local artifacts establish attribution; hashes alone do not establish causation.
No registry is active by default and this module never writes scientific data.
"""

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import _icf_screen as raw
import yaml

METHOD = "rel-occurrence-quarantine-v1"
SERIALIZATION = "utf8-csv-raw-and-canonical-json-v1"
ROOT = Path(__file__).resolve().parent.parent


class SelectionError(raw.IcfScreenError):
    """Unqualified occurrence provenance must not affect scientific selection."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SelectionError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise SelectionError(f"nonfinite JSON value: {value}")


def _json(data):
    try:
        return json.loads(data, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except (ValueError, TypeError) as exc:
        raise SelectionError("invalid occurrence-selection JSON") from exc


def _require(condition, message):
    if not condition:
        raise SelectionError(message)


def _integer(value, minimum=0):
    _require(type(value) is int and value >= minimum, "invalid occurrence ordinal/count")
    return value


def _hash(value):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "invalid SHA256 binding")
    return value


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _prefix(path, binding):
    length = _integer(binding["bytes"], 1)
    _require(Path(path).stat().st_size >= length, "bound artifact prefix truncated")
    _require(raw._sha256_prefix(str(path), length) == _hash(binding["sha256"]), "bound artifact prefix changed")
    return length


def _resolve(root, locator):
    _require(isinstance(locator, str) and bool(locator), "missing artifact locator")
    path = (root / locator).resolve()
    _require(path.is_relative_to(root.resolve()), "artifact outside approved root")
    _require(path.is_file(), "approved artifact missing")
    return path


def _artifact(root, binding):
    path = _resolve(root, binding["path"])
    _require(_file_hash(path) == _hash(binding["sha256"]), "approved artifact changed")
    return path


def _schema(entry):
    from _rel_facet_io import SCHEMA as facet_schema
    from _rel_policy import SCHEMA as policy_schema

    schemas = (raw.ICF, raw.DIMENSIONS, facet_schema, policy_schema)
    matches = [schema for schema in schemas
               if schema.columns == entry["schema_columns"] and schema.id_column == entry["id_column"]]
    _require(len(matches) == 1, "unknown or ambiguous table schema")
    return matches[0]


def _csv_occurrences(path, schema):
    """Actual CSV row bytes, including embedded newlines; Unicode separators are data."""
    with Path(path).open(encoding="utf-8", newline="") as stream:
        parts = []
        def lines():
            for line in stream:
                parts.append(line)
                yield line
        reader = csv.reader(lines())
        _require(next(reader, None) == schema.columns, "occurrence CSV schema changed")
        position = len("".join(parts).encode())
        parts.clear()
        for ordinal, values in enumerate(reader, 1):
            _require(len(values) == len(schema.columns), "malformed occurrence CSV row")
            row_bytes = "".join(parts).encode()
            parts.clear()
            position += len(row_bytes)
            yield ordinal, dict(zip(schema.columns, values, strict=True)), _digest(row_bytes), position


def _manifest_prefix(path, entry, rows):
    manifest = Path(raw.manifest_path(str(path)))
    length = _prefix(manifest, entry["manifest_prefix"])
    with manifest.open("rb") as stream:
        data = stream.read(length)
    _require(data.endswith(b"\n"), "manifest prefix ends within an event")
    events = [_json(line) for line in data.split(b"\n") if line]
    _require(bool(events), "empty append provenance")
    for event in events:
        _integer(event["rows_total"])
        _integer(event["rows_added"])
        _integer(event["bytes"], 1)
    _require(events[0]["rows_total"] == events[0]["rows_added"], "initial append counts ambiguous")
    last = events[-1]
    _require(last["bytes"] == entry["prefix"]["bytes"]
             and last["sha256"] == entry["prefix"]["sha256"]
             and last["rows_total"] == rows, "table/append prefix mismatch")
    _require(raw._sha256_prefix(str(path), last["bytes"]) == last["sha256"], "migration prefix changed")
    for previous, event in zip(events, events[1:]):
        _require(event["rows_total"] - previous["rows_total"] == event["rows_added"], "append occurrence counts ambiguous")
        _require(raw._sha256_prefix(str(path), previous["bytes"]) == previous["sha256"], "append predecessor prefix changed")
    return events


def _row_index(path, schema, ordinals, prefix_rows, targets, events=()):
    indexed, counts = {}, Counter()
    positions = {event["bytes"]: event["rows_total"] for event in events}
    seen = set()
    total = 0
    for ordinal, row, byte_hash, position in _csv_occurrences(path, schema):
        if position in positions:
            _require(positions[position] == ordinal, "append event actual CSV row count mismatch")
            seen.add(position)
        total = ordinal
        if ordinal in ordinals:
            indexed[ordinal] = (row, byte_hash)
        if ordinal <= prefix_rows and row["work_key"] in targets:
            counts[_digest(_canonical(row))] += 1
    _require(total >= prefix_rows and set(indexed) == ordinals, "occurrence ordinal outside artifact")
    _require(seen == set(positions), "append event does not end at a CSV occurrence boundary")
    return indexed, counts


def _check_event(occurrence, events, migrations, table_name):
    index = _integer(occurrence["append_event_ordinal"], 2)
    _require(index <= len(events), "append event missing")
    event, previous = events[index - 1], events[index - 2]
    _require(_digest(_canonical(event)) == _hash(occurrence["append_event_sha256"]), "append event changed")
    _require(previous["rows_total"] < occurrence["target_ordinal"] <= event["rows_total"], "target not in declared append event")
    _require(event.get("note") == "t1654 exact identity migration", "append event is not a migration")
    migration_index = _integer(occurrence["migration_record_ordinal"], 1)
    _require(migration_index <= len(migrations), "migration record missing")
    record = migrations[migration_index - 1]
    _require(_digest(_canonical(record)) == _hash(occurrence["migration_record_sha256"]), "migration record changed")
    _require(record["mapping"].get(occurrence["source_work_key"]) == occurrence["target_work_key"], "migration mapping mismatch")
    _require(record["tables"][table_name]["appended"] == event["rows_added"], "migration append multiplicity mismatch")


def _check_occurrence(occurrence, source, target, schema, counts, events, migrations, table_name):
    source_row, source_bytes = source
    target_row, target_bytes = target
    _require(occurrence["disposition"] == "exclude_migration_copy"
             and occurrence["reason"] == "unauthorized_selection_precedence", "unresolved occurrence disposition")
    _require(source_row["work_key"] == occurrence["source_work_key"]
             and target_row["work_key"] == occurrence["target_work_key"]
             and source_row["work_key"] != target_row["work_key"], "source/target identity mismatch")
    for actual, field in ((source_bytes, "source_raw_row_sha256"), (target_bytes, "target_raw_row_sha256"),
                          (_digest(_canonical(source_row)), "source_fields_sha256"),
                          (_digest(_canonical(target_row)), "target_fields_sha256")):
        _require(actual == _hash(occurrence[field]), "occurrence row hash mismatch")
    transformed = dict(source_row, work_key=target_row["work_key"])
    transformed[schema.id_column] = raw.label_id(transformed)
    _require(transformed == target_row, "migration changed non-key/non-derived-ID assessment fields")
    baseline_counts, prefix_counts = counts
    for actual, field in ((baseline_counts[occurrence["target_fields_sha256"]], "baseline_target_multiplicity"),
                          (baseline_counts[occurrence["source_fields_sha256"]], "source_multiplicity"),
                          (prefix_counts[occurrence["target_fields_sha256"]], "prefix_target_multiplicity")):
        _require(actual == _integer(occurrence[field]), "occurrence multiplicity mismatch")
    _require(occurrence["source_multiplicity"] == 1, "ambiguous source occurrence attribution")
    _require(occurrence["prefix_target_multiplicity"] > occurrence["baseline_target_multiplicity"], "no new target occurrence proved")
    _check_event(occurrence, events, migrations, table_name)


def _table_result(root, entry, migrations):
    path = _resolve(root, entry["path"])
    schema = _schema(entry)
    rows = raw.read_table(str(path), schema)
    _prefix(path, entry["prefix"])
    prefix_rows = _integer(entry["prefix"]["rows"], 1)
    events = _manifest_prefix(path, entry, prefix_rows)
    baseline_path = _artifact(root, entry["baseline"])
    _require(_artifact(root, entry["baseline_manifest"]) == Path(raw.manifest_path(str(baseline_path))), "baseline manifest locator mismatch")
    baseline = raw.read_table(str(baseline_path), schema)
    occurrences = entry["occurrences"]
    _require(isinstance(occurrences, list) and bool(occurrences), "empty occurrence registry table")
    sources = {_integer(row["source_ordinal"], 1) for row in occurrences}
    targets = {_integer(row["target_ordinal"], 1) for row in occurrences}
    _require(len(targets) == len(occurrences), "duplicate target occurrence disposition")
    _require(all(n > len(baseline) and n <= prefix_rows for n in targets), "target occurrence existed in baseline or is outside prefix")
    keys = {row[field] for row in occurrences for field in ("source_work_key", "target_work_key")}
    source_index, baseline_counts = _row_index(baseline_path, schema, sources, len(baseline), keys)
    target_index, prefix_counts = _row_index(path, schema, targets, prefix_rows, keys, events)
    _require(len(rows) >= prefix_rows and rows[:len(baseline)] == baseline, "historical baseline rows changed")
    with path.open("rb") as stream:
        _require(stream.read(baseline_path.stat().st_size) == baseline_path.read_bytes(), "historical baseline raw bytes changed")
    for occurrence in occurrences:
        _check_occurrence(occurrence, source_index[occurrence["source_ordinal"]], target_index[occurrence["target_ordinal"]],
                          schema, (baseline_counts, prefix_counts), events, migrations, entry.get("migration_table_key", entry["name"]))
    eligible = [row for n, row in enumerate(rows, 1) if n not in targets]
    return path, eligible, {"raw": len(rows), "eligible": len(eligible), "excluded": len(targets),
                            "excluded_ordinals": sorted(targets), "eligible_ordinals": [n for n in range(1, len(rows) + 1) if n not in targets],
                            "prefix_sha256": entry["prefix"]["sha256"], "table_sha256": _file_hash(path),
                            "manifest_sha256": _file_hash(raw.manifest_path(str(path)))}


def _configuration(selection):
    if selection is not None:
        return selection
    with (ROOT / "config/rel_screen.yaml").open() as stream:
        return (yaml.safe_load(stream) or {}).get("assessment_selection", {})


def _approved_registry(config):
    path = (ROOT / config["registry"]).resolve()
    _require(_file_hash(path) == _hash(config["registry_sha256"]), "registry hash changed")
    registry = _json(path.read_bytes())
    _require(config.get("method") == METHOD and registry.get("version") == METHOD, "unsupported selection method")
    _require(registry.get("serialization") == SERIALIZATION, "unsupported row serialization")
    code_hash = _file_hash(__file__)
    _require(config.get("method_sha256") == code_hash and registry.get("method_sha256") == code_hash, "selection method code binding changed")
    root = (path.parent / registry["artifact_root"]).resolve()
    evidence_path = _artifact(root, registry["evidence"])
    approval = _json(_artifact(root, registry["approval"]).read_bytes())
    evidence = _json(evidence_path.read_bytes())
    declarations = [{"table": table["name"], **row} for table in registry["tables"] for row in table["occurrences"]]
    _require(approval.get("method") == METHOD and evidence.get("method") == METHOD
             and approval.get("evidence_sha256") == registry["evidence"]["sha256"], "operator approval evidence binding mismatch")
    normalized = lambda values: sorted(_canonical(value) for value in values)
    _require(normalized(approval["approved_occurrences"]) == normalized(declarations)
             and normalized(evidence["occurrences"]) == normalized(declarations), "unapproved or ambiguous occurrence roster")
    mapping = _json(_artifact(root, registry["mapping"]).read_bytes())
    _require(all(mapping.get(row["source_work_key"]) == row["target_work_key"] for row in declarations), "approved mapping changed")
    migrations = [_json(line) for line in _artifact(root, registry["migration"]).read_bytes().split(b"\n") if line]
    return registry, root, migrations


def _context(selection=None):
    config = _configuration(selection)
    _require(isinstance(config, dict), "invalid assessment-selection configuration")
    if not config.get("registry"):
        _require(not config.get("registry_sha256") and not config.get("method_sha256"), "partial disabled selection binding")
        return {}, {"method": METHOD, "enabled": False}
    try:
        registry, root, migrations = _approved_registry(config)
        results, counts, names = {}, {}, set()
        for entry in registry["tables"]:
            _require(entry["name"] not in names, "duplicate registry table")
            names.add(entry["name"])
            path, eligible, summary = _table_result(root, entry, migrations)
            _require(str(path) not in results, "ambiguous registry table locator")
            results[str(path)] = eligible
            counts[entry["name"]] = summary
        _require(bool(results), "empty approved registry")
    except (KeyError, TypeError, ValueError, OSError, StopIteration) as exc:
        raise SelectionError("malformed or unavailable occurrence provenance") from exc
    return results, {"method": METHOD, "enabled": True, "method_sha256": config["method_sha256"],
                     "registry_sha256": config["registry_sha256"], "evidence_sha256": registry["evidence"]["sha256"],
                     "approval_sha256": registry["approval"]["sha256"], "tables": counts}


def binding(selection=None):
    """Validated method/registry and raw/eligible/excluded occurrence accounting."""
    return _context(selection)[1]


def _immutable_binding(value):
    result = dict(value)
    if value.get("enabled"):
        result["tables"] = {name: {key: table[key] for key in ("excluded_ordinals", "prefix_sha256")}
                            for name, table in value["tables"].items()}
    return result


def require_binding(recorded, selection=None, *, allow_append=False):
    """Cached views require the full basis; native imports may permit later appends."""
    current = binding(selection)
    if current["enabled"] or recorded:
        expected = _immutable_binding(current) if allow_append else current
        actual = _immutable_binding(recorded) if allow_append and isinstance(recorded, dict) else recorded
        _require(actual == expected, "stale assessment-selection binding; rebuild from eligible rows")


def effective_rows(table_path, rows, selection=None):
    """Eligibility for a pre-existing scientific reader; disabled rows stay exact."""
    results, current = _context(selection)
    if not current["enabled"]:
        return rows
    path = str(Path(table_path).resolve())
    if path in results:
        return results[path]
    _require(not any(Path(other).name == Path(path).name for other in results), "scientific reader bypasses registered table locator")
    return rows


def read_effective_table(table_path, schema=raw.ICF, selection=None):
    """Verified raw ledger followed by explicit occurrence eligibility, never append."""
    rows = raw.read_table(table_path, schema)
    return effective_rows(table_path, rows, selection)
