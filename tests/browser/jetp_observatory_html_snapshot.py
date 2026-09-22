"""Snapshot the HTML the catalogue and comparison pages render, to compare two
builds of app.js byte for byte (ticket 0852).

Run against a served preview, twice — once per build — then compare:

    uv run --no-sync python tests/browser/jetp_observatory_html_snapshot.py \
        capture --url http://127.0.0.1:8765 --output /tmp/before
    uv run --no-sync python tests/browser/jetp_observatory_html_snapshot.py \
        compare /tmp/before /tmp/after

Each filter state writes one file holding `#main`'s innerHTML after the
renderer has reacted, so a refactor that must not change the page is proved
by an empty diff, not by a green recipe. Like jetp_observatory.py, this is a
developer tool, not collected by the unit suite.
"""

import argparse
import difflib
from pathlib import Path

from playwright.sync_api import sync_playwright

# (name, hash route, [(selector, action, value)]): the states each page is
# rendered in. A select carries the same value in both builds only if the
# option exists, so the values below are ones the committed data holds.
STATES = [
    ('catalogue-all', 'projects', []),
    ('catalogue-preselected-IDN', 'projects?country=IDN', []),
    ('catalogue-search', 'projects', [('#search', 'fill', 'Bac Ai')]),
    ('catalogue-facets', 'projects', [
        ('#country-filter', 'select', 'ZAF'),
        ('#stage-filter', 'select', 'Registered financing'),
    ]),
    ('catalogue-funder', 'projects', [('#funder-filter', 'select', 'Germany')]),
    ('catalogue-technology', 'projects', [('#technology-filter', 'select', 'Electricity')]),
    ('catalogue-empty', 'projects', [('#search', 'fill', 'no-such-project-12345')]),
    ('comparison-all', 'comparison', []),
    ('comparison-preselected-ZAF', 'comparison?country=ZAF', []),
    ('comparison-search', 'comparison', [('#history-search', 'fill', 'transmission')]),
    ('comparison-instrument', 'comparison', [
        ('#history-country', 'select', 'IDN'),
        ('#history-instrument', 'select', 'Investment Project Financing'),
    ]),
    ('comparison-vintage-additional', 'comparison', [
        ('#history-vintage', 'select', '2010'),
        ('#history-additional', 'select', 'exclude'),
    ]),
    ('comparison-empty', 'comparison', [
        ('#history-search', 'fill', 'no-such-operation-12345'),
    ]),
]


def apply(page, selector, action, value):
    if action == 'fill':
        page.locator(selector).fill(value)
    else:
        page.locator(selector).select_option(value)


def capture(url, output):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        for name, route, actions in STATES:
            # A hash change alone re-renders in place; a full load per state
            # keeps each snapshot independent of the previous one's selects.
            page.goto('about:blank')
            page.goto(url + '/#' + route)
            page.wait_for_selector('#results, #history-table')
            for selector, action, value in actions:
                apply(page, selector, action, value)
            html = page.evaluate('document.getElementById("main").innerHTML')
            (output / f'{name}.html').write_text(html)
            print(f'{name}: {len(html)} bytes')
        browser.close()
        assert not errors, errors


def compare(before, after):
    names = sorted({p.name for p in before.glob('*.html')} | {p.name for p in after.glob('*.html')})
    differing = 0
    for name in names:
        a, b = before / name, after / name
        if not a.exists() or not b.exists():
            print(f'{name}: only in {"before" if a.exists() else "after"}')
            differing += 1
            continue
        if a.read_bytes() == b.read_bytes():
            print(f'{name}: identical ({a.stat().st_size} bytes)')
            continue
        differing += 1
        print(f'{name}: DIFFERENT')
        for line in difflib.unified_diff(
            a.read_text().splitlines(), b.read_text().splitlines(),
            str(a), str(b), lineterm='', n=0,
        ):
            print('    ' + line[:300])
    print(f'{len(names) - differing} identical, {differing} differing, of {len(names)} states')
    return differing == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    cap = sub.add_parser('capture')
    cap.add_argument('--url', default='http://127.0.0.1:8765')
    cap.add_argument('--output', type=Path, required=True)
    cmp = sub.add_parser('compare')
    cmp.add_argument('before', type=Path)
    cmp.add_argument('after', type=Path)
    args = parser.parse_args()
    if args.command == 'capture':
        capture(args.url.rstrip('/'), args.output)
    else:
        raise SystemExit(0 if compare(args.before, args.after) else 1)
