"""Versioned full-public-input ICF instrument and append-only import (2010).

Private maps never enter a request. UTF-8 byte counts conservatively bound
input tokens; requests exceeding either configured bound are refused, not clipped.
"""
import hashlib
import json
import os
import re
from collections import Counter

import _icf_screen as ics
import _rel_facets as facets
from utils import normalize_title

PUBLIC_FIELDS = ("title", "year", "abstract", "language", "journal", "countries")
COLUMNS = ["facet_id", *ics.KEY, "labeller", "prompt_sha256", "machine", "labelled_at",
           "source", "method_sha256", "request_sha256", "native_sha256", "record_sha256",
           "proof_sha256", "native_answer", "effective_answer", "input_quality",
           "guard_disposition", "guard_reasons", "quality_origin"]
SCHEMA = ics.Schema(COLUMNS, "facet_id", [c for c in COLUMNS if c != "facet_id"],
                    (("stage", {"2", "audit"}), ("labeller", ics.MODEL_LABELLERS),
                     ("input_quality", {"usable", "absent", "nonabstract", "truncated"}),
                     ("guard_disposition", {"accepted", "unresolved"})))
VIEW_COLUMNS = [*[f"mu_{f}" for f in facets.FACETS], "icf_instrument",
                "icf_method_sha256", "icf_guard_disposition", "icf_input_quality",
                *[f"mu_native_{f}" for f in facets.FACETS], "icf_native_input_quality",
                "icf_guard_reasons", "icf_quality_origin", "icf_native_sha256", "icf_request_sha256"]


def encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def public_record(record: dict) -> dict:
    """Only approved public bibliographic fields, with complete source strings."""
    return {f: record.get(f, [] if f == "countries" else "") for f in PUBLIC_FIELDS}


def proof_hash(record: dict) -> str:
    # Same canonical full-field hash as the provenance archive, including JSON spaces.
    return sha(json.dumps(public_record(record), ensure_ascii=False, sort_keys=True))


def method(config: dict) -> tuple[dict, str]:
    with open(config["prompt"], encoding="utf-8") as fh:
        prompt = fh.read()
    with open(config["lexicon"], encoding="utf-8") as fh:
        lexicon = fh.read()
    frozen = dict(config, prompt_text=prompt, lexicon_text=lexicon,
                  answer_fields=sorted(facets.ANSWER_FIELDS), quality_guard="v3.2")
    return frozen, sha(encoded(frozen))


def render_request(records: list[dict], frozen: dict) -> str:
    """API-safe complete JSONL; the ordinal is the only identifier sent."""
    text = "\n".join(encoded(dict(public_record(r), n=n,
                               quality_hint="usable" if r["abstract"].strip() else "absent"))
                     for n, r in enumerate(records, 1))
    return frozen["prompt_text"].replace("{lexicon}", frozen["lexicon_text"]).replace("{records}", text)




def family_source_ids(pool_record: dict) -> set[str]:
    """Exact declared source membership; no title or DOI fuzzy joins."""
    ids = {"openalex:" + x for x in pool_record.get("all_openalex_ids", "").split(";") if x}
    if pool_record.get("openalex_id"):
        ids.add("openalex:" + pool_record["openalex_id"])
    for member in pool_record.get("member_record_ids", "").split(";"):
        handle = member.partition(":")[2]
        if handle.startswith("RePEc:"):
            ids.add("repec_redif:" + handle)
    return ids


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def valid_public_proof(record: dict, proof: dict | None, family_sources: set[str]) -> bool:
    """Exact complete-field bindings to declared public native sources only.

    Legacy direct OpenAlex proofs remain accepted for their original record.
    Fieldwise proofs additionally freeze source-native hashes and value hashes;
    the caller supplies exact pool membership, never inferred alias matches.

    Trust boundary: inputs are operator-approved local producer attestations.
    These checks establish field/hash/family consistency, not authentication of
    arbitrary proof JSON or independent verification of archived native blobs.
    The public-source producer must verify complete fields against native source
    bodies before approving a proof for transmission; record text stays data.
    """
    if not proof or proof.get("work_key") != record["work_key"] or proof.get("full_sixfield_sha256") != proof_hash(record):
        return False
    if proof.get("source_type") != "public_fieldwise":
        return (bool(proof.get("native_openalex_id")) and proof["native_openalex_id"] == record.get("openalex_id")
                and f"openalex:{proof['native_openalex_id']}" in family_sources
                and not proof.get("source_type"))
    declared = proof.get("declared_source_ids")
    evidence = proof.get("field_evidence")
    if (not isinstance(declared, list) or any(not isinstance(x, str) for x in declared)
            or not declared or not set(declared) <= family_sources
            or not isinstance(evidence, dict) or set(evidence) != set(PUBLIC_FIELDS)):
        return False
    for field, value in public_record(record).items():
        binding = evidence[field]
        if not isinstance(binding, dict) or binding.get("sha256") != sha(encoded(value)):
            return False
        sources = binding.get("sources")
        if not isinstance(sources, list) or not sources:
            return False
        if any(not _valid_source(source, declared, proof) for source in sources):
            return False
    return True


def _valid_source(source: object, declared: list[str], proof: dict) -> bool:
    if not isinstance(source, dict) or not _is_sha(source.get("native_sha256")):
        return False
    kind, source_id = source.get("source_type"), source.get("source_id")
    if not isinstance(kind, str) or kind not in {"openalex", "repec_redif"} or not isinstance(source_id, str) or f"{kind}:{source_id}" not in declared:
        return False
    if kind == "openalex":
        return bool(re.fullmatch(r"W[0-9]+", source_id)) and source.get("source_url") == f"https://api.openalex.org/works/{source_id}"
    return (source_id.startswith("RePEc:") and source.get("source_url") == "rsync://rsync.repec.org/RePEc-ReDIF/"
            and bool(source.get("source_archive") or proof.get("source_archive"))
            and _is_sha(source.get("source_manifest_sha256") or proof.get("source_manifest_sha256")))


def _validate_inputs(records: list[dict], proofs: list[dict], config: dict) -> dict:
    by_proof = {}
    for p in proofs:
        if p["work_key"] in by_proof:
            raise ValueError("duplicate public proof key")
        by_proof[p["work_key"]] = p
    if len({r["work_key"] for r in records}) != len(records):
        raise ValueError("duplicate input work key")
    bounds = [config[k] for k in ("max_records", "max_request_bytes", "max_input_tokens",
                                 "reserved_output_tokens")]
    if any(type(v) is not int or v <= 0 for v in bounds):
        raise ValueError("packing bounds must be positive integers")
    return by_proof


def write_chunks(out_dir: str, records: list[dict], proofs: list[dict], config: dict,
                 family_sources: dict[str, set[str]] | None = None) -> dict:
    """Freeze proven complete records, private maps and byte-budgeted requests.

    A proof must identify the original public source and bind all six complete
    fields. Unproven rows remain local and are counted in build.json.
    """
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise ValueError(f"{out_dir} is not empty; choose a fresh run directory")
    frozen, method_sha = method(config)
    by_proof = _validate_inputs(records, proofs, config)
    limit = min(config["max_request_bytes"], config["max_input_tokens"])
    accepted, pending = [], []
    for r in records:
        p = by_proof.get(r["work_key"])
        values = public_record(r)
        if (any(not isinstance(values[f], str) for f in PUBLIC_FIELDS if f != "countries")
                or not isinstance(values["countries"], list)
                or any(not isinstance(c, str) for c in values["countries"])):
            raise ValueError("public fields must be strings and countries a string list")
        # Without a pool supplied by the CLI, only the exact canonical OA key
        # can anchor a legacy proof; an input's asserted OA id is not membership.
        fallback = {r["work_key"]} if r["work_key"].startswith("openalex:") else set()
        declared_family = family_sources.get(r["work_key"], set()) if family_sources is not None else fallback
        if not valid_public_proof(r, p, declared_family):
            pending.append(r["work_key"])
        else:
            accepted.append(dict(r, public_proof=p, source_family=sorted(declared_family)))
    chunks, current = [], []
    for r in accepted:
        candidate = current + [r]
        if len(candidate) > config["max_records"] or len(render_request(candidate, frozen).encode()) > limit:
            if current:
                chunks.append(current)
            current = [r]
        else:
            current = candidate
        if len(render_request(current, frozen).encode()) > limit:
            raise ValueError(f"{r['work_key']}: complete record exceeds request budget; nothing written")
    if current:
        chunks.append(current)
    manifest = {"method": frozen, "method_sha256": method_sha, "chunks": {},
                "proven": len(accepted), "unproven": pending,
                "quality": dict(Counter("usable" if r["abstract"].strip() else "absent"
                                        for r in accepted))}
    os.makedirs(out_dir, exist_ok=True)
    for n, chunk in enumerate(chunks, 1):
        name = f"chunk{n:02d}"
        request = render_request(chunk, frozen)
        private = {"keys": [r["work_key"] for r in chunk], "records": chunk}
        manifest["chunks"][name] = {"request_sha256": sha(request),
                                    "private_sha256": sha(encoded(private)),
                                    "input_tokens_upper_bound": len(request.encode()),
                                    "reserved_output_tokens": config["reserved_output_tokens"]}
        with open(os.path.join(out_dir, name + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(request)
        with open(os.path.join(out_dir, name + ".private.json"), "w", encoding="utf-8") as fh:
            fh.write(encoded(private) + "\n")
    with open(os.path.join(out_dir, "build.json"), "w", encoding="utf-8") as fh:
        fh.write(encoded(manifest) + "\n")
    return manifest


def parse_chunks(chunk_dir: str, suffix: str, metadata: dict) -> tuple[list, list, list, dict]:
    """Derive guarded imports from immutable native answer files and frozen maps."""
    with open(os.path.join(chunk_dir, "build.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    frozen = manifest["method"]
    if sha(encoded(frozen)) != manifest["method_sha256"]:
        raise ValueError("frozen method hash mismatch")
    raw_rows, labels, dims, report = [], [], [], {}
    for name, stamp in manifest["chunks"].items():
        with open(os.path.join(chunk_dir, name + ".txt"), encoding="utf-8") as fh:
            request = fh.read()
        with open(os.path.join(chunk_dir, name + ".private.json"), encoding="utf-8") as fh:
            private = json.load(fh)
        if sha(request) != stamp["request_sha256"] or sha(encoded(private)) != stamp["private_sha256"]:
            raise ValueError(f"{name}: request/private mapping changed")
        records = private["records"]
        keys = private["keys"]
        if keys != [r["work_key"] for r in records] or request != render_request(records, frozen):
            raise ValueError(f"{name}: ordinal mapping differs from frozen request")
        for r in records:
            if not valid_public_proof(r, r["public_proof"], set(r["source_family"])):
                raise ValueError(f"{name}: public proof mismatch")
        answer_path = os.path.join(chunk_dir, f"{name}.{suffix}.txt")
        if not os.path.exists(answer_path):
            report[name] = {"answered": 0, "pending": len(keys), "faults": ["absent answers"]}
            continue
        with open(answer_path, encoding="utf-8") as fh:
            native = fh.read()
        answers, faults = facets.parse_answers(native.split("\n"), keys)
        report[name] = {"answered": len(answers), "pending": len(keys) - len(answers), "faults": faults}
        for r in records:
            key = r["work_key"]
            if key not in answers:
                continue
            answer = answers[key]
            # This formatter sends complete source fields, never a transport prefix.
            # Only transmitted source absence and native model quality govern;
            # unsent extra input keys cannot become transport-quality evidence.
            effective, disposition, reasons = facets.effective_answer(answer, public_record(r))
            common = dict(metadata, work_key=key, prompt_sha256=sha(frozen["prompt_text"]),
                          source=f"{os.path.basename(chunk_dir)}/{name}.{suffix}.txt")
            raw_rows.append(dict(common, method_sha256=manifest["method_sha256"],
                                 request_sha256=stamp["request_sha256"], native_sha256=sha(native),
                                 record_sha256=proof_hash(r), proof_sha256=sha(encoded(r["public_proof"])),
                                 native_answer=encoded(answer), effective_answer=encoded(effective),
                                 input_quality=effective["input_quality"], guard_disposition=disposition,
                                 quality_origin="source_empty" if not r["abstract"].strip() else "model_assessed",
                                 guard_reasons=encoded(reasons)))
            labels.append(dict(common, openalex_id=r.get("openalex_id", ""), doi=r.get("doi", ""),
                               title_norm_year=f"{normalize_title(r['title'])}|{r['year']}",
                               label=facets.legacy_label(effective), doc_type=answer["doc"],
                               studied_country=answer["studied"],
                               why=encoded({"native_label": facets.legacy_label(answer),
                                            "guard": disposition, "reasons": reasons,
                                            "main_object": answer["main_object"]})))
            dims.append(dict(common, contrib=effective["contrib"], field=answer["field"],
                             contrib_type=answer["ctype"]))
    return raw_rows, labels, dims, report


def append_batches(batches: list[tuple[str, list, ics.Schema, bool]],
                   message: str = "faceted Stage2 v3.2") -> list[tuple[int, int]]:
    """Preflight every table before writing; identical repeats are idempotent.

    A changed response under an existing run key is refused, never silently
    skipped. Interrupted multi-table imports can safely resume the same batch.
    """
    for path, rows, schema, new in batches:
        ics._refuse_fork(path, new)
        existing = {ics.key_of(r): r for r in ics.read_table(path, schema)}
        seen = set()
        for row in rows:
            faults = ics.validate_row(row, schema)
            key = ics.key_of(row)
            if key in seen:
                faults.append("duplicate batch key")
            seen.add(key)
            if key in existing and any(str(row.get(c, "")) != existing[key][c]
                                       for c in schema.columns if c != schema.id_column):
                faults.append("existing run key has different payload")
            if faults:
                raise ics.IcfScreenError(f"{path}: {faults}; nothing written")
    return [ics.append_new(path, rows, message, new, schema)
            for path, rows, schema, new in batches]



def validated_judgment(judgment: dict) -> tuple[dict, dict]:
    """Revalidate persisted schemas and the deterministic native-to-effective guard."""
    native = json.loads(judgment["native_answer"], object_pairs_hook=facets._unique_object)
    effective = json.loads(judgment["effective_answer"], object_pairs_hook=facets._unique_object)
    for name, answer in (("native", native), ("effective", effective)):
        if not isinstance(answer, dict) or type(answer.get("n")) is not int or answer["n"] < 1:
            raise ValueError(f"invalid persisted {name} facet answer")
        checked, faults = facets.parse_answers([encoded(dict(answer, n=1))], [judgment["work_key"]])
        if not checked or faults:
            raise ValueError(f"invalid persisted {name} facet answer: {faults}")
    origin = judgment["quality_origin"]
    if origin not in {"source_empty", "model_assessed"}:
        raise ValueError("invalid persisted effective quality origin")
    expected, disposition, reasons = facets.effective_answer(
        native, {"abstract": "" if origin == "source_empty" else "nonempty source field"})
    if (effective != expected or judgment["input_quality"] != expected["input_quality"]
            or judgment["guard_disposition"] != disposition
            or json.loads(judgment["guard_reasons"]) != reasons):
        raise ValueError("persisted guard derivation disagrees with native answer")
    return native, effective


def assign_view(rows: list[dict], judgments: list[dict]) -> dict:
    """Expose only actual facets of the deciding Stage2 run; legacy stays blank."""
    index = {ics.key_of(j): j for j in judgments}
    qualities, guards, changes = Counter(), Counter(), Counter()
    for row in rows:
        row.update({c: "" for c in VIEW_COLUMNS})
        row["icf_instrument"] = "legacy_aggregate" if row["stage2_label"] or row["stage1_label"] else "unscored"
        key = (row["work_key"], "2", row["stage2_model"], row["stage2_run_id"])
        if key not in index:
            continue
        j = index[key]
        native, a = validated_judgment(j)
        if facets.legacy_label(a) != row["stage2_label"]:
            raise ValueError("facet-derived label disagrees with deciding canonical label")
        for f in facets.FACETS:
            row["mu_" + f] = format(a[f], ".15g")
            row["mu_native_" + f] = format(native[f], ".15g")
            changes[f] += native[f] != a[f]
        changes["contrib"] += native["contrib"] != a["contrib"]
        row.update(icf_instrument="three_facets_v3.2", icf_method_sha256=j["method_sha256"],
                   icf_guard_disposition=j["guard_disposition"], icf_input_quality=j["input_quality"],
                   icf_native_input_quality=native["input_quality"], icf_guard_reasons=j["guard_reasons"],
                   icf_quality_origin=j["quality_origin"],
                   icf_native_sha256=j["native_sha256"], icf_request_sha256=j["request_sha256"])
        qualities[j["input_quality"]] += 1
        guards[j["guard_disposition"]] += 1
    return {"judgment_rows": len(judgments), "deciding_quality": dict(qualities),
            "guard_dispositions": dict(guards), "overridden_fields": dict(changes),
            "delivery": "complete_source_fields_without_clipping"}
