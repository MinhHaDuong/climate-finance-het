"""Shared record schema, lexicon matcher and OAI-PMH reader (ticket 1653)."""

import re
import xml.etree.ElementTree as ET

import yaml
from catalog_rel_sud_search import spelling_variants, split_terms
from openalex_corpus import retry_get
from pipeline_io import MAILTO, POLITE_MAX_RETRIES
from pipeline_text import normalize_doi_safe

# One normalized record, whatever the source.
RECORD_FIELDS = [
    "record_id", "url", "doi", "title", "authors", "year", "language",
    "venue", "doc_type", "abstract", "matched_terms",
]

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def load_lexicon(path="config/rel_sud_search.yaml"):
    """The 1530 query lexicon: ``{lang: {theme: '"a" OR "b"'}}``."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["queries"]


def lexicon_terms(lexicon, languages):
    """Every phrase of the given languages, with its spelling variants."""
    return sorted({v for lang in languages for s in lexicon[lang].values()
                   for t in split_terms(s) for v in spelling_variants(t)})


def term_matcher(terms):
    """Function returning the lexicon phrases found in a text, in stable order.

    Latin-script phrases need word boundaries ('REDD' must not match inside a
    word); CJK, Arabic and Indic scripts have none.
    """
    def part(t):
        if all(ord(c) < 0x250 for c in t):
            return r"(?<!\w)" + re.escape(t) + r"(?!\w)"
        return re.escape(t)

    ordered = sorted(terms, key=len, reverse=True)
    pattern = re.compile("|".join(part(t) for t in ordered), re.IGNORECASE)
    canon = {t.casefold(): t for t in ordered}

    def match(text):
        found = {canon.get(m.group(0).casefold(), m.group(0))
                 for m in pattern.finditer(text or "")}
        return sorted(found)

    return match


def find_doi(values):
    for v in values:
        m = DOI_RE.search(v or "")
        if m:
            return normalize_doi_safe(m.group(0).rstrip(".,;"))
    return ""


def find_year(values):
    for v in values:
        m = YEAR_RE.search(v or "")
        if m:
            return int(m.group(0))
    return None


def empty_record(**kw):
    rec = {k: "" for k in RECORD_FIELDS}
    rec["year"] = None
    rec.update(kw)
    return rec


# ---------------------------------------------------------------------------
# OAI-PMH
# ---------------------------------------------------------------------------

NS = {"oai": "http://www.openarchives.org/OAI/2.0/",
      "dc": "http://purl.org/dc/elements/1.1/",
      "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"}


def parse_oai_dc(record_el):
    """Dublin Core fields of one OAI ``<record>`` as ``{field: [values]}``, plus
    ``_identifier`` (the OAI identifier) and ``_deleted``."""
    header = record_el.find("oai:header", NS)
    out = {"_identifier": header.findtext("oai:identifier", "", NS) if header is not None else "",
           "_deleted": header is not None and header.get("status") == "deleted"}
    dc = record_el.find("oai:metadata/oai_dc:dc", NS)
    if dc is None:
        return out
    for el in dc:
        tag = el.tag.rsplit("}", 1)[-1]
        if el.text and el.text.strip():
            out.setdefault(tag, []).append(el.text.strip())
    return out


def dc_to_record(dc, match):
    """Normalized record from parsed Dublin Core, lexicon matched on title+abstract."""
    ids = dc.get("identifier", []) + dc.get("relation", [])
    title = " / ".join(dc.get("title", []))
    abstract = " ".join(dc.get("description", []))
    url = next((i for i in ids if i.startswith("http")), "")
    return empty_record(
        record_id=dc.get("_identifier", ""), url=url, doi=find_doi(ids),
        title=title, authors="; ".join(dc.get("creator", [])),
        year=find_year(dc.get("date", [])),
        language="; ".join(dc.get("language", [])),
        venue="; ".join(dc.get("source", []) + dc.get("publisher", [])[:1]),
        doc_type="; ".join(dc.get("type", [])),
        abstract=abstract[:3000],
        matched_terms="; ".join(match(title + " " + abstract)))


def oai_get(url, params=None, delay=1.0):
    """The OAI-PMH getter: ``polite_get`` without the ``mailto`` query parameter.

    ``polite_get`` appends ``mailto=...`` to every request (an OpenAlex
    courtesy). OAI-PMH servers must reject arguments outside the protocol, and
    OJS does: ``badArgument`` on every AJOL journal (2026-09-30). Same retries,
    same identifying User-Agent (which carries the contact address instead).
    """
    return retry_get(url, params=params, delay=delay, max_retries=POLITE_MAX_RETRIES,
                     timeout=30, mailto=None,
                     user_agent=f"ClimateFinancePipeline/1.0 (mailto:{MAILTO})")


# Characters XML 1.0 forbids. OJS lets them through from pasted abstracts
# (U+FFFE inside an AJOL abstract broke a whole OAI page, 2026-09-30).
XML_INVALID_RE = re.compile("[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


def xml_clean(content):
    """UTF-8 bytes with XML-forbidden characters removed (undecodable bytes
    become U+FFFD). One forbidden character otherwise makes a whole OAI page,
    and with it every later page of the set, unreadable."""
    text = content.decode("utf-8", errors="replace")
    return XML_INVALID_RE.sub("", text).encode("utf-8")


def oai_list_records(endpoint, metadata_prefix="oai_dc", set_spec=None,
                     date_from=None, delay=1.0, *, get):
    """Yield ('meta', completeListSize|''), ('dc', dict)*, ('end', reason).

    Follows resumption tokens to the end. ``noRecordsMatch`` is a complete,
    empty answer, not an error. Each page is cleaned of XML-forbidden
    characters before parsing (``xml_clean``).

    ``get`` has no default: the caller chooses. ``oai_get`` is the
    protocol-conformant choice (no extra argument); ``polite_get`` adds
    ``mailto``, which a strict server rejects (OJS) and a lenient one ignores
    (SciELO, CyberLeninka ran with it on 2026-09-30).
    """
    params = {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
    if set_spec:
        params["set"] = set_spec
    if date_from:
        params["from"] = date_from
    first = True
    while True:
        try:
            resp = get(endpoint, params=params, delay=delay)
        except Exception as exc:  # network failure after retries
            yield ("end", f"error: {type(exc).__name__}")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code}")
            return
        try:
            root = ET.fromstring(xml_clean(resp.content))
        except ET.ParseError:
            yield ("end", "error: bad xml")
            return
        err = root.find("oai:error", NS)
        if err is not None:
            code = err.get("code", "")
            if code == "noRecordsMatch":
                if first:
                    yield ("meta", 0)
                yield ("end", "")
            else:
                yield ("end", f"oai error: {code}")
            return
        lr = root.find("oai:ListRecords", NS)
        token_el = lr.find("oai:resumptionToken", NS) if lr is not None else None
        if first:
            size = token_el.get("completeListSize", "") if token_el is not None else ""
            yield ("meta", int(size) if size.isdigit() else "")
            first = False
        for rec in (lr.findall("oai:record", NS) if lr is not None else []):
            yield ("dc", parse_oai_dc(rec))
        token = (token_el.text or "").strip() if token_el is not None else ""
        if not token:
            yield ("end", "")
            return
        params = {"verb": "ListRecords", "resumptionToken": token}
