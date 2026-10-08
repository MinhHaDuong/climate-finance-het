"""Citation discovery preserves every route, full text and resumable pages."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from catalog_rel_citation_chaining import (
    ChainError,
    Store,
    exact_rekey_map,
    forward_edges,
    intake_record,
    query_page,
)

pytestmark = pytest.mark.domain_corpus


def test_forward_work_retains_both_seed_edges_and_complete_abstract():
    work = {
        "id": "https://openalex.org/W3", "display_name": "Candidate", "publication_year": 2026,
        "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"],
        "abstract_inverted_index": {"complete": list(range(1600))},
    }
    assert forward_edges(work, ["W1", "W2"], "forward-01") == [
        ("W1", "W3", "forward", "forward-01"),
        ("W2", "W3", "forward", "forward-01"),
    ]
    record = intake_record(work, "forward-01", "2026-10-08T00:00:00Z")
    assert record["openalex_id"] == "W3"
    assert record["abstract"].split() == ["complete"] * 1600
    assert record["year"] == 2026


def test_cursor_resumes_without_losing_edges_or_repeating_first_page(tmp_path):
    store = Store(tmp_path / "round1")
    store.bind("budget_usd", 20)
    store.add_query("forward01", "forward", "cites:W1|W2", ["W1", "W2"])
    cursors = []

    class Reply:
        status_code = 200
        headers = {}

        def json(self):
            return {"meta": {"count": 2, "next_cursor": "page2" if len(cursors) == 1 else None, "cost": 1},
                    "results": [{"id": "https://openalex.org/W" + str(2 + len(cursors)),
                                 "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"]}]}

    def get(url, params, timeout):
        assert "publication_year" not in params["filter"]
        cursors.append(params["cursor"])
        return Reply()

    query_page(store, store.db.execute("SELECT * FROM queries").fetchone(), get)
    reopened = Store(tmp_path / "round1")
    query_page(reopened, reopened.db.execute("SELECT * FROM queries").fetchone(), get)
    assert cursors == ["*", "page2"]
    assert reopened.db.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 2
    assert reopened.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 4
    assert reopened.db.execute("SELECT completed FROM queries").fetchone()[0] == 1


def test_budget_is_shared_across_rounds_and_reserves_ambiguous_calls(tmp_path):
    one, two = Store(tmp_path / "round1"), Store(tmp_path / "round2")
    for store in (one, two):
        store.bind("budget_usd", 1)
    one.reserve("screen", .8, {})
    with pytest.raises(ChainError, match="cumulative budget"):
        two.reserve("openalex", .3, {})


def test_resume_refuses_changed_input_basis(tmp_path):
    store = Store(tmp_path / "round1")
    store.bind("basis", {"seed_hash": "first"})
    with pytest.raises(ChainError, match="resume basis changed"):
        store.bind("basis", {"seed_hash": "changed"})


def test_concurrent_reservations_cannot_overcommit_cap(tmp_path):
    root = tmp_path / "round1"
    store = Store(root)
    store.bind("budget_usd", 1)

    def reserve(_):
        local = Store(root)
        try:
            local.reserve("test", .3, {})
            return True
        except ChainError:
            return False
        finally:
            local.db.close()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(reserve, range(8)))
    assert sum(results) == 3
    assert store.db.execute("SELECT SUM(reserve) FROM budget.calls").fetchone()[0] == pytest.approx(.9)


def test_rekey_requires_unique_identity_and_refuses_many_to_one_history():
    old = [{"work_key": "doi:10.x/a", "all_dois": "10.x/a"}]
    new = [{"work_key": "openalex:W1", "all_dois": "10.x/a", "all_openalex_ids": "W1"}]
    mapping, unresolved = exact_rekey_map(old, new)
    assert mapping == {"doi:10.x/a": "openalex:W1"} and not unresolved
    ambiguous = new + [{"work_key": "openalex:W2", "all_dois": "10.x/a"}]
    mapping, unresolved = exact_rekey_map(old, ambiguous)
    assert not mapping and unresolved[0]["reason"] == "absent or ambiguous exact identity"
    merged_history = old + [{"work_key": "title:old-a", "all_dois": "10.x/a"}]
    mapping, unresolved = exact_rekey_map(merged_history, new)
    assert not mapping and len(unresolved) == 2
