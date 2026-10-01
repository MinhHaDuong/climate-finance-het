"""Every REL intake lane is placed in the pool's lane_order and the stage-1
lane_priority (ticket 1810, PR 1640 round 2, F13).

A lane missing from either list is ranked after it by name, so a lane
appended last (1810) silently outranked two earlier lanes. The committed
``data/rel_intake/<lane>.dvc`` pointers are the list of lanes: no data needed.
"""

import glob
import os

import pytest
import yaml

pytestmark = pytest.mark.domain_corpus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lanes() -> list[str]:
    return sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "data", "rel_intake", "*.dvc")))


def _yaml(name: str) -> dict:
    with open(os.path.join(ROOT, "config", name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_every_intake_lane_is_in_lane_order():
    lanes = _lanes()
    assert lanes, "no data/rel_intake/*.dvc pointer found"
    order = _yaml("rel_pool.yaml")["lane_order"]
    assert [lane for lane in lanes if lane not in order] == []


def test_every_intake_lane_has_a_stage1_priority():
    priority = _yaml("rel_screen.yaml")["stage1"]["lane_priority"]
    missing = [lane for lane in _lanes()
               if not any(lane == p or lane.startswith(p + "-") for p in priority)]
    assert missing == []


def test_repec_lane_is_last_in_both():
    assert _yaml("rel_pool.yaml")["lane_order"][-1] == "t1810-repec-local"
    assert _yaml("rel_screen.yaml")["stage1"]["lane_priority"][-1] == "t1810"
