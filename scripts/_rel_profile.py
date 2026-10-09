"""REL minimum metadata profile: the DataCite mandatory set (ticket 2043, child of 0700).

Pure functions over one pool work (a dict with the pool columns, plus the
optional intake columns ``repec_handle`` (ticket 2040) and ``host_org_name``
(ticket 2041)). Declared in ``config/rel_profile.yaml`` (one block, versioned);
``corpus_rel_view.py`` and ``corpus_rel_profile.py`` do the I/O.

The six DataCite mandatory properties, as read on a pool work:

- ``identifier``: a DOI or an OpenAlex id; else a persistent id among the
  member record ids or ``repec_handle``: a RePEc, hdl, oai or HAL handle, or an
  id of a registered repository platform (``identifier.platforms``) in the form
  that platform resolves. A title key (``title:``, ``ty:``) or the id of an
  unregistered site is not one;
- ``creator``: ``first_author`` or ``all_authors`` not blank;
- ``title``: at least one letter or digit;
- ``publisher``: resolved in the configured order, else unresolved. First the
  OpenAlex host organization of the work's source (``host_org_name``). Then the
  registrant of the DOI prefix, when the prefix is a ``publisher`` row of
  ``config/rel_doi_prefixes.csv``. A ``platform`` prefix (SSRN, Zenodo,
  Figshare, JSTOR...) hosts other people's work and resolves nothing, and a
  journal name is not a publisher;
- ``publicationYear``: four digits;
- ``resourceType``: ``doc_type`` not blank.

``missing_fields`` returns every missing property, whatever is required, so the
view records the full picture (``profile_missing``) and the required subset
decides the exclusion (``profile_missing_<field>``, first in declared order).
"""

import csv
import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_profile.yaml")
FIELDS = ["identifier", "creator", "title", "publisher", "publicationYear", "resourceType"]
CODE_PREFIX = "profile_missing_"

_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_OPENALEX = re.compile(r"^W\d+$")
_GENERIC = {
    "repec": re.compile(r"^RePEc:[^:\s]+:[^:\s]+:\S+$", re.IGNORECASE),
    "hdl": re.compile(r"^hdl:\S+/\S+$"),
    "oai": re.compile(r"^oai:[^:\s]+:\S+$"),
    "hal": re.compile(r"^(?:hal|halshs|tel|medihal)-\d+$", re.IGNORECASE),
}


def load_profile(path: str = DEFAULT_CONFIG) -> dict:
    """The profile block, validated, with the DOI-prefix table loaded."""
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    required = list(cfg["required"])
    unknown = [f for f in required if f not in FIELDS]
    if unknown:
        raise ValueError(f"rel_profile.required: unknown fields {unknown}; known {FIELDS}")
    generic = list(cfg["identifier"]["generic"])
    if any(g not in _GENERIC for g in generic):
        raise ValueError(f"rel_profile.identifier.generic: known forms {sorted(_GENERIC)}")
    order = list(cfg["publisher"]["order"])
    if any(o not in ("host_org", "doi_prefix") for o in order):
        raise ValueError("rel_profile.publisher.order: host_org and doi_prefix only")
    table = os.path.join(ROOT, cfg["publisher"]["prefix_table"])
    with open(table, encoding="utf-8", newline="") as fh:
        prefixes = {r["prefix"]: (r["registrant"], r["kind"]) for r in csv.DictReader(fh)}
    if any(k not in ("publisher", "platform") for _, k in prefixes.values()):
        raise ValueError(f"{table}: kind must be publisher or platform")
    platforms = {}
    for name, spec in cfg["identifier"]["platforms"].items():
        if not spec.get("url"):
            raise ValueError(f"rel_profile.identifier.platforms.{name}: a resolvable url is required")
        platforms[name] = re.compile(spec["id"])
    return {"version": cfg["version"], "enabled": bool(cfg["enabled"]), "required": required,
            "generic": generic, "platforms": platforms, "order": order, "prefixes": prefixes}


def rule(profile: dict, enabled: bool | None = None, required: list | None = None) -> dict:
    """The switch as it enters the seriousness rule and ``rel_counts.json``."""
    return {"version": profile["version"],
            "enabled": profile["enabled"] if enabled is None else enabled,
            "required": list(profile["required"] if required is None else required)}


def _record_ids(rec: dict) -> list[str]:
    """Id parts of ``member_record_ids`` (``lane/delivery:<id>``, or a bare catalogue id)."""
    out = []
    for item in (rec.get("member_record_ids") or "").split(";"):
        head, _, tail = item.partition(":")
        part = tail if "/" in head else item
        out.append(part[len("excluded:"):] if part.startswith("excluded:") else part)
    return out


def identifier_of(rec: dict, profile: dict) -> str:
    """Kind of the first accepted identifier (``doi``, ``openalex``, ``repec``... or the
    platform name), else ``""``."""
    dois = [rec.get("doi") or ""] + re.split(r"[;|\s]+", rec.get("all_dois") or "")
    if any(_DOI.match(d.strip()) for d in dois):
        return "doi"
    oas = [rec.get("openalex_id") or ""] + re.split(r"[;|\s]+", rec.get("all_openalex_ids") or "")
    if any(_OPENALEX.match(o.strip()) for o in oas):
        return "openalex"
    candidates = _record_ids(rec)
    if (rec.get("repec_handle") or "").strip():
        candidates.append(rec["repec_handle"].strip())
    for part in candidates:
        for g in profile["generic"]:
            if _GENERIC[g].match(part):
                return g
        name, _, rest = part.partition(":")
        pattern = profile["platforms"].get(name)
        if pattern and pattern.match(rest):
            return name
    return ""


def publisher_of(rec: dict, profile: dict) -> tuple[str, str]:
    """``(name, how)`` of the publisher, ``("", "unresolved")`` when none."""
    for step in profile["order"]:
        if step == "host_org":
            org = (rec.get("host_org_name") or "").strip()
            if org:
                return org, "host_org"
        else:
            dois = [rec.get("doi") or ""] + re.split(r"[;|\s]+", rec.get("all_dois") or "")
            for d in dois:
                prefix = d.strip().split("/", 1)[0]
                registrant, kind = profile["prefixes"].get(prefix, ("", ""))
                if kind == "publisher" and _DOI.match(d.strip()):
                    return registrant, "doi_prefix"
    return "", "unresolved"


def missing_fields(rec: dict, profile: dict) -> list[str]:
    """Every DataCite mandatory property the work lacks, in ``FIELDS`` order."""
    has = {
        "identifier": bool(identifier_of(rec, profile)),
        "creator": bool((rec.get("first_author") or "").strip()
                        or (rec.get("all_authors") or "").strip()),
        "title": bool(re.search(r"[^\W_]", rec.get("title") or "")),
        "publisher": bool(publisher_of(rec, profile)[0]),
        "publicationYear": bool(re.fullmatch(r"\d{4}", (rec.get("year") or "").strip())),
        "resourceType": bool((rec.get("doc_type") or "").strip()),
    }
    return [f for f in FIELDS if not has[f]]


def codes(missing: list[str]) -> str:
    """The ``profile_missing`` cell: ``profile_missing_<field>`` codes joined by ``;``."""
    return ";".join(CODE_PREFIX + f for f in missing)


def counts(rows: list[dict], prof: dict | None) -> dict:
    """The ``profile`` block of ``rel_counts.json``: per-field gaps, whatever the switch,
    and the works the filter removes when it is on (``profile_excluded``)."""
    cells = [set(filter(None, r["profile_missing"].split(";"))) for r in rows]
    return {
        "rule": prof,
        "fields": FIELDS,
        "missing_any_works": sum(bool(c) for c in cells),
        "missing_by_field_works": {f: sum(CODE_PREFIX + f in c for c in cells) for f in FIELDS},
        "excluded_works": sum(r["rel_reason"] == "profile_excluded" for r in rows),
        "note": ("missing_*: every mandatory property a work lacks, filter on or off; "
                 "excluded_works: removed by the filter at the first facet (zero while the "
                 "switch is off; the sensitivity rows profile_on and "
                 "profile_on_publisher_optional show it on). Nothing is deleted."),
    }


def first_required_code(cell: str, required: list[str]) -> str:
    """The first code of ``cell`` whose field is required (declared order), else ``""``."""
    present = set(cell.split(";")) if cell else set()
    return next((CODE_PREFIX + f for f in FIELDS if f in required and CODE_PREFIX + f in present), "")
