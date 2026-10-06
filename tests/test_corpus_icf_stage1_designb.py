"""Design-B stage 1 through OpenRouter: labels, resume, retries, budget (ticket 1733)."""

import json
import os
import re
import threading
import types

import _icf_screen as ics
import _rel_view as rv
import corpus_icf_import as ci
import corpus_icf_stage1_designb as db
import pytest
import yaml

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEMMA, JEV = "google/gemma-4-26b-a4b-it", "typesafe/jev-1.13-20260917"


def _cfgs(batch_size=2, chunk=3, retry_rounds=2):
    with open(os.path.join(ROOT, "config", "rel_sud_screen.yaml"), encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    with open(os.path.join(ROOT, "config", "rel_screen.yaml"), encoding="utf-8") as fh:
        screen = yaml.safe_load(fh)
    d = cfg["designb"]
    d["llm"].update(batch_size=batch_size, workers=2)
    d["classifier"].update(workers=2)
    d.update(chunk_works=chunk, retry_rounds=retry_rounds)
    return cfg, screen


def _input(tmp_path, n):
    path = tmp_path / "screen_input.jsonl"
    path.write_text("".join(json.dumps({
        "work_key": f"openalex:W{i}", "openalex_id": f"W{i}", "doi": "", "title": f"Title {i}",
        "year": "2020", "language": "en", "journal": "J", "countries": ["KE"],
        "abstract": f"Abstract {i}"}) + "\n" for i in range(1, n + 1)), encoding="utf-8")
    return str(path)


class FakeRouter:
    """OpenRouter stand-in: work i gets LLM label LLM[i] and classifier (label, P(out))."""

    def __init__(self, llm, clf, cost=(0.0004, 0.00003)):
        self.llm, self.clf, self.cost = llm, clf, cost
        self.calls = []
        self.drop_llm_once = set()      # works whose line the first LLM answer omits
        self.garble_clf_once = set()    # works whose first classifier answer is malformed
        self.fail_first = 0             # HTTP 429 for the first N calls
        self.served = {"llm": GEMMA, "classifier": JEV}
        self.report_cost = True
        self._lock = threading.Lock()

    def __call__(self, url, body, timeout):
        with self._lock:
            self.calls.append((url, body))
            if self.fail_first:
                self.fail_first -= 1
                return 429, {"error": "rate"}, "http 429"
        if "decisions" in url:
            i = int(re.search(r"Title (\d+)", body["state"]).group(1))
            label, p = self.clf[i]
            with self._lock:
                garble = i in self.garble_clf_once
                self.garble_clf_once.discard(i)
            ans = {"label": {"type": "choice", "choice": "maybe" if garble else label,
                             "probabilities": {"out": p, "aux" if label == "out" else label:
                                               round(1 - p, 4)}},
                   "doc": {"type": "choice", "choice": "research"}}
            return 200, {"model": self.served["classifier"], "provider": "TypeSafe",
                         "answers": ans, "usage": {"cost": self.cost[1]} if self.report_cost
                         else {}}, None
        prompt = body["messages"][0]["content"]
        ids = [int(x) for x in re.findall(r"Title: Title (\d+)", prompt)]
        lines = []
        for n, i in enumerate(ids, 1):
            with self._lock:
                if i in self.drop_llm_once:
                    self.drop_llm_once.discard(i)
                    continue
            lines.append(f"{n}|{self.llm[i]}|research|why {i}")
        return 200, {"model": self.served["llm"], "provider": "NextBit",
                     "choices": [{"message": {"content": "\n".join(lines)}}],
                     "usage": {"cost": self.cost[0]} if self.report_cost else {}}, None


def _args(tmp_path, inp, budget=1.0, out="run"):
    return types.SimpleNamespace(input=inp, output_dir=str(tmp_path / out), budget_usd=budget,
                                 limit=0, sample_seed=7)


def _labels(d, name):
    return {x["work_key"]: x for x in db.read_jsonl(os.path.join(d, f"{name}.jsonl"))}


LLM5 = {1: "out", 2: "out", 3: "aux", 4: "out", 5: "icf"}
with open(os.path.join(ROOT, "config", "rel_screen.yaml"), encoding="utf-8") as _fh:
    P_MIN = yaml.safe_load(_fh)["stage1_joint"]["classifier_p_out_min"]
BELOW = round(P_MIN - 0.01, 4)  # a "out" classifier verdict just under the configured threshold
CLF5 = {1: ("out", 0.99), 2: ("out", BELOW), 3: ("out", 0.99), 4: ("aux", 0.10), 5: ("icf", 0.0)}


def test_both_labellers_label_every_work_and_the_summary_previews_design_b(tmp_path):
    cfg, screen = _cfgs()
    router = FakeRouter(LLM5, CLF5)
    args = _args(tmp_path, _input(tmp_path, 5))
    assert db.run(cfg, screen, args, post=router, sleep=lambda s: None) == 0
    llm, clf = _labels(args.output_dir, "llm"), _labels(args.output_dir, "classifier")
    assert {k: v["label"] for k, v in llm.items()} == {f"openalex:W{i}": l for i, l in LLM5.items()}
    assert clf["openalex:W2"]["p_out"] == BELOW and clf["openalex:W1"]["model"] == JEV
    assert llm["openalex:W1"]["provider"] == "NextBit" and llm["openalex:W1"]["why"] == "why 1"
    s = json.loads(open(os.path.join(args.output_dir, "summary.json")).read())
    # only W1 has both "out" with P >= the threshold; W2 (just below), W3, W4 disagree
    assert (s["labelled_both"], s["designb_stage1_out"], s["designb_to_stage2"]) == (5, 1, 4)
    assert s["llm_out_classifier_below_threshold"] == 2
    assert s["spent_usd"] == pytest.approx(3 * 0.0004 + 5 * 0.00003)
    (head,) = db.read_jsonl(os.path.join(args.output_dir, "screen_runs.jsonl"))
    assert head["id_field"] == "work_key" and head["llm_prompt_sha256"] == db.llm_prompt_sha256(cfg)


def test_requests_carry_the_stage1_prompt_and_the_jev_d1_questions(tmp_path):
    cfg, screen = _cfgs()
    router = FakeRouter(LLM5, CLF5)
    db.run(cfg, screen, _args(tmp_path, _input(tmp_path, 2)), post=router, sleep=lambda s: None)
    llm_body = next(b for u, b in router.calls if "chat/completions" in u)
    assert llm_body["model"] == GEMMA and llm_body["reasoning"] == {"enabled": False}
    prompt = llm_body["messages"][0]["content"]
    assert "INTERNATIONAL\nCLIMATE FINANCE" in prompt and "n|label|doc|why" in prompt
    assert "1. [en | 2020 | J | affiliations: KE]" in prompt
    clf_body = next(b for u, b in router.calls if "decisions" in u)
    assert clf_body["model"] == "typesafe/jev-1.13"
    assert set(clf_body["questions"]) == {"label", "doc"}
    assert set(clf_body["questions"]["label"]["criteria"]) == {"icf", "aux", "out", "unsure"}
    assert clf_body["state"].startswith("[en | 2020 | J | affiliations: KE]\nTitle: Title")


def test_a_rerun_sends_nothing_already_labelled(tmp_path):
    cfg, screen = _cfgs()
    inp = _input(tmp_path, 5)
    db.run(cfg, screen, _args(tmp_path, inp), post=FakeRouter(LLM5, CLF5), sleep=lambda s: None)
    again = FakeRouter(LLM5, CLF5)
    db.run(cfg, screen, _args(tmp_path, inp), post=again, sleep=lambda s: None)
    assert again.calls == []
    assert len(db.read_jsonl(str(tmp_path / "run" / "screen_runs.jsonl"))) == 2


def test_partial_and_unparsable_answers_are_retried(tmp_path):
    cfg, screen = _cfgs()
    router = FakeRouter(LLM5, CLF5)
    router.drop_llm_once, router.garble_clf_once = {2, 5}, {3}
    router.fail_first = 1
    args = _args(tmp_path, _input(tmp_path, 5))
    db.run(cfg, screen, args, post=router, sleep=lambda s: None)
    s = json.loads(open(os.path.join(args.output_dir, "summary.json")).read())
    assert s["labelled_both"] == 5 and s["unlabelled"] == 0
    assert s["llm_works_unparsed_first_attempt"] == 2
    assert s["classifier_works_unparsed_first_attempt"] == 1
    calls = db.read_jsonl(os.path.join(args.output_dir, "calls.jsonl"))
    assert {c["attempt"] for c in calls} == {1, 2}


def test_retries_stop_after_the_configured_rounds(tmp_path):
    cfg, screen = _cfgs(retry_rounds=0)
    router = FakeRouter(LLM5, CLF5)
    router.drop_llm_once = {2}
    args = _args(tmp_path, _input(tmp_path, 5))
    db.run(cfg, screen, args, post=router, sleep=lambda s: None)
    assert "openalex:W2" not in _labels(args.output_dir, "llm")
    # the rerun picks it up
    db.run(cfg, screen, args, post=router, sleep=lambda s: None)
    assert "openalex:W2" in _labels(args.output_dir, "llm")


def test_budget_cap_stops_cleanly_and_a_rerun_resumes(tmp_path):
    cfg, screen = _cfgs(batch_size=2, chunk=2)
    cfg["designb"]["llm"]["est_cost_per_call"] = 0.0004
    cfg["designb"]["classifier"]["est_cost_per_call"] = 0.00003
    llm = {i: "out" for i in range(1, 21)}
    clf = {i: ("out", 0.99) for i in range(1, 21)}
    inp = _input(tmp_path, 20)
    args = _args(tmp_path, inp, budget=0.002)
    assert db.run(cfg, screen, args, post=FakeRouter(llm, clf), sleep=lambda s: None) == 0
    s = json.loads(open(os.path.join(args.output_dir, "summary.json")).read())
    assert s["stopped"].startswith("budget") and s["spent_usd"] <= 0.002
    assert 0 < s["labelled_both"] < 20
    args2 = _args(tmp_path, inp, budget=1.0)
    db.run(cfg, screen, args2, post=FakeRouter(llm, clf), sleep=lambda s: None)
    s2 = json.loads(open(os.path.join(args.output_dir, "summary.json")).read())
    assert s2["labelled_both"] == 20 and s2["stopped"] == ""


def test_spend_already_at_the_cap_sends_nothing(tmp_path):
    cfg, screen = _cfgs()
    inp = _input(tmp_path, 5)
    db.run(cfg, screen, _args(tmp_path, inp), post=FakeRouter(LLM5, CLF5), sleep=lambda s: None)
    (tmp_path / "b").mkdir()
    more = _input(tmp_path / "b", 8)
    router = FakeRouter({**LLM5, 6: "out", 7: "out", 8: "out"},
                        {**CLF5, 6: ("out", 1), 7: ("out", 1), 8: ("out", 1)})
    db.run(cfg, screen, _args(tmp_path, more, budget=0.0001), post=router, sleep=lambda s: None)
    assert router.calls == []


def test_a_call_without_reported_cost_is_charged_its_reservation(tmp_path):
    cfg, screen = _cfgs()
    router = FakeRouter(LLM5, CLF5)
    router.report_cost = False
    args = _args(tmp_path, _input(tmp_path, 2))
    db.run(cfg, screen, args, post=router, sleep=lambda s: None)
    s = json.loads(open(os.path.join(args.output_dir, "summary.json")).read())
    assert s["spent_usd"] == pytest.approx(cfg["designb"]["llm"]["est_cost_per_call"]
                                           + 2 * cfg["designb"]["classifier"]["est_cost_per_call"])
    assert s["calls_without_reported_cost"] == 3


def test_an_unexpected_served_model_stops_the_run_and_writes_no_label(tmp_path):
    cfg, screen = _cfgs()
    router = FakeRouter(LLM5, CLF5)
    router.served["classifier"] = "typesafe/jev-1.14-20261101"
    args = _args(tmp_path, _input(tmp_path, 5))
    db.run(cfg, screen, args, post=router, sleep=lambda s: None)
    assert _labels(args.output_dir, "classifier") == {}
    s = json.loads(open(os.path.join(args.output_dir, "summary.json")).read())
    assert "not in the accepted list" in s["stopped"] and s["labelled_both"] == 0


def test_run_import_view_end_to_end(tmp_path):
    """Runner -> icf_screen rows -> REL view: the design-B rule decides the status."""
    cfg, screen = _cfgs()
    args = _args(tmp_path, _input(tmp_path, 5))
    db.run(cfg, screen, args, post=FakeRouter(LLM5, CLF5), sleep=lambda s: None)
    with open(os.path.join(args.output_dir, "run.log"), "w") as fh:  # the run's stderr
        fh.write("INFO labelled 5, unlabelled 0 (rerun to retry)\n")
    joint = rv.joint_rule(screen["stage1_joint"])
    rows, half = ci.designb_rows(args.output_dir, args.input, "designB-test", joint)
    assert half == 0 and len(rows) == 10
    table = str(tmp_path / "rel_screen" / "icf_screen.csv")
    ics.append_rows(table, rows, new_table=True)
    pool = [{**{f: "" for f in rv.POOL_FIELDS}, "work_key": f"openalex:W{i}",
             "openalex_id": f"W{i}", "all_openalex_ids": f"W{i}", "title": f"Title {i}",
             "year": "2020"} for i in range(1, 6)]
    window = {"search_date": "2026-09-28", "year_min": 1990, "last_complete_year": 2025,
              "partial_year": 2026, "require_full_date_for_partial_year": True}
    view, _ = rv.build_view(pool, ics.read_table(table), window, rv.screen_rule(screen))
    assert {r["work_key"]: r["status"] for r in view} == {
        "openalex:W1": "stage1_out",        # both out, P 0.99
        "openalex:W2": "pending_stage2",    # both out, P just below the threshold
        "openalex:W3": "pending_stage2",    # LLM aux
        "openalex:W4": "pending_stage2",    # classifier aux
        "openalex:W5": "pending_stage2"}


def test_parse_classifier_rejects_malformed_answers():
    ok = {"answers": {"label": {"choice": "out", "probabilities": {"out": 0.97}},
                      "doc": {"choice": "institutional"}}}
    assert db.parse_classifier(ok) == {"label": "out", "doc": "institutional", "p_out": 0.97,
                                       "probabilities": {"out": 0.97}}
    assert db.parse_classifier({"answers": {"label": {"choice": "out"}}}) is None
    assert db.parse_classifier({"answers": {"label": {"choice": "out",
                                                      "probabilities": {"out": 1.7}}}}) is None
    assert db.parse_classifier({}) is None


@pytest.mark.parametrize("block", [None, {"llm_models": [GEMMA]},
                                   {"llm_models": [GEMMA], "classifier_models": [JEV],
                                    "classifier_p_out_min": 2}])
def test_runner_refuses_a_missing_or_malformed_stage1_joint_block(tmp_path, block):
    cfg, screen = _cfgs()
    screen = {k: v for k, v in screen.items() if k != "stage1_joint"}
    if block is not None:
        screen["stage1_joint"] = block
    router = FakeRouter(LLM5, CLF5)
    assert db.run(cfg, screen, _args(tmp_path, _input(tmp_path, 2)), post=router,
                  sleep=lambda s: None) == 2
    assert router.calls == []


def test_settled_balance_waits_until_key_usage_stops_moving():
    readings = iter([1.0, 1.2, 1.5, 1.5, 1.5, 1.5, 1.5])
    snap = db.settled_balance("k", wait_s=600, quiet_s=45, sleep=lambda s: None,
                              read=lambda k: {"key": {"usage": next(readings)}})
    assert snap["key"]["usage"] == 1.5 and snap["settled_after_s"] == 75
    capped = db.settled_balance("k", wait_s=30, sleep=lambda s: None,
                                read=lambda k, it=iter(range(100)): {"key": {"usage": next(it)}})
    assert capped["settled_after_s"] == 30


def test_key_usage_delta():
    assert db.key_usage_delta({"key": {"usage": 124.4}}, {"key": {"usage": 129.8}}) == 5.4
    assert db.key_usage_delta({}, {"key": {"usage": 1}}) is None


def test_budget_reservations_never_cross_the_cap():
    b = db.Budget(0.001)
    assert b.reserve(0.0006) and not b.reserve(0.0006) and b.stopped
    b2 = db.Budget(0.01)
    b2.settle("llm", 0.0, 0.002)
    assert b2.estimate("llm", 0.001) == pytest.approx(0.003)
