"""Deduplication keys of the REL pool (tickets 1731, 1655).

Shared by the pool merge (``corpus_rel_pool``) and the intake contract check
(``qa_rel_intake``), so the two agree on which identifier is a key. Standard
library only, like the contract check.

Only persistent identifiers are keys. A URL is one only when it names a
Handle or a resolvable id:

- ``https://doi.org/<doi>`` fills the DOI, ``https://openalex.org/W…`` the
  OpenAlex id; neither is a URL key;
- ``hdl.handle.net/X`` (or ``handle.net/X``) is the global Handle ``hdl:X``;
- ``<host>/handle/X`` keeps its host, ``<host>:hdl:X``: repositories reuse
  local prefixes such as DSpace's default ``123456789``, so the same X on two
  hosts may be two works;
- anything else (landing page, issue page, bare host, a resolver URL that
  names nothing) is no key.

URLs are canonicalised first: query and fragment dropped, ``http`` read as
``https``, host lowercased without ``www.``, trailing slash dropped.

Dedup version 2 (``dedup_version``, ticket 2047; version 1 is the default)
adds one key, the RePEc handle (``repec_key``): a lane's ``repec_handle``
column (ticket 2040, verified against the RePEc mirror) or a ``record_id``
that is itself a handle (the RePEc mirror lane, t1810). RePEc handles are
case-insensitive, so the key is the handle lowercased, ``repec:<archive>:
<series>:<item>``; two rows share it only when the handles are equal.
"""

import re

OPENALEX_ID = re.compile(r"^W\d+$")
URL_PARTS = re.compile(r"^(https?)://([^/?#\s]+)(\S*)$", re.IGNORECASE)
DOI_RESOLVERS = {"doi.org", "dx.doi.org"}
OPENALEX_HOSTS = {"openalex.org", "api.openalex.org"}
HANDLE_RESOLVERS = {"hdl.handle.net", "handle.net"}
# A Handle is <prefix>/<suffix>, the prefix dotted digits (e.g. 10568/1234).
HANDLE = re.compile(r"^\d+(?:\.\d+)*/\S+$")
_HANDLE_PATH = re.compile(r"^/handle/(.+)$")
# RePEc:<archive>:<series>:<item>, the shape qa_rel_intake checks.
REPEC_HANDLE = re.compile(r"^repec:[a-z0-9]{3}:[a-z0-9_-]+:\S+$", re.IGNORECASE)

# Step-4 guard: a title-only row joins on its title alone, so a generic title
# ("Introduction", "Book reviews") would join an unrelated work.
GENERIC_TITLES = {"introduction", "editorial", "preface", "foreword", "book review",
                  "book reviews", "conclusion", "conclusions", "index", "erratum",
                  "corrigendum", "contents", "table of contents"}
MIN_TITLE_WORDS = 4
MIN_TITLE_CHARS = 25


def norm_year(v):
    """``2026.0`` / ``2026`` → ``2026``; anything else → ``""``."""
    s = str(v or "").strip()
    try:
        y = int(float(s))
    except ValueError:
        return ""
    return str(y) if 1000 <= y <= 2999 else ""


def norm_openalex(v):
    s = str(v or "").strip()
    s = s.rsplit("/", 1)[-1]
    return s.upper() if OPENALEX_ID.match(s.upper()) else ""


def canonical_url(v):
    """``(host, path)`` of an http(s) URL, canonicalised; None otherwise."""
    m = URL_PARTS.match(str(v or "").strip())
    if not m:
        return None
    host = m.group(2).lower()
    host = host[4:] if host.startswith("www.") else host
    path = re.split(r"[?#]", m.group(3), maxsplit=1)[0].rstrip("/")
    return host, path


def handle_key(v):
    """``hdl:X`` or ``<host>:hdl:X`` for a Handle URL, else ``""``."""
    parts = canonical_url(v)
    if not parts:
        return ""
    host, path = parts
    if host in HANDLE_RESOLVERS:
        h = path.lstrip("/")
        return f"hdl:{h}" if HANDLE.match(h) else ""
    m = _HANDLE_PATH.match(path)
    if m and HANDLE.match(m.group(1)):
        return f"{host}:hdl:{m.group(1)}"
    return ""


def repec_key(v):
    """``repec:<archive>:<series>:<item>`` (lowercased) for a RePEc handle, else ``""``."""
    s = str(v or "").strip()
    return s.lower() if REPEC_HANDLE.match(s) else ""


def url_ids(raw):
    """``(doi, openalex_id, handle)`` a URL yields; the DOI as written, not normalized.

    A DOI resolver URL yields its DOI, an OpenAlex URL its work id, a Handle
    URL its Handle key; any other URL yields nothing.
    """
    parts = canonical_url(raw)
    if not parts:
        return "", "", ""
    host, path = parts
    if host in DOI_RESOLVERS:
        return path.lstrip("/"), "", ""
    if host in OPENALEX_HOSTS:
        return "", norm_openalex(path), ""
    return "", "", handle_key(raw)


def url_is_key(raw):
    """Whether ``raw`` alone deduplicates a record (a Handle, a DOI or work URL)."""
    return any(url_ids(raw))


def is_generic_title(title):
    """A normalized title too generic to join on its own (step 4)."""
    words = title.split()
    return (title in GENERIC_TITLES
            or (len(words) < MIN_TITLE_WORDS and len(title) < MIN_TITLE_CHARS))
