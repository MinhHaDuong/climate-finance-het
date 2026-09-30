"""ReDIF parsing for the local RePEc mirror (ticket 1810).

ReDIF is RePEc's metadata format: plain text, one ``Attribute: value`` per
line, a record (a *template*) opened by ``Template-Type:``, several templates
per file. A value runs on over the following lines until the next line that
opens a known attribute, so an abstract may span many lines and even contain
``Purpose:`` or ``https://`` at the start of a line.

Known attributes are the ReDIF template attributes (exact names) plus the
cluster prefixes (``Author-``, ``Editor-``, ``File-``, ``Provider-``, …). A
colon-terminated word that is neither stays part of the running value: that is
the continuation rule, and it is what keeps ``https://…`` or ``Findings:``
inside an abstract (census of 14,638 mirror files, 2026-10-01).

Files are UTF-8 by the ReDIF specification; a file that does not decode as
UTF-8 is read as cp1252 and the row says so (``encoding``); a byte-order
mark (UTF-8 or UTF-16) is honoured.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

# Record types kept as works (ticket 1810, action 1); the others are counted.
WORK_TYPES = ("redif-paper", "redif-article", "redif-book", "redif-chapter")
SERIES_TYPES = ("redif-series",)

KNOWN_ATTRIBUTES = frozenset("""
template-type handle title abstract keywords classification-jel year month
volume issue pages number journal creation-date revision-date
publication-status publication-type publication-date note length language
series doi x-doi isbn issn edition in-book book-title chapter haschapter price
availability name type description homepage url email phone fax postal
maintainer-name maintainer-email x-bibl x-file-ref x-ssrn-id article-handle
paper-handle short-id registered-date last-login-date x-authorcount
""".split())

KNOWN_PREFIXES = ("author-", "editor-", "file-", "classification-", "provider-",
                  "publisher-", "contact-", "maintainer-", "workplace-", "order-",
                  "contributor-", "name-", "primary-", "secondary-", "tertiary-",
                  "x-", "payment-", "restriction-")

_ATTR = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:(.*)$")
_SNIFF = re.compile(rb"(?im)^(?:\xef\xbb\xbf)?\s*template-type\s*:\s*redif-")
_DOI = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)")


def is_attribute(name: str) -> bool:
    n = name.lower()
    return n in KNOWN_ATTRIBUTES or n.startswith(KNOWN_PREFIXES)


def looks_like_redif(head: bytes) -> bool:
    """True when the first bytes of a file open a ReDIF template (UTF-16 included)."""
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        head = head.decode("utf-16", errors="ignore").encode("utf-8")
    return bool(_SNIFF.search(head))


def decode(raw: bytes) -> tuple[str, str]:
    """(text, encoding): UTF-8 when it decodes, else cp1252 with replacement."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace"), "cp1252"


def iter_templates(text: str) -> Iterator[dict[str, list[str]]]:
    """Every template of a ReDIF text, as {lower-case attribute: [values]}."""
    cur: dict[str, list[str]] | None = None
    key: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if cur is not None and key is not None:
            cur.setdefault(key, []).append(" ".join(" ".join(buf).split()))

    for line in text.splitlines():
        if line.startswith("#") and key is None:
            continue
        m = _ATTR.match(line)
        if m and is_attribute(m.group(1)):
            flush()
            key, buf = m.group(1).lower(), [m.group(2).strip()]
            if key == "template-type":
                if cur is not None:
                    yield cur
                cur = {}
            continue
        if key is not None:
            buf.append(line.strip())
    flush()
    if cur is not None:
        yield cur


def template_type(tpl: dict[str, list[str]]) -> str:
    """``redif-paper`` etc. from ``ReDIF-Paper 1.0``; empty when absent."""
    v = (tpl.get("template-type") or [""])[0].split()
    return v[0].lower() if v else ""


def first(tpl: dict[str, list[str]], key: str) -> str:
    for v in tpl.get(key, []):
        if v:
            return v
    return ""


def norm_doi(value: str) -> str:
    """A bare lower-case DOI found in ``value``, or empty."""
    m = _DOI.search(value or "")
    if not m:
        return ""
    return m.group(1).rstrip(".,;)]}>").lower()


def find_doi(tpl: dict[str, list[str]]) -> str:
    """DOI from the ``DOI`` attribute, a doi.org File-URL, or a ``DOI:`` note."""
    for key in ("doi", "x-doi"):
        for v in tpl.get(key, []):
            d = norm_doi(v)
            if d:
                return d
    for v in tpl.get("file-url", []):
        if re.search(r"(?i)//(dx\.)?doi\.org/", v):
            d = norm_doi(v)
            if d:
                return d
    for v in tpl.get("note", []):
        if re.search(r"(?i)\bdoi\b", v):
            d = norm_doi(v)
            if d:
                return d
    return ""


def find_year(tpl: dict[str, list[str]]) -> str:
    """Four-digit year: ``Year``, else the start of ``Creation-Date`` or
    ``Publication-Date`` (``20210430`` and ``2013-06`` both give the year)."""
    for key in ("year", "creation-date", "publication-date"):
        m = re.match(r"\s*((?:1[89]|20)\d\d)(?!\d{1,3}\b)", first(tpl, key))
        if m:
            return m.group(1)
    return ""


def split_jel(value: str) -> list[str]:
    """JEL codes of a ``Classification-JEL`` value, upper case, de-duplicated."""
    out: list[str] = []
    for code in re.findall(r"\b([A-Za-z]\d{0,2})\b", value or ""):
        c = code.upper()
        if c not in out:
            out.append(c)
    return out


def series_handle(handle: str) -> str:
    """``RePEc:aea:aecrev`` from ``RePEc:aea:aecrev:v:100:…``."""
    parts = handle.split(":")
    return ":".join(parts[:3]).lower() if len(parts) >= 3 else ""


def to_row(tpl: dict[str, list[str]], series_names: dict[str, str] | None = None) -> dict[str, str]:
    """The table row of one work template (paper, article, book, chapter)."""
    handle = first(tpl, "handle")
    ttype = template_type(tpl)
    sh = series_handle(handle)
    jel: list[str] = []
    for v in tpl.get("classification-jel", []):
        jel += [c for c in split_jel(v) if c not in jel]
    journal = first(tpl, "journal") or first(tpl, "book-title")
    if not journal and series_names:
        journal = series_names.get(sh, "")
    urls = tpl.get("file-url", [])
    return {
        "handle": handle,
        "template_type": ttype,
        "title": first(tpl, "title"),
        "abstract": first(tpl, "abstract"),
        "keywords": "; ".join(v for v in tpl.get("keywords", []) if v),
        "jel": "; ".join(jel),
        "authors": "; ".join(v for v in (tpl.get("author-name") or tpl.get("editor-name") or []) if v),
        "year": find_year(tpl),
        "creation_date": first(tpl, "creation-date"),
        "journal": journal,
        "series_handle": sh,
        "volume": first(tpl, "volume"),
        "issue": first(tpl, "issue"),
        "pages": first(tpl, "pages"),
        "number": first(tpl, "number"),
        "doi": find_doi(tpl),
        "language": first(tpl, "language"),
        "publication_status": first(tpl, "publication-status"),
        "file_url": urls[0] if urls else "",
    }


def series_of(tpl: dict[str, list[str]]) -> tuple[str, str]:
    """(series handle lower-case, name) of a ReDIF-Series template."""
    return first(tpl, "handle").lower(), first(tpl, "name")
