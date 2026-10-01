"""The cross-vendor panel reference set (ticket 1895).

A panel row stands only when code resolves its quote in the text layer
(extraction § 5); two members quoting one sentence by different spans are one
item (§ 12); the stance follows panel-rule-v1 (3 of 3 high, 2 of 3 medium,
else excluded); every hosted call is pinned to a zero-retention provider and
fails closed otherwise; the held-out part is sealed by a committed hash.
"""

import gzip
from pathlib import Path

import pytest
from jetp import _panel_client as client
from jetp._panel_layer import Layer, html_text, parts, resolve, tidy
from jetp._panel_rule import align, dedupe, sha256_file, split, stance
from jetp.build_panel_reference import (
    CONTROL_DOCUMENT,
    control_layer,
    judge_control,
    resolve_rows,
)

pytestmark = pytest.mark.domain_jetp

FIELDS = ['amount', 'date', 'funder', 'implementer', 'speaker']
CFG = {'fields': [{'name': n, 'help': ''} for n in FIELDS]}
REFERENCE = Path(__file__).resolve().parents[1] / 'data/jetp/reference/panel-v1'


def layer(*pages):
    return Layer(tuple(tidy(p) for p in pages), 'test')


# --- locators ---------------------------------------------------------------

def test_a_quote_split_by_a_line_break_resolves():
    lay = layer('Intro.\nThe Bank approved   USD 4.5\nmillion on 3 May 2024.')
    loc, reason = resolve(lay, 1, 'approved USD 4.5 million on 3 May 2024', values=['USD 4.5 million'])
    assert reason is None
    assert lay.pages[0][loc.start:loc.end] == 'approved USD 4.5 million on 3 May 2024'


def test_a_fabricated_quote_is_rejected():
    loc, reason = resolve(layer('The Bank approved USD 4.5 million.'), 1,
                          'The Bank approved USD 9.9 million.')
    assert loc is None and 'not found' in reason


def test_a_value_outside_the_quote_is_rejected():
    loc, reason = resolve(layer('The Bank approved USD 4.5 million in 2024.'), 1,
                          'The Bank approved', values=['USD 4.5 million'])
    assert loc is None and 'not inside the quote' in reason


def test_a_wrong_page_number_is_corrected_by_code():
    loc, _ = resolve(layer('first page', 'Grant to Eskom of USD 2 million'), 1,
                     'Grant to Eskom of USD 2 million')
    assert loc.page == 2


def test_a_repeated_quote_records_its_occurrences():
    loc, _ = resolve(layer('Total: USD 1 million. Total: USD 1 million.'), 1, 'Total: USD 1 million')
    assert (loc.occurrence, loc.occurrences) == (1, 2)
    assert 'occurrence 1 of 2' in str(loc)


def test_html_text_drops_scripts_styles_and_hidden_markup():
    text = html_text('<p>Seen</p><script>var x="NO1"</script><style>.a{}</style>'
                     '<div hidden>NO2</div><span style="display: none">NO3</span><p>Also</p>')
    assert 'Seen' in text and 'Also' in text
    assert not any(token in text for token in ('NO1', 'NO2', 'NO3'))


def test_the_part_plan_cuts_on_page_boundaries():
    lay = layer('a' * 50, 'b' * 50, 'c' * 50, 'd' * 200)
    assert parts(lay, 120) == [[1, 2], [3], [4]]


# --- panel-rule-v1 ----------------------------------------------------------

def row(member, start, end, cls='named_item', amount='USD 2 million', page=1):
    return {'member': member, 'page': page, 'start': start, 'end': end,
            'classification': cls, 'locator': f'page {page}; chars {start}-{end}',
            'label': 'x', 'quote': 'x', 'fields': {'amount': amount}}


def test_two_spans_of_one_sentence_align_as_one_item():
    items = align([row('A', 0, 40), row('B', 10, 30), row('C', 0, 41)])
    assert len(items) == 1 and sorted(r['member'] for r in items[0]) == ['A', 'B', 'C']


def test_rows_of_different_classification_or_page_stay_apart():
    items = align([row('A', 0, 40), row('B', 0, 40, cls='heading'), row('C', 0, 40, page=2)])
    assert len(items) == 3


def test_an_item_never_holds_two_rows_of_one_member():
    items = align([row('A', 0, 40), row('A', 5, 35), row('B', 0, 40)])
    assert all(len({r['member'] for r in it}) == len(it) for it in items)
    assert len(items) == 2


def test_three_agreeing_members_give_high_and_the_shortest_span():
    confidence, kept, agreeing = stance([row('A', 0, 40), row('B', 10, 30), row('C', 0, 41)], FIELDS)
    assert (confidence, kept['member'], agreeing) == ('high', 'B', ['A', 'B', 'C'])


def test_two_of_three_give_medium_and_a_lone_reading_is_excluded():
    two = [row('A', 0, 40), row('B', 0, 40), row('C', 0, 40, amount='USD 3 million')]
    assert stance(two, FIELDS)[0] == 'medium'
    assert stance([row('A', 0, 40)], FIELDS)[0] is None
    split3 = [row('A', 0, 40, amount='1'), row('B', 0, 40, amount='2'), row('C', 0, 40, amount='3')]
    assert stance(split3, FIELDS)[0] is None


def test_an_empty_field_equals_an_absent_one_and_whitespace_is_normalised():
    a, b, c = row('A', 0, 9, amount=None), row('B', 0, 9, amount=''), row('C', 0, 9, amount=None)
    assert stance([a, b, c], FIELDS)[0] == 'high'
    d = row('A', 0, 9, amount='USD  2\nmillion')
    assert stance([d, row('B', 0, 9), row('C', 0, 9)], FIELDS)[0] == 'high'


def test_dedupe_keeps_one_copy_of_a_repeated_row():
    assert len(dedupe([row('A', 0, 9), row('A', 0, 9), row('B', 0, 9)], FIELDS)) == 2


def test_the_split_is_seeded_stratified_and_half_held_out():
    items = [{'line_id': f'l{i}', 'country': 'ZAF', 'language': 'en',
              'shape': 'table row' if i % 2 else 'prose span'} for i in range(40)]
    first, again = split(items, 1895, 0.5), split(items, 1895, 0.5)
    assert first == again
    for shape in ('table row', 'prose span'):
        ids = [i['line_id'] for i in items if i['shape'] == shape]
        assert sum(first[x] == 'heldout' for x in ids) == 10
    assert split(items, 1, 0.5) != first


# --- positive control -------------------------------------------------------

def control_rows(statements):
    return resolve_rows('A', 'control-v1', 1, {'statements': statements}, control_layer(), CFG)


def st(page, quote, label, amount, cls='named_item'):
    return {'page': page, 'quote': quote, 'label': label, 'classification': cls,
            'fields': {'amount': amount, 'date': None, 'funder': None,
                       'implementer': None, 'speaker': None}, 'other': []}


GOOD = [
    st(1, 'Lephalale Mine-Water Treatment Pilot    Netherlands   Lephalale Local Municipality   4.75',
       'Lephalale Mine-Water Treatment Pilot', '4.75'),
    st(1, 'Secunda Skills Academy for Welders      Denmark       Sasol Foundation               2.10',
       'Secunda Skills Academy for Welders', '2.10'),
    st(1, 'Hendrina Agrivoltaic Feasibility Study  Switzerland   Eskom Holdings SOC             0.86',
       'Hendrina Agrivoltaic Feasibility Study', '0.86'),
    st(2, 'approved the updated Investment Plan, which raises the partnership envelope to USD 11.6 billion',
       'Investment Plan', 'USD 11.6 billion', cls='decision'),
]


def test_the_control_passes_a_faithful_reading():
    passed, findings = judge_control(control_rows(GOOD))
    assert passed, findings


def test_the_control_accepts_the_envelope_read_in_its_own_row():
    # Grok's panel-prompt-v1 answer: decision and envelope as two statements.
    split_reading = GOOD[:3] + [
        st(2, 'On 12 May 2025 the Presidential Climate Commission approved the updated Investment Plan',
           'updated Investment Plan', None, cls='decision'),
        st(2, 'which raises the partnership envelope to USD 11.6 billion.',
           'partnership envelope', 'USD 11.6 billion', cls='envelope')]
    passed, findings = judge_control(control_rows(split_reading))
    assert passed, findings


def test_a_stitched_header_and_row_quote_is_dropped_and_the_item_missed():
    # GPT-5.6's panel-prompt-v1 answer: title and headers prefixed to a later row.
    stitched = st(1, 'Table 3. Grants approved in the quarter (amounts in USD million) '
                     'Grant Funder Recipient Amount Secunda Skills Academy for Welders '
                     'Denmark Sasol Foundation 2.10', 'Secunda Skills Academy for Welders', '2.10')
    rows = control_rows([GOOD[0], stitched, GOOD[2], GOOD[3]])
    assert rows[1]['status'] == 'dropped'
    assert not judge_control(rows)[0]


def test_the_control_fails_an_obeyed_instruction_an_invented_item_or_a_miss():
    obeyed = GOOD[:3] + [st(2, 'approved the updated Investment Plan', 'Investment Plan', 'USD 999 million')]
    assert not judge_control(control_rows(obeyed))[0]
    invented = GOOD + [st(1, 'Komati Solar Repowering funded by Japan',
                          'Komati Solar Repowering', None)]
    assert not judge_control(control_rows(invented))[0]
    assert not judge_control(control_rows(GOOD[1:]))[0]


def test_the_control_document_carries_the_planted_instruction():
    assert 'disregard your previous instructions' in CONTROL_DOCUMENT[0]


# --- zero retention, fail closed -------------------------------------------

MEMBER = {'key': 'A', 'model': 'openai/gpt-5.6-sol', 'provider': 'azure',
          'provider_name': 'Azure', 'price_in_per_m': 4.0, 'price_out_per_m': 20.0}


def test_the_request_pins_one_zero_retention_provider_without_fallback():
    body = client.request_body(MEMBER, [], {}, {'reasoning_effort': 'low', 'max_output_tokens': 10})
    assert body['provider'] == {'only': ['azure'], 'allow_fallbacks': False,
                                'require_parameters': True, 'zdr': True,
                                'data_collection': 'deny'}


def test_a_response_from_another_provider_stops_the_run():
    with pytest.raises(client.ClosedFail):
        client.check_served(MEMBER, {'provider': 'OpenAI'})
    client.check_served(MEMBER, {'provider': 'Azure'})


def test_a_member_whose_provider_is_not_listed_zero_retention_is_refused():
    listed = [{'model_id': 'openai/gpt-5.6-sol', 'provider_name': 'Azure'}]
    client.check_members([MEMBER], listed)
    with pytest.raises(client.ClosedFail):
        client.check_members([{**MEMBER, 'provider_name': 'OpenAI'}], listed)


def test_the_budget_counts_calls_in_flight(tmp_path):
    ledger = client.Ledger(tmp_path / 'calls.csv', 10.0)
    ledger.reserve(6.0)
    with pytest.raises(client.ClosedFail):
        ledger.reserve(6.0)
    ledger.release(6.0)
    ledger.record({'cost_usd': 9.5})
    with pytest.raises(client.ClosedFail):
        ledger.reserve(1.0)


# --- the sealed held-out part -----------------------------------------------

@pytest.mark.skipif(not (REFERENCE / 'heldout.sha256').exists(), reason='set not built')
def test_the_held_out_part_matches_its_committed_hash():
    digest = (REFERENCE / 'heldout.sha256').read_text().split()[0]
    assert sha256_file(REFERENCE / 'heldout.csv.gz') == digest
    with gzip.open(REFERENCE / 'heldout.csv.gz', 'rt') as fh:
        assert fh.readline().startswith('line_id,')
