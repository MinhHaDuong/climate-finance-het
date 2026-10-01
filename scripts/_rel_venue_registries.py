"""Parse the archived REL venue registries into flag entries (ticket 1841).

One parser per registry of ``config/rel_venue_registries.yaml``. Each returns
``(rows, entries)``: ``rows`` the number of data rows read from the raw file,
``entries`` the flag entries the registry's filter keeps, each a dict

    registry   registry key
    entry_id   the registry's own id for the entry (journal id, Scopus source
               record id, ISSN, checker row number)
    title      title as the registry spells it
    issns      tuple of normalized ISSNs (``NNNN-NNNC``), possibly empty
    domain     clone host (hijacked checker only)
    levels     ``{year: level}`` of every non-blank yearly level (Kanalregisteret only)
    reason     the registry's stated status or reason
    entry_url  where a reader can see the entry

Pure parsing, no network. Matching entries to venues is in ``_rel_venues``.
"""

import csv
import re
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

from _xlsx_rows import read_sheet, sheet_names

_ISSN_RE = re.compile(r"\b(\d{4})-?(\d{3}[\dXx])\b")


def norm_issn(value):
    """``NNNN-NNNC`` from any spelling (``10133119``, ``1013-3119``); else ``""``."""
    s = re.sub(r"[^0-9Xx]", "", str(value or "")).upper()
    return f"{s[:4]}-{s[4:]}" if len(s) == 8 and s[:7].isdigit() else ""


def issns_in(text):
    """Every normalized ISSN found in a free-text cell, sorted, unique."""
    out = {norm_issn(a + b) for a, b in _ISSN_RE.findall(str(text or ""))}
    # Scopus writes ISSNs without the hyphen as a bare 8-character token.
    for tok in re.split(r"[\s,;/]+", str(text or "")):
        out.add(norm_issn(tok))
    out.discard("")
    return tuple(sorted(out))


def host_of(url):
    """Lower-cased host of a URL without ``www.``; a bare domain is accepted."""
    s = str(url or "").strip()
    if s and "://" not in s:
        s = "http://" + s
    host = (urlsplit(s).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _entry(registry, entry_id, title, issns=(), domain="", reason="", entry_url="", levels=None):
    return {"registry": registry, "entry_id": str(entry_id), "title": title.strip(),
            "issns": tuple(issns), "domain": domain, "reason": reason.strip(),
            "entry_url": entry_url, "levels": dict(levels or {})}


# ── Kanalregisteret (HK-dir), table 851 ──────────────────


def levels_text(levels):
    """``{2024: "1", 2025: "1", 2026: "X"}`` as ``Nivå 2024-2025 1, 2026 X``."""
    runs = []
    for y in sorted(levels):
        if runs and runs[-1][2] == levels[y] and runs[-1][1] == y - 1:
            runs[-1][1] = y
        else:
            runs.append([y, y, levels[y]])
    return "Nivå " + ", ".join((f"{a}" if a == b else f"{a}-{b}") + f" {lv}" for a, b, lv in runs)


def level_at(levels, year):
    """A journal's level for a work of ``year``.

    The register's yearly level is a per-year status (X is provisional and is
    resolved in a later cycle), so a work takes the level of its own
    publication year. A year the journal has no level for (blank cell, or
    outside the register's columns) takes the journal's nearest year with a
    level, the earlier one on a tie. An undated work (``year`` None) gets
    ``None``: no level can be dated to it.
    """
    if year is None or not levels:
        return None
    if year in levels:
        return levels[year]
    return levels[min(levels, key=lambda y: (abs(y - year), y))]


def parse_kanalregisteret(path, entry_url="{id}"):
    """Journals with level X in at least one year, with every yearly level."""
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        years = {int(c[-4:]): c for c in reader.fieldnames if re.fullmatch(r"Nivå \d{4}", c)}
        if not years:
            raise ValueError(f"{path}: no 'Nivå YYYY' column")
        rows, entries = 0, []
        for r in reader:
            rows += 1
            levels = {y: r[c].strip().upper() for y, c in years.items() if r[c].strip()}
            if "X" not in levels.values():
                continue
            jid = r["Tidsskrift id"].strip()
            entries.append(_entry(
                "kanalregisteret", jid, r.get("Original tittel") or r.get("Internasjonal tittel") or "",
                issns_in(f"{r.get('Print ISSN', '')} {r.get('Online ISSN', '')}"),
                reason=levels_text(levels), entry_url=entry_url.format(id=jid), levels=levels))
    return rows, entries


# ── Scopus discontinued titles ───────────────────────────


def parse_scopus_discontinued(path, entry_url="{id}"):
    """Rows of the 'Discontinued Titles' sheet whose indexation change is a discontinuation."""
    sheet = next((n for n in sheet_names(path) if n.lower().startswith("discontinued titles")), None)
    if sheet is None:
        raise ValueError(f"{path}: no 'Discontinued Titles' sheet")
    grid = read_sheet(path, sheet)
    head_i = next(i for i, r in enumerate(grid) if r and r[0].strip().lower() == "sourcerecord id")
    head = [h.strip().lower() for h in grid[head_i]]

    def col(prefix):
        return next(i for i, h in enumerate(head) if h.startswith(prefix))

    i_id, i_title, i_issn, i_eissn = col("sourcerecord"), col("source title"), col("issn"), col("eissn")
    i_change = col("indexation change")
    rows, entries = 0, []
    for r in grid[head_i + 1:]:
        r = r + [""] * (len(head) - len(r))
        if not r[i_id].strip():
            continue
        rows += 1
        if r[i_change].strip().lower() != "discontinuation":
            continue
        sid = r[i_id].strip()
        entries.append(_entry("scopus_discontinued", sid, r[i_title],
                              issns_in(f"{r[i_issn]} {r[i_eissn]}"),
                              reason=r[i_change].strip(), entry_url=entry_url.format(id=sid)))
    return rows, entries


# ── DOAJ change log ──────────────────────────────────────


def parse_doaj_date(value):
    """A DOAJ log date: Excel serial (old log) or ``28-September-2026`` / ``dd/mm/yyyy``."""
    s = str(value or "").strip()
    if not s:
        return None
    try:
        serial = float(s)
        return date(1899, 12, 30) + timedelta(days=int(serial))
    except ValueError:
        pass
    for fmt in ("%d-%B-%Y", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _doaj_table(path, sheet):
    """``(title, issns, date, reason)`` rows of one DOAJ sheet, header found by 'ISSN'."""
    grid = read_sheet(path, sheet)
    head_i = next((i for i, r in enumerate(grid) if "ISSN" in [c.strip() for c in r]), None)
    if head_i is None:
        return []
    head = [c.strip().lower() for c in grid[head_i]]
    i_t = next(i for i, h in enumerate(head) if h.startswith("journal title"))
    i_i = head.index("issn")
    i_d = next(i for i, h in enumerate(head) if h.startswith("date"))
    i_r = next((i for i, h in enumerate(head) if h.startswith("reason")), None)
    out = []
    for r in grid[head_i + 1:]:
        r = r + [""] * (len(head) - len(r))
        issns = issns_in(r[i_i])
        if not (r[i_t].strip() or issns):
            continue
        out.append((r[i_t].strip(), issns, parse_doaj_date(r[i_d]),
                    r[i_r].strip() if i_r is not None else ""))
    return out


def parse_doaj_withdrawn(paths, reason_pattern, entry_url="{id}"):
    """Withdrawals for publication-practice reasons, minus later re-admissions."""
    rx = re.compile(reason_pattern, re.I)
    withdrawn, added = [], {}
    for path in paths:
        for sheet in sheet_names(path):
            low = sheet.lower()
            if low.startswith("withdrawn"):
                withdrawn.extend(_doaj_table(path, sheet))
            elif low.startswith("added"):
                for _, issns, d, _ in _doaj_table(path, sheet):
                    for issn in issns:
                        if d and (issn not in added or d > added[issn]):
                            added[issn] = d
    entries = []
    for title, issns, d, reason in withdrawn:
        if not issns or not rx.search(reason):
            continue
        if d and any(added.get(i) and added[i] > d for i in issns):
            continue
        eid = issns[0]
        entries.append(_entry("doaj_withdrawn", eid, title, issns,
                              reason=f"{reason} ({d.isoformat() if d else 'undated'})",
                              entry_url=entry_url.format(id=eid)))
    return len(withdrawn), entries


# ── Retraction Watch Hijacked Journal Checker ────────────


def parse_hijacked(path, entry_url=""):
    """Clone domains with the legitimate title and ISSNs they impersonate."""
    with open(path, encoding="utf-8", newline="") as fh:
        grid = list(csv.reader(fh))
    head_i = next(i for i, r in enumerate(grid) if any("URL (Hijacked)" in c for c in r))
    head = [c.strip() for c in grid[head_i]]
    i_url = head.index("URL (Hijacked)")
    i_title = head.index("Hijacked Journal Title")
    i_orig = head.index("Original journal")
    i_issn = head.index("ISSN (Original)")
    rows, entries = 0, []
    for r in grid[head_i + 1:]:
        r = r + [""] * (len(head) - len(r))
        if not any(c.strip() for c in r):
            continue
        rows += 1
        for url in re.split(r"[\s,;]+", r[i_url].strip()):
            dom = host_of(url)
            if not dom:
                continue
            entries.append(_entry("hijacked", r[0].strip() or str(rows), r[i_title],
                                  issns_in(r[i_issn]), domain=dom,
                                  reason=f"clone of {r[i_orig].strip()}",
                                  entry_url=entry_url))
    return rows, entries
