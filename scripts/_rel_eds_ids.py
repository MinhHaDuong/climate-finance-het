"""Identifiers hidden in EDS accession numbers (ticket 2040).

Standard library only; shared by ``catalog_rel_eds_repec_handles`` (which checks
them against the local RePEc mirror) and ``corpus_rel_causal_yield`` (which
writes them to the intake).

``edsrep.<kind>.<archive>.<series>.<item>`` is a RePEc handle
``RePEc:<archive>:<series>:<item>`` with the item re-spelled: EDS drops the
colons of article items (``v:152:y:2022`` becomes ``v152y2022``) and turns
other punctuation into dots, so the item cannot be decoded back by rule. The
archive and the series are exact. The decoded item is therefore only a
*candidate*: it becomes a handle when exactly one mirror handle of the same
archive and series has the same item once both are reduced to lower-case
letters and digits (``item_key``). Anything else stays labelled, never dropped.

``EDSZBW<ppn>`` (database ``edszbw``, provider ECONIS) is the K10plus PPN, the
catalogue record number of the ZBW/GBV union catalogue (four to nine digits and a
mod-11 check character, ``ppn_valid``). It identifies a record in that
catalogue only; it is not a Handle, a DOI or any intake key.
"""

import re

EDSREP = re.compile(r"^edsrep\.([a-z])\.([a-z0-9]{3})\.([a-z0-9_-]+)\.(.+)$", re.IGNORECASE)
ZBW = re.compile(r"^EDSZBW(\d{4,9})([0-9X])$")
HANDLE = re.compile(r"^RePEc:[a-z0-9]{3}:[a-z0-9_-]+:\S+$", re.IGNORECASE)
KINDS = {"p": "paper", "a": "article", "h": "chapter", "b": "book"}

STATUS_MATCHED = "matched"      # exactly one mirror handle has this archive, series and item key
STATUS_AMBIGUOUS = "ambiguous"  # several mirror handles share the item key
STATUS_UNMATCHED = "unmatched"  # archive and series known, no mirror handle with this item
STATUS_NO_SERIES = "no_series"  # archive or series absent from the mirror
STATUS_UNDECODABLE = "undecodable"


def item_key(item):
    """The item reduced to lower-case letters and digits, the form on which an
    EDS item and a mirror item are compared."""
    return re.sub(r"[^a-z0-9]", "", (item or "").lower())


def decode_edsrep(an):
    """``{kind, archive, series, item, candidate}`` of an ``edsrep.`` accession
    number, or None. ``candidate`` is ``RePEc:archive:series:item`` with the
    item as EDS spells it, to be verified."""
    m = EDSREP.match((an or "").strip())
    if not m:
        return None
    kind, archive, series, item = m.group(1).lower(), m.group(2).lower(), m.group(3).lower(), m.group(4)
    return {"kind": KINDS.get(kind, kind), "archive": archive, "series": series, "item": item,
            "candidate": f"RePEc:{archive}:{series}:{item}"}


def mirror_key(handle):
    """``(archive, series, item_key)`` of a cleaned mirror handle, or None."""
    parts = (handle or "").split(":", 3)
    if len(parts) != 4 or parts[0].lower() != "repec" or not HANDLE.match(handle):
        return None
    return parts[1].lower(), parts[2].lower(), item_key(parts[3])


def resolve(decoded, index, archives=(), series=()):
    """``(status, handle)`` of a decoded accession number against ``index``, a
    mapping ``(archive, series, item_key) -> set of mirror handles``;
    ``archives`` and ``series`` are the (archive) and (archive, series) pairs
    the mirror holds, to tell an absent series from an absent item."""
    if decoded is None:
        return STATUS_UNDECODABLE, ""
    key = (decoded["archive"], decoded["series"], item_key(decoded["item"]))
    hits = index.get(key, ())
    if len(hits) == 1:
        return STATUS_MATCHED, next(iter(hits))
    if len(hits) > 1:
        return STATUS_AMBIGUOUS, ""
    if (decoded["archive"], decoded["series"]) not in series:
        return STATUS_NO_SERIES, ""
    return STATUS_UNMATCHED, ""


def ppn_valid(an):
    """Whether an ``EDSZBW`` accession number is a K10plus PPN: four to nine digits and
    the check character of the PICA modulus-11 scheme (weights 2..10 from the
    last digit; remainder 0 gives 0, remainder 1 gives X)."""
    m = ZBW.match((an or "").strip())
    if not m:
        return False
    total = sum(int(d) * (i + 2) for i, d in enumerate(reversed(m.group(1))))
    check = (11 - total % 11) % 11
    return m.group(2) == ("X" if check == 10 else str(check))
