"""Strict, independent ICF facets; scores are memberships, never probabilities."""
import json
import re
from collections import Counter
from collections.abc import Iterable

import _icf_screen as ics

FACETS = ("international", "climate", "finance")
SCORES = {0, .5, 1}
PREFIXES = {0: "contrary:", .5: "insufficient:", 1: "supporting:"}
ANSWER_FIELDS = {"n", "main_object", "doc", "studied", "contrib", "field", "ctype",
                 "discipline_evidence", "input_quality", *FACETS, *(f + "_evidence" for f in FACETS)}


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key}")
        result[key] = value
    return result


def membership(answer: dict) -> float:
    return min(answer[f] for f in FACETS)


def legacy_label(answer: dict) -> str:
    value = membership(answer)
    if value == 1:
        return "icf"
    if value == .5:
        return "unsure"
    return "out" if all(answer[f] == 0 for f in FACETS) else "aux"



def validate_answer(row: dict) -> None:
    """Check independent scores, evidence and unscored vocabulary without coercion."""
    if set(row) != ANSWER_FIELDS:
        raise ValueError("missing or unexpected fields")
    for facet in FACETS:
        score = row[facet]
        if type(score) not in {float, int} or score not in SCORES:
            raise ValueError(f"invalid {facet} membership")
        evidence = row[facet + "_evidence"]
        if not isinstance(evidence, str) or not evidence.startswith(PREFIXES[score]):
            raise ValueError(f"inconsistent {facet} evidence")
        if not evidence[len(PREFIXES[score]):].strip():
            raise ValueError("empty evidence")
    for field in ("main_object", "studied", "discipline_evidence"):
        if not isinstance(row[field], str) or not row[field].strip():
            raise ValueError(f"empty {field}")
    vocabularies = {"input_quality": {"usable", "absent", "nonabstract", "truncated"}, "doc": ics.DOC_TYPES, "contrib": {"yes", "no", "unsure"},
                    "field": ics.FIELDS - {"na"}, "ctype": ics.CONTRIB_TYPES - {"na"}}
    for field, allowed in vocabularies.items():
        if row[field] not in allowed:
            raise ValueError(f"invalid {field}")


def parse_answers(lines: Iterable[str], keys: list[str]) -> tuple[dict, list[str]]:
    """Quarantine ambiguity; a malformed ordinal cannot silently become a decision."""
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate mapped work keys")
    candidates = []
    faults = []
    mentioned = []
    ambiguous = False
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        ordinal = None
        try:
            row = json.loads(line, object_pairs_hook=_unique_object)
            if not isinstance(row, dict):
                raise ValueError("answer is not an object")
            ordinal = row.get("n")
            if type(ordinal) is not int or not 1 <= ordinal <= len(keys):
                ambiguous = True
                raise ValueError("invalid ordinal")
            mentioned.append(ordinal)
            validate_answer(row)
            candidates.append(row)
        except (ValueError, TypeError) as exc:
            if "duplicate JSON field" in str(exc) or ordinal is None:
                ambiguous = True
            faults.append(f"line {number}: {exc}")
    counts = Counter(mentioned)
    duplicate = {n for n, count in counts.items() if count > 1}
    if duplicate:
        faults.append(f"duplicate ordinals: {sorted(duplicate)}")
    answers = {} if ambiguous else {keys[r["n"] - 1]: r for r in candidates
                                   if r["n"] not in duplicate}
    missing = [n for n, key in enumerate(keys, 1) if key not in answers]
    if missing:
        faults.append(f"missing ordinals: {missing}")
    return answers, faults


def guard_quality(answers: dict, records: dict) -> tuple[dict, list[str]]:
    """Keep unsupported damaged-input negatives pending without editing raw answers.

    A poor-quality negative must cite an exact title phrase. The citation is
    structural evidence, not certification of semantic truth; instrument review
    still checks whether that title establishes the claimed contrary object.
    """
    valid, faults = {}, []
    for key, answer in answers.items():
        record = records[key]
        quality = "absent" if not record.get("abstract", "").strip() else answer["input_quality"]
        if quality == "usable":
            valid[key] = answer
            continue
        title = record.get("title", "")
        negatives = [f + "_evidence" for f in FACETS if answer[f] == 0]
        if answer["contrib"] == "no":
            negatives.append("discipline_evidence")
        unsupported = []
        for field in negatives:
            # Require source identification plus a literal supplied-title anchor.
            matches = re.findall(r'title:\s*"([^"\n]+)"', answer[field], re.IGNORECASE)
            if not any(phrase.strip() and phrase in title for phrase in matches):
                unsupported.append(field)
        if unsupported:
            faults.append(f"{key}: unsupported {quality} negative: {unsupported}")
        else:
            valid[key] = answer
    return valid, faults


def effective_answer(answer: dict, record: dict) -> tuple[dict, str, list[str]]:
    """Quality-guarded copy; native scores/evidence remain untouched.

    Missing substantive evidence changes only unsupported negatives to unsure.
    Exact supplied-title quotations establish provenance only. Automatic imports
    abstain on every poor-input negative pending separate semantic adjudication.
    """
    effective = dict(answer)
    quality = "absent" if not record.get("abstract", "").strip() else (
        "truncated" if record.get("quality_hint") == "truncated" else answer["input_quality"])
    reasons = []
    if quality != "usable":
        for facet in FACETS:
            if answer[facet] == 0:
                effective[facet] = .5
                effective[facet + "_evidence"] = f"insufficient: quality guard; {quality} substantive evidence"
                reasons.append(f"{facet}: unsupported {quality} negative")
        if answer["contrib"] == "no":
            effective["contrib"] = "unsure"
            effective["discipline_evidence"] = f"insufficient: quality guard; {quality} substantive evidence"
            reasons.append(f"contrib: unsupported {quality} negative")
    effective["input_quality"] = quality
    return effective, "unresolved" if reasons else "accepted", reasons

