"""Identifiers hidden in EDS accession numbers and their mirror check (ticket 2040); offline."""

import gzip
import json

import _rel_eds_ids as ids
import catalog_rel_eds_repec_handles as hand
import pytest

pytestmark = pytest.mark.domain_corpus


def _index(*handles):
    idx, series = {}, set()
    for h in handles:
        k = ids.mirror_key(h)
        idx.setdefault(k, set()).add(h)
        series.add(k[:2])
    return idx, series


def test_a_paper_number_decodes_to_its_handle_exactly():
    d = ids.decode_edsrep("edsrep.p.nbr.nberwo.35497")
    assert d["candidate"] == "RePEc:nbr:nberwo:35497" and d["kind"] == "paper"
    assert (d["archive"], d["series"]) == ("nbr", "nberwo")


def test_an_article_item_without_colons_matches_the_mirror_handle_that_has_them():
    # EDS drops the colons of the item: the mirror spelling is recovered, not guessed
    mirror = "RePEc:eee:wdevel:v:152:y:2022:i:c:s0305750x21003995"
    idx, series = _index(mirror, "RePEc:eee:wdevel:v:153:y:2022:i:c:s1")
    d = ids.decode_edsrep("edsrep.a.eee.wdevel.v152y2022ics0305750x21003995")
    assert ids.resolve(d, idx, series=series) == (ids.STATUS_MATCHED, mirror)


def test_unmatched_ambiguous_and_absent_series_are_labelled_not_dropped():
    idx, series = _index("RePEc:aaa:ser:a:1", "RePEc:aaa:ser:a-1", "RePEc:aaa:ser:b")
    r = lambda an: ids.resolve(ids.decode_edsrep(an), idx, series=series)[0]
    assert r("edsrep.a.aaa.ser.a1") == ids.STATUS_AMBIGUOUS
    assert r("edsrep.a.aaa.ser.zzz") == ids.STATUS_UNMATCHED
    assert r("edsrep.a.aaa.other.b") == ids.STATUS_NO_SERIES
    assert ids.resolve(ids.decode_edsrep("EDSZBW1968531777"), idx)[0] == ids.STATUS_UNDECODABLE


def test_zbw_numbers_are_checked_as_catalogue_numbers():
    assert ids.ppn_valid("EDSZBW1968531777") and ids.ppn_valid("EDSZBW185231947X")
    assert not ids.ppn_valid("EDSZBW1968531778") and not ids.ppn_valid("edsrep.p.a.b.c")


def _mirror(tmp_path, handles):
    d = tmp_path / "mirror" / "nbr" / "nberwo"
    d.mkdir(parents=True)
    body = "".join(f"Template-Type: ReDIF-Paper 1.0\nTitle: t\nHandle: {h}\n\n" for h in handles)
    (d / "nberwo2020.rdf").write_text(body)
    (d / "nberwo2020.rdf~").write_text("Template-Type: ReDIF-Paper 1.0\nHandle: RePEc:nbr:nberwo:777\n")
    return tmp_path / "mirror"


def _results(tmp_path, ans):
    p = tmp_path / "results.jsonl.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        for an in ans:
            fh.write(json.dumps({"eds_an": an, "search_id": "EDS-RePEc-x", "doi": ""}) + "\n")
    return str(p)


def test_run_writes_counts_after_the_positive_control_and_skips_backup_files(tmp_path):
    mirror = _mirror(tmp_path, ["RePEc:nbr:nberwo:35497", "RePEc:nbr:nberwo:28000"])
    res = _results(tmp_path, ["edsrep.p.nbr.nberwo.28000", "edsrep.p.nbr.nberwo.777", "EDSZBW1968531777"])
    out = tmp_path / "out"
    assert hand.main(["--results", res, "--mirror", str(mirror), "--output-dir", str(out)]) == 0
    summary = json.loads((out / "eds_repec_handles.json").read_text())
    assert summary["controls"]["positive"]["handle"] == "RePEc:nbr:nberwo:35497"
    assert summary["status_distinct"] == {"matched": 1, "unmatched": 1}  # 777 only in the ~ backup
    assert summary["zbw_ppn_check_digit_valid"] == 1


def test_run_stops_without_a_count_when_the_positive_control_fails(tmp_path):
    mirror = _mirror(tmp_path, ["RePEc:nbr:nberwo:28000"])  # control record absent
    res = _results(tmp_path, ["edsrep.p.nbr.nberwo.28000"])
    out = tmp_path / "out"
    assert hand.main(["--results", res, "--mirror", str(mirror), "--output-dir", str(out)]) == 1
    assert not (out / "eds_repec_handles.json").exists()
