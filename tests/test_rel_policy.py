"""Honest scoped local policy abstentions preserve source and prior judgments."""
import json

import pytest

pytestmark = pytest.mark.domain_corpus


def _fixture(scope="full_facets"):
    from test_corpus_rel_view import _lab, _work
    key = "openalex:W1"
    pool = _work(key, title="Local source title", oas="W1")
    pool.update(abstract="A nonempty source abstract", affiliation_countries="FR")
    record = {"work_key": key, "openalex_id": "W1", "doi": "", "title": pool["title"],
              "year": pool["year"], "abstract": pool["abstract"], "language": pool["language"],
              "journal": pool["journal"], "countries": ["FR"]}
    context = {"scope": scope, "approved_keys": [key], "pool_rows": [pool],
               "pool_sha256": "a" * 64, "input_sha256": "b" * 64, "roster_sha256": "b" * 64,
               "decision_sha256": "c" * 64, "decision_ref": "decision.md",
               "authority_sha256": "d" * 64, "method_sha256": "e" * 64,
               "proof_gaps": {key: ["abstract", "year"]}, "proof_gaps_sha256": "f" * 64,
               "failed_route_ref": "failed-route.json", "failed_route_sha256": "1" * 64,
               "native_attempts": {"calibration.reply.json": "2" * 64}}
    labels = [_lab(key, "1", "icf")] if scope == "full_facets" else [_lab(key, "2", "icf")]
    return record, context, labels


def test_policy_full_facets_native_absent_and_dimension_only_has_no_icf_values():
    import _rel_policy as policy
    record, context, labels = _fixture()
    original = json.dumps(record)
    dispositions, icf, dims = policy.build_rows([record], context, labels, [], "policy-run", "2026-10-08", "padme")
    assert dispositions[0]["native_answer"] == ""
    assert dispositions[0]["input_quality"] == "unassessed"
    assert json.loads(dispositions[0]["icf_values"]) == {"international": .5, "climate": .5, "finance": .5}
    assert icf[0]["labeller"] == dims[0]["labeller"] == "policy"
    assert icf[0]["model"] == policy.METHOD and icf[0]["label"] == "unsure"
    assert dims[0]["contrib"] == "unsure" and dims[0]["field"] == dims[0]["contrib_type"] == "other"
    assert json.dumps(record) == original
    record, context, labels = _fixture("discipline_only")
    dispositions, icf, dims = policy.build_rows([record], context, labels, [], "policy-run", "2026-10-08", "padme")
    assert icf == [] and dispositions[0]["icf_values"] == ""
    assert dims[0]["stage"] == "catchup"
    assert dispositions[0]["reason"] == "remote_public_proof_incomplete/local_route_not_validated"

@pytest.mark.parametrize("scope", ["full_facets", "discipline_only"])
@pytest.mark.parametrize("excluded", [False, True])
def test_policy_view_restriction_and_later_valid_assessment(scope, excluded):
    import _rel_facet_io as fio
    import _rel_policy as policy
    import _rel_reasons as rr
    import _rel_view as rv
    from test_corpus_rel_view import RULE, WINDOW, _lab
    from test_rel_reasons import MRULE, SRULE, _dim, _ven
    record, context, labels = _fixture(scope)
    dispositions, icf, dims = policy.build_rows([record], context, labels, [], "policy-run", "2026-10-08", "padme")
    pool = context["pool_rows"]
    def view(labels, dims):
        rows, _ = rv.build_view(pool, labels, WINDOW, RULE)
        fio.assign_view(rows, [])
        rr.assign(rows, pool, dims, {record["work_key"]: _ven(record["work_key"], tier="C" if excluded else "A")},
                  SRULE, MRULE, dispositions)
        return rows[0]
    row = view(labels + icf, dims)
    assert row["abstract_flag"] == "" and row["local_screen_abstention"] == "true"
    assert row["rel_use_reason"] == "local_screen_abstention"
    assert row["rel_use"] == ("" if excluded else "bibliometric_only")
    assert row["policy_scope"] == scope
    assert row["mu_international"] == ("0.5" if scope == "full_facets" else "")
    later = _lab(record["work_key"], "2", "icf")
    later["run_id"] = "later"
    row = view(labels + icf + [later], dims + [_dim(record["work_key"], "yes", run_id="later")])
    assert row["local_screen_abstention"] == "false" and row["policy_method"] == ""
    assert row["rel_use"] == ("" if excluded else "synthesis")


def test_scope_source_and_assessed_dimension_guards():
    import _rel_policy as policy
    from test_rel_reasons import _dim
    record, context, labels = _fixture("discipline_only")
    def build(records, dims=None):
        return policy.build_rows(records, context, labels, dims or [], "policy-run", "2026-10-08", "padme")
    for records in ([], [record, record], [dict(record, work_key="openalex:W999")]):
        with pytest.raises(ValueError, match="roster"):
            build(records)
    with pytest.raises(ValueError, match="source fields"):
        build([dict(record, abstract="different")])
    with pytest.raises(ValueError, match="assessed discipline"):
        build([record], [_dim(record["work_key"], "yes", stage="catchup")])


def test_policy_cannot_fabricate_native_answer_or_values():
    import _rel_policy as policy
    record, context, labels = _fixture()
    dispositions, _, _ = policy.build_rows([record], context, labels, [], "run", "2026-10-08", "padme")
    for mutation in ({"native_answer": "model said unsure"}, {"input_quality": "usable"},
                     {"icf_values": '{"international":0.7,"climate":0.5,"finance":0.5}'},
                     {"reason": "Qwen assessed this work"}):
        with pytest.raises(ValueError, match="invalid policy"):
            policy.validate_policy(dict(dispositions[0], **mutation))


@pytest.mark.parametrize("scope", ["full_facets", "discipline_only"])
def test_import_append_idempotent_and_history_preserved(tmp_path, scope):
    import _icf_screen as ics
    import _rel_policy as policy
    import corpus_rel_policy as cli
    record, context, labels = _fixture(scope)
    table, dims, output = [str(tmp_path / n) for n in ("icf.csv", "dims.csv", "policy.csv")]
    ics.append_new(table, labels)
    before = open(table, "rb").read()
    kwargs = dict(table=table, dimensions=dims, output=output, run_id="policy-run", labelled_at="2026-10-08", machine="padme")
    result = cli.import_dispositions([record], context, **kwargs)
    assert result["native_model_answers"] == 0
    assert open(table, "rb").read().startswith(before)
    if scope == "discipline_only":
        assert open(table, "rb").read() == before
    frozen = [open(p, "rb").read() for p in (table, dims, output)]
    cli.import_dispositions([record], context, **kwargs)
    assert frozen == [open(p, "rb").read() for p in (table, dims, output)]
    assert ics.read_table(output, policy.SCHEMA)[0]["native_answer"] == ""
    assert policy.METHOD in open(ics.manifest_path(output)).read()
    with pytest.raises(ics.IcfScreenError):
        cli.import_dispositions([record], context, **dict(kwargs, labelled_at="2026-10-09"))
    assert frozen == [open(p, "rb").read() for p in (table, dims, output)]


def test_registered_manifest_cli_and_artifact_guards(tmp_path):
    import csv

    import _icf_screen as ics
    import _rel_policy as policy
    import _rel_view as rv
    import corpus_rel_policy as cli
    import yaml
    def _write(path, columns, rows):
        with path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    root = tmp_path
    full, full_context, full_labels = _fixture()
    dim, dim_context, dim_labels = _fixture("discipline_only")
    dim = dict(dim, work_key="openalex:W2", openalex_id="W2")
    dim_pool = dict(dim_context["pool_rows"][0], work_key="openalex:W2", openalex_id="W2", all_openalex_ids="W2")
    dim_labels[0].update(work_key="openalex:W2", openalex_id="W2")
    pool_path = root / "pool.csv"
    _write(pool_path, list(full_context["pool_rows"][0]), full_context["pool_rows"] + [dim_pool])
    full["public_proof_missing_fields"] = ["abstract"]
    files = {"full.jsonl": json.dumps(full) + "\n", "dim.jsonl": json.dumps(dim) + "\n",
             "gaps.jsonl": json.dumps({"work_key": dim["work_key"], "public_proof_missing_fields": ["year"]}) + "\n",
             "decision.md": "Approved synthetic test roster", "failed.json": "Calibration failed",
             "native.reply.json": "Actual failed test calibration attempt"}
    for name, contents in files.items():
        (root / name).write_text(contents)
    digest = lambda name: rv.sha256_file(str(root / name))
    manifest = {"version": "policy-local-evidence-abstention-v1", "pool_sha256": digest("pool.csv"),
                "authority": {"path": "decision.md", "sha256": digest("decision.md")},
                "scopes": {"full_facets": {"path": "full.jsonl", "sha256": digest("full.jsonl"), "records": 1},
                           "discipline_only": {"path": "dim.jsonl", "sha256": digest("dim.jsonl"), "records": 1,
                                               "proof_gap_manifest": {"path": "gaps.jsonl", "sha256": digest("gaps.jsonl")}}},
                "unique_union": 2, "overlap": 0,
                "local_calibration_failure_sha256": digest("failed.json"),
                "local_native_attempt_sha256": {"native.reply.json": digest("native.reply.json")}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    registry = {"version": manifest["version"], "method": policy.METHOD,
                "approved_manifest_sha256": digest("manifest.json"), "failed_route_ref": "failed.json"}
    (root / "config.yaml").write_text(yaml.safe_dump(registry))
    table, dimensions, output = [root / name for name in ("icf.csv", "dimensions.csv", "policy.csv")]
    ics.append_new(str(table), full_labels + dim_labels)
    args = ["--input", str(root / "manifest.json"), "--output", str(output), "--archive-root", str(root),
            "--pool", str(pool_path), "--table", str(table), "--dimensions", str(dimensions),
            "--config", str(root / "config.yaml"), "--run-id", "test-policy", "--labelled-at", "2026-10-08"]
    assert cli.main(args + ["--scope", "full_facets"]) == 0
    before = table.read_bytes()
    assert cli.main(args + ["--scope", "discipline_only"]) == 0
    assert table.read_bytes() == before
    assert len(ics.read_table(str(output), policy.SCHEMA)) == 2
    (root / "native.reply.json").write_text("changed native artifact")
    assert cli.main(args + ["--scope", "discipline_only"]) == 1
    assert table.read_bytes() == before
    with pytest.raises(ValueError, match="registered"):
        policy.load_context(str(root / "manifest.json"), str(root), str(pool_path), "full_facets",
                            dict(registry, approved_manifest_sha256="0" * 64))


def test_existing_valid_historical_icf_cannot_be_replaced_by_policy():
    import _rel_policy as policy
    from test_corpus_rel_view import _lab
    record, context, labels = _fixture()
    historical = _lab(record["work_key"], "2", "aux")
    with pytest.raises(ValueError, match="relabel assessed ICF"):
        policy.build_rows([record], context, labels + [historical], [], "policy-run", "2026-10-08", "padme")


def test_selected_policy_without_provenance_refused():
    import _rel_facet_io as fio
    import _rel_policy as policy
    import _rel_reasons as rr
    import _rel_view as rv
    from test_corpus_rel_view import RULE, WINDOW
    from test_rel_reasons import MRULE, SRULE, _ven
    record, context, labels = _fixture("discipline_only")
    _, _, dims = policy.build_rows([record], context, labels, [], "run", "2026-10-08", "padme")
    pool = context["pool_rows"]
    rows, _ = rv.build_view(pool, labels, WINDOW, RULE)
    fio.assign_view(rows, [])
    with pytest.raises(ValueError, match="aligned provenance"):
        rr.assign(rows, pool, dims, {record["work_key"]: _ven(record["work_key"])}, SRULE, MRULE)
