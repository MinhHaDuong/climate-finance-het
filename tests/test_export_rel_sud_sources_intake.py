"""Ticket 1653 delivery to the REL pool: the exporter meets the intake contract."""

import csv
import json
import os

import export_rel_sud_sources_intake as ex
import pytest
import qa_rel_intake

pytestmark = pytest.mark.domain_corpus

REG = ["query_id", "source", "route", "endpoint", "query_string", "run_at",
       "n_expected", "n_received", "n_matched", "completed", "stop_reason"]
CAND = ["source", "query_id", "query_string", "route", "endpoint", "run_at",
        "export_file", "record_id", "url", "doi", "title", "authors", "year",
        "language", "venue", "doc_type", "abstract", "matched_terms"]
LANGS = {"clacso": ["es", "pt"], "scielo": ["es", "pt", "en"]}
T = "2026-09-30T13:00:00+00:00"


def write(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def cand(source, qid, rid, route="api", **kw):
    return {"source": source, "query_id": qid, "route": route, "run_at": T,
            "export_file": f"raw/{source}.jsonl.gz", "record_id": rid,
            "title": f"Title {rid}", "authors": "Doe, J.; Roe, R.", "year": "2019",
            "language": "spa", **kw}


@pytest.fixture
def runs(tmp_path):
    a = tmp_path / "latam"
    write(str(a / "registry.csv"), REG, [
        {"query_id": "S-clacso-es-T1", "source": "clacso", "route": "api",
         "query_string": "query=\"financiamiento climático\"", "run_at": T,
         "n_expected": "3", "n_received": "3", "n_matched": "3", "completed": "True"},
        {"query_id": "S-clacso-es-T2", "source": "clacso", "route": "api",
         "query_string": "query=\"REDD\"", "run_at": T, "n_expected": "1",
         "n_received": "1", "n_matched": "1", "completed": "True"},
        {"query_id": "S-uwi-en-T1", "source": "uwi", "route": "api", "query_string": "q",
         "run_at": T, "n_expected": "1", "n_received": "1", "n_matched": "1",
         "completed": "True"},
    ])
    write(str(a / "candidates.csv"), CAND, [
        cand("clacso", "S-clacso-es-T1", "hdl:1", matched_terms="financiamiento climático"),
        cand("clacso", "S-clacso-es-T1", "hdl:2", year="", doi="",
             url="info:doi/10.1234/ABC.9"),
        cand("clacso", "S-clacso-es-T1", "hdl:3", year="", url="https://x/3"),
        cand("clacso", "S-clacso-es-T2", "hdl:1"),  # the same item again
        cand("uwi", "S-uwi-en-T1", "hdl:9"),
    ])
    b = tmp_path / "scielo"
    write(str(b / "registry.csv"), REG, [
        {"query_id": "S-scielo-mex-0185", "source": "scielo", "route": "oai-pmh",
         "query_string": "OAI-PMH ListRecords set=0185", "run_at": T, "n_expected": "",
         "n_received": "500", "n_matched": "1", "completed": "False",
         "stop_reason": "error: bad xml"},
    ])
    write(str(b / "candidates.csv"), CAND, [
        cand("scielo", "S-scielo-mex-0185", "oai:scielo:1", route="oai-pmh",
             matched_terms="financiamiento climático", doi="10.5555/x.1"),
    ])
    write(str(a / "year_enrichment.csv"), ex.ENRICHMENT_FIELDS,
          [{"record_id": "hdl:3", "year": "", "source_url": "u", "fetched_at": T,
            "status": "no date"}])
    return tmp_path, [(str(a), {"clacso"}), (str(b), None)]


def test_search_routes_deliver_every_hit_deduplicated_in_lane(runs):
    root, spec = runs
    records, registry, excluded, stats = ex.build(spec, root=str(root), languages=LANGS)
    ids = [r["record_id"] for r in records]
    assert ids == ["clacso:hdl:1", "clacso:hdl:2", "scielo:oai:scielo:1"]  # hdl:3 has no key
    assert "uwi" not in {r["platform"] for r in records}  # source filter honoured
    assert excluded[:1] == [{"record_id": "clacso:hdl:1", "query_id": "S-clacso-es-T2",
                         "reason": "duplicate_in_lane", "title": "Title hdl:1",
                         "note": "also retrieved by S-clacso-es-T1"}]
    first = records[0]
    assert first["query_ids_all"] == "S-clacso-es-T1; S-clacso-es-T2"
    assert first["lane_status"] == "lexicon_match" and first["language"] == "es"
    assert first["first_author"] == "Doe, J." and first["all_authors"] == "Doe, J.; Roe, R."
    assert records[1]["lane_status"] == "no_lexicon_match"  # information, never a filter


def test_harvest_route_counts_the_lexicon_match_as_what_the_query_returned(runs):
    root, spec = runs
    _, registry, _, _ = ex.build(spec, root=str(root), languages=LANGS)
    row = next(r for r in registry if r["platform"] == "scielo")
    assert row["n_received"] == "1" and row["n_expected"] == "500"
    assert row["completed"] == "false" and row["stop_reason"] == "error: bad xml"
    assert "local 1530 lexicon match on title+abstract" in row["query"]
    assert "languages es/pt/en" in row["query"]
    search = next(r for r in registry if r["query_id"] == "S-clacso-es-T1")
    assert search["n_received"] == "3" and "lexicon" not in search["query"]


def test_doi_from_url_and_records_without_any_identifier_are_listed_not_dropped(runs):
    root, spec = runs
    records, registry, excluded, stats = ex.build(spec, root=str(root), languages=LANGS)
    by = {r["record_id"]: r for r in records}
    assert by["clacso:hdl:2"]["doi"] == "10.1234/abc.9"
    assert "DOI read from the record URL" in by["clacso:hdl:2"]["lane_note"]
    assert "clacso:hdl:3" not in by
    [row] = [e for e in excluded if e["reason"] == "not_retrievable"]
    assert row["record_id"] == "clacso:hdl:3"
    assert row["note"] == ex.NO_KEY_NOTE + "; Handle recorded: https://hdl.handle.net/3"
    assert row["url"] == "https://x/3" and row["platform_record_id"] == "hdl:3"
    assert stats["no_doi_no_year"] == 1 and stats["doi_from_url"] == 1
    t1 = next(r for r in registry if r["query_id"] == "S-clacso-es-T1")
    assert t1["n_delivered"] == 2


def test_enrichment_year_fills_a_record_with_neither_doi_nor_year(runs):
    root, spec = runs
    write(os.path.join(spec[0][0], "year_enrichment.csv"), ex.ENRICHMENT_FIELDS,
          [{"record_id": "hdl:3", "year": "2012", "source_url": "https://d/3",
            "fetched_at": T, "status": "ok"}])
    records, _, _, stats = ex.build(spec, root=str(root), languages=LANGS)
    rec = next(r for r in records if r["record_id"] == "clacso:hdl:3")
    assert rec["year"] == "2012" and "year from https://d/3" in rec["lane_note"]
    assert stats["no_doi_no_year"] == 0


def test_no_key_note_names_the_handle_and_the_oai_identifier():
    rec = {"platform_record_id": "hdl:2139/51529", "platform": "uwi", "url": ""}
    assert ex.no_key_note(rec).endswith(
        "Handle recorded: https://hdl.handle.net/2139/51529; "
        "OAI identifier oai:uwispace.sta.uwi.edu:2139/51529")
    page = {"platform_record_id": "https://c/p", "platform": "ceew", "url": "https://c/p"}
    assert ex.no_key_note(page).endswith("stable URL recorded: https://c/p")


def test_contract_columns_are_the_checkers():
    assert ex.RECORD_COLUMNS == qa_rel_intake.RECORD_COLUMNS
    assert ex.EXCLUDED_COLUMNS == qa_rel_intake.EXCLUDED_COLUMNS


def test_export_writes_a_delivery_the_checker_accepts(runs, tmp_path):
    root, spec = runs
    write(os.path.join(spec[0][0], "year_enrichment.csv"), ex.ENRICHMENT_FIELDS,
          [{"record_id": "hdl:3", "year": "2012", "source_url": "https://d/3",
            "fetched_at": T, "status": "ok"}])
    status = tmp_path / "status.yaml"
    status.write_text(
        "sources:\n"
        "  clacso: {status: run, reason: ok, stratum: LAC}\n"
        "  scielo: {status: partial, reason: 'Brazil 404', stratum: LAC,\n"
        "           needs_human: 'SciELO OAI access'}\n"
        "  cnki: {status: impossible, reason: 'robots', stratum: China,\n"
        "         needs_human: 'bibCNRS export'}\n"
        "unreviewed_languages: [zh, ru]\n", encoding="utf-8")
    sentinels = tmp_path / "sentinels.csv"
    write(str(sentinels), ["sentinel", "class", "title", "doi"],
          [{"sentinel": "S01", "class": "b", "title": "Title hdl:2"},
           {"sentinel": "S02", "class": "b", "title": "Absent ... work"}])
    out = tmp_path / "data" / "rel_intake" / ex.LANE / "2026-09-30"
    args = [f"--run={d}:{','.join(sorted(s))}" if s else f"--run={d}" for d, s in spec]
    assert ex.main(["export", *args, "--root", str(root), "--output-dir", str(out),
                    "--status", str(status), "--sentinels", str(sentinels),
                    "--commit", "abc123", "--machine", "test"]) == 0
    assert qa_rel_intake.check_delivery(str(out)) == []
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["coverage"] == "incomplete"
    assert man["counts"]["records"] == 4
    assert man["counts"]["excluded"] == {"duplicate_in_lane": 1}
    units = [i["unit"] for i in man["incomplete"]]
    assert units[:2] == ["scielo (LAC)", "cnki (China)"]
    assert any("zh, ru" in u for u in units)
    assert {n["item"] for n in man["needs_human"]} >= {"SciELO OAI access", "bibCNRS export"}
    with open(out / "sentinels.csv", encoding="utf-8") as fh:
        found = {r["sentinel"]: r["found"] for r in csv.DictReader(fh)}
    assert found == {"S01": "True", "S02": "False"}


def test_a_record_without_doi_or_year_passes_the_checker_as_an_exclusion(runs, tmp_path):
    """Listed in excluded.csv, counted and explained in the manifest."""
    root, spec = runs
    status = tmp_path / "status.yaml"
    status.write_text("sources: {}\nunreviewed_languages: [zh]\n", encoding="utf-8")
    sentinels = tmp_path / "s.csv"
    write(str(sentinels), ["sentinel", "class", "title", "doi"], [])
    out = tmp_path / "data" / "rel_intake" / ex.LANE / "2026-09-30"
    ex.main(["export", f"--run={spec[0][0]}:clacso", "--output-dir", str(out),
             "--status", str(status), "--sentinels", str(sentinels),
             "--commit", "abc", "--machine", "t"])
    assert qa_rel_intake.check_delivery(str(out)) == []
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["counts"]["no_doi_no_openalex_no_year"] == 1
    assert man["counts"]["excluded"] == {"duplicate_in_lane": 1, "not_retrievable": 1}
    assert "1 record(s) carry no DOI" in man["notes"] and "bends" in man["notes"]
