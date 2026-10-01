"""Recall pre-filter for the RePEc lane: embeddings + logistic regression (ticket 1810, step 5).

Purpose, author decision of 2026-09-30: the full RePEc mirror is too large for
the stage-1 screen, so a light classifier trained mainly on Opus labels may
drop records it is confident are *hors sujet* ("out"). It never admits
anything: every record it keeps still goes through stage 1 and stage 2 like
any other pool record. The threshold is set so that no ICF-labelled training
work (out of fold) and no tuning sentinel would have been dropped; reserve
(hold-out) sentinels, the Jev-pilot held-out reference set and the 200-work
control set are only measured, never used to set it.

How this differs from the refined-corpus v2 filter, which dropped 122 ICF
works out of 489 later re-read: v2 scored a fixed query ("climate policy and
financial mechanisms") with a reranker and cut at a threshold chosen for
precision of the whole corpus; this model is fitted to the review's own ICF
labels, predicts "out" rather than relevance, and its threshold is the
largest one that loses zero known ICF works, so it trades share dropped for
recall by construction.

Subcommands (padme for texts/embed/fit; the Opus sample anywhere with the key):

- ``texts``  build ``texts.jsonl``: training and validation works from the pool
             (Opus stage-2 labels of ``icf_screen``, ``config/rel_prefilter_labels.csv``),
             sentinels, and the lane's delivered records;
- ``embed``  bge-m3 on CPU (``CUDA_VISIBLE_DEVICES`` is forced empty), resumable
             blocks, throughput logged;
- ``fit``    5-fold out-of-fold scores, threshold, validation measures, the frozen
             model (``model.npz`` + sha256) and ``scores.csv`` for the delivered records;
- ``opus-sample``: a fresh Opus sample of delivered records,
             stratified by the drop decision, against distribution shift.

Text of a work: ``title + ". " + abstract[:2000]`` (as the Jev-pilot router).
Label target: 1 when the Opus (or adjudicated) label is ``out``.
"""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

from utils import get_logger

log = get_logger('rel_repec_prefilter')

MODEL_NAME = "BAAI/bge-m3"
MAX_SEQ = 256
BLOCK = 512
ABSTRACT_CHARS = 2000
OPUS_MODEL = "anthropic/claude-opus-5.5"


def text_of(title: str, abstract: str) -> str:
    t = (title or "").strip()
    a = (abstract or "").strip()[:ABSTRACT_CHARS]
    return f"{t}. {a}" if a else t


def _blank(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v != v:
        return ""
    return str(v)


# --- texts ---------------------------------------------------------------------

def screen_opus_labels(screen_csv: str) -> dict[str, dict]:
    """Last Opus stage-2 label per work_key of ``icf_screen`` (read-only)."""
    import pandas as pd
    s = pd.read_csv(screen_csv, dtype=str, low_memory=False).fillna("")
    s = s[(s.stage == "2") & s.model.str.contains("opus", case=False)]
    s = s.sort_values("labelled_at")
    out = {}
    for _, r in s.iterrows():
        out[r.work_key] = {"label": r.label, "openalex_id": r.openalex_id,
                           "control": r.source.endswith("pilot_opus.json")}
    return out


def build_texts(pool_csv: str, screen_csv: str, labels_csv: str, delivery: str | None,
                sentinel_files: list[str], recall_sentinels: str | None = None) -> list[dict]:
    import pandas as pd
    pool = pd.read_csv(pool_csv, dtype=str, low_memory=False,
                       usecols=["work_key", "openalex_id", "doi", "title", "abstract"]).fillna("")
    by_key = {r.work_key: r for r in pool.itertuples()}
    by_oa = {r.openalex_id: r for r in pool.itertuples() if r.openalex_id}
    by_doi = {r.doi.lower(): r for r in pool.itertuples() if r.doi}
    out: list[dict] = []
    held = set()
    reg = pd.read_csv(labels_csv, dtype=str).fillna("")
    for r in reg.itertuples():
        p = by_oa.get(r.openalex_id)
        if p is None:
            continue
        role = "heldout" if r.split == "heldout" else "train"
        if role == "heldout":
            held.add(p.work_key)
        out.append({"key": p.work_key, "role": role, "label": r.label, "source": r.label_source,
                    "weight": r.weight, "stratum": r.stratum, "text": text_of(p.title, p.abstract)})
    seen = {(o["key"], o["role"]) for o in out}
    for wk, v in screen_opus_labels(screen_csv).items():
        p = by_key.get(wk) or by_oa.get(v["openalex_id"])
        if p is None:
            continue
        role = "control" if v["control"] else "train"
        if role == "train" and (p.work_key in held or (p.work_key, "train") in seen):
            continue
        if role == "control":
            held.add(p.work_key)
        seen.add((p.work_key, role))
        out.append({"key": p.work_key, "role": role, "label": v["label"], "source": "icf_screen_opus",
                    "weight": "", "stratum": "", "text": text_of(p.title, p.abstract)})
    # a work used for validation is never trained on
    out = [o for o in out if not (o["role"] == "train" and o["key"] in held)]
    sentinel_works = set()
    for path in sentinel_files:
        for s in csv.DictReader(open(path, encoding="utf-8")):
            p = by_oa.get(s.get("openalex_id", "")) or by_doi.get((s.get("doi") or "").lower())
            if p is not None:
                sentinel_works.add(p.work_key)
            text = text_of(p.title, p.abstract) if p is not None else text_of(s.get("title", ""), "")
            out.append({"key": f"sentinel:{os.path.basename(path)}:{s['sentinel']}", "role": "sentinel",
                        "label": "icf", "source": os.path.basename(path),
                        "weight": "", "stratum": s.get("set", ""), "text": text,
                        "has_abstract": bool(p is not None and p.abstract)})
    # a sentinel work is validation, every sentinel set included: never a training row
    out = [o for o in out if not (o["role"] == "train" and o["key"] in sentinel_works)]
    return out + (delivery_texts(delivery, recall_sentinels) if delivery else [])


def delivery_texts(delivery: str, recall_sentinels: str | None = None) -> list[dict]:
    """The lane's delivered records (role ``repec``, ``no_dedup_key`` rows
    included) and, with ``recall_sentinels``, its record of each retrieved
    sentinel (role ``sentinel_repec``)."""
    import pandas as pd
    out: list[dict] = []
    rec = pd.read_csv(os.path.join(delivery, "records.csv"), dtype=str, low_memory=False).fillna("")
    for r in rec.itertuples():
        out.append({"key": r.record_id, "role": "repec", "label": "", "source": r.query_id,
                    "weight": "", "stratum": r.doc_type, "text": text_of(r.title, r.abstract),
                    "title": r.title, "abstract": r.abstract})
    if recall_sentinels:
        # the lane's own record of each retrieved sentinel, scored as the pre-filter would see it
        recs = {r.record_id: r for r in rec.itertuples()}
        for s in csv.DictReader(open(recall_sentinels, encoding="utf-8")):
            for h in (s.get("handles") or "").split("|"):
                r = recs.get(h)
                if r is not None and s.get("retrieved") == "True":
                    out.append({"key": f"{s['file']}:{s['sentinel']}:{h}", "role": "sentinel_repec",
                                "label": "icf", "source": s["file"], "weight": "",
                                "stratum": s.get("set", ""), "text": text_of(r.title, r.abstract)})
    exc = pd.read_csv(os.path.join(delivery, "excluded.csv"), dtype=str).fillna("")
    for r in exc[exc.reason == "no_dedup_key"].itertuples():
        out.append({"key": r.record_id, "role": "repec", "label": "", "source": r.query_id,
                    "weight": "", "stratum": "no_dedup_key", "text": text_of(r.title, ""),
                    "title": r.title, "abstract": ""})
    return out


# --- embeddings ------------------------------------------------------------------

def embed(texts_path: str, out_dir: str, limit: int | None = None, threads: int | None = None,
          roles: set[str] | None = None) -> dict:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer

    rows = [json.loads(line) for line in open(texts_path, encoding="utf-8")]
    if roles:
        rows = [r for r in rows if r["role"] in roles]
    if limit:
        rows = random.Random(1810).sample(rows, min(limit, len(rows)))
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]["text"]))
    torch.set_num_threads(threads or os.cpu_count() or 4)
    model = SentenceTransformer(MODEL_NAME, device="cpu")
    model.max_seq_length = MAX_SEQ
    parts = os.path.join(out_dir, "parts")
    os.makedirs(parts, exist_ok=True)
    t_all, n_new = time.time(), 0
    for b in range(0, len(order), BLOCK):
        f = os.path.join(parts, f"part{b // BLOCK:05d}.npz")
        if os.path.exists(f):
            continue
        idx = order[b:b + BLOCK]
        t0 = time.time()
        v = model.encode([rows[i]["text"] for i in idx], batch_size=32, normalize_embeddings=True,
                         show_progress_bar=False)
        np.savez(f, vectors=v.astype(np.float32),
                 keys=np.array([rows[i]["key"] + "\t" + rows[i]["role"] for i in idx], dtype=object))
        n_new += len(idx)
        log.info(f"block {b // BLOCK} {b + len(idx)}/{len(order)} {time.time() - t0:.1f}s "
              f"{len(idx) / max(time.time() - t0, 1e-9):.1f}/s")
    keys, vecs = [], []
    for f in sorted(os.listdir(parts)):
        z = np.load(os.path.join(parts, f), allow_pickle=True)
        keys += list(z["keys"])
        vecs.append(z["vectors"])
    np.savez(os.path.join(out_dir, "embeddings.npz"), vectors=np.concatenate(vecs),
             keys=np.array(keys, dtype=object))
    el = time.time() - t_all
    stats = {"model": MODEL_NAME, "max_seq_length": MAX_SEQ, "device": "cpu",
             "threads": threads or os.cpu_count(), "texts": len(order), "encoded_this_run": n_new,
             "seconds_this_run": round(el, 1),
             "texts_per_second": round(n_new / el, 2) if n_new else None,
             "mean_chars": round(sum(len(r["text"]) for r in rows) / max(1, len(rows)), 1)}
    with open(os.path.join(out_dir, "embed_stats.json"), "w") as fh:
        json.dump(stats, fh, indent=1)
    return stats


# --- fit, threshold, measures ------------------------------------------------------

def choose_threshold(p_out_icf: list[float], p_out_guard: list[float], margin: float = 0.0) -> float:
    """Drop when p_out > threshold; the threshold is the largest score of any
    ICF-labelled training work (out of fold) or tuning sentinel, plus a margin.
    Nothing at or below a known ICF score is dropped."""
    scores = list(p_out_icf) + list(p_out_guard)
    return (max(scores) if scores else 1.0) + margin


def dropped(p: float, t: float) -> bool:
    return p > t


def _measure(items: list[dict], t: float) -> dict:
    lab = Counter(i["label"] for i in items)
    drop = [i for i in items if dropped(i["p_out"], t)]
    dl = Counter(i["label"] for i in drop)
    w = [float(i["weight"]) if i.get("weight") else 1.0 for i in items]
    wd = sum(wi for wi, i in zip(w, items) if dropped(i["p_out"], t))
    return {"n": len(items), "labels": dict(lab), "dropped": len(drop), "dropped_by_label": dict(dl),
            "icf_lost": dl.get("icf", 0), "out_recall": round(dl.get("out", 0) / max(1, lab.get("out", 0)), 3),
            "share_dropped": round(len(drop) / max(1, len(items)), 3),
            "weighted_share_dropped": round(wd / max(1e-9, sum(w)), 3)}


def fit(texts_path: str, emb_paths: list[str] | str, out_dir: str, seed: int = 1810) -> dict:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold

    rows = [json.loads(line) for line in open(texts_path, encoding="utf-8")]
    E = {}
    for path in [emb_paths] if isinstance(emb_paths, str) else emb_paths:
        z = np.load(path, allow_pickle=True)
        E.update(zip(z["keys"], z["vectors"]))
    for r in rows:
        r["vec"] = E.get(r["key"] + "\t" + r["role"])
    missing = sum(1 for r in rows if r["vec"] is None)
    rows = [r for r in rows if r["vec"] is not None]
    train = [r for r in rows if r["role"] == "train"]
    X = np.stack([r["vec"] for r in train])
    y = np.array([1 if r["label"] == "out" else 0 for r in train])
    C = 1.0
    oof = np.zeros(len(train))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        m = LogisticRegression(C=C, class_weight="balanced", max_iter=2000).fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    for r, p in zip(train, oof):
        r["p_out"] = float(p)
    model = LogisticRegression(C=C, class_weight="balanced", max_iter=2000).fit(X, y)
    for r in rows:
        if r["role"] != "train":
            r["p_out"] = float(model.predict_proba(r["vec"][None, :])[0, 1])
    tuning_sent = [r["p_out"] for r in rows if r["role"] == "sentinel" and r["stratum"] == "tuning"]
    t = choose_threshold([r["p_out"] for r in train if r["label"] == "icf"], tuning_sent)
    os.makedirs(out_dir, exist_ok=True)
    np.savez(os.path.join(out_dir, "model.npz"), coef=model.coef_, intercept=model.intercept_,
             classes=model.classes_, threshold=np.array([t]), C=np.array([C]))
    with open(os.path.join(out_dir, "model.npz"), "rb") as fh:
        model_sha = hashlib.sha256(fh.read()).hexdigest()
    by = defaultdict(list)
    for r in rows:
        by[r["role"]].append(r)
    sent = by["sentinel"]
    rep = {
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding": MODEL_NAME, "max_seq_length": MAX_SEQ, "text": "title + '. ' + abstract[:2000]",
        "classifier": f"LogisticRegression(C={C}, class_weight=balanced), target = label 'out'",
        "threshold": round(t, 6), "rule": "drop when p_out > threshold",
        "model_sha256": model_sha, "rows_without_embedding": missing,
        "train": {**_measure(train, t), "by_source": dict(Counter(r["source"] for r in train))},
        "control_200": _measure(by["control"], t),
        "reference_heldout": _measure(by["heldout"], t),
        "sentinels": {
            s: {"n": len(g), "dropped": [r["key"] for r in g if dropped(r["p_out"], t)],
                "max_p_out": round(max((r["p_out"] for r in g), default=0), 4)}
            for s, g in (("tuning", [r for r in sent if r["stratum"] == "tuning"]),
                         ("reserve", [r for r in sent if r["stratum"] == "holdout"]),
                         ("other", [r for r in sent if r["stratum"] not in ("tuning", "holdout")]))},
        "sentinels_lane_records": {
            s: {"n": len(g), "dropped": [r["key"] for r in g if dropped(r["p_out"], t)],
                "max_p_out": round(max((r["p_out"] for r in g), default=0), 4)}
            for s, g in (("reserve", [r for r in by["sentinel_repec"] if r["stratum"] == "holdout"]),
                         ("non_reserve", [r for r in by["sentinel_repec"] if r["stratum"] != "holdout"]))},
        "repec": {"n": len(by["repec"]), "dropped": sum(dropped(r["p_out"], t) for r in by["repec"]),
                  "share_dropped": round(sum(dropped(r["p_out"], t) for r in by["repec"])
                                         / max(1, len(by["repec"])), 3)},
        "sweep": [],
    }
    for q in (0.5, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99):
        rep["sweep"].append({"threshold": q,
                             "train_icf_lost_oof": sum(1 for r in train if r["label"] == "icf" and r["p_out"] > q),
                             "reserve_sentinels_lost": sum(1 for r in sent if r["stratum"] == "holdout" and r["p_out"] > q),
                             "reserve_sentinel_lane_records_lost": sum(
                                 1 for r in by["sentinel_repec"] if r["stratum"] == "holdout" and r["p_out"] > q),
                             "repec_share_dropped": round(sum(r["p_out"] > q for r in by["repec"])
                                                          / max(1, len(by["repec"])), 3)})
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    with open(os.path.join(out_dir, "scores.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "role", "label", "source", "stratum", "p_out", "drop"])
        for r in rows:
            if r["role"] != "train":
                w.writerow([r["key"], r["role"], r["label"], r["source"], r["stratum"],
                            f"{r['p_out']:.6f}", int(dropped(r["p_out"], t))])
        for r in train:
            w.writerow([r["key"], "train_oof", r["label"], r["source"], r["stratum"],
                        f"{r['p_out']:.6f}", int(dropped(r["p_out"], t))])
    return rep


# --- fresh Opus sample --------------------------------------------------------------

LINE = re.compile(r"^\s*(\d+)\s*\|\s*(icf|aux|out|unsure)\s*\|\s*(\w+)\s*\|([^|]*)\|?(.*)$")
STAGE2 = """Be strict: use "icf" only when the record's own title or abstract shows an
international climate-finance object; "aux" for related-but-not-ICF; "out" for unrelated;
"unsure" only when the text truly does not allow a decision. Records are in many languages;
judge each in its own language. Use only the record text.

Write one line per record, in order, format exactly:
n|label|doc|studied|why
where doc is research, institutional or other; studied is the country or region the work is
about (ISO country code or 'global' or '?'), why is max 12 words and given only when the label
is icf or unsure (empty otherwise). No other text."""


def _key(keyfile: str, var: str) -> str:
    for line in open(os.path.expanduser(keyfile), encoding="utf-8"):
        m = re.match(rf"^\s*(?:export\s+)?{var}\s*=\s*(.*)$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit("key variable not found")


def balance(key: str) -> dict:
    import requests
    out: dict = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    r = requests.get("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {key}"},
                     timeout=30)
    body = r.json().get("data", {}) if r.status_code == 200 else {}
    out["credits"] = {k: v for k, v in body.items() if k in ("total_credits", "total_usage")}
    out["status"] = r.status_code
    return out


def sample_for_opus(scores_csv: str, texts_path: str, n_drop: int, n_keep: int, seed: int = 1810) -> list[dict]:
    texts = {}
    for line in open(texts_path, encoding="utf-8"):
        r = json.loads(line)
        if r["role"] == "repec":
            texts[r["key"]] = r
    rows = [r for r in csv.DictReader(open(scores_csv, encoding="utf-8")) if r["role"] == "repec"]
    drop = sorted(r["key"] for r in rows if r["drop"] == "1")
    keep = sorted(r["key"] for r in rows if r["drop"] == "0")
    rng = random.Random(seed)
    pick = [(k, "drop", len(drop)) for k in rng.sample(drop, min(n_drop, len(drop)))] + \
           [(k, "keep", len(keep)) for k in rng.sample(keep, min(n_keep, len(keep)))]
    n_by = Counter(s for _, s, _ in pick)
    out = []
    for k, stratum, N in pick:
        t = texts[k]
        out.append({"key": k, "stratum": stratum, "weight": N / n_by[stratum],
                    "title": t.get("title", ""), "abstract": t.get("abstract", "")})
    rng.shuffle(out)
    return out


def opus_prompt(template: str, chunk: list[dict], title_max: int, abstract_max: int) -> str:
    lines = []
    for i, r in enumerate(chunk, 1):
        title, ab = r["title"], r["abstract"]
        lines.append(f"{i}. [? | ? | RePEc | affiliations: ?]\n   Title: {title[:title_max]}\n"
                     f"   Abstract: {(ab[:abstract_max] or '(no abstract)')}")
    return template.replace("{answer_format}", STAGE2).replace("{records}", "\n".join(lines))


def opus_run(sample: list[dict], out_path: str, key: str, screen_cfg: dict, chunk_size: int = 40) -> list[dict]:
    import requests
    results = []
    for c in range(0, len(sample), chunk_size):
        chunk = sample[c:c + chunk_size]
        prompt = opus_prompt(screen_cfg["prompt_template"], chunk, screen_cfg["title_max_chars"],
                             screen_cfg["abstract_max_chars"])
        body = {}
        for attempt in range(3):
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                              json={"model": OPUS_MODEL, "max_tokens": 16000,
                                    "messages": [{"role": "user", "content": prompt}],
                                    "usage": {"include": True}}, timeout=900)
            if r.status_code == 200:
                body = r.json()
                break
            time.sleep(5 * (attempt + 1))
        txt = (body.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        got = {}
        for line in txt.splitlines():
            m = LINE.match(line)
            if m and 1 <= int(m.group(1)) <= len(chunk):
                got[int(m.group(1))] = m
        for n, m in sorted(got.items()):
            s = chunk[n - 1]
            results.append({"key": s["key"], "stratum": s["stratum"], "weight": s["weight"],
                            "label": m.group(2), "doc": m.group(3).lower(), "studied": m.group(4).strip(),
                            "why": m.group(5).strip()})
        with open(out_path + ".calls.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"chunk": c // chunk_size, "n": len(chunk), "parsed": len(got),
                                 "usage": body.get("usage"), "status": r.status_code}) + "\n")
        log.info("chunk %d: %d sent, %d parsed, cost %s", c // chunk_size, len(chunk), len(got),
                 (body.get("usage") or {}).get("cost"))
    with open(out_path, "w", encoding="utf-8") as fh:
        for x in results:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    return results


def opus_summary(results: list[dict]) -> dict:
    out = {}
    for s in ("drop", "keep"):
        g = [r for r in results if r["stratum"] == s]
        lab = Counter(r["label"] for r in g)
        n = len(g)
        k = lab.get("icf", 0)
        out[s] = {"n": n, "labels": dict(lab), "icf": k,
                  "icf_rate_upper95": round((3.0 / n) if (n and k == 0) else _upper95(k, n), 4) if n else None,
                  "icf_keys": [r["key"] for r in g if r["label"] == "icf"]}
    return out


def _upper95(k: int, n: int) -> float:
    from scipy.stats import beta
    return float(beta.ppf(0.975, k + 1, n - k)) if n else 1.0


def remap_embeddings(old_npz: str, old_texts: str, new_texts: str, out_npz: str) -> dict:
    """Carry delivered-record embeddings over to a re-delivery: an old key
    (raw RePEc handle) maps to ``norm_handle`` of it, and a vector is kept only
    when the new delivery holds that record with a byte-identical text."""
    import numpy as np
    from _redif import norm_handle

    def texts(path: str) -> dict[str, str]:
        return {r["key"]: r["text"] for r in map(json.loads, open(path, encoding="utf-8"))
                if r["role"] == "repec"}
    old, new = texts(old_texts), texts(new_texts)
    z = np.load(old_npz, allow_pickle=True)
    keys, vecs, c = [], [], Counter()
    for k, v in zip(z["keys"], z["vectors"]):
        key, role = k.split("\t")
        if role != "repec":
            c["other_role"] += 1
            continue
        nk = norm_handle(key) or key
        if nk not in new:
            c["absent_from_new_delivery"] += 1
        elif new[nk] != old.get(key):
            c["text_changed"] += 1
        else:
            c["kept"] += 1
            keys.append(nk + "\trepec")
            vecs.append(v)
    np.savez(out_npz, vectors=np.array(vecs, dtype=np.float32), keys=np.array(keys, dtype=object))
    return dict(c)


def opus_rescore(results: list[dict], scores_csv: str) -> dict:
    """The existing Opus sample read again at a new threshold, labels reused.

    The sample was drawn as two simple random samples, from the old drop and
    old keep regions. Each record is re-classed by the new decision; the part
    of an old stratum that falls in a new region is a simple random sample of
    that intersection, so the ICF bound is reported per intersection."""
    from _redif import norm_handle
    dec = {r["key"]: r["drop"] for r in csv.DictReader(open(scores_csv, encoding="utf-8"))
           if r["role"] == "repec"}
    cells: dict[str, list[dict]] = defaultdict(list)
    missing = 0
    for r in results:
        k = norm_handle(r["key"]) or r["key"]
        if k not in dec:
            missing += 1
            continue
        cells[f"old_{r['stratum']}__new_{'drop' if dec[k] == '1' else 'keep'}"].append(r)
    out: dict = {"not_scored": missing}
    for cell, g in sorted(cells.items()):
        k = sum(r["label"] == "icf" for r in g)
        out[cell] = {"n": len(g), "labels": dict(Counter(r["label"] for r in g)), "icf": k,
                     "icf_rate_upper95": round(3.0 / len(g) if k == 0 else _upper95(k, len(g)), 4),
                     "icf_keys": [r["key"] for r in g if r["label"] == "icf"]}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("texts")
    t.add_argument("--pool", required=True)
    t.add_argument("--screen", required=True)
    t.add_argument("--labels", default="config/rel_prefilter_labels.csv")
    t.add_argument("--delivery", help="the lane delivery; omitted = training and validation texts only")
    t.add_argument("--sentinels", nargs="+",
                   default=["config/rel_sud_sentinels.csv", "config/rel_causal_sentinels.csv"])
    t.add_argument("--recall-sentinels", help="recall.sentinels.csv of the search script: adds the lane's "
                   "record of each retrieved sentinel (role sentinel_repec)")
    t.add_argument("--output", required=True)
    e = sub.add_parser("embed")
    e.add_argument("--texts", required=True)
    e.add_argument("--output-dir", required=True)
    e.add_argument("--limit", type=int)
    e.add_argument("--threads", type=int)
    e.add_argument("--roles", help="comma-separated roles to embed (default all)")
    f = sub.add_parser("fit")
    f.add_argument("--texts", required=True)
    f.add_argument("--embeddings", required=True, nargs="+")
    f.add_argument("--output-dir", required=True)
    o = sub.add_parser("opus-sample")
    o.add_argument("--scores", required=True)
    o.add_argument("--texts", required=True)
    o.add_argument("--n-drop", type=int, default=120)
    o.add_argument("--n-keep", type=int, default=80)
    o.add_argument("--screen-config", default="config/rel_sud_screen.yaml")
    o.add_argument("--keyfile", default="~/.config/keys/openrouter.env")
    o.add_argument("--key-var", default="OPENROUTER_API_KEY_CLIMATEFINANCE")
    o.add_argument("--output", required=True)
    m = sub.add_parser("remap-embeddings")
    m.add_argument("--embeddings", required=True)
    m.add_argument("--old-texts", required=True)
    m.add_argument("--texts", required=True)
    m.add_argument("--output", required=True)
    r = sub.add_parser("opus-rescore")
    r.add_argument("--opus-sample", required=True)
    r.add_argument("--scores", required=True)
    r.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "remap-embeddings":
        log.info(json.dumps(remap_embeddings(a.embeddings, a.old_texts, a.texts, a.output)))
        return 0
    if a.cmd == "opus-rescore":
        res = [json.loads(line) for line in open(a.opus_sample, encoding="utf-8")]
        summ = opus_rescore(res, a.scores)
        with open(a.output, "w", encoding="utf-8") as fh:
            json.dump(summ, fh, indent=1)
        log.info(json.dumps(summ, indent=1))
        return 0
    if a.cmd == "texts":
        rows = build_texts(a.pool, a.screen, a.labels, a.delivery, a.sentinels, a.recall_sentinels)
        with open(a.output, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        log.info(json.dumps(Counter((r["role"], r["label"]) for r in rows).most_common(), ensure_ascii=False))
    elif a.cmd == "embed":
        log.info(json.dumps(embed(a.texts, a.output_dir, a.limit, a.threads,
                                          set(a.roles.split(",")) if a.roles else None), indent=1))
    elif a.cmd == "fit":
        rep = fit(a.texts, a.embeddings, a.output_dir)
        log.info(json.dumps({k: v for k, v in rep.items() if k != "sweep"}, indent=1))
    else:
        import yaml
        cfg = yaml.safe_load(open(a.screen_config, encoding="utf-8"))
        key = _key(a.keyfile, a.key_var)
        before = balance(key)
        sample = sample_for_opus(a.scores, a.texts, a.n_drop, a.n_keep)
        res = opus_run(sample, a.output, key, cfg)
        after = balance(key)
        summ = {"model": OPUS_MODEL, "balance_before": before, "balance_after": after,
                "summary": opus_summary(res)}
        with open(os.path.splitext(a.output)[0] + ".summary.json", "w", encoding="utf-8") as fh:
            json.dump(summ, fh, indent=1)
        log.info(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
