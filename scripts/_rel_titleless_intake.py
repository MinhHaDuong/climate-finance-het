"""Exact operator-approved native-titleless admission, never invented metadata.

The frozen registry authenticates the approved local manifest selection. Native
page checks establish archived source correspondence; they do not independently
authenticate an arbitrary provider response. No network or model call occurs.
"""
import gzip
import hashlib
import json
from pathlib import Path

from openalex_corpus import normalize_doi, reconstruct_abstract
from utils import DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = "native_titleless_provenance"
INTAKE_ROOT = Path(DATA_DIR) / "rel_intake"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def intake_registry():
    with (ROOT / "config/rel_titleless_policy.json").open(encoding="utf-8") as fh:
        return json.load(fh)["intake"]


def verified_path(root, reference):
    path = (root / reference["path"]).resolve()
    if not path.is_relative_to(root.resolve()) or digest(path) != reference["sha256"]:
        raise ValueError("titleless archive path/hash mismatch")
    return path


def native_fields(work):
    """Same full source fields as the normal OpenAlex intake producer."""
    source = ((work.get("primary_location") or {}).get("source") or {})
    countries = sorted({c for a in work.get("authorships") or [] for c in a.get("countries") or []})
    return {"title": work.get("display_name") or work.get("title") or "",
            "abstract": reconstruct_abstract(work.get("abstract_inverted_index")) or "",
            "year": str(work.get("publication_year") or ""), "language": work.get("language") or "",
            "journal": source.get("display_name") or "", "affiliation_countries": "; ".join(countries),
            "doc_type": work.get("type") or "", "is_paratext": "" if work.get("is_paratext") is None else str(work["is_paratext"]).lower()}


def validate_admission(root, manifest, records, registry=None):
    """Return exact record provenance only after every approved native binding passes."""
    root = Path(root)
    declaration = manifest.get("native_titleless")
    if not declaration:
        return {}
    registry = intake_registry() if registry is None else registry
    if digest(root / "manifest.json") != registry["approved_manifest_sha256"]:
        raise ValueError("unregistered titleless intake manifest")
    if declaration.get("version") != 1 or declaration.get("basis") != "native_titleless":
        raise ValueError("unsupported titleless admission basis")
    authority = declaration["authority"]
    if authority["sha256"] != registry["authority_sha256"]:
        raise ValueError("unapproved titleless authority")
    verified_path(root, authority)
    roster = json.loads(verified_path(root, declaration["roster"]).read_text())
    by_record = {r["record_id"]: r for r in records}
    keys = [p["record_id"] for p in roster]
    if (len(keys) != registry["records"] or len(set(keys)) != len(keys)
            or set(keys) != set(by_record) or len(by_record) != len(records)):
        raise ValueError("titleless intake roster mismatch")
    result, identities, dois, pages = {}, set(), set(), {}
    for proof in roster:
        record = by_record[proof["record_id"]]
        if (proof.get("source_type") != "openalex" or proof.get("native_title_empty") is not True
                or record.get("platform") != "openalex"
                or any(record.get(k) != proof.get(k) for k in ("record_id", "query_id", "openalex_id", "doi", "retrieved_at"))
                or not record.get("openalex_id") or not record.get("doi")):
            raise ValueError("titleless identity/source binding mismatch")
        identity, doi = record["openalex_id"], normalize_doi(record["doi"])
        if doi != record["doi"] or identity in identities or doi in dois:
            raise ValueError("titleless identity is ambiguous or not canonical")
        identities.add(identity)
        dois.add(doi)
        reference = (proof["native_archive_path"], proof["native_compressed_sha256"])
        if reference not in pages:
            path = verified_path(root, {"path": reference[0], "sha256": reference[1]})
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                page = json.load(fh)
            pages[reference] = (page, hashlib.sha256(encoded(page["body"]).encode()).hexdigest(),
                                hashlib.sha256(encoded(page["query"]).encode()).hexdigest())
        page, body_sha, query_sha = pages[reference]
        body = page["body"]
        if (page.get("status") != 200 or page.get("retrieved_at") != proof["retrieved_at"]
                or body_sha != proof["native_body_sha256"]
                or query_sha != proof["source_query_sha256"]):
            raise ValueError("titleless native response/query mismatch")
        matches = [w for w in body["results"] if str(w.get("id", "")).rsplit("/", 1)[-1] == identity
                   and normalize_doi(w.get("doi")) == doi]
        if len(matches) != 1 or hashlib.sha256(encoded(matches[0]).encode()).hexdigest() != proof["native_work_sha256"]:
            raise ValueError("titleless native work is absent or ambiguous")
        native = matches[0]
        if (native.get("title") or "").strip() or (native.get("display_name") or "").strip():
            raise ValueError("native title is not empty")
        if any(str(record.get(k) or "") != value for k, value in native_fields(native).items()):
            raise ValueError("titleless complete native fields differ")
        result[proof["record_id"]] = encoded({"manifest": f"{manifest['lane']}/{manifest['delivery']}/manifest.json",
            "manifest_sha256": registry["approved_manifest_sha256"], "record_id": proof["record_id"]})
    return result


def pool_admission(record, intake_root=None):
    """Revalidate discoverable source admission for a derived pool row."""
    provenance = record.get(PROVENANCE) or ""
    if not provenance:
        return False
    binding = json.loads(provenance)
    root = Path(intake_root) if intake_root is not None else INTAKE_ROOT
    path = (root / binding["manifest"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("titleless pool source outside intake root")
    if digest(path) != binding["manifest_sha256"]:
        raise ValueError("titleless pool provenance changed")
    import csv
    with (path.parent / "records.csv").open(encoding="utf-8", newline="") as fh:
        records = list(csv.DictReader(fh))
    manifest = json.loads(path.read_text())
    proofs = validate_admission(path.parent, manifest, records)
    original = next(r for r in records if r["record_id"] == binding["record_id"])
    if binding["record_id"] not in proofs or any(record.get(k, "") != original.get(k, "")
            for k in ("openalex_id", "doi", "title", "abstract", "year", "language", "journal", "affiliation_countries", "doc_type", "is_paratext")):
        raise ValueError("titleless pool/source correspondence changed")
    if record.get("work_key") != f"openalex:{record['openalex_id']}":
        raise ValueError("titleless stable work identity changed")
    expected_member = f"{manifest['lane']}/{manifest['delivery']}:{binding['record_id']}"
    if expected_member not in record.get("member_record_ids", "").split(";"):
        raise ValueError("titleless source outside exact pool family")
    return True


def read_pool(path):
    """Keep optional admission columns; existing view loader intentionally projects them."""
    import csv
    csv.field_size_limit(1 << 30)
    with open(path, encoding="utf-8", newline="") as fh:
        return [{k: value or "" for k, value in row.items()} for row in csv.DictReader(fh)]
