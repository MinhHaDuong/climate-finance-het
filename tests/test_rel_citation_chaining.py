"""Citation discovery preserves every route, full text and resumable pages."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from _rel_chaining import (
    ChainError,
    Store,
    forward_edges,
    intake_record,
    oa_request,
    query_page,
    resolve_one_seed,
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


def test_raw_response_replay_avoids_recharging_after_cursor_commit_interruption(tmp_path):
    store = Store(tmp_path / "round1")
    store.bind("budget_usd", 20)
    params = {"filter": "cites:W1", "cursor": "*", "per_page": 100}

    class Reply:
        status_code = 200
        headers = {"X-RateLimit-Cost-USD": ".0001"}

        def json(self):
            return {"meta": {"count": 1, "next_cursor": None}, "results": [{"id": "https://openalex.org/W2"}]}

    first = oa_request(store, params, lambda *args, **kwargs: Reply())
    reopened = Store(tmp_path / "round1")

    def forbidden(*args, **kwargs):
        raise AssertionError("durable raw page must be replayed without another request")

    assert oa_request(reopened, params, forbidden) == first
    assert reopened.db.execute("SELECT COUNT(*) FROM budget.calls").fetchone()[0] == 1


def test_explicit_redirect_keeps_both_original_seed_routes():
    work = {"id": "https://openalex.org/W9", "referenced_works": ["https://openalex.org/W3"]}
    assert forward_edges(work, ["W1", "W2"], "q", {"W1": "W3", "W2": "W3"}) == [
        ("W1", "W9", "forward", "q"), ("W2", "W9", "forward", "q")]


def test_free_singleton_archives_native_payload_and_zero_charge(tmp_path):
    import gzip
    import json

    store = Store(tmp_path / "round1")
    store.bind("budget_usd", 20)

    class Reply:
        status_code = 200
        headers = {"X-RateLimit-Cost-USD": "0"}

        def json(self):
            return {"id": "https://openalex.org/W2", "referenced_works": []}

    def get(url, params, timeout):
        assert url.endswith("/works/W1") and "entity" not in params
        return Reply()

    result = oa_request(store, {"entity": "W1"}, get)
    assert result["results"][0]["id"].endswith("/W2")
    raw = next((store.root / "raw").glob("*.gz"))
    assert json.load(gzip.open(raw, "rt"))["body"] == Reply().json()
    assert store.db.execute("SELECT cost FROM budget.calls").fetchone()[0] == 0


def test_identity_lookup_uses_title_field_and_delivers_nonmatching_results(tmp_path):
    import json

    store = Store(tmp_path / "round1")
    store.bind("budget_usd", 20)
    seed = {"k": "old", "body": json.dumps({"title": "How additional is CDM?", "year": "2026", "first_author": "A Author"})}
    store.db.execute("INSERT INTO seeds VALUES(?,?,?,?,?)", ("old", "", seed["body"], "baseline:icf", "pending"))
    store.db.commit()

    class Reply:
        status_code = 200
        headers = {"X-RateLimit-Cost-USD": ".001"}

        def json(self):
            return {"meta": {"count": 2}, "results": [
                {"id": "https://openalex.org/W1", "display_name": "How additional is CDM?", "publication_year": 2026,
                 "authorships": [{"author": {"display_name": "A Author"}}]},
                {"id": "https://openalex.org/W2", "display_name": "Another record", "publication_year": 2020}]}

    def get(url, params, timeout):
        assert params["filter"] == 'title.search:"How additional is CDM"'
        assert "search" not in params and "publication_year" not in params["filter"]
        return Reply()

    resolve_one_seed(store.root, store.budget_path, seed, {}, get)
    assert store.db.execute("SELECT oa FROM seeds").fetchone()[0] == "W1"
    assert store.db.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 2


def test_atomic_admission_ceiling_preserves_completion_headroom(tmp_path):
    ledger = tmp_path / 'shared-budget.sqlite'
    first = Store(tmp_path / 'first', ledger)
    first.bind('budget_usd', 30)
    first.reserve('prior', 20, {})
    # Independent connections share BEGIN IMMEDIATE admission, so only one
    # simultaneous wave fits the protected ceiling, irrespective of timing.
    def admit(n):
        store = Store(tmp_path / str(n), ledger)
        store.bind('budget_usd', 30)
        try:
            store.reserve('main-wave', 3, {}, admission_ceiling=24)
            return True
        except ChainError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(admit, [2, 3])) == [False, True]
    # Completion tasks can still use the author-approved global capacity.
    first.reserve('completion', 6, {})
    with pytest.raises(ChainError, match='cumulative budget'):
        first.reserve('exceeds-global', 2, {}, admission_ceiling=100)
    with pytest.raises(ChainError, match='admission ceiling'):
        first.reserve('invalid-ceiling', 1, {}, admission_ceiling=float('nan'))


def test_direction_delta_preserves_interrupted_forward_and_plans_missing_forward(tmp_path):
    import _rel_chaining as chain
    store = Store(tmp_path / "round2")
    for identity in ("W1", "W2"):
        store.db.execute("INSERT INTO seeds VALUES(?,?,?,?,?)", (identity, identity, "{}", "new-frontier", "identified"))
    store.add_query("old-backward", "backward", "openalex_id:W1|W2", ["W1", "W2"])
    store.add_query("old-forward", "forward", "cites:W1", ["W1"])
    store.db.execute("UPDATE queries SET completed=1 WHERE k='old-backward'")
    store.db.execute("UPDATE queries SET cursor='next-page',pages=1 WHERE k='old-forward'")
    store.db.execute("INSERT INTO edges VALUES('W1','W9','forward','old-forward')")
    store.db.commit()
    chain.plan_citation_queries(store)
    forward = list(store.db.execute("SELECT * FROM queries WHERE kind='forward' ORDER BY k"))
    assert len(forward) == 2
    assert next(r for r in forward if r['k'] == 'old-forward')['cursor'] == 'next-page'
    assert next(r for r in forward if r['k'] != 'old-forward')['filter'] == 'cites:W2'
    assert store.db.execute("SELECT COUNT(*) FROM queries WHERE kind='backward'").fetchone()[0] == 1
    assert store.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 1
    chain.plan_citation_queries(store)
    assert store.db.execute("SELECT COUNT(*) FROM queries").fetchone()[0] == 3


def test_explicit_frontier_does_not_expand_historical_icf_and_binds_closure(tmp_path):
    import csv
    import json

    import _rel_chaining as chain
    pool, view = tmp_path / 'pool.csv', tmp_path / 'view.csv'
    with pool.open('w') as f:
        w = csv.DictWriter(f, fieldnames=['work_key', 'openalex_id', 'title']);w.writeheader()
        w.writerows([{'work_key': 'new', 'openalex_id': 'W1', 'title': 'New uncertain work'},
                     {'work_key': 'historical', 'openalex_id': 'W2', 'title': 'Historical ICF'}])
    with view.open('w') as f:
        w = csv.DictWriter(f, fieldnames=['work_key', 'status']);w.writeheader()
        w.writerows([{'work_key': 'new', 'status': 'unsure_unresolved'}, {'work_key': 'historical', 'status': 'icf'}])
    closure = tmp_path / 'closure.json'
    closure.write_text(json.dumps({'round_dispositions_reconciled': True, 'venue_dimensions_reconciled': True, 'yield_reconciled': True, 'pool_sha256': chain.sha(pool), 'view_sha256': chain.sha(view)}))
    frontier = tmp_path / 'frontier.json'
    frontier.write_text(json.dumps({'version': '1654-final-frontier-v1', 'pool_sha256': chain.sha(pool),
        'view_sha256': chain.sha(view), 'closure_artifact': str(closure), 'closure_sha256': chain.sha(closure),
        'records': [{'work_key': 'new', 'selection_reason': 'genuinely_new_uncertain', 'stratum': 'new_round1'}]}))
    store = Store(tmp_path / 'round2')
    chain.init_seeds(store, pool, view, [], 30, frontier_path=frontier)
    assert [r[0] for r in store.db.execute('SELECT k FROM seeds')] == ['new']
    assert store.db.execute('SELECT reason FROM seeds').fetchone()[0] == 'frontier:new_round1:genuinely_new_uncertain'
    closure.write_text('{}')
    with pytest.raises(ChainError, match='closure'):
        chain.init_seeds(store, pool, view, [], 30, frontier_path=frontier)


def test_completed_direction_reuse_requires_native_page_chain_and_preserves_edge_source(tmp_path):
    import gzip
    import json

    import _rel_chaining as chain
    prior = Store(tmp_path / 'prior')
    prior.add_query('back', 'backward', 'openalex_id:W1', ['W1'])
    prior.add_query('forward', 'forward', 'cites:W1', ['W1'])
    for kind, filt in [('backward', 'openalex_id:W1'), ('forward', 'cites:W1')]:
        params = {'filter': filt, 'per_page': 100, 'cursor': '*'}
        key = chain.hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        path = prior.root / 'raw' / (kind + '.json.gz')
        with gzip.open(path, 'wt') as f:
            json.dump({'query': params, 'status': 200, 'retrieved_at': '2026-10-08T00:00:00Z', 'body': {'meta': {'count': 1, 'next_cursor': None},
                'results': [{'id': 'https://openalex.org/' + ('W1' if kind == 'backward' else 'W9'), 'referenced_works': ['https://openalex.org/W1']}] }}, f)
        prior.db.execute('INSERT INTO api_pages VALUES(?,?,?)', (key, str(path.relative_to(prior.root)), 1))
    prior.db.execute("UPDATE queries SET completed=1,received=1,expected=1,pages=1,cursor='' ")
    prior.db.execute("INSERT INTO edges VALUES('W1','W9','forward','forward')")
    prior.db.commit()
    snapshot = tmp_path / 'prior.sqlite'
    import sqlite3
    with sqlite3.connect(snapshot) as target:
        prior.db.backup(target)
    native_index = tmp_path / 'native-index.json'
    pages = {r['path']: {'sha256': chain.sha(prior.root / r['path']), 'request_sha256': r['k']}
             for r in prior.db.execute('SELECT * FROM api_pages')}
    routing_source = tmp_path / 'routing.py'
    routing_source.write_text('OA = "https://api.openalex.org/works"\n')
    native_index.write_text(json.dumps({'snapshot_sha256': chain.sha(snapshot), 'pages': pages,
        'acquisition_source': {'artifact': str(routing_source), 'artifact_sha256': chain.sha(routing_source),
            'recorded_revision': 'a' * 40, 'method': 'GET', 'endpoint': chain.OA}}))
    index_args = {'native_index_path': native_index, 'native_index_sha256': chain.sha(native_index)}
    current = Store(tmp_path / 'next')
    current.db.execute("INSERT INTO seeds VALUES('new','W1','{}','new','identified')")
    current.db.commit()
    chain.reuse_completed_directions(current, snapshot, prior.root, chain.sha(snapshot), **index_args)
    chain.plan_citation_queries(current)
    assert current.db.execute('SELECT COUNT(*) FROM queries').fetchone()[0] == 0
    assert current.db.execute('SELECT COUNT(*) FROM direction_reuse').fetchone()[0] == 2
    assert prior.db.execute('SELECT COUNT(*) FROM edges').fetchone()[0] == 1
    def no_duplicate_singleton(*args, **kwargs):
        raise AssertionError('reused exact source metadata must not cause another singleton request')
    chain.resolve_seed_aliases(current, get=no_duplicate_singleton)
    original_routing = routing_source.read_bytes()
    routing_source.write_text('OA = "https://unrelated.example/works"\n')
    changed_source = Store(tmp_path / 'changed-source')
    changed_source.db.execute("INSERT INTO seeds VALUES('new','W1','{}','new','identified')")
    changed_source.db.commit()
    with pytest.raises(ChainError, match='routing source binding'):
        chain.reuse_completed_directions(changed_source, snapshot, prior.root, chain.sha(snapshot), **index_args)
    assert changed_source.db.execute('SELECT COUNT(*) FROM direction_reuse').fetchone()[0] == 0
    routing_source.write_bytes(original_routing)
    (prior.root / 'raw' / 'forward.json.gz').unlink()
    failed = Store(tmp_path / 'fail')
    failed.db.execute("INSERT INTO seeds VALUES('new','W1','{}','new','identified')")
    failed.db.commit()
    with pytest.raises(ChainError, match='native'):
        chain.reuse_completed_directions(failed, snapshot, prior.root, chain.sha(snapshot), **index_args)
    assert failed.db.execute('SELECT COUNT(*) FROM direction_reuse').fetchone()[0] == 0


def test_metadata_get_protects_completion_headroom_before_network(tmp_path):
    store = Store(tmp_path / 'metadata')
    store.bind('budget_usd', 30)
    store.reserve('other', 23.9995, {})
    def no_network(*args, **kwargs):
        raise AssertionError('protected ceiling must refuse before HTTP')
    with pytest.raises(ChainError, match='cumulative budget'):
        oa_request(store, {'filter': 'doi:https://doi.org/10.1/public', 'per_page': 100, 'cursor': '*'},
                   get=no_network, admission_ceiling=24)
    assert store.db.execute('SELECT COUNT(*) FROM budget.calls').fetchone()[0] == 1


def test_reuse_rejects_seed_list_not_bound_to_exact_direction_filter(tmp_path):
    import _rel_chaining as chain
    prior = Store(tmp_path / 'prior')
    query = {'kind': 'forward', 'seeds': '["W1"]', 'filter': 'cites:W2'}
    with pytest.raises(ChainError, match='seed/filter'):
        chain._completed_direction_evidence(prior.db, prior.root, query, {'pages': {}})

@pytest.mark.parametrize('invalid', [-1.0, float('nan'), float('inf'), -float('inf')])
def test_budget_rejects_invalid_settlement_without_changing_liability(tmp_path, invalid):
    store = Store(tmp_path / 'round')
    store.bind('budget_usd', 1)
    call = store.reserve('offline', .5, {})
    with pytest.raises(ChainError, match='finite|nonnegative'):
        store.settle(call, invalid, {})
    row = store.db.execute('SELECT cost,status FROM budget.calls WHERE k=?', (call,)).fetchone()
    assert row['cost'] is None and row['status'] == 'reserved'
    with pytest.raises(ChainError, match='budget'):
        store.reserve('offline', .6, {})

@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), -1.0, 0.0])
def test_budget_bind_rejects_nonfinite_nonpositive_cap(tmp_path, invalid):
    store = Store(tmp_path / 'round')
    with pytest.raises(ChainError, match='finite|positive'):
        store.bind('budget_usd', invalid)
    assert store.db.execute('SELECT COUNT(*) FROM config').fetchone()[0] == 0

@pytest.mark.parametrize('field,value', [('cost', -1.0), ('reserve', -1.0), ('reserve', float('inf'))])
def test_budget_refuses_corrupt_existing_meter_without_new_admission(tmp_path, field, value):
    store = Store(tmp_path / 'round')
    store.bind('budget_usd', 10)
    call = store.reserve('offline', 1, {})
    store.db.execute(f'UPDATE budget.calls SET {field}=? WHERE k=?', (value, call))
    store.db.commit()
    with pytest.raises(ChainError, match='finite|nonnegative'):
        store.reserve('new', 1, {})
    assert store.db.execute('SELECT COUNT(*) FROM budget.calls').fetchone()[0] == 1

@pytest.mark.parametrize('mutation', ['version', 'closure_pool', 'closure_view', 'closure_source'])
def test_frontier_rejects_unrecognized_version_and_mismatched_closure(tmp_path, mutation):
    import json

    import _rel_chaining as chain
    pool, view = tmp_path / 'pool.csv', tmp_path / 'view.csv'
    pool.write_text('work_key,openalex_id,title\nnew,W1,New\n')
    view.write_text('work_key,status\nnew,icf\n')
    closure = tmp_path / 'closure.json'
    body = {'round_dispositions_reconciled': True, 'venue_dimensions_reconciled': True,
            'yield_reconciled': True, 'pool_sha256': chain.sha(pool), 'view_sha256': chain.sha(view)}
    if mutation == 'closure_pool': body['pool_sha256'] = '0' * 64
    if mutation == 'closure_view': body['view_sha256'] = '0' * 64
    closure.write_text(json.dumps(body))
    frontier = tmp_path / 'frontier.json'
    specification = {'version': 'unknown' if mutation == 'version' else '1654-final-frontier-v1',
        'pool_sha256': chain.sha(pool), 'view_sha256': chain.sha(view), 'closure_artifact': str(closure),
        'closure_sha256': chain.sha(closure), 'records': [{'work_key': 'new', 'selection_reason': 'confirmed', 'stratum': 'confirmed'}]}
    if mutation == 'closure_source':
        specification['previous_round'] = {'snapshot_sha256': '0' * 64, 'native_index_sha256': '1' * 64}
    frontier.write_text(json.dumps(specification))
    store = Store(tmp_path / 'round')
    with pytest.raises(ChainError, match='version|closure'):
        chain.init_seeds(store, pool, view, [], 30, frontier_path=frontier)
    assert store.db.execute('SELECT COUNT(*) FROM seeds').fetchone()[0] == 0

def test_forward_reuse_preserves_native_relationship_gap(tmp_path):
    import gzip
    import json
    import sqlite3

    import _rel_chaining as chain
    prior = Store(tmp_path / 'prior')
    prior.add_query('forward', 'forward', 'cites:W1', ['W1'])
    params = {'filter': 'cites:W1', 'per_page': 100, 'cursor': '*'}
    request = chain.hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = prior.root / 'raw/forward.json.gz'
    with gzip.open(path, 'wt') as f:
        json.dump({'query': params, 'status': 200, 'retrieved_at': '2026-10-08T00:00:00Z',
            'body': {'meta': {'count': 1, 'next_cursor': None}, 'results': [{'id': 'https://openalex.org/W9', 'referenced_works': []}]}}, f)
    prior.db.execute('INSERT INTO api_pages VALUES(?,?,?)', (request, 'raw/forward.json.gz', 1))
    prior.db.execute("UPDATE queries SET completed=1,received=1,expected=1,pages=1,cursor=''")
    prior.db.execute("INSERT INTO unresolved VALUES('forward:W9','edge','forward result has no returned seed reference')")
    prior.db.commit()
    snapshot = tmp_path / 'prior.sqlite'
    with sqlite3.connect(snapshot) as target: prior.db.backup(target)
    routing = tmp_path / 'routing.py';routing.write_text('OA public collector')
    index = tmp_path / 'index.json'
    index.write_text(json.dumps({'snapshot_sha256': chain.sha(snapshot), 'pages': {'raw/forward.json.gz': {'sha256': chain.sha(path), 'request_sha256': request}}, 'acquisition_source': {'artifact': str(routing), 'artifact_sha256': chain.sha(routing), 'recorded_revision': 'a'*40, 'method': 'GET', 'endpoint': chain.OA}}))
    current = Store(tmp_path / 'current');current.db.execute("INSERT INTO seeds VALUES('new','W1','{}','new','identified')");current.db.commit()
    chain.reuse_completed_directions(current, snapshot, prior.root, chain.sha(snapshot), native_index_path=index, native_index_sha256=chain.sha(index))
    evidence = json.loads(current.db.execute('SELECT evidence FROM direction_reuse').fetchone()[0])
    assert evidence['source_unresolved'] == [{'k': 'forward:W9', 'kind': 'edge', 'note': 'forward result has no returned seed reference'}]
    assert evidence['source_edge_count'] == 0
    assert current.db.execute("SELECT kind,note FROM unresolved WHERE k='forward:W9'").fetchone()[:] == ('edge', 'forward result has no returned seed reference')
    chain.plan_citation_queries(current)
    assert current.db.execute("SELECT COUNT(*) FROM queries WHERE kind='forward'").fetchone()[0] == 0
    assert current.db.execute('SELECT COUNT(*) FROM edges').fetchone()[0] == 0

def test_budget_overflow_meter_rolls_back_and_refuses_new_call(tmp_path):
    store = Store(tmp_path / 'round')
    store.bind('budget_usd', 10)
    for _ in range(2):
        store.db.execute("INSERT INTO budget.calls(round,provider,reserve,status,details,date) VALUES('offline','corrupt',1e308,'reserved','{}','offline')")
    store.db.commit()
    with pytest.raises(ChainError, match='finite'):
        store.reserve('new', 1, {})
    assert not store.db.in_transaction
    assert store.db.execute('SELECT COUNT(*) FROM budget.calls').fetchone()[0] == 2


@pytest.mark.parametrize('references', ['missing', None, False, '', {}, ['bad-id'], [1], ['https://openalex.org/W2', None]])
def test_backward_reference_absence_remains_source_bound_uncertainty(tmp_path, monkeypatch, references):
    import json

    import _rel_chaining as chain

    store = Store(tmp_path / 'round')
    store.add_query('backward', 'backward', 'openalex_id:W1', ['W1'])
    work = {'id': 'https://openalex.org/W1'}
    if references != 'missing':
        work['referenced_works'] = references
    body = {'results': [work], 'meta': {'count': 1, 'next_cursor': None}}
    monkeypatch.setattr(chain, 'oa_request', lambda *args: body)
    chain.query_page(store, store.db.execute('SELECT * FROM queries').fetchone())
    assert store.db.execute('SELECT completed FROM queries').fetchone()[0] == 1
    assert store.db.execute('SELECT COUNT(*) FROM edges').fetchone()[0] == 0
    gap = store.db.execute("SELECT * FROM unresolved WHERE kind='reference_evidence'").fetchone()
    assert gap is not None
    evidence = json.loads(gap['note'])
    assert evidence['query_id'] == 'backward' and evidence['work_id'] == 'W1'
    assert evidence['native_work_sha256'] == chain.hashlib.sha256(json.dumps(work, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def test_reference_gaps_preserve_cursor_coverage_native_empty_list_and_export(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    import _rel_chaining as chain

    store = Store(tmp_path / 'round')
    store.add_query('backward', 'backward', 'openalex_id:W1|W2|W3', ['W1', 'W2', 'W3'])
    bodies = iter([
        {'results': [{'id': 'https://openalex.org/W1', 'display_name': 'First', 'publication_year': 2020}],
         'meta': {'count': 3, 'next_cursor': 'next'}},
        {'results': [{'id': 'https://openalex.org/W2', 'display_name': 'Second', 'publication_year': 2020, 'referenced_works': []},
                     {'id': 'https://openalex.org/W3', 'display_name': 'Third', 'publication_year': 2020, 'referenced_works': ['https://openalex.org/W9']}],
         'meta': {'count': 3, 'next_cursor': None}}])
    monkeypatch.setattr(chain, 'oa_request', lambda *args: next(bodies))
    for _ in range(2):
        chain.query_page(store, store.db.execute('SELECT * FROM queries').fetchone())
    q = store.db.execute('SELECT * FROM queries').fetchone()
    assert (q['completed'], q['pages'], q['received']) == (1, 2, 3)
    assert [tuple(row) for row in store.db.execute('SELECT * FROM edges')] == [('W3', 'W9', 'backward', 'backward')]
    assert store.db.execute('SELECT COUNT(*) FROM unresolved').fetchone()[0] == 1
    monkeypatch.setattr(chain.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(stdout='a' * 40))
    monkeypatch.setattr(chain.contract, 'check_delivery', lambda *args: [])
    chain.export_delivery(store, tmp_path / 'delivery')
    manifest = json.loads((tmp_path / 'delivery/manifest.json').read_text())
    assert manifest['coverage'] == 'incomplete'
    assert len(manifest['incomplete']) == 1
    registry = list(chain.rows(tmp_path / 'delivery/registry.csv'))
    assert registry[0]['completed'] == 'true' and registry[0]['n_received'] == '3'


def test_singleton_and_archive_recovery_retain_source_reference_gaps(tmp_path, monkeypatch):
    import gzip
    import json

    import _rel_chaining as chain

    store = Store(tmp_path / 'round')
    work = {'id': 'https://openalex.org/W1', 'referenced_works': None}
    monkeypatch.setattr(chain, 'oa_request', lambda *args: {'results': [work]})
    chain.resolve_seed_alias(store.root, store.budget_path, 'W1', None)
    initial = dict(store.db.execute("SELECT * FROM unresolved WHERE kind='reference_evidence'").fetchone())
    assert store.db.execute('SELECT completed FROM queries').fetchone()[0] == 1
    store.db.execute("INSERT INTO seeds VALUES('seed','W1','{}','test','identified')")
    store.db.commit()
    (store.root / 'cache_targets.txt').write_text('W1\n')
    cache = tmp_path / 'cache'; cache.mkdir()
    archive = cache / 'native.jsonl.gz'
    with gzip.open(archive, 'wt') as stream:
        stream.write(json.dumps(work) + '\n')
    chain.restore_cached_metadata(store, cache)
    gaps = [dict(row) for row in store.db.execute("SELECT * FROM unresolved WHERE kind='reference_evidence'")]
    assert initial in gaps and len(gaps) == 2
    archive_gap = next(row for row in gaps if row['k'].startswith('archive:'))
    archive_query = store.db.execute("SELECT filter FROM queries WHERE kind='archive'").fetchone()[0]
    assert chain.sha(archive) in archive_query
    assert json.loads(archive_gap['note'])['query_id'] == 'archive:native.jsonl.gz'
    assert store.db.execute('SELECT COUNT(*) FROM edges').fetchone()[0] == 0


def test_backward_reuse_keeps_absent_reference_diagnostic_without_zero_claim(tmp_path):
    import gzip
    import json
    import sqlite3

    import _rel_chaining as chain

    prior = Store(tmp_path / 'prior')
    prior.add_query('backward', 'backward', 'openalex_id:W1', ['W1'])
    params = {'filter': 'openalex_id:W1', 'per_page': 100, 'cursor': '*'}
    request = chain.hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = prior.root / 'raw/backward.json.gz'
    work = {'id': 'https://openalex.org/W1'}
    with gzip.open(path, 'wt') as stream:
        json.dump({'query': params, 'status': 200, 'retrieved_at': '2026-10-08T00:00:00Z',
                   'body': {'meta': {'count': 1, 'next_cursor': None}, 'results': [work]}}, stream)
    prior.db.execute('INSERT INTO api_pages VALUES(?,?,?)', (request, 'raw/backward.json.gz', 1))
    prior.db.execute("UPDATE queries SET completed=1,received=1,expected=1,pages=1,cursor=''")
    prior.db.commit()
    snapshot = tmp_path / 'prior.sqlite'
    with sqlite3.connect(snapshot) as target:
        prior.db.backup(target)
    routing = tmp_path / 'routing.py'; routing.write_text('OA public collector')
    index = tmp_path / 'index.json'
    index.write_text(json.dumps({'snapshot_sha256': chain.sha(snapshot), 'pages': {
        'raw/backward.json.gz': {'sha256': chain.sha(path), 'request_sha256': request}},
        'acquisition_source': {'artifact': str(routing), 'artifact_sha256': chain.sha(routing),
                               'recorded_revision': 'a' * 40, 'method': 'GET', 'endpoint': chain.OA}}))
    current = Store(tmp_path / 'current')
    current.db.execute("INSERT INTO seeds VALUES('new','W1','{}','new','identified')")
    current.db.commit()
    chain.reuse_completed_directions(current, snapshot, prior.root, chain.sha(snapshot),
                                     native_index_path=index, native_index_sha256=chain.sha(index))
    assert current.db.execute('SELECT COUNT(*) FROM direction_reuse').fetchone()[0] == 0
    gap = current.db.execute("SELECT * FROM unresolved WHERE kind='reference_evidence'").fetchone()
    assert gap is not None
    assert dict(gap) == chain.reference_diagnostic(work, 'backward')
    assert prior.db.execute('SELECT completed FROM queries').fetchone()[0] == 1
    chain.plan_citation_queries(current)
    assert current.db.execute("SELECT COUNT(*) FROM queries WHERE kind='backward'").fetchone()[0] == 1
