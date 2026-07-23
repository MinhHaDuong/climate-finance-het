"""Shared seed-YAML validation guard (ticket 0304).

One sweep over config/*_sources.yaml enforcing, per seed idiom:

- key-documents lists (unfccc, oecd_dac): required fields, symbol/title
  uniqueness, valid doc_class — via catalog_keydocs.load_seed — and the DOI
  polarity: keydocs entries MUST NOT carry DOIs (the dedup boundary with the
  academic path).
- grey list: required fields, title+year uniqueness; entries MAY carry DOIs
  (that is the grey idiom — DOI-joined works enter via OpenAlex and are
  collapsed by catalog_merge).

Any new config/*_sources.yaml file must be claimed by one of the idioms
below, so a fourth seed list cannot land unvalidated.
"""

import glob
import os
import sys

import yaml

BASE = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(BASE, "scripts", "harvest"))

import catalog_keydocs as ck

KEYDOC_SEEDS = {
    "unfccc_sources.yaml": "unfccc",
    "oecd_dac_sources.yaml": "oecd",
}
GREY_SEEDS = {"grey_sources.yaml"}
GREY_REQUIRED = ("title", "author", "year", "source_org")


def seed_files():
    return sorted(glob.glob(os.path.join(BASE, "config", "*_sources.yaml")))


def test_every_seed_file_is_claimed():
    known = set(KEYDOC_SEEDS) | GREY_SEEDS
    unclaimed = [os.path.basename(p) for p in seed_files()
                 if os.path.basename(p) not in known]
    assert not unclaimed, (
        f"seed files with no validation idiom: {unclaimed} — "
        "register them in tests/test_seed_yaml_guard.py")


def test_keydoc_seeds_validate_with_no_doi():
    for fname, source in KEYDOC_SEEDS.items():
        entries = ck.load_seed(os.path.join(BASE, "config", fname), source)
        assert entries, fname
        # load_seed already enforces required fields, doc_class, symbol and
        # filename-stem uniqueness, and rejects any doi: key.
        titles = [(e["title"], e["year"]) for e in entries]
        assert len(titles) == len(set(titles)), (
            f"{fname}: duplicate title+year pairs would collide in "
            "catalog_merge dedup")


def test_grey_seed_valid_doi_allowed():
    path = os.path.join(BASE, "config", "grey_sources.yaml")
    entries = yaml.safe_load(open(path, encoding="utf-8"))
    assert entries
    keys = set()
    for e in entries:
        for field in GREY_REQUIRED:
            assert e.get(field), f"grey entry missing {field}: {e}"
        key = (e["title"].lower(), str(e["year"]))
        assert key not in keys, f"duplicate grey entry: {key}"
        keys.add(key)
    # polarity: DOIs are allowed here (and present today)
    assert any(e.get("doi") for e in entries), (
        "grey idiom expects DOI-joined entries; if this changed, "
        "update the guard deliberately")
