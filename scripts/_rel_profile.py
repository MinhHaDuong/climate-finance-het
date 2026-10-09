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
- ``venue`` (the field that stands for the DataCite ``publisher``; author decision
  of 2026-10-09: the filter requires a venue identity, not a publisher string): the
  work names a journal or a series, or a publisher resolves by any route. First
  hit wins, recorded in ``profile_venue_via``: (1) ``journal``, the pool's
  ``journal`` field (journal or series name; a platform name such as SSRN
  Electronic Journal does not count); (2) ``host_org``, the OpenAlex host
  organization (``host_org_name``; a platform name does not count); (3)
  ``doi_prefix``, the registrant of a ``publisher`` row of
  ``config/rel_doi_prefixes.csv`` (a ``platform`` prefix never counts); (4)
  ``repec_archive``, the archive code of a RePEc handle read as the issuing body
  of a working paper (``config/rel_repec_archives.csv``). Else ``unresolved``
  and the reason code ``profile_missing_venue``;
- ``publicationYear``: four digits;
- ``resourceType``: ``doc_type`` not blank.

``missing_fields`` returns every missing property, whatever is required, so the
view records the full picture (``profile_missing``) and the required subset
decides the exclusion. The reason code ``profile_missing_<field>`` names the
first missing required property in the fixed order of ``FIELDS`` (identifier,
creator, title, venue, publicationYear, resourceType), not the order of
``required`` in the config.
"""

import csv
import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "config", "rel_profile.yaml")
FIELDS = ["identifier", "creator", "title", "venue", "publicationYear", "resourceType"]
VENUE_STEPS = ("journal", "host_org", "doi_prefix", "repec_archive")
_REPEC = re.compile(r"(?:^|:)RePEc:([^:\s]+):([^:\s]+):\S", re.IGNORECASE)
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
    venue = cfg["venue"]
    order = list(venue["order"])
    if any(o not in VENUE_STEPS for o in order):
        raise ValueError(f"rel_profile.venue.order: known steps {VENUE_STEPS}")
    table = os.path.join(ROOT, venue["prefix_table"])
    with open(table, encoding="utf-8", newline="") as fh:
        prefixes = {r["prefix"]: (r["registrant"], r["kind"]) for r in csv.DictReader(fh)}
    if any(k not in ("publisher", "platform") for _, k in prefixes.values()):
        raise ValueError(f"{table}: kind must be publisher or platform")
    with open(os.path.join(ROOT, venue["repec_archive_table"]), encoding="utf-8", newline="") as fh:
        # key (archive, series): an empty series covers every series of the archive
        archives = {(r["archive"].casefold(), r["series"].casefold()): r["body"]
                    for r in csv.DictReader(fh)}
    platforms = {}
    for name, spec in cfg["identifier"]["platforms"].items():
        if not spec.get("url"):
            raise ValueError(f"rel_profile.identifier.platforms.{name}: a resolvable url is required")
        platforms[name] = re.compile(spec["id"])
    # A host organization that is a platform is not a publisher either: the registrants of the
    # platform prefix rows plus the names OpenAlex gives them (config venue.platform_names).
    names = {r.casefold() for r, k in prefixes.values() if k == "platform"}
    names |= {str(n).casefold() for n in venue.get("platform_names") or []}
    junk = {" ".join(str(n).split()).casefold() for n in venue.get("placeholder_names") or []}
    return {"version": cfg["version"], "enabled": bool(cfg["enabled"]), "required": required,
            "generic": generic, "platforms": platforms, "order": order, "prefixes": prefixes,
            "platform_names": names, "placeholder_names": junk, "repec_archives": archives}


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


def is_platform_name(name: str, profile: dict) -> bool:
    """A platform name (exact, or the platform followed by a parenthesis: ``Zenodo (CERN...)``)."""
    n = name.strip().casefold()
    return n in profile["platform_names"] or any(n.startswith(p + " (") for p in profile["platform_names"])


def usable_name(name: str, profile: dict) -> str:
    """The trimmed ``name`` if it can name a venue, else ``""``: it needs at least one letter
    (as ``title`` does), must not be a configured placeholder (``nan``, ``-``, ``Preprint``,
    ``Unknown``...: pandas and exporter fillers) and must not be a platform name."""
    name = " ".join((name or "").split())
    if not re.search(r"[^\W\d_]", name) or name.casefold() in profile["placeholder_names"]:
        return ""
    return "" if is_platform_name(name, profile) else name


def _host_org(rec: dict, profile: dict) -> str:
    return usable_name(rec.get("host_org_name") or "", profile)


def _doi_registrant(rec: dict, profile: dict) -> str:
    for d in [rec.get("doi") or ""] + re.split(r"[;|\s]+", rec.get("all_dois") or ""):
        registrant, kind = profile["prefixes"].get(d.strip().split("/", 1)[0], ("", ""))
        if kind == "publisher" and _DOI.match(d.strip()):
            return registrant
    return ""


def _repec_body(rec: dict, profile: dict) -> str:
    cands = _record_ids(rec) + [(rec.get("repec_handle") or "").strip()]
    for part in cands:
        m = _REPEC.search(part)
        if m:
            key = (m.group(1).casefold(), m.group(2).casefold())
            body = profile["repec_archives"].get(key) or profile["repec_archives"].get((key[0], ""))
            if body:
                return body
    return ""


def publisher_of(rec: dict, profile: dict) -> tuple[str, str]:
    """``(name, how)`` of the publisher *string* (host organization, DOI-prefix registrant),
    ``("", "unresolved")`` when none: the pre-decision rule of 2026-10-09, kept to count what
    the venue identity rescues."""
    for step in profile["order"]:
        if step == "host_org" and _host_org(rec, profile):
            return _host_org(rec, profile), "host_org"
        if step == "doi_prefix" and _doi_registrant(rec, profile):
            return _doi_registrant(rec, profile), "doi_prefix"
    return "", "unresolved"


def venue_of(rec: dict, profile: dict) -> tuple[str, str]:
    """``(name, how)`` of the venue identity, first hit of ``venue.order`` wins;
    ``("", "unresolved")`` when none."""
    for step in profile["order"]:
        if step == "journal":
            name = usable_name(rec.get("journal") or "", profile)
        elif step == "host_org":
            name = _host_org(rec, profile)
        elif step == "doi_prefix":
            name = _doi_registrant(rec, profile)
        else:
            name = _repec_body(rec, profile)
        if name:
            return name, step
    return "", "unresolved"


def missing_fields(rec: dict, profile: dict) -> list[str]:
    """Every DataCite mandatory property the work lacks, in ``FIELDS`` order."""
    has = {
        "identifier": bool(identifier_of(rec, profile)),
        "creator": bool((rec.get("first_author") or "").strip()
                        or (rec.get("all_authors") or "").strip()),
        "title": bool(re.search(r"[^\W_]", rec.get("title") or "")),
        "venue": bool(venue_of(rec, profile)[0]),
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
                 "profile_on_venue_optional show it on). Nothing is deleted."),
    }


def first_required_code(cell: str, required: list[str]) -> str:
    """The first code of ``cell`` whose field is required (declared order), else ``""``."""
    present = set(cell.split(";")) if cell else set()
    return next((CODE_PREFIX + f for f in FIELDS if f in required and CODE_PREFIX + f in present), "")
