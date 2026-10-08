"""Independent ICF memberships preserve uncertain evidence and discipline."""
import itertools
import json

import _rel_facets as facets
import pytest

pytestmark = pytest.mark.domain_corpus


def answer(n=1, scores=(1, 1, 1), **overrides):
    row = {"n": n, "input_quality": "usable", "main_object": "international climate finance instrument",
           "doc": "unknown", "studied": "?", "contrib": "no", "field": "data_science",
           "ctype": "method", "discipline_evidence": "forecasting method rather than policy"}
    for name, score in zip(facets.FACETS, scores, strict=True):
        row[name] = score
        row[name + "_evidence"] = {1: "supporting: instrument", .5: "insufficient: sparse text",
                                   0: "contrary: explicitly domestic-only object"}[score]
    return row | overrides


def test_topic_and_discipline_separate_and_uncertainty_preserved():
    parsed, faults = facets.parse_answers([json.dumps(answer()),
                                           json.dumps(answer(2, (.5, 1, 1), contrib="unsure"))],
                                          ["openalex:W1", "openalex:W2"])
    assert not faults
    assert facets.membership(parsed["openalex:W1"]) == 1
    assert facets.legacy_label(parsed["openalex:W1"]) == "icf"
    assert parsed["openalex:W1"]["contrib"] == "no"
    assert facets.membership(parsed["openalex:W2"]) == .5
    assert facets.legacy_label(parsed["openalex:W2"]) == "unsure"
    assert parsed["openalex:W2"]["doc"] == "unknown"


def test_duplicate_and_missing_ordinals_stay_pending():
    parsed, faults = facets.parse_answers([json.dumps(answer()), json.dumps(answer())],
                                          ["openalex:W1", "openalex:W2"])
    assert parsed == {}
    assert any("duplicate" in f for f in faults)
    assert any("missing" in f for f in faults)


@pytest.mark.parametrize("scores", list(itertools.product((0, .5, 1), repeat=3)))
def test_minimum_and_legacy_mapping(scores):
    row = answer(scores=scores)
    assert facets.membership(row) == min(scores)
    expected = "icf" if min(scores) == 1 else "unsure" if min(scores) == .5 else (
        "out" if scores == (0, 0, 0) else "aux")
    assert facets.legacy_label(row) == expected


@pytest.mark.parametrize("value", [True, "1", .25, float("nan"), float("inf"), -1])
def test_invalid_scores_not_coerced(value):
    parsed, faults = facets.parse_answers([json.dumps(answer(international=value))], ["openalex:W1"])
    assert not parsed and faults


def test_contrary_prefix_required_for_zero_and_duplicate_json_is_ambiguous():
    row = answer(scores=(0, 1, 1), international_evidence="insufficient: no mention")
    parsed, faults = facets.parse_answers([json.dumps(row)], ["openalex:W1"])
    assert not parsed and faults
    text = json.dumps(answer()).replace('"n": 1', '"n": 1, "n": 2')
    parsed, faults = facets.parse_answers([json.dumps(answer(2)), text],
                                          ["openalex:W1", "openalex:W2"])
    assert not parsed and any("duplicate JSON" in f for f in faults)


def test_malformed_unmapped_answer_quarantines_unknown_association():
    parsed, faults = facets.parse_answers([json.dumps(answer()), "{invalid"],
                                          ["openalex:W1", "openalex:W2"])
    assert not parsed and faults


def test_quality_guard_retains_raw_answers_and_quarantines_unsupported_negatives():
    row = answer(scores=(.5, .5, 0), input_quality="nonabstract")
    original = json.loads(json.dumps(row))
    valid, faults = facets.guard_quality({"openalex:W1": row},
                                        {"openalex:W1": {"title": "Property rights and REDD",
                                                         "abstract": "University dissertation frontmatter"}})
    assert not valid and faults
    assert row == original
    row = answer(scores=(.5, .5, .5), input_quality="nonabstract", contrib="unsure")
    valid, faults = facets.guard_quality({"openalex:W1": row},
                                        {"openalex:W1": {"title": "Property rights and REDD",
                                                         "abstract": "University dissertation frontmatter"}})
    assert valid and not faults


def test_absent_abstract_cannot_override_quality_by_claiming_usable():
    row = answer(scores=(0, .5, .5), input_quality="usable", contrib="unsure")
    valid, faults = facets.guard_quality({"openalex:W1": row},
                                        {"openalex:W1": {"title": "Greenhouse effect", "abstract": ""}})
    assert not valid and faults
    row["international_evidence"] = 'contrary: title: "Domestic carbon tax" identifies domestic arrangement'
    valid, faults = facets.guard_quality({"openalex:W1": row},
                                        {"openalex:W1": {"title": "Domestic carbon tax", "abstract": ""}})
    assert valid and not faults


def _record(key="openalex:W1", **extra):
    return {"work_key": key, "openalex_id": key.split(":")[1], "title": "CDM " + "é" * 300,
            "abstract": "international climate finance " * 70 + "funding evidence at the end",
            "year": "2020", "language": "en", "journal": "Journal", "countries": ["FR"], **extra}


def _config():
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / "config/rel_screen.yaml").read_text())["stage2_facets"]
    return dict(cfg, prompt=str(root / cfg["prompt"]), lexicon=str(root / cfg["lexicon"]))


def _proof(record):
    import _rel_facet_io as fio
    return {"work_key": record["work_key"], "native_openalex_id": record["openalex_id"],
            "full_sixfield_sha256": fio.proof_hash(record)}


def _parsed(tmp_path, records, answers):
    import _rel_facet_io as fio
    fio.write_chunks(str(tmp_path), records, [_proof(r) for r in records], _config())
    (tmp_path / "chunk01.luna.txt").write_text("\n".join(json.dumps(a) for a in answers))
    return fio.parse_chunks(str(tmp_path), "luna", {
        "stage": "2", "model": "luna", "run_id": "run", "machine": "padme",
        "labeller": "llm", "labelled_at": "2026-10-08"})


def test_full_text_public_proof_and_byte_packing(tmp_path):
    import _rel_facet_io as fio
    r = _record()
    cfg = _config()
    frozen, _ = fio.method(cfg)
    cfg["max_request_bytes"] = len(fio.render_request([r], frozen).encode()) + 30
    records = [r, _record("openalex:W2"), _record("openalex:W3")]
    manifest = fio.write_chunks(str(tmp_path), records, [_proof(x) for x in records[:2]], cfg)
    assert len(manifest["chunks"]) == 2
    assert manifest["unproven"] == ["openalex:W3"]
    request = (tmp_path / "chunk01.txt").read_text()
    assert r["title"] in request and r["abstract"] in request
    assert "openalex:W1" not in request and '"work_key"' not in request
    assert manifest["chunks"]["chunk01"]["input_tokens_upper_bound"] == len(request.encode())
    with pytest.raises(ValueError, match="not empty"):
        fio.write_chunks(str(tmp_path), records, [], cfg)


def test_long_record_refused_without_truncation_or_partial_output(tmp_path):
    import _rel_facet_io as fio
    cfg = dict(_config(), max_request_bytes=50)
    out = tmp_path / "new"
    r = _record()
    with pytest.raises(ValueError, match="complete record exceeds"):
        fio.write_chunks(str(out), [r], [_proof(r)], cfg)
    assert not out.exists()


def test_truncated_prefix_proof_does_not_authorize_full_fields(tmp_path):
    import _rel_facet_io as fio
    r = _record()
    proof = _proof(dict(r, abstract=r["abstract"][:650]))
    manifest = fio.write_chunks(str(tmp_path), [r], [proof], _config())
    assert manifest["proven"] == 0 and manifest["unproven"] == [r["work_key"]]


@pytest.mark.parametrize("quality", ["absent", "nonabstract", "truncated"])
def test_quality_uncertainty_even_exact_local_title_does_not_certify_negative(quality):
    r = _record(title="Heating in Tianjin", abstract="" if quality == "absent" else "frontmatter")
    native = answer(scores=(0, 1, 0), input_quality=quality,
                    international_evidence='contrary: title: "Heating in Tianjin" local',
                    finance_evidence='contrary: title: "Heating in Tianjin" engineering',
                    discipline_evidence='title: "Heating in Tianjin" engineering')
    before = json.dumps(native)
    effective, disposition, reasons = facets.effective_answer(native, r)
    assert (effective["international"], effective["climate"], effective["finance"], effective["contrib"]) == (.5, 1, .5, "unsure")
    assert disposition == "unresolved" and len(reasons) == 3
    assert json.dumps(native) == before


def test_append_import_provenance_minimum_and_legacy_preservation(tmp_path):
    import _icf_screen as ics
    import _rel_facet_io as fio
    from test_corpus_rel_view import _lab
    run = tmp_path / "run"
    raw, labels, dims, report = _parsed(run, [_record()], [answer(scores=(.5, 1, 1), contrib="yes")])
    assert labels[0]["label"] == "unsure" and dims[0]["contrib"] == "yes"
    assert report["chunk01"]["pending"] == 0
    for k in ("method_sha256", "request_sha256", "native_sha256", "record_sha256", "proof_sha256"):
        assert len(raw[0][k]) == 64
    table = str(tmp_path / "labels.csv")
    ics.append_new(table, [_lab("openalex:W2", "2", "out", model="historic", run_id="v2")])
    before = (tmp_path / "labels.csv").read_bytes()
    batches = [(str(tmp_path / "facets.csv"), raw, fio.SCHEMA, False),
               (table, labels, ics.ICF, False), (str(tmp_path / "dims.csv"), dims, ics.DIMENSIONS, False)]
    assert fio.append_batches(batches) == [(1, 0)] * 3
    assert (tmp_path / "labels.csv").read_bytes().startswith(before)
    assert fio.append_batches(batches) == [(0, 1)] * 3
    changed = [dict(raw[0], native_sha256="f" * 64)]
    with pytest.raises(ics.IcfScreenError, match="different payload"):
        fio.append_batches([(batches[0][0], changed, fio.SCHEMA, False)])


def test_quality_guard_native_and_canonical_dispositions_remain_separate(tmp_path):
    raw, labels, dims, _ = _parsed(tmp_path, [_record(abstract="University examination frontmatter")],
                                  [answer(scores=(.5, .5, 0), input_quality="nonabstract")])
    assert json.loads(raw[0]["native_answer"])["finance"] == 0
    assert json.loads(raw[0]["effective_answer"])["finance"] == .5
    assert raw[0]["guard_disposition"] == "unresolved"
    assert labels[0]["label"] == "unsure" and dims[0]["contrib"] == "unsure"


def test_mapping_request_and_method_tampering_refused(tmp_path):
    import _rel_facet_io as fio
    _parsed(tmp_path, [_record()], [answer()])
    request = tmp_path / "chunk01.txt"
    request.write_text(request.read_text() + "tamper")
    with pytest.raises(ValueError, match="mapping changed"):
        fio.parse_chunks(str(tmp_path), "luna", {})


def test_missing_and_duplicate_answers_not_imported(tmp_path):
    raw, labels, dims, report = _parsed(tmp_path, [_record(), _record("openalex:W2")], [answer(), answer()])
    assert not raw and not labels and not dims
    assert report["chunk01"]["pending"] == 2


def test_view_real_facets_blank_legacy_and_unusable_evidence_use(tmp_path):
    import _rel_facet_io as fio
    import _rel_reasons as rr
    import _rel_view as rv
    from test_corpus_rel_view import RULE, WINDOW, _lab, _work
    from test_rel_reasons import MRULE, SRULE, _dim, _ven
    raw, labels, dims, _ = _parsed(tmp_path, [_record(abstract="frontmatter")],
                                  [answer(scores=(.5, 1, 0), input_quality="nonabstract")])
    pool = [_work("openalex:W1"), _work("openalex:W2")]
    pool[0]["abstract"] = "frontmatter"
    pool[1]["abstract"] = "historic abstract"
    rows, _ = rv.build_view(pool, labels + [_lab("openalex:W2", "2", "icf")], WINDOW, RULE)
    fio.assign_view(rows, raw)
    rr.assign(rows, pool, dims + [_dim("openalex:W2", "yes")],
              {p["work_key"]: _ven(p["work_key"]) for p in pool}, SRULE, MRULE)
    assert rows[0]["mu_finance"] == "0.5" and rows[0]["mu_icf"] == "0.5"
    assert rows[0]["mu_discipline"] == "0.5" and rows[0]["rel_final"] == "true"
    assert rows[0]["abstract_flag"] == ""
    assert rows[0]["rel_use"] == "bibliometric_only" and rows[0]["rel_use_reason"] == "nonabstract_input"
    assert rows[1]["mu_finance"] == "" and rows[1]["icf_instrument"] == "legacy_aggregate"
    assert rows[1]["rel_use"] == "synthesis" and rows[1]["rel_use_reason"] == "legacy_abstract_unassessed"


def test_normal_cli_build_parse_roundtrip_with_frozen_v2_unchanged(tmp_path):
    import csv
    from pathlib import Path

    import _icf_screen as ics
    import _rel_facet_io as fio
    import corpus_icf_stage2 as cli
    import yaml
    from test_corpus_rel_view import _lab, _work
    root = Path(__file__).resolve().parents[1]
    v2 = (root / "config/rel_stage2_prompt_v2.md").read_bytes()
    cfg = yaml.safe_load((root / "config/rel_screen.yaml").read_text())
    cfg.update(pool=str(tmp_path / "pool.csv"), table=str(tmp_path / "labels.csv"),
               dimensions_table=str(tmp_path / "dims.csv"), facets_table=str(tmp_path / "facets.csv"),
               stage2_facets=_config())
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(cfg))
    r = _record()
    work = dict(_work(r["work_key"]), title=r["title"], abstract=r["abstract"])
    with open(cfg["pool"], "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(work))
        writer.writeheader()
        writer.writerow(work)
    ics.append_new(cfg["table"], [_lab(r["work_key"], "1", "icf")])
    inputs, proof = tmp_path / "input.jsonl", tmp_path / "proof.jsonl"
    inputs.write_text(json.dumps(r) + "\n")
    proof.write_text(json.dumps(_proof(r)) + "\n")
    out = tmp_path / "run"
    assert cli.main(["--config", str(config), "build-facets", "--input", str(inputs),
                     "--public-proofs", str(proof), "--output-dir", str(out)]) == 0
    (out / "chunk01.luna.txt").write_text(json.dumps(answer(scores=(1, .5, 1))) + "\n")
    args = ["--config", str(config), "parse-facets", "--chunk-dir", str(out),
            "--model", "luna", "--run-id", "run", "--machine", "padme", "--labelled-at", "2026-10-08"]
    assert cli.main(args) == 0 and cli.main(args) == 0
    assert len(ics.read_table(cfg["table"])) == 2
    assert ics.read_table(cfg["facets_table"], fio.SCHEMA)[0]["native_answer"]
    assert ics.read_table(cfg["dimensions_table"], ics.DIMENSIONS)[0]["contrib"] == "no"
    assert (root / "config/rel_stage2_prompt_v2.md").read_bytes() == v2


def test_raw_empty_forces_absent_and_consistent_effective_evidence():
    row = answer(scores=(0, 0, 0), input_quality="usable")
    effective, disposition, _ = facets.effective_answer(row, _record(abstract=""))
    assert effective["input_quality"] == "absent" and row["input_quality"] == "usable"
    assert disposition == "unresolved" and effective["contrib"] == "unsure"
    facets.validate_answer(effective)
    assert all(effective[f] == .5 for f in facets.FACETS)


def test_unicode_line_separator_in_json_evidence_is_not_an_answer_boundary(tmp_path):
    import _rel_facet_io as fio
    r = _record()
    fio.write_chunks(str(tmp_path), [r], [_proof(r)], _config())
    native = answer(finance_evidence="supporting: finance\u2028instrument\u2029allocation")
    (tmp_path / "chunk01.luna.txt").write_text(json.dumps(native, ensure_ascii=False) + "\n")
    raw, labels, dims, report = fio.parse_chunks(str(tmp_path), "luna", {
        "stage": "2", "model": "luna", "run_id": "unicode", "machine": "padme",
        "labeller": "llm", "labelled_at": "2026-10-08"})
    assert len(raw) == len(labels) == len(dims) == 1
    assert report["chunk01"]["pending"] == 0
    assert json.loads(raw[0]["native_answer"])["finance_evidence"] == native["finance_evidence"]


def _typed_proof(r, source_id="W2", source_type="openalex"):
    import _rel_facet_io as fio
    witness = {"source_type": source_type, "source_id": source_id, "native_sha256": "a" * 64,
               "source_url": f"https://api.openalex.org/works/{source_id}" if source_type == "openalex"
               else "rsync://rsync.repec.org/RePEc-ReDIF/"}
    return {"work_key": r["work_key"], "source_type": "public_fieldwise",
            "full_sixfield_sha256": fio.proof_hash(r), "declared_source_ids": [f"{source_type}:{source_id}"],
            "field_evidence": {f: {"sha256": fio.sha(fio.encoded(v)), "sources": [dict(witness)]}
                               for f, v in fio.public_record(r).items()}}


def test_public_fieldwise_proof_exact_member_and_field_hashes(tmp_path):
    import _rel_facet_io as fio
    r = _record()
    proof = _typed_proof(r)
    family = {r["work_key"]: {"openalex:W1", "openalex:W2"}}
    manifest = fio.write_chunks(str(tmp_path), [r], [proof], _config(), family)
    assert manifest["proven"] == 1
    assert "openalex:W2" not in (tmp_path / "chunk01.txt").read_text()
    assert not fio.valid_public_proof(r, proof, {"openalex:W1"})
    altered = json.loads(json.dumps(proof))
    altered["field_evidence"]["abstract"]["sha256"] = "f" * 64
    assert not fio.valid_public_proof(r, altered, family[r["work_key"]])
    altered = json.loads(json.dumps(proof))
    altered["field_evidence"]["abstract"]["sources"][0]["source_type"] = "licensed_database"
    assert not fio.valid_public_proof(r, altered, family[r["work_key"]])
    altered = json.loads(json.dumps(proof))
    altered["field_evidence"]["title"]["sources"][0]["native_sha256"] = ""
    assert not fio.valid_public_proof(r, altered, family[r["work_key"]])


def test_redif_proof_exact_handle_with_native_archive_and_no_openalex_id(tmp_path):
    import _rel_facet_io as fio
    r = _record("doi:10.123/example", openalex_id="")
    handle = "RePEc:ags:feemdp:59418"
    proof = _typed_proof(r, handle, "repec_redif")
    proof.update(source_archive="native-redif-subset.jsonl", source_manifest_sha256="b" * 64)
    family = {r["work_key"]: fio.family_source_ids({"member_record_ids": f"t1810-repec-local/2026-10-08:{handle}"})}
    assert fio.write_chunks(str(tmp_path), [r], [proof], _config(), family)["proven"] == 1
    assert not fio.valid_public_proof(r, dict(proof, source_manifest_sha256=""), family[r["work_key"]])
    assert not fio.valid_public_proof(r, {"work_key": r["work_key"], "public": True,
                                       "full_sixfield_sha256": fio.proof_hash(r)}, family[r["work_key"]])



def test_redif_mixed_field_proof_carries_archive_on_source_witness():
    import _rel_facet_io as fio
    r = _record()
    handle = "RePEc:ags:feemdp:59418"
    proof = _typed_proof(r, handle, "repec_redif")
    for binding in proof["field_evidence"].values():
        binding["sources"][0].update(source_archive="ags/feemdp/feemdp.redif", source_manifest_sha256="b" * 64)
    family = {f"repec_redif:{handle}"}
    assert fio.valid_public_proof(r, proof, family)
    proof["field_evidence"]["abstract"]["sources"][0]["source_manifest_sha256"] = ""
    assert not fio.valid_public_proof(r, proof, family)


def test_legacy_proof_must_belong_to_actual_pool_family():
    import _rel_facet_io as fio
    r = _record(openalex_id="W999")
    proof = _proof(r)
    assert not fio.valid_public_proof(r, proof, {"openalex:W1"})
    assert fio.valid_public_proof(r, proof, {"openalex:W1", "openalex:W999"})
    genuine = _record()
    assert fio.valid_public_proof(genuine, _proof(genuine), {"openalex:W1"})


@pytest.mark.parametrize("score", [.7, .5])
def test_persisted_effective_score_schema_and_guard_relation_rechecked(tmp_path, score):
    import _rel_facet_io as fio
    import _rel_view as rv
    from test_corpus_rel_view import RULE, WINDOW, _work
    raw, labels, _, _ = _parsed(tmp_path, [_record()], [answer(scores=(0, 1, 1))])
    a = json.loads(raw[0]["effective_answer"])
    a["finance"] = score
    a["finance_evidence"] = "insufficient: altered persisted judgment"
    raw[0]["effective_answer"] = fio.encoded(a)
    rows, _ = rv.build_view([_work("openalex:W1")], labels, WINDOW, RULE)
    with pytest.raises(ValueError, match="persisted effective|guard derivation"):
        fio.assign_view(rows, raw)



def test_explicit_empty_family_map_never_uses_canonical_fallback(tmp_path):
    import _rel_facet_io as fio
    r = _record()
    denied = fio.write_chunks(str(tmp_path / "denied"), [r], [_proof(r)], _config(), {})
    assert denied["proven"] == 0 and denied["unproven"] == [r["work_key"]]
    approved = fio.write_chunks(str(tmp_path / "standalone"), [r], [_proof(r)], _config())
    assert approved["proven"] == 1
