"""Source-absence policy has no fabricated model answers or measured facets."""
import json

import pytest

pytestmark = pytest.mark.domain_corpus


def _absence_fixture(tmp_path, monkeypatch):
    import corpus_rel_pool as pool_module
    from _rel_pool_dedup import cluster
    from test_qa_rel_intake import _native_titleless_delivery
    from test_rel_policy import _fixture
    d, _ = _native_titleless_delivery(tmp_path, monkeypatch, abstract=False)
    records, _ = pool_module.load_delivery("t1650-sommaires/2026-10-01", str(d))
    pool = pool_module.build_pool(records, cluster(records), {"t1650-sommaires": 0})
    p = pool[0]
    record = {k: p[k] for k in ("work_key", "openalex_id", "doi", "title", "abstract", "year", "language", "journal")}
    record["countries"] = []
    _, context, _ = _fixture()
    context.update(basis="native_titleless_absent_abstract", pool_rows=pool, approved_keys=[p["work_key"]],
                   source_absence_keys=[p["work_key"]], proof_gaps={p["work_key"]: []},
                   proof_gaps_sha256="", failed_route_ref="", failed_route_sha256="", native_attempts={})
    return d, record, context


def test_source_absence_policy_has_blank_actual_facets(tmp_path, monkeypatch):
    import _rel_facet_io as fio
    import _rel_policy as policy
    import _rel_reasons as rr
    import _rel_view as rv
    from test_corpus_rel_view import RULE, WINDOW
    from test_rel_reasons import MRULE, SRULE, _ven
    _, record, context = _absence_fixture(tmp_path, monkeypatch)
    dispositions, icf, dims = policy.build_rows([record], context, [], [], "absent", "2026-10-09", "padme")
    p = dispositions[0]
    assert p["icf_values"] == p["native_answer"] == p["native_attempts"] == ""
    assert p["failed_route_ref"] == p["proof_gaps"] == ""
    assert p["reason"] == "native_titleless_absent_abstract"
    assert icf[0]["labeller"] == "policy"
    rows, _ = rv.build_view(context["pool_rows"], icf, WINDOW, RULE)
    fio.assign_view(rows, [])
    rr.assign(rows, context["pool_rows"], dims, {record["work_key"]: _ven(record["work_key"])}, SRULE, MRULE, dispositions)
    row = rows[0]
    assert all(row["mu_" + f] == "" for f in ("international", "climate", "finance"))
    assert row["icf_instrument"] == "policy_native_titleless_absent_abstract_v1"
    assert row["rel_disposition"] == "exclude_missing_title" and row["rel_use"] == "bibliometric_only"
    assert row["local_screen_abstention"] == "true"


def test_absence_policy_append_read_idempotent_and_strict(tmp_path, monkeypatch):
    import _icf_screen as ics
    import _rel_policy as policy
    import corpus_rel_policy as cli
    _, record, context = _absence_fixture(tmp_path, monkeypatch)
    paths = [str(tmp_path / n) for n in ("icf.csv", "dims.csv", "policy.csv")]
    kwargs = dict(table=paths[0], dimensions=paths[1], output=paths[2], run_id="absent", labelled_at="2026-10-09", machine="padme", new_table=True)
    cli.import_dispositions([record], context, **kwargs)
    before = [open(p, "rb").read() for p in paths]
    cli.import_dispositions([record], context, **kwargs)
    assert before == [open(p, "rb").read() for p in paths]
    p = ics.read_table(paths[2], policy.SCHEMA)[0]
    policy.validate_policy(p)
    for change in ({"icf_values": json.dumps({"finance": .5})}, {"native_answer": "model response"},
                   {"native_attempts": "{}"}, {"proof_gaps_sha256": "a" * 64}, {"reason": "local_calibration_failed"}):
        with pytest.raises(ValueError):
            policy.validate_policy(dict(p, **change))
    with pytest.raises(ValueError):
        policy.build_rows([dict(record, abstract="present")], context, [], [], "x", "2026-10-09", "padme")


def test_hash_registered_source_absence_manifest_and_roster_guards(tmp_path, monkeypatch):
    import csv
    import hashlib

    import _rel_policy as policy
    d, record, context = _absence_fixture(tmp_path, monkeypatch)
    pool = tmp_path / "pool.csv"
    with pool.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(context["pool_rows"][0]))
        writer.writeheader(); writer.writerows(context["pool_rows"])
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    full, empty = tmp_path / "full.jsonl", tmp_path / "empty.jsonl"
    full.write_text(json.dumps(record) + "\n"); empty.write_text("")
    manifest = {"version": "native-titleless-absence-v1", "basis": policy.SOURCE_ABSENCE,
                "pool_sha256": sha(pool), "authority": {"path": str((d / "authority.md").relative_to(tmp_path)), "sha256": sha(d / "authority.md")},
                "intake_manifest": {"path": str((d / "manifest.json").relative_to(tmp_path)), "sha256": sha(d / "manifest.json")},
                "scopes": {"full_facets": {"path": "full.jsonl", "sha256": sha(full), "records": 1},
                           "discipline_only": {"path": "empty.jsonl", "sha256": sha(empty), "records": 0}},
                "unique_union": 1, "overlap": 0}
    path = tmp_path / "scope.json"; path.write_text(json.dumps(manifest))
    registry = {"version": manifest["version"], "basis": policy.SOURCE_ABSENCE,
                "method": policy.METHOD, "approved_manifest_sha256": sha(path)}
    records, frozen = policy.load_context(str(path), str(tmp_path), str(pool), "full_facets", registry)
    assert records == [record] and frozen["native_attempts"] == {}
    assert frozen["source_absence_keys"] == [record["work_key"]]
    for change in ({"basis": "unapproved"}, {"approved_manifest_sha256": "a" * 64}):
        with pytest.raises(ValueError):
            policy.load_context(str(path), str(tmp_path), str(pool), "full_facets", dict(registry, **change))
    full.write_text(json.dumps(dict(record, abstract="invented")) + "\n")
    with pytest.raises(ValueError, match="hash"):
        policy.load_context(str(path), str(tmp_path), str(pool), "full_facets", registry)


def test_true_stage1_outcomes_required_for_titleless_facet_queue(tmp_path, monkeypatch):
    import _rel_facet_io as fio
    import _rel_facets as facets
    import _rel_view as rv
    import corpus_rel_pool as cp
    from _rel_pool_dedup import cluster
    from test_corpus_rel_view import RULE, WINDOW, _lab
    from test_qa_rel_intake import _native_titleless_delivery
    from test_rel_facets import _config, _proof, answer
    d, _ = _native_titleless_delivery(tmp_path, monkeypatch)
    records, _ = cp.load_delivery("t1650-sommaires/2026-10-01", str(d))
    pool = cp.build_pool(records, cluster(records), {"t1650-sommaires": 0})
    p = pool[0]
    before, _ = rv.build_view(pool, [], WINDOW, RULE)
    assert before[0]["status"] == "unscreened"
    graded, _ = rv.build_view(pool, [_lab(p["work_key"], "1", "icf")], WINDOW, RULE)
    assert graded[0]["status"] == "pending_stage2"
    record = {k: p[k] for k in ("work_key", "openalex_id", "doi", "title", "abstract", "year", "language", "journal")}
    record["countries"] = []
    result = fio.write_chunks(str(tmp_path / "facets"), [record], [_proof(record)], _config(), {p["work_key"]: fio.family_source_ids(p)})
    assert result["proven"] == 1 and record["title"] == ""
    native = answer(scores=(0, 1, 0), input_quality="nonabstract")
    effective, disposition, _ = facets.effective_answer(native, record)
    assert (effective["international"], effective["finance"]) == (.5, .5)
    assert disposition == "unresolved" and native["international"] == 0
