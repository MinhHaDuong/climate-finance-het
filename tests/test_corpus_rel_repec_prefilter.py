"""Ticket 1810 step 5: the recall pre-filter keeps every known ICF work."""

import csv
import json

import corpus_rel_prefilter_labels as labels
import corpus_rel_repec_prefilter as pf
import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.domain_corpus


def test_threshold_keeps_every_known_icf_score():
    t = pf.choose_threshold([0.1, 0.62, 0.3], [0.7])
    assert t == 0.7
    assert not pf.dropped(0.7, t) and pf.dropped(0.7001, t)


def test_measure_counts_icf_lost_and_weighted_share():
    items = [{"label": "icf", "p_out": 0.2, "weight": "1"},
             {"label": "out", "p_out": 0.99, "weight": "3"},
             {"label": "aux", "p_out": 0.5, "weight": "1"}]
    m = pf._measure(items, 0.9)
    assert m["icf_lost"] == 0 and m["dropped"] == 1 and m["out_recall"] == 1.0
    assert m["weighted_share_dropped"] == 0.6


def test_opus_summary_rule_of_three():
    res = [{"key": str(i), "stratum": "drop", "label": "out"} for i in range(100)]
    res += [{"key": "k", "stratum": "keep", "label": "icf"}]
    s = pf.opus_summary(res)
    assert s["drop"]["icf"] == 0 and s["drop"]["icf_rate_upper95"] == 0.03
    assert s["keep"]["icf_keys"] == ["k"]


def test_opus_prompt_keeps_titles_with_full_stops():
    p = pf.opus_prompt("R:\n{answer_format}\n{records}", [{"title": "U.S. aid. A study",
                                                        "abstract": "Text"}], 220, 650)
    assert "Title: U.S. aid. A study" in p and "Abstract: Text" in p and "n|label|doc" in p


def test_build_texts_never_trains_on_validation(tmp_path):
    pool = tmp_path / "pool.csv"
    pd.DataFrame([
        {"work_key": "openalex:W1", "openalex_id": "W1", "doi": "", "title": "A", "abstract": "a"},
        {"work_key": "openalex:W2", "openalex_id": "W2", "doi": "", "title": "B", "abstract": ""},
        {"work_key": "openalex:W3", "openalex_id": "W3", "doi": "10.1000/x", "title": "C", "abstract": "c"},
    ]).to_csv(pool, index=False)
    screen = tmp_path / "screen.csv"
    pd.DataFrame([
        {"work_key": "openalex:W1", "openalex_id": "W1", "stage": "2", "model": "claude-code-subagent:opus",
         "label": "icf", "labelled_at": "1", "source": "x/stage2/chunk01.opus.txt"},
        {"work_key": "openalex:W2", "openalex_id": "W2", "stage": "2", "model": "claude-code-subagent:opus",
         "label": "out", "labelled_at": "1", "source": "x/pilot_opus.json"},
        {"work_key": "openalex:W3", "openalex_id": "W3", "stage": "1", "model": "qwen",
         "label": "out", "labelled_at": "1", "source": "q"},
    ]).to_csv(screen, index=False)
    lab = tmp_path / "labels.csv"
    pd.DataFrame([{"openalex_id": "W1", "label": "aux", "label_source": "ref", "split": "heldout",
                   "stratum": "", "weight": "2"}]).to_csv(lab, index=False)
    sen = tmp_path / "sen.csv"
    pd.DataFrame([{"sentinel": "S1", "set": "holdout", "openalex_id": "", "doi": "10.1000/X",
                   "title": "C"}]).to_csv(sen, index=False)
    d = tmp_path / "deliv"
    d.mkdir()
    pd.DataFrame([{"record_id": "RePEc:a:b:1", "query_id": "Q", "doc_type": "article",
                   "title": "T. x", "abstract": "ab"}]).to_csv(d / "records.csv", index=False)
    pd.DataFrame([{"record_id": "RePEc:a:b:2", "query_id": "Q", "reason": "no_dedup_key",
                   "title": "Only title", "note": ""}]).to_csv(d / "excluded.csv", index=False)
    rec_sen = tmp_path / "recall.sentinels.csv"
    pd.DataFrame([{"file": "sen.csv", "sentinel": "S1", "set": "holdout", "retrieved": True,
                   "handles": "RePEc:a:b:1"}]).to_csv(rec_sen, index=False)
    rows = pf.build_texts(str(pool), str(screen), str(lab), str(d), [str(sen)], str(rec_sen))
    sr = [r for r in rows if r["role"] == "sentinel_repec"]
    assert [(r["key"], r["stratum"], r["text"]) for r in sr] == [("sen.csv:S1:RePEc:a:b:1", "holdout", "T. x. ab")]
    roles = {(r["key"], r["role"]) for r in rows}
    assert ("openalex:W1", "heldout") in roles and ("openalex:W1", "train") not in roles
    assert ("openalex:W2", "control") in roles
    s = [r for r in rows if r["role"] == "sentinel"][0]
    assert s["text"] == "C. c" and s["stratum"] == "holdout"
    rep = [r for r in rows if r["role"] == "repec"]
    assert [r["key"] for r in rep] == ["RePEc:a:b:1", "RePEc:a:b:2"]
    assert rep[0]["title"] == "T. x"


def test_fit_threshold_loses_no_training_icf(tmp_path):
    rng = np.random.default_rng(0)
    rows, keys, vecs = [], [], []
    for i in range(120):
        lab = ["icf", "aux", "out"][i % 3]
        v = rng.normal(size=8) + (3 if lab == "out" else 0)
        rows.append({"key": f"k{i}", "role": "train", "label": lab, "source": "s", "weight": "",
                     "stratum": "", "text": "t"})
        keys.append(f"k{i}\ttrain")
        vecs.append(v / np.linalg.norm(v))
    rows.append({"key": "r1", "role": "repec", "label": "", "source": "Q", "weight": "",
                 "stratum": "article", "text": "t"})
    keys.append("r1\trepec")
    vecs.append(np.ones(8) / np.sqrt(8))
    tp = tmp_path / "texts.jsonl"
    tp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    ep = tmp_path / "emb.npz"
    np.savez(ep, vectors=np.array(vecs, dtype=np.float32), keys=np.array(keys, dtype=object))
    rep = pf.fit(str(tp), str(ep), str(tmp_path / "m"))
    assert rep["train"]["icf_lost"] == 0
    assert len(rep["model_sha256"]) == 64
    sc = list(csv.DictReader(open(tmp_path / "m" / "scores.csv")))
    assert {r["role"] for r in sc} == {"repec", "train_oof"}


def test_label_register_prefers_adjudicated(tmp_path):
    a = tmp_path
    (a / "router").mkdir()
    (a / "reference").mkdir()
    (a / "router" / "sample.jsonl").write_text(
        json.dumps({"openalex_id": "W1", "stratum": "out|en", "weight": 5}) + "\n"
        + json.dumps({"openalex_id": "W2", "stratum": "icf|en", "weight": 2}) + "\n")
    (a / "router" / "opus_labels.jsonl").write_text(
        json.dumps({"openalex_id": "W1", "label": "out"}) + "\n"
        + json.dumps({"openalex_id": "W2", "label": "icf"}) + "\n")
    (a / "reference" / "adjudicated.jsonl").write_text(
        json.dumps({"openalex_id": "W1", "label": "aux", "split": "heldout", "ref_stratum": "random:out|en",
                    "weight": 5}) + "\n")
    rows = labels.build(str(a))
    assert [(r["openalex_id"], r["label"], r["split"]) for r in rows] == [
        ("W1", "aux", "heldout"), ("W2", "icf", "train")]


def test_sentinel_works_never_train(tmp_path):
    """Replays the PR 1640 defect: a reserve sentinel that is also a register
    training row was scored in-sample."""
    pool = tmp_path / "pool.csv"
    pd.DataFrame([
        {"work_key": "openalex:W1", "openalex_id": "W1", "doi": "", "title": "A", "abstract": "a"},
        {"work_key": "openalex:W2", "openalex_id": "W2", "doi": "10.1000/s", "title": "B", "abstract": "b"},
    ]).to_csv(pool, index=False)
    screen = tmp_path / "screen.csv"
    pd.DataFrame([{"work_key": "openalex:W2", "openalex_id": "W2", "stage": "2",
                   "model": "claude-code-subagent:opus", "label": "icf", "labelled_at": "1",
                   "source": "x/chunk01.opus.txt"}]).to_csv(screen, index=False)
    lab = tmp_path / "labels.csv"
    pd.DataFrame([{"openalex_id": "W1", "label": "icf", "label_source": "ref", "split": "train",
                   "stratum": "topup:sentinel-a", "weight": ""}]).to_csv(lab, index=False)
    sen = tmp_path / "sen.csv"
    pd.DataFrame([{"sentinel": "S1", "set": "holdout", "openalex_id": "W1", "doi": "", "title": "A"},
                  {"sentinel": "S2", "set": "tuning", "openalex_id": "", "doi": "10.1000/S",
                   "title": "B"}]).to_csv(sen, index=False)
    rows = pf.build_texts(str(pool), str(screen), str(lab), None, [str(sen)])
    assert [r for r in rows if r["role"] == "train"] == []
    assert sorted(r["stratum"] for r in rows if r["role"] == "sentinel") == ["holdout", "tuning"]


def test_remap_and_rescore_reuse_the_old_sample(tmp_path):
    old = tmp_path / "old.jsonl"
    new = tmp_path / "new.jsonl"
    old.write_text("".join(json.dumps(r) + "\n" for r in [
        {"key": "RePEc:zbw:hwware:1 #END", "role": "repec", "text": "x"},
        {"key": "RePEc:aaa:bbb:2", "role": "repec", "text": "old text"},
        {"key": "RePEc:aaa:bbb:3", "role": "repec", "text": "y"}]))
    new.write_text("".join(json.dumps(r) + "\n" for r in [
        {"key": "RePEc:zbw:hwware:1", "role": "repec", "text": "x"},
        {"key": "RePEc:aaa:bbb:2", "role": "repec", "text": "new text"}]))
    npz = tmp_path / "e.npz"
    np.savez(npz, vectors=np.ones((3, 2), dtype=np.float32),
             keys=np.array(["RePEc:zbw:hwware:1 #END\trepec", "RePEc:aaa:bbb:2\trepec",
                            "RePEc:aaa:bbb:3\trepec"], dtype=object))
    c = pf.remap_embeddings(str(npz), str(old), str(new), str(tmp_path / "out.npz"))
    assert c == {"kept": 1, "text_changed": 1, "absent_from_new_delivery": 1}
    z = np.load(tmp_path / "out.npz", allow_pickle=True)
    assert list(z["keys"]) == ["RePEc:zbw:hwware:1\trepec"]
    sc = tmp_path / "scores.csv"
    pd.DataFrame([{"key": "RePEc:zbw:hwware:1", "role": "repec", "drop": 0},
                  {"key": "RePEc:aaa:bbb:4", "role": "repec", "drop": 1}]).to_csv(sc, index=False)
    res = [{"key": "RePEc:zbw:hwware:1 #END", "stratum": "drop", "label": "out"},
           {"key": "RePEc:aaa:bbb:4", "stratum": "drop", "label": "icf"},
           {"key": "RePEc:aaa:bbb:9", "stratum": "keep", "label": "aux"}]
    s = pf.opus_rescore(res, str(sc))
    assert s["not_scored"] == 1
    assert s["old_drop__new_keep"]["n"] == 1 and s["old_drop__new_drop"]["icf"] == 1
