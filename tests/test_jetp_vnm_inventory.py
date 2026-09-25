"""Bounded official inventory rows remain positions, including wrapped counts."""

import os
from collections import Counter
from pathlib import Path

import pytest
from jetp._vnm_inventory import assemble_inventory, extract_inventory

pytestmark = pytest.mark.wp_jetp

def test_wrapped_count_is_not_an_ordinal_or_named_asset():
    rows = assemble_inventory(
        [
            {
                "annex": "I.1",
                "page": 157,
                "cells": [
                    "36",
                    "Convert and replace 244 locomotives and\n80 generator cars to use electricity and\ngreen energy",
                    "National",
                ],
                "source_wording": "36 Convert and replace 244 locomotives and\n80 generator cars to use electricity and\ngreen energy",
            },
            {
                "annex": "I.2",
                "page": 159,
                "cells": [
                    "1",
                    "Pilot testing for 3-4 suitable coal-fired power plants (CFPPs)",
                    "TBD",
                ],
                "source_wording": "1 Pilot testing for 3-4 suitable coal-fired power plants (CFPPs) TBD",
            },
        ],
        require_complete=False,
    )
    assert [r["ordinal"] for r in rows] == [36, 1]
    assert all(r["classification"] == "programme" for r in rows)
    assert rows[0]["source_cells"][1].endswith("green energy")
    assert rows[0]["printed_pages"] == [141]
    assert not any("events" in r or "project_id" in r for r in rows)


def test_continuation_preserves_all_cells_and_both_page_locators():
    rows = assemble_inventory(
        [
            {
                "annex": "I.2",
                "page": 161,
                "cells": ["23", "Unreviewed proposal", "first"],
                "source_wording": "23 Unreviewed proposal first",
            },
            {
                "annex": "I.2",
                "page": 162,
                "cells": ["", "continued wording", "second"],
                "source_wording": "continued wording second",
            },
        ],
        require_complete=False,
    )
    assert len(rows) == 1
    assert rows[0]["pages"] == [161, 162]
    assert rows[0]["source_cells"] == [
        "23",
        "Unreviewed proposal\ncontinued wording",
        "first\nsecond",
    ]
    assert (
        rows[0]["source_wording"]
        == "23 Unreviewed proposal first\n\f\ncontinued wording second"
    )
    assert rows[0]["classification"] == "unknown"


@pytest.mark.slow
def test_saved_rmp_has_all_279_rows_without_solar_hydro_identity_join():
    source = os.environ.get("VNM_INVENTORY_PDF")
    if not source:
        pytest.skip(
            "Set VNM_INVENTORY_PDF to the saved English RMP for source-byte audit"
        )
    rows = extract_inventory(Path(source))
    assert Counter(r["annex"] for r in rows) == {"I.1": 37, "I.2": 181, "II": 61}
    solar = next(r for r in rows if r["annex"] == "I.1" and r["ordinal"] == 22)
    assert "KN Tri An Floating Solar Farm" in solar["source_cells"][1]
    assert solar["classification"] == "named"
    assert "project_id" not in solar
    transport = next(r for r in rows if r["annex"] == "I.1" and r["ordinal"] == 36)
    assert "80 generator cars" in transport["source_wording"]
    assert all(r["source_wording"] and r["pages"] for r in rows)
    assert rows == extract_inventory(Path(source))


def test_incomplete_or_duplicate_inventory_fails_closed():
    fragment = {'annex': 'I.1', 'page': 155, 'cells': ['1', 'Long Tao Hydropower plan'], 'source_wording': '1 Long Tao Hydropower plan'}
    with pytest.raises(ValueError, match='incomplete'):
        assemble_inventory([fragment])
    with pytest.raises(ValueError, match='Duplicate'):
        assemble_inventory([fragment, fragment], require_complete=False)


def test_continuation_cannot_cross_annex_or_skip_page():
    fragments = [
        {'annex': 'I.1', 'page': 155, 'cells': ['1', 'Long Tao Hydropower plan'], 'source_wording': '1 Long Tao Hydropower plan'},
        {'annex': 'I.2', 'page': 159, 'cells': ['', 'unrelated'], 'source_wording': 'unrelated'},
    ]
    with pytest.raises(ValueError, match='Orphan or nonconsecutive'):
        assemble_inventory(fragments, require_complete=False)
