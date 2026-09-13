"""Manual browser acceptance checks for a running static observatory preview.

Run with Playwright installed and Chromium available. This is deliberately not
collected by the Python unit suite: browser installation is a developer tool.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check_site(url, output):
    """Exercise data navigation, filtering, downloads and mobile layout."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []
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
        for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
            page.goto(url + '/#country/' + code)
            page.wait_for_selector('.markdown h2')
            assert page.locator('.markdown').inner_text().strip()
        page.set_viewport_size({'width': 390, 'height': 844})
        for route in ('overview', 'countries', 'projects', 'comparison', 'methods'):
            page.goto(url + '/#' + route)
            page.wait_for_timeout(150)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
        assert not errors, errors
        browser.close()
        print(f'Browser checks passed; {count} historical records; screenshot: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--screenshot', type=Path, default=Path('/tmp/jetp-overview.png'))
    args = parser.parse_args()
    check_site(args.url.rstrip('/'), args.screenshot)
