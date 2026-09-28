"""Freeze the IATI Datastore Classic energy query as compact country snapshots.

The API returns complete XML-to-JSON activities, often with large location and
description arrays.  Retain only the source fields used by the comparator ledger;
record each response URL, SHA-256, and reported total for an auditable pull.
"""

import argparse
import gzip
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = 'https://datastore.codeforiati.org/api/1/access/activity.json'
SECTORS = ('230', '231', '232', '233', '236', '23110', '23183', '23210',
           '23220', '23230', '23240', '23250', '23260', '23270', '23310',
           '23320', '23340', '23410', '23510')
ENERGY_CODES = frozenset(SECTORS)
COUNTRIES = ('ID', 'SN', 'VN', 'ZA')
PAGE_SIZE = 100


def _items(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _narrative(value):
    if isinstance(value, str):
        return ' '.join(value.split())
    if isinstance(value, list):
        return next((title for item in value if (title := _narrative(item))), '')
    if not isinstance(value, dict):
        return ''
    return _narrative(value.get('narrative')) or _narrative(value.get('text'))


def _code(value):
    code = value.get('code') if isinstance(value, dict) else value
    return code.strip() if isinstance(code, str) else code


def _codes(value):
    return {code for item in _items(value) if (code := _code(item))}


def _dac_codes(value):
    codes = set()
    for sector in _items(value):
        if not isinstance(sector, dict):
            continue
        code = sector.get('code')
        # IATI defaults an omitted vocabulary to DAC 5-digit purpose codes.
        vocabulary = str(sector.get('vocabulary') or '1')
        if isinstance(code, str) and ((vocabulary == '1' and len(code) == 5) or
                                      (vocabulary == '2' and len(code) == 3)):
            codes.add(code)
    return codes


def project(activity, country):
    """Small, typed copy of source facts; transaction order stays source order."""
    identifier = activity.get('iati-identifier')
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError('IATI activity without identifier')
    transactions = []
    unallocated_country = 0
    unallocated_sector = 0
    all_transactions = _items(activity.get('transaction'))
    activity_countries = _codes(activity.get('recipient-country'))
    activity_sectors = _dac_codes(activity.get('sector'))
    matched = country in activity_countries and bool(activity_sectors & ENERGY_CODES)
    for transaction in all_transactions:
        transaction_countries = _codes(transaction.get('recipient-country'))
        transaction_sectors = _dac_codes(transaction.get('sector'))
        recipients = (transaction_countries if _items(transaction.get('recipient-country'))
                      else activity_countries)
        if country not in recipients:
            continue
        sectors = (transaction_sectors if _items(transaction.get('sector'))
                   else activity_sectors)
        if not sectors & ENERGY_CODES:
            continue
        matched = True
        if len(recipients) != 1:
            unallocated_country += 1
            continue
        if sectors - ENERGY_CODES:
            unallocated_sector += 1
            continue
        amount = transaction.get('value') or {}
        transactions.append({
            'code': _code(transaction.get('transaction-type')),
            'value': amount.get('text'),
            'currency': amount.get('currency') or activity.get('default-currency'),
            'date': (transaction.get('transaction-date') or {}).get('iso-date'),
        })
    if not matched:
        return None
    return {
        'id': identifier.strip(),
        'title': _narrative(activity.get('title')),
        'status': _code(activity.get('activity-status')),
        'reporting_org': (activity.get('reporting-org') or {}).get('ref'),
        'sectors': [{'code': x.get('code'), 'vocabulary': x.get('vocabulary')}
                    for x in _items(activity.get('sector'))],
        'other_identifiers': [{'ref': x.get('ref'),
                               'owner': (x.get('owner-org') or {}).get('ref')}
                              for x in _items(activity.get('other-identifier'))],
        'source_transaction_count': len(all_transactions),
        'unallocated_country_count': unallocated_country,
        'unallocated_sector_count': unallocated_sector,
        'transactions': transactions,
    }


def collect(country, output):
    records = {}
    seen = set()
    queries = []
    sector_filter = '|'.join(SECTORS)
    offset = 0
    while True:
        url = BASE + '?' + urlencode({'recipient-country': country,
                                      'sector': sector_filter, 'offset': offset,
                                      'limit': PAGE_SIZE})
        with urlopen(Request(url, headers={'User-Agent': 'climate-finance-het/0886'}),
                     timeout=120) as response:
            raw = response.read()
        payload = json.loads(raw)
        if payload.get('ok') is not True:
            raise ValueError(f'IATI API error at {url}')
        entries = payload.get('iati-activities', [])
        total = int(payload['total-count'])
        if queries and total != queries[0]['total']:
            raise ValueError(f'IATI page total changed during pull: {country}')
        queries.append({'url': url, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'total': total, 'returned': len(entries)})
        for entry in entries:
            activity = entry.get('iati-activity', entry)
            identifier = activity.get('iati-identifier')
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError(f'missing API page identifier at {url}')
            identifier = identifier.strip()
            if identifier in seen:
                raise ValueError(f'duplicate API page identifier: {identifier}')
            seen.add(identifier)
            record = project(activity, country)
            if record is None:
                continue
            records[record['id']] = record
        offset += len(entries)
        if offset >= total:
            break
        if not entries:
            raise ValueError(f'incomplete pagination at {url}')
    if len(seen) != total:
        raise ValueError(f'{country}: {len(seen)} unique IDs, API reported {total}')
    snapshot = {'source': BASE, 'country_code': country,
                'retrieved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'queries': queries, 'source_total': total, 'count': len(records),
                'records': sorted(records.values(), key=lambda row: row['id'])}
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    output.write_bytes(gzip.compress(payload, mtime=0))
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--country', choices=COUNTRIES, nargs='+', default=COUNTRIES)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    for country in args.country:
        count = collect(country, args.output_dir / f'{country}.json.gz')
        logging.info('%s: %s IATI energy activities', country, count)


if __name__ == '__main__':
    main()
