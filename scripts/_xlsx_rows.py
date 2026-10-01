"""Read one worksheet of an .xlsx file as rows of strings, standard library only.

The REL venue registries (ticket 1841) ship two spreadsheets (Elsevier's Scopus
source list, DOAJ's 2014-2024 withdrawal log). The project carries no Excel
dependency and needs none for this: an .xlsx is a zip of XML parts, and the
cells needed here are shared strings, inline strings and numbers. Formulas,
styles and dates are not interpreted (a date cell comes back as its serial
number); the callers read text columns only.
"""

import re
import xml.etree.ElementTree as ET
import zipfile

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _col_index(ref):
    """Zero-based column index of a cell reference such as ``AB12``."""
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _text(el):
    """Concatenated text of every ``<t>`` under an element (rich runs included)."""
    return "".join(t.text or "" for t in el.iter(f"{_NS}t"))


def sheet_names(path):
    """Worksheet names in workbook order."""
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
    return [s.get("name") for s in wb.iter(f"{_NS}sheet")]


def _sheet_part(z, name):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rid = None
    for s in wb.iter(f"{_NS}sheet"):
        if s.get("name") == name:
            rid = s.get(f"{_REL_NS}id")
    if rid is None:
        raise KeyError(f"no worksheet named {name!r}")
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    for r in rels.iter(f"{_PKG_REL_NS}Relationship"):
        if r.get("Id") == rid:
            target = r.get("Target").lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise KeyError(f"worksheet {name!r} has no relationship target")


def read_sheet(path, name):
    """Rows of worksheet ``name`` as lists of stripped strings (ragged rows padded)."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            with z.open("xl/sharedStrings.xml") as fh:
                for _, el in ET.iterparse(fh):
                    if el.tag == f"{_NS}si":
                        shared.append(_text(el))
                        el.clear()
        rows = []
        with z.open(_sheet_part(z, name)) as fh:
            for _, el in ET.iterparse(fh):
                if el.tag != f"{_NS}row":
                    continue
                cells = {}
                for c in el.iter(f"{_NS}c"):
                    kind = c.get("t")
                    if kind == "inlineStr":
                        val = _text(c)
                    else:
                        v = c.find(f"{_NS}v")
                        raw = v.text if v is not None and v.text is not None else ""
                        val = shared[int(raw)] if kind == "s" and raw else raw
                    cells[_col_index(c.get("r"))] = val.strip()
                width = max(cells) + 1 if cells else 0
                rows.append([cells.get(i, "") for i in range(width)])
                el.clear()
    return rows
