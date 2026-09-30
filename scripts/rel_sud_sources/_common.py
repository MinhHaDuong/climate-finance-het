"""Shared record schema, lexicon matcher, OAI-PMH reader, route semantics,
adapter discovery and sentinel matcher of the southern-source lane (ticket 1653)."""

import importlib
import pkgutil
import re
import unicodedata
import xml.etree.ElementTree as ET

import yaml
from catalog_rel_sud_search import spelling_variants, split_terms
from openalex_corpus import retry_get
from pipeline_io import MAILTO, POLITE_MAX_RETRIES
from pipeline_text import normalize_doi_safe

import rel_sud_sources

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


# Scripts below U+0530 (Latin, Greek, Cyrillic, Armenian) separate words with
# spaces, so a phrase must sit on word boundaries ('REDD' must not match inside
# a word). CJK has no word separator; for Arabic and Indic scripts ``\w`` does
# not cover every combining sign, so a boundary test would misfire.
BOUNDED_SCRIPTS_BELOW = 0x530


def term_matcher(terms):
    """Function returning the lexicon phrases found in a text, in stable order.

    Text and phrases are compared in Unicode NFC (pasted abstracts often carry
    decomposed accents). Phrases in space-separated scripts need word
    boundaries (``BOUNDED_SCRIPTS_BELOW``); the others match as substrings.
    """
    def part(t):
        if all(ord(c) < BOUNDED_SCRIPTS_BELOW for c in t):
            return r"(?<!\w)" + re.escape(t) + r"(?!\w)"
        return re.escape(t)

    terms = {unicodedata.normalize("NFC", t) for t in terms}
    ordered = sorted((t for t in terms if t.strip()), key=len, reverse=True)
    if not ordered:
        return lambda text: []
    pattern = re.compile("|".join(part(t) for t in ordered), re.IGNORECASE)
    canon = {t.casefold(): t for t in ordered}

    def match(text):
        text = unicodedata.normalize("NFC", text or "")
        found = {canon.get(m.group(0).casefold(), m.group(0))
                 for m in pattern.finditer(text)}
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
    ``_identifier`` (the OAI identifier) and ``_deleted`` (a deleted-status
    header: no metadata; each adapter skips it)."""
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
CHAR_REF_RE = re.compile(r"&#(x[0-9a-fA-F]+|[0-9]+);")
XML_DECL_RE = re.compile(rb"^\s*<\?xml[^>]*?encoding=[\"']([A-Za-z0-9._-]+)[\"'][^>]*\?>")


def _allowed_ref(m):
    """Keep a numeric character reference only if XML 1.0 allows its target."""
    ref = m.group(1)
    try:
        code = int(ref[1:], 16) if ref[0] in "xX" else int(ref)
        allowed = not XML_INVALID_RE.match(chr(code))
    except (ValueError, OverflowError):
        allowed = False
    return m.group(0) if allowed else ""


def xml_clean(content):
    """UTF-8 bytes of an XML page with the characters XML 1.0 forbids removed,
    raw or as numeric references. One of them otherwise makes a whole OAI page,
    and with it every later page of the set, unreadable.

    The page is decoded by its declared encoding (UTF-8 when none; undecodable
    bytes become U+FFFD) and the declaration is dropped, since the result is
    UTF-8 whatever the source said.
    """
    m = XML_DECL_RE.match(content)
    encoding = m.group(1).decode("ascii") if m else "utf-8"
    if m:
        content = content[m.end():]
    try:
        text = content.decode(encoding, errors="replace")
    except LookupError:  # an encoding name Python does not know
        text = content.decode("utf-8", errors="replace")
    text = CHAR_REF_RE.sub(_allowed_ref, XML_INVALID_RE.sub("", text))
    return text.encode("utf-8")


def _oai_page(endpoint, params, delay, get):
    """``(ListRecords element, None)``, or ``(None, end reason)`` where the
    reason ``''`` is ``noRecordsMatch`` (a complete, empty answer)."""
    try:
        resp = get(endpoint, params=params, delay=delay)
    except Exception as exc:  # network failure after retries
        return None, f"error: {type(exc).__name__}"
    if resp.status_code != 200:
        return None, f"http {resp.status_code}"
    try:
        root = ET.fromstring(xml_clean(resp.content))
    except ET.ParseError:
        return None, "error: bad xml"
    err = root.find("oai:error", NS)
    if err is not None:
        code = err.get("code", "")
        return None, "" if code == "noRecordsMatch" else f"oai error: {code}"
    lr = root.find("oai:ListRecords", NS)
    if root.tag != "{%s}OAI-PMH" % NS["oai"] or lr is None:
        return None, "error: not an OAI-PMH ListRecords answer"
    return lr, None


def oai_list_records(endpoint, metadata_prefix="oai_dc", set_spec=None,
                     date_from=None, delay=1.0, *, get, max_pages=100_000):
    """Yield ('meta', completeListSize|''), ('dc', dict)*, ('end', reason).

    Follows resumption tokens to the end. ``noRecordsMatch`` is a complete,
    empty answer, not an error. Each page is cleaned of XML-forbidden
    characters before parsing (``xml_clean``). A page that is XML but not an
    OAI-PMH answer, a resumption token seen before, or more than ``max_pages``
    pages end the set incomplete, never complete. Deleted-status records are
    yielded with ``_deleted`` set.

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
    first, seen_tokens = True, set()
    for _ in range(max_pages):
        lr, stop = _oai_page(endpoint, params, delay, get)
        if lr is None:
            if stop == "" and first:
                yield ("meta", 0)
            yield ("end", stop)
            return
        token_el = lr.find("oai:resumptionToken", NS)
        if first:
            size = token_el.get("completeListSize", "") if token_el is not None else ""
            yield ("meta", int(size) if size.isdigit() else "")
            first = False
        for rec in lr.findall("oai:record", NS):
            yield ("dc", parse_oai_dc(rec))
        token = (token_el.text or "").strip() if token_el is not None else ""
        if not token:
            yield ("end", "")
            return
        if token in seen_tokens:
            yield ("end", "error: repeated resumptionToken")
            return
        seen_tokens.add(token)
        params = {"verb": "ListRecords", "resumptionToken": token}
    yield ("end", f"error: page guard ({max_pages} pages)")


# ---------------------------------------------------------------------------
# Routes, adapter discovery and sentinels (shared by the runner and the exporter)
# ---------------------------------------------------------------------------

# Routes with no server-side search: the whole set or listing is read and
# archived, and the local 1530 lexicon match selects the candidates. For them
# the lexicon match *is* the query (team-lead decision, 2026-09-30); the
# archived harvest is the record of what was read.
HARVEST_ROUTES = {"oai-pmh", "listing"}


def discover():
    """``{source name: adapter module}`` for every module defining SOURCE."""
    out = {}
    for info in pkgutil.iter_modules(rel_sud_sources.__path__):
        mod = importlib.import_module(f"rel_sud_sources.{info.name}")
        if hasattr(mod, "SOURCE"):
            out[mod.SOURCE["name"]] = mod
    return out


def keep(route, rec):
    """Search routes keep every hit; harvest and listing routes keep lexicon
    matches only (``HARVEST_ROUTES``: the match is their query)."""
    return route not in HARVEST_ROUTES or bool(rec.get("matched_terms"))


def _norm(text):
    text = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"[\W_]+", " ", text).strip()


def sentinel_hits(sentinel, rows):
    """Candidate rows matching a sentinel by DOI, or by every fragment of its
    title as whole words. Sentinel titles elide words with '...' and add notes
    in brackets: bracketed text is a note, never required."""
    doi = normalize_doi_safe(sentinel.get("doi") or "")
    title = re.sub(r"\([^)]*\)", " ", sentinel.get("title") or "")
    frags = [f for f in (_norm(x) for x in re.split(r"\.\.\.|…", title)) if f]
    out = []
    for r in rows:
        if doi and normalize_doi_safe(r.get("doi") or "") == doi:
            out.append(r)
        elif frags and all(f" {f} " in f" {_norm(r.get('title'))} " for f in frags):
            out.append(r)
    return out


def sentinel_report(sentinels, rows, klass="b"):
    """One line per sentinel of the class: id, found, sources and query ids."""
    report = []
    for s in sentinels:
        if s.get("class") != klass:
            continue
        hits = sentinel_hits(s, rows)
        report.append({"sentinel": s["sentinel"], "found": bool(hits),
                       "sources": "; ".join(sorted({h["source"] for h in hits})),
                       "query_ids": "; ".join(sorted({h["query_id"] for h in hits})),
                       "title": s["title"]})
    return report
