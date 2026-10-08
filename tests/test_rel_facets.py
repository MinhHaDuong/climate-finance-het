"""Independent ICF memberships preserve uncertain evidence and discipline."""
import itertools
import json

import pytest

import _rel_facets as facets

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
