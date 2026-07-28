"""Paired within-work test of English-query score depression in flag 6.

Study script for the 2026-07-28 flag-6 language-bias diagnosis (see README.md
in this directory; tickets 0337/0283/0540). Same model and text-building path
as scripts/filter_flags_llm.py::_score_batch. Each work is scored twice — once
against the deployed English query, once against a translation of that query
into the work's own language. Pairing within a work holds subject matter
constant, so a systematic shift is the query's doing. Symmetric control:
English works scored against the same non-English queries.

Run with the source roots on the path (see .claude/rules/coding.md):

    PYTHONPATH=scripts:libs/openalex-corpus/src PER_LANG=200 \
        uv run python .../flag6-language-bias/paired_query.py
"""

import argparse
import os
import pathlib

import numpy as np
import pandas as pd
import yaml
from pipeline_loaders import CATALOGS_DIR

CFG = yaml.safe_load(pathlib.Path("config/corpus_filter.yaml").read_text())["llm_relevance"]
EN_QUERY = CFG["reranker_query"].strip()
THRESH = float(CFG["reranker_threshold"])
MODEL = CFG["reranker_model"]
TITLE_MAX = int(CFG.get("title_max", 300))
ABS_MAX = int(CFG.get("abstract_max", 1500))

QUERIES = {
    "pt": "política climática e mecanismos financeiros",
    "es": "política climática y mecanismos financieros",
    "fr": "politique climatique et mécanismes financiers",
    "de": "Klimapolitik und Finanzierungsmechanismen",
    "id": "kebijakan iklim dan mekanisme keuangan",
    "tr": "iklim politikası ve finansal mekanizmalar",
    "ru": "климатическая политика и финансовые механизмы",
    "ko": "기후 정책 및 금융 메커니즘",
    "ar": "سياسة المناخ والآليات المالية",
    "pl": "polityka klimatyczna i mechanizmy finansowe",
    "it": "politica climatica e meccanismi finanziari",
    "nl": "klimaatbeleid en financiële mechanismen",
    "ja": "気候政策と金融メカニズム",
    "zh": "气候政策与金融机制",
}
SEED = 20260728


def build_text(row):
    title = str(row["title"] if pd.notna(row["title"]) else "")[:TITLE_MAX]
    abstract = str(row["abstract"] if pd.notna(row["abstract"]) else "")[:ABS_MAX]
    return f"{title}. {abstract}" if abstract else title


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", default="data/derived", help="where per-work score CSVs land")
    ap.add_argument("--per-lang", type=int, default=int(os.environ.get("PER_LANG", "200")))
    args = ap.parse_args()
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(os.path.join(CATALOGS_DIR, "extended_works.csv"), low_memory=False)
    df["text"] = df.apply(build_text, axis=1)
    has_abs = df["abstract"].fillna("").str.strip().ne("")
    lang = df["language"].fillna("unknown")

    rng = np.random.default_rng(SEED)
    frames = []
    for lg in QUERIES:
        sub = df[lang.eq(lg) & has_abs]
        if len(sub) == 0:
            continue
        take = sub if len(sub) <= args.per_lang else sub.iloc[
            rng.choice(len(sub), args.per_lang, replace=False)]
        frames.append(take.assign(_lang=lg))
    ne = pd.concat(frames, ignore_index=True)

    en_ctl = df[lang.eq("en") & has_abs]
    en_ctl = en_ctl.iloc[rng.choice(len(en_ctl), min(args.per_lang * 3, len(en_ctl)), replace=False)]

    import torch
    from sentence_transformers import CrossEncoder
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"model={MODEL} device={dev} threshold={THRESH}", flush=True)
    rr = CrossEncoder(MODEL, device=dev)

    def score(texts, query):
        return np.asarray(rr.predict([(query, t) for t in texts], batch_size=64,
                                     show_progress_bar=False), dtype=float)

    # arm 1: non-English works, English query vs own-language query
    ne["score_en_query"] = score(ne["text"].tolist(), EN_QUERY)
    own = np.empty(len(ne))
    for lg, idx in ne.groupby("_lang").groups.items():
        own[ne.index.get_indexer(idx)] = score(ne.loc[idx, "text"].tolist(), QUERIES[lg])
    ne["score_own_query"] = own

    # arm 2 (control): English works, English query vs each non-English query
    en_texts = en_ctl["text"].tolist()
    en_base = score(en_texts, EN_QUERY)
    ctl_rows = []
    for lg, q in QUERIES.items():
        s = score(en_texts, q)
        ctl_rows.append({
            "query_lang": lg,
            "n": len(en_texts),
            "pass_en_query": float((en_base >= THRESH).mean()),
            "pass_foreign_query": float((s >= THRESH).mean()),
            "median_en": float(np.median(en_base)),
            "median_foreign": float(np.median(s)),
        })

    ne.to_csv(outdir / "paired_nonenglish_scores.csv", index=False)
    pd.DataFrame(ctl_rows).to_csv(outdir / "paired_english_control.csv", index=False)

    print("\n=== ARM 1: non-English works, English query vs own-language query ===")
    for lg, g in ne.groupby("_lang"):
        pe = (g["score_en_query"] >= THRESH).mean()
        po = (g["score_own_query"] >= THRESH).mean()
        print(f"{lg:<6}n={len(g):<5} pass@EN={100*pe:5.1f}%  pass@own={100*po:5.1f}%  "
              f"Δ={100*(po-pe):+5.1f}pp")
    pe = (ne["score_en_query"] >= THRESH).mean()
    po = (ne["score_own_query"] >= THRESH).mean()
    print(f"ALL   n={len(ne):<5} pass@EN={100*pe:5.1f}%  pass@own={100*po:5.1f}%  "
          f"Δ={100*(po-pe):+5.1f}pp")

    from scipy.stats import wilcoxon
    st, p = wilcoxon(ne["score_own_query"], ne["score_en_query"])
    print(f"Wilcoxon signed-rank (paired): stat={st:.0f} p={p:.3g}")

    print("\n=== ARM 2 (control): English works vs foreign queries ===")
    c = pd.DataFrame(ctl_rows)
    for _, r in c.iterrows():
        print(f"{r['query_lang']:<6}pass={100*r['pass_foreign_query']:5.1f}%  "
              f"Δ vs EN={100*(r['pass_foreign_query']-r['pass_en_query']):+6.1f}pp")


if __name__ == "__main__":
    main()
