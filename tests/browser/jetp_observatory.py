"""Manual browser acceptance checks for a running static observatory preview.

Run with Playwright installed and Chromium available. This is deliberately not
collected by the Python unit suite: browser installation is a developer tool.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def download_matches(page, url, href):
    """Assert that a browser download is the byte-identical served artifact."""
    with page.expect_download() as download:
        page.locator(f'a[download][href="{href}"]').click()
    assert Path(download.value.path()).read_bytes() == page.request.get(
        url + '/' + href
    ).body()


def check_documents(page, url):
    """Exercise the registry page: full count, a filter, and an archived copy."""
    registry = page.request.get(url + '/data/documents.json').json()['documents']
    page.goto(url + '/#documents')
    page.wait_for_selector('#documents-filters')
    assert str(len(registry)) in page.locator('#documents-count').inner_text()
    page.locator('#documents-filter-country').select_option('SEN')
    page.locator('#documents-filter-status').select_option('blocked')
    blocked = [row for row in registry
               if row['country'] == 'SEN' and row['status'] == 'blocked']
    assert page.locator('#documents-results tbody tr').count() == len(blocked)
    # The archived ZAF register must open from this page, byte-identical to the
    # snapshot the registry pins. A missing local copy is a provisioning gap
    # (make jetp-observatory-documents), not a renderer defect.
    page.locator('#documents-filter-status').select_option('')
    page.locator('#documents-filter-country').select_option('ZAF')
    entry = next(row for row in registry
                 if row['id'] == 'zaf-jet-investment-register-q1-2026')
    link = page.locator('a[data-document-id="zaf-jet-investment-register-q1-2026"]')
    assert entry['local_path'], 'Archived ZAF register absent; run make jetp-observatory-documents'
    with page.expect_popup() as popup:
        link.click()
    opened = popup.value
    opened.wait_for_load_state()
    assert opened.url.endswith(entry['local_path'])
    assert hashlib.sha256(
        page.request.get(url + '/' + entry['local_path']).body()
    ).hexdigest() == entry['sha256']
    opened.close()


def check_inventory(page, url):
    """Exercise an M1a inventory page: a filter, and a row opening its document.

    The two recipes of ticket 0834: Viet Nam annex I.1 holds 37 rows, and its
    ordinal 22 opens the RMP at PDF page 156 — not the printed page 140, not the
    ordinal. South Africa's completed rows are 88 of 257.
    """
    registry = page.request.get(url + '/data/documents.json').json()['documents']
    payload = page.request.get(url + '/data/m1a/VNM.json').json()
    rows = [dict(zip(payload['fields'], values)) for values in payload['rows']]
    page.goto(url + '/#inventory/VNM')
    page.wait_for_selector('#inventory-filters')
    assert str(len(rows)) in page.locator('#inventory-count').inner_text()
    page.locator('#inventory-search').fill('Annex I.1')
    annex = [row for row in rows if 'Annex I.1' in row['evidence_locator']]
    assert len(annex) == 37, len(annex)
    assert page.locator('#inventory-results tbody tr').count() == len(annex)

    page.locator('#inventory-search').fill('Tri An')
    link = page.locator('a[data-inventory-row="vnm-rmp-2023:annex-I.1:022"]')
    link.wait_for()
    entry = next(row for row in registry
                 if row['id'] == 'vnm-rmp-2023' and row['local_path'])
    assert entry['local_path'], 'Archived RMP absent; run make jetp-observatory-documents'
    # The address the row resolves to, then the fact that it really opens. The
    # target is a 30 MB PDF handed to the browser's own viewer, which reports
    # neither a load state nor a URL back to the driver, so the assertion is on
    # the href and the popup is only checked to exist.
    assert link.get_attribute('href') == entry['local_path'] + '#page=156', \
        link.get_attribute('href')
    with page.expect_popup() as popup:
        link.click()
    assert popup.value is not None
    popup.value.close()

    # A per-country column set must not need a renderer change: the 21 ZAF
    # pass-through columns appear in the row detail, in the export's own order.
    page.goto(url + '/#inventory/ZAF')
    page.wait_for_selector('#inventory-filters')
    page.locator('#inventory-filter-reported_status').select_option('D. Completed')
    assert '88 of 257' in page.locator('#inventory-count').inner_text()
    detail = page.locator('#inventory-results tbody tr details').first
    detail.locator('summary').click()
    keys = detail.locator('dt').all_inner_texts()
    assert keys[:2] == ['country', 'source_layer'], keys[:2]
    assert 'raw_project_name' in keys
    # Unknowns are shown per sub-layer, never pooled: one metric per sub-layer,
    # each naming the sub-layer it counts.
    manifest = page.request.get(url + '/data/m1a/manifest.json').json()
    sublayers = manifest['countries']['ZAF']['sublayers']
    unknowns = page.locator('.metrics .metric')
    assert unknowns.count() == len(sublayers)
    assert sublayers[0]['sublayer_id'] in unknowns.first.inner_text()


def check_site(url, output):
    """Exercise data navigation, filtering, downloads and mobile layout."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []
        external_requests = []

        def local_only(route):
            if urlsplit(route.request.url).netloc == urlsplit(url).netloc:
                route.continue_()
            else:
                external_requests.append(route.request.url)
                route.abort()

        page.route('**/*', local_only)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url)
        page.wait_for_selector('.country-grid')
        assert page.locator('.country-card').count() == 4
        with page.expect_response('**/data/comparison.json') as response:
            page.reload()
        count = len(response.value.json()['projects'])
        page.wait_for_selector('.country-grid')
        page.screenshot(path=str(output), full_page=True)
        page.goto(url + '/#projects')
        page.wait_for_selector('#search')
        page.locator('#search').fill('Bac Ai')
        assert page.locator('#results tbody tr').count() == 1
        page.locator('#results tbody tr a').click()
        page.wait_for_selector('.project-layout')
        assert page.locator('.sources a').count() > 0
        page.goto(url + '/#project/sen-project-qw-02')
        link = page.locator('[data-link-id="round4-boad-linguere"]')
        link.wait_for()
        assert 'possible match' in link.inner_text()
        assert 'provisional' in link.inner_text()
        assert 'JETP' in link.inner_text()
        page.goto(url + '/#project/sen-project-qw-04')
        report = page.locator('[data-event-id="sen-puelec-three-villages-reported-20251109"]')
        report.wait_for()
        assert 'Event date not established' in report.inner_text()
        assert 'Source published' in report.inner_text()
        page.goto(url + '/#comparison')
        page.wait_for_selector('#history-country')
        assert page.locator('#history-table tbody tr').count() == count
        page.locator('#history-country').select_option('IDN')
        assert 0 < page.locator('#history-table tbody tr').count() < count
        page.locator('#history-instrument').select_option('Investment Project Financing')
        assert page.locator('#history-table tbody tr').count() > 0
        page.locator('#history-search').fill('no-such-operation-12345')
        assert page.locator('#history-table .empty').count() == 1
        page.goto(url + '/#methods')
        page.wait_for_selector('.downloads')
        with page.expect_download() as download:
            page.locator('a[download][href="data/comparison.json"]').click()
        downloaded = json.loads(Path(download.value.path()).read_text())
        assert len(downloaded['projects']) == count
        for view in ('overview', 'comparison', 'documents', 'ZAF', 'IDN', 'VNM', 'SEN'):
            download_matches(page, url, f'data/{view}.json')
        for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
            download_matches(page, url, f'data/m1a/{code}.csv')
        download_matches(page, url, 'data/m1a/manifest.json')
        check_documents(page, url)
        check_inventory(page, url)
        for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
            page.goto(url + '/#country/' + code)
            page.wait_for_selector('.markdown h2')
            assert page.locator('.markdown').inner_text().strip()
        # Hash routes must remain usable with a keyboard and expose the current
        # location to assistive technology.
        page.goto(url + '/#country/IDN')
        page.wait_for_selector('.page-head h1')
        active = page.locator('nav a[aria-current="page"]')
        assert active.count() == 1
        assert active.get_attribute('href') == '#countries'
        page.locator('.skip').focus()
        page.keyboard.press('Enter')
        assert page.evaluate('document.activeElement.id') == 'main'
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.tagName') == 'A'
        page.set_viewport_size({'width': 390, 'height': 844})
        for route in ('overview', 'countries', 'documents', 'projects', 'comparison',
                      'inventory/SEN', 'methods'):
            page.goto(url + '/#' + route)
            page.wait_for_timeout(150)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
        assert not errors, errors
        assert not external_requests, external_requests
        browser.close()
        print(f'Browser checks passed; {count} historical records; screenshot: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--screenshot', type=Path, default=Path('/tmp/jetp-overview.png'))
    args = parser.parse_args()
    check_site(args.url.rstrip('/'), args.screenshot)
