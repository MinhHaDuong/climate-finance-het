"""Design-B stage 1 of the ICF screen through OpenRouter (ticket 1733).

Author decision of 2026-10-01: the pool works that no local Qwen run screens
get stage 1 from two labellers, and leave only when both say "hors sujet":

- the LLM, Gemma 4 26B-A4B, with the stage-1 prompt of
  ``config/rel_sud_screen.yaml`` (pipe answer format of its ``local`` block,
  thinking off), in batches (``designb.llm``);
- the classifier, Jev D1 on OpenRouter's decisions endpoint, one record per
  call, the four stage-1 labels as one choice with their probabilities
  (``designb.classifier``; the Jev pilot of 2026-09-30).

The drop rule is not applied here: the REL view applies it from the two
``icf_screen`` rows (``config/rel_screen.yaml`` → ``stage1_joint``). This
script only labels, and records what each labeller said.

Run directory (``--output-dir``), all append-only:

- ``llm.jsonl`` / ``classifier.jsonl``: one line per labelled work
  (``work_key``, label, doc, and ``why`` for the LLM, ``p_out`` and the
  probabilities for the classifier; the served model id and provider);
- ``calls.jsonl``: one line per HTTP call, with its cost as OpenRouter
  reports it (``usage.cost``), the works sent and parsed, or the error;
- ``screen_runs.jsonl``: one header per invocation (models, prompt hashes,
  input, budget, start);
- ``balance_<start>.json`` / ``balance_<end>.json`` per invocation (account
  credits, numeric fields only), and ``summary.json`` (last invocation).

Resumable: a work already labelled by a labeller is not sent to it again;
works a call left unlabelled (partial or unparsable answer, HTTP failure,
unexpected served model) are re-sent in up to ``retry_rounds`` rounds, and a
rerun retries them again. Works go in input order, in chunks that both
labellers finish before the next.

Budget: ``--budget-usd`` caps the spend of the run directory, all invocations
together (the sum of ``calls.jsonl`` costs). Before each call a reservation
(``est_cost_per_call``, or 1.5 times the dearest call seen if higher) is taken;
a call whose reservation would cross the cap is not sent, and the run stops
cleanly after the calls in flight. A call without a reported cost is counted
at its reservation.

The run ends with ``labelled N, unlabelled M`` in the log (N: works labelled
by both labellers), the line ``corpus_icf_import.py stage1-designb`` checks.

Credentials: ``OPENROUTER_API_KEY_CLIMATEFINANCE`` through
``pipeline_keystore.read_credential``; never logged.

Usage:
    python scripts/corpus_icf_stage1_designb.py --input DIR/screen_input.jsonl \\
        --output-dir DIR --budget-usd 5 [--limit N] [--sample-seed 7]
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone

import corpus_rel_sud_screen as sc
import yaml
from utils import get_logger

log = get_logger("corpus_icf_stage1_designb")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_sud_screen.yaml")
KEY_PROVIDER, KEY_VAR = "openrouter", "OPENROUTER_API_KEY_CLIMATEFINANCE"
CREDITS_URL = "https://openrouter.ai/api/v1/credits"
RETRY_STATUS = {408, 429, 500, 502, 503, 504, 524, 529}
LLM, CLF = "llm", "classifier"

# post(url, body, timeout) -> (HTTP status or None, parsed JSON or None, error text or None)
Post = Callable[[str, dict, float], tuple]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Prompts ─────────────────────────────────────────────


def llm_cfg(cfg: dict) -> dict:
    """Prompt settings of the LLM: the stage-1 prompt, pipe answer format."""
    return {**cfg, "answer_format": cfg["local"]["answer_format"]}


def llm_prompt_sha256(cfg: dict) -> str:
    """Same hash as ``corpus_rel_sud_screen.run`` gives a run with this format."""
    c = llm_cfg(cfg)
    return hashlib.sha256((c["prompt_template"] + "\n" + c["answer_format"]).encode()).hexdigest()


def state_text(rec: dict, cfg: dict) -> str:
    """The record as the classifier sees it: the LLM's record text, unnumbered."""
    title = (rec.get("title") or "")[: cfg["title_max_chars"]]
    abstract = (rec.get("abstract") or "")[: cfg["abstract_max_chars"]] or "(no abstract)"
    where = ", ".join(rec.get("countries") or []) or "?"
    return (f"[{rec.get('language') or '?'} | {rec.get('year') or '?'} | "
            f"{rec.get('journal') or '?'} | affiliations: {where}]\n"
            f"Title: {title}\nAbstract: {abstract}")


def classifier_prompt_sha256(cfg: dict) -> str:
    """Hash of the classifier's questions and of the state format they apply to."""
    blob = json.dumps({"questions": cfg["designb"]["classifier"]["questions"],
                       "state": "state_text/v1", "title_max_chars": cfg["title_max_chars"],
                       "abstract_max_chars": cfg["abstract_max_chars"]}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def llm_body(batch: list[dict], cfg: dict) -> dict:
    b = cfg["designb"]["llm"]
    return {"model": b["model"], "temperature": 0, "max_tokens": b["max_tokens"],
            "messages": [{"role": "user", "content": sc.build_prompt(batch, llm_cfg(cfg))}],
            "reasoning": {"enabled": False}, "usage": {"include": True}}


def classifier_body(rec: dict, cfg: dict) -> dict:
    c = cfg["designb"]["classifier"]
    return {"model": c["model"], "state": state_text(rec, cfg), "questions": c["questions"]}


# ── Parsing ─────────────────────────────────────────────


def parse_llm(resp: dict, batch: list[dict]) -> dict:
    """``{work_key: {label, doc, why}}`` from a chat completion (valid lines only)."""
    choices = resp.get("choices") or []
    text = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
    return sc.parse_answer(text, batch, "work_key")


def parse_classifier(resp: dict) -> dict | None:
    """``{label, doc, p_out, probabilities}`` from a decision, or None if malformed."""
    answers = resp.get("answers") or {}
    lab, doc = answers.get("label") or {}, answers.get("doc") or {}
    choice = str(lab.get("choice") or "").strip().lower()
    probs = lab.get("probabilities")
    if choice not in sc.LABELS or not isinstance(probs, dict):
        return None
    p_out = probs.get("out", 0)
    if isinstance(p_out, bool) or not isinstance(p_out, (int, float)) or not 0 <= p_out <= 1:
        return None
    d = str(doc.get("choice") or "").strip().lower()
    return {"label": choice, "doc": d if d in sc.DOCS else "unknown", "p_out": float(p_out),
            "probabilities": probs}


def cost_of(resp: dict | None) -> float | None:
    usage = (resp or {}).get("usage") or {}
    c = usage.get("cost")
    return float(c) if isinstance(c, (int, float)) and not isinstance(c, bool) else None


# ── Budget ──────────────────────────────────────────────


class Budget:
    """Spend cap for the run directory; thread-safe reservations."""

    def __init__(self, cap: float, spent: float = 0.0):
        self.cap, self.spent, self.reserved = cap, spent, 0.0
        self.dearest: dict = {}
        self.stopped = False
        self._lock = threading.Lock()

    def estimate(self, kind: str, floor: float) -> float:
        return max(floor, 1.5 * self.dearest.get(kind, 0.0))

    def reserve(self, amount: float) -> bool:
        with self._lock:
            if self.stopped or self.spent + self.reserved + amount > self.cap:
                self.stopped = True
                return False
            self.reserved += amount
            return True

    def settle(self, kind: str, reserved: float, actual: float | None) -> float:
        """Release a reservation; count the real cost (the reservation if unknown)."""
        charged = reserved if actual is None else actual
        with self._lock:
            self.reserved -= reserved
            self.spent += charged
            if actual is not None:
                self.dearest[kind] = max(self.dearest.get(kind, 0.0), actual)
        return charged


# ── HTTP ────────────────────────────────────────────────


def make_post(key: str) -> Post:
    """A ``post`` that sends the key in the header only (never logged)."""
    import requests

    session = requests.Session()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "X-Title": "climate-finance-het ICF stage 1 design B"}

    def post(url, body, timeout):
        try:
            r = session.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as exc:
            return None, None, type(exc).__name__
        try:
            data = r.json()
        except ValueError:
            data = None
        err = None if r.status_code == 200 else f"http {r.status_code}"
        return r.status_code, data, err

    return post


def balance(key: str) -> dict:
    """Account credits (numeric fields only); ``{}`` fields when unreadable."""
    import requests

    out: dict = {"at": now()}
    try:
        r = requests.get(CREDITS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
        body = (r.json() or {}).get("data", {}) if r.status_code == 200 else {}
        out["status"] = r.status_code
    except (requests.RequestException, ValueError) as exc:
        body, out["status"] = {}, type(exc).__name__
    for k in ("total_credits", "total_usage"):
        if isinstance(body.get(k), (int, float)):
            out[k] = body[k]
    if "total_credits" in out and "total_usage" in out:
        out["remaining"] = round(out["total_credits"] - out["total_usage"], 6)
    return out


def call_with_retries(post: Post, url: str, body: dict, timeout: float,
                      tries: int = 4, sleep: Callable = time.sleep) -> tuple:
    """``(response or None, error or None, latency)``; transient failures retried.

    A transient failure (no response, a retry status) costs nothing on
    OpenRouter, so its retries need no reservation.
    """
    err = None
    t0 = time.monotonic()
    for attempt in range(tries):
        status, data, err = post(url, body, timeout)
        if status == 200 and isinstance(data, dict) and not data.get("error"):
            return data, None, time.monotonic() - t0
        if status == 200:
            err = "error in body: " + str((data or {}).get("error"))[:200]
        if status is not None and status not in RETRY_STATUS and status != 200:
            break
        sleep(min(2 ** attempt + 1, 20))
    return None, err, time.monotonic() - t0


# ── Run ─────────────────────────────────────────────────


def read_jsonl(path: str) -> list[dict]:
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                x = json.loads(line)
            except ValueError:
                log.warning("skipping an unreadable line in %s (killed mid-write?)", path)
                continue
            if isinstance(x, dict):
                out.append(x)
    return out


def _ensure_newline(path: str) -> None:
    """A killed write may leave a partial last line: start the next on its own."""
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                with open(path, "a", encoding="utf-8") as out:
                    out.write("\n")


class Runner:
    def __init__(self, cfg: dict, out_dir: str, budget: Budget, post: Post,
                 accepted: dict, sleep: Callable = time.sleep):
        self.cfg, self.out_dir, self.budget, self.post = cfg, out_dir, budget, post
        self.accepted, self.sleep = accepted, sleep
        self.paths = {k: os.path.join(out_dir, f"{k}.jsonl") for k in (LLM, CLF, "calls")}
        for p in self.paths.values():
            _ensure_newline(p)
        self.done = {k: {x["work_key"] for x in read_jsonl(self.paths[k])} for k in (LLM, CLF)}
        self.stop_reason = ""
        self._seq = len(read_jsonl(self.paths["calls"]))

    # one call: returns (call record, [label lines])
    def _call(self, kind: str, recs: list[dict], attempt: int) -> tuple[dict, list[dict]] | None:
        b = self.cfg["designb"][kind]
        est = self.budget.estimate(kind, b["est_cost_per_call"])
        if not self.budget.reserve(est):
            return None
        body = (llm_body(recs, self.cfg) if kind == LLM else classifier_body(recs[0], self.cfg))
        resp, err, latency = call_with_retries(self.post, b["url"], body, b["timeout"],
                                               sleep=self.sleep)
        actual = cost_of(resp)
        charged = self.budget.settle(kind, est, actual if resp is not None else 0.0)
        served = (resp or {}).get("model")
        lines: list[dict] = []
        if resp is not None and served not in self.accepted[kind]:
            err = f"served model {served!r} not in the accepted list"
            self.stop_reason = self.stop_reason or f"{kind}: {err}"
            self.budget.stopped = True
        elif resp is not None:
            stamp = {"model": served, "provider": resp.get("provider") or "", "labelled_at": now()}
            if kind == LLM:
                for key, r in parse_llm(resp, recs).items():
                    lines.append({"work_key": key, **r, **stamp})
            else:
                r = parse_classifier(resp)
                if r:
                    lines.append({"work_key": recs[0]["work_key"], **r, **stamp})
        rec = {"labeller": kind, "attempt": attempt, "n": len(recs), "n_parsed": len(lines),
               "work_keys": [r["work_key"] for r in recs] if kind == LLM else [recs[0]["work_key"]],
               "cost": charged, "cost_reported": actual is not None, "model": served,
               "provider": (resp or {}).get("provider"), "latency_s": round(latency, 3),
               "err": err, "at": now()}
        return rec, lines

    def _write(self, kind: str, rec: dict, lines: list[dict], fh: dict) -> None:
        self._seq += 1
        fh["calls"].write(json.dumps({"call": self._seq, **rec}, ensure_ascii=False) + "\n")
        for x in lines:
            if x["work_key"] not in self.done[kind]:
                self.done[kind].add(x["work_key"])
                fh[kind].write(json.dumps(x, ensure_ascii=False) + "\n")
        for f in fh.values():
            f.flush()

    def run_chunk(self, recs: list[dict], attempt: int, fh: dict) -> None:
        size = self.cfg["designb"]["llm"]["batch_size"]
        todo_llm = [r for r in recs if r["work_key"] not in self.done[LLM]]
        todo_clf = [r for r in recs if r["work_key"] not in self.done[CLF]]
        jobs = [(LLM, todo_llm[i:i + size]) for i in range(0, len(todo_llm), size)]
        jobs += [(CLF, [r]) for r in todo_clf]
        pools = {k: ThreadPoolExecutor(self.cfg["designb"][k]["workers"]) for k in (LLM, CLF)}
        try:
            futures = {pools[k].submit(self._call, k, batch, attempt): k for k, batch in jobs}
            pending = set(futures)
            while pending:
                finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                for f in finished:
                    res = f.result()
                    if res is not None:
                        self._write(futures[f], *res, fh)
        finally:
            for p in pools.values():
                p.shutdown(wait=True)

    def run(self, recs: list[dict]) -> None:
        d = self.cfg["designb"]
        with open(self.paths[LLM], "a", encoding="utf-8") as fl, \
                open(self.paths[CLF], "a", encoding="utf-8") as fc, \
                open(self.paths["calls"], "a", encoding="utf-8") as fk:
            fh = {LLM: fl, CLF: fc, "calls": fk}
            for attempt in range(1, d["retry_rounds"] + 2):
                todo = [r for r in recs if r["work_key"] not in self.done[LLM]
                        or r["work_key"] not in self.done[CLF]]
                if not todo:
                    break
                log.info("round %d: %d works to label (llm %d, classifier %d)", attempt, len(todo),
                         sum(r["work_key"] not in self.done[LLM] for r in todo),
                         sum(r["work_key"] not in self.done[CLF] for r in todo))
                for i in range(0, len(todo), d["chunk_works"]):
                    self.run_chunk(todo[i:i + d["chunk_works"]], attempt, fh)
                    log.info("round %d: %d/%d works sent; spent USD %.4f of %.2f", attempt,
                             min(i + d["chunk_works"], len(todo)), len(todo), self.budget.spent,
                             self.budget.cap)
                    if self.budget.stopped:
                        self.stop_reason = self.stop_reason or (
                            f"budget: next call would cross USD {self.budget.cap}")
                        return


def summarize(out_dir: str, recs: list[dict], threshold: float) -> dict:
    """Counts of the run directory over ``recs``; the design-B tally is a preview
    of the rule the view applies (``config/rel_screen.yaml`` → ``stage1_joint``)."""
    keys = {r["work_key"] for r in recs}
    llm = {x["work_key"]: x for x in read_jsonl(os.path.join(out_dir, "llm.jsonl"))}
    clf = {x["work_key"]: x for x in read_jsonl(os.path.join(out_dir, "classifier.jsonl"))}
    calls = read_jsonl(os.path.join(out_dir, "calls.jsonl"))
    both = keys & set(llm) & set(clf)
    drop = {k for k in both if llm[k]["label"] == "out" and clf[k]["label"] == "out"
            and clf[k]["p_out"] >= threshold}
    first = [c for c in calls if c["attempt"] == 1]

    def tally(rows):
        return dict(sorted(Counter(r["label"] for r in rows).items()))

    return {
        "works_input": len(keys),
        "labelled_llm": len(keys & set(llm)), "labelled_classifier": len(keys & set(clf)),
        "labelled_both": len(both), "unlabelled": len(keys - both),
        "designb_stage1_out": len(drop), "designb_to_stage2": len(both) - len(drop),
        "llm_labels": tally(llm[k] for k in both), "classifier_labels": tally(clf[k] for k in both),
        "llm_out_classifier_below_threshold": sum(
            1 for k in both if llm[k]["label"] == "out" and k not in drop),
        "calls": len(calls), "calls_failed": sum(bool(c.get("err")) for c in calls),
        "llm_works_unparsed_first_attempt": sum(
            c["n"] - c["n_parsed"] for c in first if c["labeller"] == LLM),
        "classifier_works_unparsed_first_attempt": sum(
            c["n"] - c["n_parsed"] for c in first if c["labeller"] == CLF),
        "spent_usd": round(sum(c.get("cost") or 0 for c in calls), 6),
        "spent_usd_by_labeller": {k: round(sum(c.get("cost") or 0 for c in calls
                                               if c["labeller"] == k), 6) for k in (LLM, CLF)},
        "calls_without_reported_cost": sum(1 for c in calls if not c.get("cost_reported")
                                           and not c.get("err")),
        "providers": dict(sorted(Counter(c.get("provider") or "?" for c in calls).items())),
        "classifier_p_out_min": threshold,
    }


def run(cfg: dict, screen_cfg: dict, args, post: Post | None = None,
        key: str | None = None, sleep: Callable = time.sleep) -> int:
    os.makedirs(args.output_dir, exist_ok=True)
    joint = screen_cfg["stage1_joint"]
    accepted = {LLM: set(joint["llm_models"]), CLF: set(joint["classifier_models"])}
    if post is None:
        from pipeline_keystore import read_credential
        key = read_credential(KEY_PROVIDER, KEY_VAR)
        if not key:
            log.error("no OpenRouter key (%s in the keystore)", KEY_VAR)
            return 2
        post = make_post(key)
    recs = sc.select_records(args.input, set(), args.limit, args.sample_seed, "work_key")
    spent = sum(c.get("cost") or 0 for c in read_jsonl(os.path.join(args.output_dir, "calls.jsonl")))
    budget = Budget(args.budget_usd, spent)
    started = now()
    stamp = started.replace(":", "").replace("+0000", "Z")
    if key:
        with open(os.path.join(args.output_dir, f"balance_{stamp}_before.json"), "w") as fh:
            json.dump(balance(key), fh)
            fh.write("\n")
    header = {"started": started, "id_field": "work_key", "input": args.input,
              "n_input": len(recs), "budget_usd": args.budget_usd, "spent_before_usd": spent,
              "llm_model": cfg["designb"]["llm"]["model"],
              "llm_prompt_sha256": llm_prompt_sha256(cfg),
              "llm_batch_size": cfg["designb"]["llm"]["batch_size"],
              "classifier_model": cfg["designb"]["classifier"]["model"],
              "classifier_prompt_sha256": classifier_prompt_sha256(cfg),
              "accepted_models": {k: sorted(v) for k, v in accepted.items()}}
    with open(os.path.join(args.output_dir, "screen_runs.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(header) + "\n")
    runner = Runner(cfg, args.output_dir, budget, post, accepted, sleep)
    if spent >= args.budget_usd:
        runner.stop_reason = f"budget: USD {spent:.4f} already spent of {args.budget_usd}"
    else:
        runner.run(recs)
    summary = summarize(args.output_dir, recs, joint["classifier_p_out_min"])
    summary.update({"stopped": runner.stop_reason, "finished": now()})
    if key:
        with open(os.path.join(args.output_dir, f"balance_{stamp}_after.json"), "w") as fh:
            json.dump(balance(key), fh)
            fh.write("\n")
    with open(os.path.join(args.output_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    if runner.stop_reason:
        log.warning("stopped: %s", runner.stop_reason)
    log.info("spent USD %.4f (cap %.2f); design B: %d stage1_out, %d to stage 2",
             summary["spent_usd"], args.budget_usd, summary["designb_stage1_out"],
             summary["designb_to_stage2"])
    log.info("labelled %d, unlabelled %d (rerun to retry)", summary["labelled_both"],
             summary["unlabelled"])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="prompts and designb block")
    ap.add_argument("--screen-config", default=os.path.join(ROOT, "config", "rel_screen.yaml"),
                    help="stage1_joint: accepted models and the drop threshold")
    ap.add_argument("--input", required=True, help="JSONL from corpus_icf_stage1_input.py")
    # Multi-output script (labels, calls, headers, balances): --output-dir, not --output.
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--budget-usd", type=float, required=True,
                    help="spend cap of the run directory, all invocations together")
    ap.add_argument("--limit", type=int, default=0, help="random sample size (0 = all)")
    ap.add_argument("--sample-seed", type=int, default=7)
    args = ap.parse_args(argv)
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    with open(args.screen_config, encoding="utf-8") as fh:
        screen_cfg = yaml.safe_load(fh)
    return run(cfg, screen_cfg, args)


if __name__ == "__main__":
    sys.exit(main())
