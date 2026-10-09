"""The backfill merge keeps every id once, is deterministic and never overwrites."""

import gzip
import json

import catalog_rel_oa_backfill_merge as bm
import pytest
from catalog_rel_sud_search import read_backfill

pytestmark = pytest.mark.domain_corpus


def _src(tmp_path, name, recs):
    d = tmp_path / name
    d.mkdir()
    with gzip.open(d / "backfill.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in recs)
    return str(d)


def test_merge_unions_ids_is_byte_deterministic_and_records_the_sources(tmp_path):
    a = _src(tmp_path, "lanes", [{"openalex_id": "W1", "first_author": "A"},
                                 {"openalex_id": "W2", "first_author": "B"}])
    b = _src(tmp_path, "pool", [{"openalex_id": "W2", "first_author": "B"},
                                {"openalex_id": "W3", "first_author": "C"}])
    n, digest = bm.merge([a, b], str(tmp_path / "m1"))
    n2, digest2 = bm.merge([a, b], str(tmp_path / "m2"))
    assert (n, digest) == (3, digest2) and n2 == 3
    assert sorted(read_backfill(str(tmp_path / "m1"))) == ["W1", "W2", "W3"]
    assert (tmp_path / "m1" / "MERGED.sha256").read_text().startswith(digest)
    assert len((tmp_path / "m1" / "SOURCES.sha256").read_text().splitlines()) == 2
    with pytest.raises(SystemExit):
        bm.merge([a, b], str(tmp_path / "m1"))


def test_merge_refuses_conflicting_content(tmp_path):
    a = _src(tmp_path, "a", [{"openalex_id": "W1", "first_author": "A"}])
    b = _src(tmp_path, "b", [{"openalex_id": "W1", "first_author": "Z"}])
    with pytest.raises(SystemExit):
        bm.merge([a, b], str(tmp_path / "m"))
