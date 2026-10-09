"""Scoped deterministic policy abstentions, never synthetic model answers (2011).

The approved registry binds local frozen source/decision/failure artifacts. It
permits only its registered complete rosters; it is not blanket screening authority.
Native calibration attempts remain separate and none of these works was inferred.
"""
import json
from pathlib import Path

import _icf_screen as ics
import _rel_facet_io as fio
import _rel_view as rv

METHOD = ics.POLICY_METHOD
SOURCE_ABSENCE = "native_titleless_absent_abstract"
SCOPES = {"full_facets", "discipline_only"}
REASONS = {"full_facets": "local_calibration_failed",
           "discipline_only": "remote_public_proof_incomplete/local_route_not_validated"}
COLUMNS = ["policy_id", *ics.KEY, "labeller", "prompt_sha256", "machine", "labelled_at", "source",
           "scope", "method_sha256", "authority_sha256", "decision_ref", "decision_sha256",
           "pool_sha256", "input_sha256", "roster_sha256", "input_record_sha256", "proof_gaps_sha256",
           "proof_gaps", "failed_route_ref", "failed_route_sha256", "native_attempts", "native_answer",
           "input_quality", "reason", "icf_values", "contrib", "field", "contrib_type"]
SCHEMA = ics.Schema(COLUMNS, "policy_id", [c for c in COLUMNS if c not in {"policy_id", "native_answer", "icf_values"}],
                    (("stage", {"2", "catchup"}), ("labeller", {"policy"}), ("model", {METHOD}),
                     ("scope", SCOPES), ("input_quality", {"unassessed"}), ("contrib", {"unsure"}),
                     ("field", {"other"}), ("contrib_type", {"other"})))
VIEW_COLUMNS = ["local_screen_abstention", "policy_scope", "policy_run_id", "policy_method",
                "policy_decision_sha256", "policy_reason", "policy_proof_gaps", "policy_input_quality"]


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _verified_path(root: Path, reference: str, expected_sha: str) -> Path:
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()) or rv.sha256_file(str(path)) != expected_sha:
        raise ValueError(f"approved artifact hash/path mismatch: {reference}")
    return path


def _source_absence_context(manifest: dict, rosters: dict, root: Path, pool_path: str,
                            scope: str, registry: dict, decision: dict) -> tuple[list, dict]:
    """Bind honest source absence to the complete admitted subset and actual pool."""
    if manifest.get("basis") != SOURCE_ABSENCE or scope != "full_facets" or rosters["discipline_only"]:
        raise ValueError("source-absence policy scope/basis mismatch")
    from _rel_titleless_intake import digest, pool_admission, read_pool
    admitted = manifest["intake_manifest"]
    intake_path = _verified_path(root, admitted["path"], admitted["sha256"])
    intake_root = intake_path.parent.parent.parent
    pool_rows = read_pool(pool_path)
    by_pool = {p["work_key"]: p for p in pool_rows}
    exact_absent = {p["work_key"] for p in pool_rows if not p["title"].strip()
                    and not p["abstract"].strip() and p.get("native_titleless_provenance")
                    and pool_admission(p, intake_root)}
    records = rosters[scope]
    if set(r["work_key"] for r in records) != exact_absent:
        raise ValueError("source-absence roster differs from complete admitted subset")
    for record in records:
        binding = json.loads(by_pool[record["work_key"]]["native_titleless_provenance"])
        if binding["manifest_sha256"] != digest(intake_path):
            raise ValueError("source-absence intake authority mismatch")
    context = {"basis": SOURCE_ABSENCE, "scope": scope, "approved_keys": sorted(exact_absent),
        "source_absence_keys": sorted(exact_absent), "pool_rows": pool_rows, "intake_root": str(intake_root),
        "pool_sha256": manifest["pool_sha256"],
        "input_sha256": manifest["scopes"][scope]["sha256"],
        "roster_sha256": manifest["scopes"][scope]["sha256"],
        "decision_ref": decision["path"], "decision_sha256": decision["sha256"],
        "authority_sha256": registry["approved_manifest_sha256"],
        "method_sha256": fio.sha(fio.encoded(registry)),
        "proof_gaps": {key: [] for key in exact_absent}, "proof_gaps_sha256": "",
        "failed_route_ref": "", "failed_route_sha256": "", "native_attempts": {}}
    return records, context


def load_context(manifest_path: str, archive_root: str, pool_path: str,
                 scope: str, registry: dict) -> tuple[list[dict], dict]:
    """Verify the approved scope registry and every local immutable input artifact."""
    if registry.get("method") != METHOD:
        raise ValueError("unregistered policy method")
    basis = registry.get("basis")
    if basis not in {None, SOURCE_ABSENCE}:
        raise ValueError("unsupported policy authority basis")
    root = Path(archive_root)
    if rv.sha256_file(manifest_path) != registry["approved_manifest_sha256"]:
        raise ValueError("policy manifest is not registered approved authority")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    if (manifest["version"] != registry["version"] or scope not in SCOPES
            or rv.sha256_file(pool_path) != manifest["pool_sha256"]):
        raise ValueError("policy scope or approved pool snapshot mismatch")
    decision = manifest["authority"]
    _verified_path(root, decision["path"], decision["sha256"])
    rosters = {}
    for name in sorted(SCOPES):
        approved = manifest["scopes"][name]
        path = _verified_path(root, approved["path"], approved["sha256"])
        roster = _read_jsonl(path)
        if len(roster) != approved["records"] or len({r["work_key"] for r in roster}) != len(roster):
            raise ValueError("approved roster count/identity mismatch")
        rosters[name] = roster
    if {r["work_key"] for r in rosters["full_facets"]} & {r["work_key"] for r in rosters["discipline_only"]}:
        raise ValueError("policy scope rosters overlap")
    if sum(map(len, rosters.values())) != manifest["unique_union"] or manifest["overlap"] != 0:
        raise ValueError("approved union count mismatch")
    if basis == SOURCE_ABSENCE:
        return _source_absence_context(manifest, rosters, root, pool_path, scope, registry, decision)
    if manifest.get("basis") is not None:
        raise ValueError("unregistered policy authority basis")
    failure = registry["failed_route_ref"]
    _verified_path(root, failure, manifest["local_calibration_failure_sha256"])
    for reference, digest in manifest["local_native_attempt_sha256"].items():
        _verified_path(root, reference, digest)
    approved = manifest["scopes"][scope]
    records = rosters[scope]
    if scope == "full_facets":
        gaps = {r["work_key"]: r["public_proof_missing_fields"] for r in records}
        gaps_sha = approved["sha256"]
    else:
        gap_artifact = approved["proof_gap_manifest"]
        gap_records = _read_jsonl(_verified_path(root, gap_artifact["path"], gap_artifact["sha256"]))
        gaps = {r["work_key"]: r["public_proof_missing_fields"] for r in gap_records}
        if len(gap_records) != len(records) or set(gaps) != {r["work_key"] for r in records}:
            raise ValueError("proof-gap roster mismatch")
        gaps_sha = gap_artifact["sha256"]
    context = {"scope": scope, "approved_keys": [r["work_key"] for r in records],
               "pool_rows": rv.read_pool(pool_path), "pool_sha256": manifest["pool_sha256"],
               "input_sha256": approved["sha256"], "roster_sha256": approved["sha256"],
               "decision_ref": decision["path"], "decision_sha256": decision["sha256"],
               "authority_sha256": registry["approved_manifest_sha256"],
               "method_sha256": fio.sha(fio.encoded(registry)), "proof_gaps": gaps,
               "proof_gaps_sha256": gaps_sha, "failed_route_ref": failure,
               "failed_route_sha256": manifest["local_calibration_failure_sha256"],
               "native_attempts": manifest["local_native_attempt_sha256"]}
    return records, context


def _check_record(record: dict, pool: dict, context: dict) -> None:
    key = record["work_key"]
    fields = dict(pool, countries=[x.strip() for x in pool["affiliation_countries"].split(";") if x.strip()])
    if fio.public_record(record) != fio.public_record(fields):
        raise ValueError(f"{key}: source fields differ from approved pool snapshot")
    if context.get("basis") == SOURCE_ABSENCE:
        from _rel_titleless_intake import pool_admission
        if (record["title"].strip() or record["abstract"].strip()
                or key not in context["source_absence_keys"] or not pool_admission(pool, context.get("intake_root"))):
            raise ValueError("source-absence policy lacks exact empty native evidence")
        return
    gaps = context["proof_gaps"].get(key)
    if (not isinstance(gaps, list) or not gaps or len(set(gaps)) != len(gaps)
            or not set(gaps) <= set(fio.PUBLIC_FIELDS)):
        raise ValueError(f"{key}: invalid exact proof gaps")


def _check_eligibility(key: str, labels: list[dict], dims: list[dict], scope: str) -> None:
    # Same normal selection rule as the view, without a window reclassification.
    rule = {"stage1_exit_labels": ["out"], "stage2_unsure_in_rel": True, "stage1_joint": None}
    row = rv.work_status(labels, rule)
    import _rel_reasons as rr
    selected, _, _ = rr.discipline_of(row, dims)
    if selected and selected["labeller"] != "policy":
        raise ValueError(f"{key}: already has a valid selected assessed discipline judgment")
    s2 = [r for r in labels if r["stage"] == "2"]
    if scope == "full_facets" and any(r["labeller"] != "policy" for r in s2):
        raise ValueError(f"{key}: full-facet policy would relabel assessed ICF")
    if scope == "discipline_only" and (not s2 or s2[-1]["label"] not in {"icf", "unsure"}):
        raise ValueError(f"{key}: dimension-only policy requires existing final icf/unsure")


def build_rows(records: list[dict], context: dict, labels: list[dict], dims: list[dict],
               run_id: str, labelled_at: str, machine: str) -> tuple[list, list, list]:
    """Deterministic scoped plan; no files written and no source text changed."""
    scope = context["scope"]
    basis = context.get("basis")
    if basis not in {None, SOURCE_ABSENCE} or (basis and scope != "full_facets"):
        raise ValueError("unsupported policy authority basis")
    keys = [r["work_key"] for r in records]
    if scope not in SCOPES or len(set(keys)) != len(keys) or set(keys) != set(context["approved_keys"]):
        raise ValueError("records do not exactly match approved policy roster")
    pool = context["pool_rows"]
    by_pool = {p["work_key"]: i for i, p in enumerate(pool)}
    matched, _, _ = rv.match_labels(pool, labels)
    import _rel_reasons as rr
    dimensions = rr._match_dimensions(pool, dims)
    dispositions, icf_rows, dim_rows = [], [], []
    for record in records:
        key = record["work_key"]
        if key not in by_pool:
            raise ValueError(f"{key}: absent from approved pool")
        i = by_pool[key]
        _check_record(record, pool[i], context)
        _check_eligibility(key, matched.get(i, []), dimensions.get(i, []), scope)
        stage = "2" if scope == "full_facets" else "catchup"
        common = {"work_key": key, "stage": stage, "labeller": "policy", "model": METHOD,
                  "run_id": run_id, "machine": machine, "labelled_at": labelled_at,
                  # Historical compatibility field stores the deterministic method hash,
                  # not a nonexistent model prompt.
                  "prompt_sha256": context["method_sha256"],
                  "source": f"policy:{(basis + ':') if basis else ''}{context['authority_sha256']}/{scope}/{context['roster_sha256']}"}
        policy = dict(common, scope=scope, method_sha256=context["method_sha256"],
                      **{k: context[k] for k in ("authority_sha256", "decision_ref", "decision_sha256",
                         "pool_sha256", "input_sha256", "roster_sha256", "proof_gaps_sha256",
                         "failed_route_ref", "failed_route_sha256")},
                      input_record_sha256=fio.proof_hash(record), proof_gaps="" if basis else fio.encoded(context["proof_gaps"][key]),
                      native_attempts="" if basis else fio.encoded(context["native_attempts"]), native_answer="",
                      input_quality="unassessed", reason=basis or REASONS[scope],
                      icf_values=fio.encoded({f: .5 for f in ("international", "climate", "finance")}) if scope == "full_facets" and not basis else "",
                      contrib="unsure", field="other", contrib_type="other")
        validate_policy(policy)
        dispositions.append(policy)
        dim_rows.append(dict(common, contrib="unsure", field="other", contrib_type="other"))
        if scope == "full_facets":
            from utils import normalize_title
            icf_rows.append(dict(common, openalex_id=record["openalex_id"], doi=record["doi"],
                                 title_norm_year="" if basis else f"{normalize_title(record['title'])}|{record['year']}",
                                 label="unsure", doc_type="unknown", studied_country="?",
                                 why=f"policy abstention: {policy['reason']}; scientific scope unresolved"))
    return dispositions, icf_rows, dim_rows


def validate_policy(row: dict, *, schema_checks: bool = True) -> None:
    """Reject synthetic native replies, unapproved policy vectors or scope confusion."""
    faults = ics.validate_row(row, SCHEMA, profile_checks=False) if schema_checks else []
    scope = row.get("scope")
    basis = SOURCE_ABSENCE if row.get("reason") == SOURCE_ABSENCE else None
    expected = fio.encoded({f: .5 for f in ("international", "climate", "finance")}) if scope == "full_facets" and not basis else ""
    if (row.get("native_answer") != "" or row.get("icf_values") != expected
            or row.get("stage") != ("2" if scope == "full_facets" else "catchup")
            or row.get("reason") != (basis or REASONS.get(scope))
            or (basis and scope != "full_facets")):
        faults.append("policy scope/native absence/value invariant")
    hashes = ("prompt_sha256", "method_sha256", "authority_sha256", "decision_sha256", "pool_sha256",
              "input_sha256", "roster_sha256", "input_record_sha256", "proof_gaps_sha256", "failed_route_sha256")
    if any(not fio._is_sha(row.get(k)) for k in hashes if not (basis and k in {"proof_gaps_sha256", "failed_route_sha256"})):
        faults.append("policy provenance hashes must be SHA256")
    expected_source = f"policy:{(basis + ':') if basis else ''}{row.get('authority_sha256')}/{scope}/{row.get('roster_sha256')}"
    if row.get("source") != expected_source or row.get("prompt_sha256") != row.get("method_sha256"):
        faults.append("policy method/source provenance mismatch")
    if basis:
        if any(row.get(k) != "" for k in ("proof_gaps", "proof_gaps_sha256", "failed_route_ref", "failed_route_sha256", "native_attempts")):
            faults.append("source-absence policy must not fabricate failed routes/gaps/attempts")
        if faults:
            raise ValueError(f"invalid policy disposition: {faults}")
        return
    try:
        gaps = json.loads(row.get("proof_gaps", ""))
        attempts = json.loads(row.get("native_attempts", ""))
        if (not isinstance(gaps, list) or not gaps or len(set(gaps)) != len(gaps)
                or not set(gaps) <= set(fio.PUBLIC_FIELDS) or not isinstance(attempts, dict)
                or not attempts or any(not fio._is_sha(v) for v in attempts.values())):
            faults.append("policy exact gaps/failure attempt provenance invalid")
    except (TypeError, ValueError):
        faults.append("policy gap/attempt provenance malformed")
    if faults:
        raise ValueError(f"invalid policy disposition: {faults}")


def _expose(row: dict, policy: dict) -> None:
    validate_policy(policy)
    row.update(local_screen_abstention="true", policy_scope=policy["scope"], policy_run_id=policy["run_id"],
               policy_method=policy["model"], policy_decision_sha256=policy["decision_sha256"],
               policy_reason=policy["reason"], policy_proof_gaps=policy["proof_gaps"], policy_input_quality="unassessed")


def assign_full_view(rows: list[dict], policies: list[dict]) -> dict:
    index = {ics.key_of(p): p for p in policies}
    for row in rows:
        row.update({c: "" for c in VIEW_COLUMNS})
        row["local_screen_abstention"] = "false"
        if row["stage2_model"] != METHOD:
            continue
        key = (row["work_key"], "2", METHOD, row["stage2_run_id"])
        if key not in index or index[key]["scope"] != "full_facets" or row["stage2_label"] != "unsure":
            raise ValueError("selected policy ICF judgment lacks aligned scoped provenance")
        p = index[key]
        _expose(row, p)
        row.update(icf_instrument="policy_native_titleless_absent_abstract_v1" if p["reason"] == SOURCE_ABSENCE else "policy_local_abstention_v1", icf_input_quality="unassessed",
                   icf_quality_origin="policy_unassessed", icf_method_sha256=p["method_sha256"],
                   icf_guard_disposition="policy_abstention")
        for facet in ("international", "climate", "finance"):
            row["mu_" + facet] = "" if p["reason"] == SOURCE_ABSENCE else "0.5"
    return index


def assign_dimension_view(row: dict, dimension: dict | None, index: dict) -> None:
    if not dimension or dimension["labeller"] != "policy":
        return
    key = ics.key_of(dimension)
    if key not in index:
        raise ValueError("selected policy discipline judgment lacks aligned provenance")
    p = index[key]
    if any(dimension[k] != p[k] for k in ("contrib", "field", "contrib_type", "model", "prompt_sha256")):
        raise ValueError("selected policy dimension differs from scoped disposition")
    _expose(row, p)
