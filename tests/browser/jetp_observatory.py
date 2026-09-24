"""Manual browser acceptance checks for a running static observatory preview.

Run with Playwright installed and Chromium available. This is deliberately not
collected by the Python unit suite: browser installation is a developer tool.

The same checks run on the local preview and on the public bundle (ticket
0915). Every document link to the publisher's page is checked on both; the
archived-copy checks follow ``documents/index.json``: where the server serves
it, each listed copy must be linked and open, and where it does not, no page
may link into ``documents/``.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def download_matches(page, url, href):
    """Assert that a browser download is the byte-identical served artifact."""
    # Headless Chromium honours at most ten `<a download>` clicks per loaded
    # document: the eleventh never leaves the browser (the server logs no
    # request) and Playwright's download event never fires, which is where
    # the full recipe stalled — on data/m1a/VNM.csv, its eleventh download.
    # The local-only route handler and the automatic-downloads content
    # setting were each varied without effect; a document navigation resets
    # the count, so every download here starts from a freshly loaded page.
    page.reload()
    page.wait_for_selector('.downloads')
    with page.expect_download() as download:
        page.locator(f'a[download][href="{href}"]').click()
    assert Path(download.value.path()).read_bytes() == page.request.get(
        url + '/' + href
    ).body()


COUNTRIES = ('ZAF', 'IDN', 'VNM', 'SEN')


def staged_copies(page, url):
    """The archived copies this server says it holds; empty on the public site."""
    response = page.request.get(url + '/documents/index.json')
    return set(response.json()['objects']) if response.ok else set()


def publisher(selector):
    return selector + '[data-link="publisher"]'


def archived(selector):
    return selector + '[data-link="archived"]'


def check_archived(page, url, locator, entry, staged, suffix='', exact=True, opens=True):
    """The archived link of one document: present, right and opening where the
    copy is served; absent everywhere else."""
    if entry['local_path'] not in staged:
        assert locator.count() == 0, locator
        return
    href = locator.get_attribute('href')
    if exact:
        assert href == entry['local_path'] + suffix, href
    else:
        assert href.startswith(entry['local_path']), href
    if opens:
        with page.expect_popup() as popup:
            locator.click()
        assert popup.value is not None
        popup.value.close()


def served_tables(page, url):
    """The tables the Documents page joins at read time (ticket 0858)."""
    m1a = {}
    for code in COUNTRIES:
        payload = page.request.get(url + f'/data/m1a/{code}.json').json()
        m1a[code] = [dict(zip(payload['fields'], values)) for values in payload['rows']]
    return {
        'm1a': m1a,
        'observations': {code: page.request.get(url + f'/data/observations/{code}.json').json()
                         for code in COUNTRIES},
        'projects': [p for code in COUNTRIES
                     for p in page.request.get(url + f'/data/{code}.json').json()['projects']],
        'reviewed': page.request.get(url + '/data/reviewed-evidence.json').json()['records'],
    }


def climb(tables, source_id, code):
    """What one Documents row must show, from the served tables: the two
    stage-two products of the attempt's country filtered on source_id, and
    the facts whose sources or proofs name it — three lists, never a total."""
    return {
        'm1a': [r for r in tables['m1a'][code] if r['source_id'] == source_id],
        'ledger': [r for r in tables['observations'][code] if r['source_id'] == source_id],
        'facts': [p for p in tables['projects'] if source_id in p['sources']]
        + [r for r in tables['reviewed']
           if any(e['source_id'] == source_id for e in r['evidence'])],
    }


def check_documents(page, url, staged):
    """Exercise the registry page: full count, a filter, and each document's links."""
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
    # The filter carries the code as value and the name as label (ticket 0853).
    assert page.locator(
        '#documents-filter-country option[value="ZAF"]'
    ).inner_text() == 'South Africa'
    entry = next(row for row in registry
                 if row['id'] == 'zaf-jet-investment-register-q1-2026')
    # Addressed by the row key, not the source id: 21 identifiers carry more
    # than one collection attempt, so the id alone is not a selector. The
    # publisher's page is always linked; the register is an HTML page, so it
    # takes no page fragment.
    link = page.locator(publisher(f'a[data-document-id="{entry["row_key"]}"]'))
    assert link.get_attribute('href') == entry['url'], link.get_attribute('href')
    assert entry['local_path'], 'The registry names no archived copy of the ZAF register'
    # Ticket 0856: the register was read twice, once per stage-two product,
    # and the two readings are shown as two counts, never added (257 + 257
    # is not 514 rows). The counts come from the served views the page joins
    # at read time (ticket 0858), never from an index in the registry view.
    tables = served_tables(page, url)
    linked = climb(tables, entry['id'], entry['country'])
    per_product = {'ledger': len(linked['ledger']), 'm1a': len(linked['m1a'])}
    assert all(per_product.values()), per_product
    row = page.locator('#documents-results tbody tr').filter(has=link).first
    for product, count in per_product.items():
        fold = row.locator(f'details[data-extracted-product="{product}"]')
        # The fold-out lands once the ZAF views have loaded; get_attribute
        # waits for it.
        assert fold.get_attribute('data-extracted-count') == str(count), product
    assert str(sum(per_product.values())) not in ' '.join(
        row.locator('details > summary').all_inner_texts()
    )
    # The fingerprint of the bytes read is on the row, on both sites.
    assert row.locator(f'[data-sha256="{entry["sha256"]}"]').count() == 1
    copy = page.locator(archived(f'a[data-document-id="{entry["row_key"]}"]'))
    if entry['local_path'] in staged:
        with page.expect_popup() as popup:
            copy.click()
        opened = popup.value
        opened.wait_for_load_state()
        assert opened.url.endswith(entry['local_path'])
        assert hashlib.sha256(
            page.request.get(url + '/' + entry['local_path']).body()
        ).hexdigest() == entry['sha256']
        opened.close()
    else:
        assert copy.count() == 0

    # Ticket 0857, recipe VN step 1: from this page the RMP 2023 opens at
    # printed page 139 — PDF page 155, the first page its extracted positions
    # name — and each position links to its own inventory row and, where its
    # locator names one, to its own page: the 22nd (KN Tri An) to page 156.
    page.locator('#documents-filter-country').select_option('')
    page.locator('#documents-search').fill('vnm-rmp-2023')
    rmp = next(row for row in registry if row['id'] == 'vnm-rmp-2023' and row['local_path'])
    link = page.locator(publisher(f'a[data-document-id="{rmp["row_key"]}"]'))
    row = page.locator('#documents-results tbody tr').filter(has=link).first
    fold = row.locator('details[data-extracted-product="m1a"]')
    # The page is set on the links once the VNM views have loaded, just before
    # the fold-outs land (ticket 0858): wait for those, then read the links.
    # The RMP's origin is a PDF, so the publisher's page takes the fragment.
    fold.wait_for()
    assert link.get_attribute('href') == rmp['url'] + '#page=155', link.get_attribute('href')
    check_archived(page, url, page.locator(archived(f'a[data-document-id="{rmp["row_key"]}"]')),
                   rmp, staged, '#page=155')
    fold.locator('summary').click()
    position = fold.locator('li').nth(21)
    assert 'KN Tri An' in position.inner_text(), position.inner_text()
    key = 'a[data-extracted-page="vnm-rmp-2023:annex-I.1:022"]'
    pdf = position.locator(publisher(key))
    assert pdf.get_attribute('href') == rmp['url'] + '#page=156', pdf.get_attribute('href')
    check_archived(page, url, position.locator(archived(key)), rmp, staged, '#page=156')
    # The climb lands on the one row, not on the 279.
    position.locator('a[href="#document-rows/VNM?row=22"]').click()
    page.wait_for_selector('[data-inventory-focus="22"]')
    assert page.locator('#inventory-count').inner_text().startswith('1 of 1 ')
    key = 'a[data-inventory-row="vnm-rmp-2023:annex-I.1:022"]'
    assert page.locator(publisher(key)).get_attribute('href') == rmp['url'] + '#page=156'
    check_archived(page, url, page.locator(archived(key)), rmp, staged, '#page=156', opens=False)
    assert page.locator('#inventory-results details[open]').count() == 1


def check_documents_row_height(page, url):
    """The Documents rows stay short at desktop width (PR #1459, cold read).

    Measured at 1280 px before the fix: the fold-out column was squeezed to
    101 px, wrapped at every word and set every row's height (median 255 px,
    max 276 px). Now a row is at most one line per fold-out, and the links
    cell of ticket 0915 is a fixed block: the publisher's page (two lines at
    this width), the collection date and fingerprint, and the archived copy
    where served — 126 px on the public site, 146 px in the preview. 150 px
    bounds that block and the cell padding, well under the word-by-word wrap
    it guards against. A failed attempt shows a short label with the
    collector's full message in its title, never a broken URL.
    """
    page.set_viewport_size({'width': 1280, 'height': 1000})
    page.goto(url + '/#documents')
    page.wait_for_selector('#documents-results tbody tr')
    page.wait_for_function(
        "!document.querySelector('#documents-results').textContent.includes('Loading what')")
    heights = page.evaluate("[...document.querySelectorAll('#documents-results tbody tr')]"
                            ".map((r) => r.getBoundingClientRect().height)")
    assert max(heights) <= 150, sorted(heights)[-5:]
    registry = page.request.get(url + '/data/documents.json').json()['documents']
    failed = next(row for row in registry
                  if row['error'] and len(row['error']) > 100 and not row['local_path'])
    page.locator('#documents-search').fill(failed['id'])
    label = page.locator(f'tr:has(code:text-is("{failed["id"]}")) [data-collection-error]').first
    label.wait_for()
    assert label.get_attribute('title') == failed['error']
    assert len(label.inner_text()) <= 24, label.inner_text()
    page.set_viewport_size({'width': 1440, 'height': 1100})


def check_inventory(page, url, staged):
    """Exercise an M1a inventory page: a filter, and a row opening its document.

    The two recipes of ticket 0834: Viet Nam annex I.1 holds 37 rows, and its
    ordinal 22 opens the RMP at PDF page 156 — not the printed page 140, not the
    ordinal. South Africa's completed rows are 88 of 257.
    """
    registry = page.request.get(url + '/data/documents.json').json()['documents']
    payload = page.request.get(url + '/data/m1a/VNM.json').json()
    rows = [dict(zip(payload['fields'], values)) for values in payload['rows']]
    page.goto(url + '/#document-rows/VNM')
    page.wait_for_selector('#inventory-filters')
    assert str(len(rows)) in page.locator('#inventory-count').inner_text()
    page.locator('#inventory-search').fill('Annex I.1')
    annex = [row for row in rows if 'Annex I.1' in row['evidence_locator']]
    assert len(annex) == 37, len(annex)
    assert page.locator('#inventory-results tbody tr').count() == len(annex)

    page.locator('#inventory-search').fill('Tri An')
    key = 'a[data-inventory-row="vnm-rmp-2023:annex-I.1:022"]'
    link = page.locator(publisher(key))
    link.wait_for()
    entry = next(row for row in registry
                 if row['id'] == 'vnm-rmp-2023' and row['local_path'])
    # The address the row resolves to, then the fact that it really opens. The
    # target is a 30 MB PDF handed to the browser's own viewer, which reports
    # neither a load state nor a URL back to the driver, so the assertion is on
    # the href and the popup is only checked to exist. The publisher's copy is
    # never opened: the recipe makes no request off this server.
    assert link.get_attribute('href') == entry['url'] + '#page=156', \
        link.get_attribute('href')
    check_archived(page, url, page.locator(archived(key)), entry, staged, '#page=156')

    # A per-country column set must not need a renderer change: the 21 ZAF
    # pass-through columns appear in the row detail, in the export's own order.
    page.goto(url + '/#document-rows/ZAF')
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
    # Scoped to the inventory panel: the ledger observations tab of the same
    # page carries its own per-table metrics, in the DOM though hidden.
    unknowns = page.locator('#panel-inventory .metrics .metric')
    assert unknowns.count() == len(sublayers)
    assert sublayers[0]['sublayer_id'] in unknowns.first.inner_text()


def check_senegal_and_indonesia(page, url, staged):
    """Walk the two countries the recipe had never reached (ticket 0861).

    Senegal: row 1 of Annex 2 opens the archived annexes at PDF page 13 — on
    that file printed page N is PDF page N, measured at ticket 0861. Indonesia:
    the project the 2025 progress report is cited for most often descends to
    its ledger rows, and a row read from that report opens its archived copy.
    """
    registry = page.request.get(url + '/data/documents.json').json()['documents']

    annexes = next(row for row in registry
                   if row['id'] == 'sen-investment-plan-annexes-mirror' and row['local_path'])
    page.goto(url + '/#document-rows/SEN?row=1')
    page.wait_for_selector('[data-inventory-focus="1"]')
    key = 'a[data-inventory-row="sen-annex-received-01"]'
    link = page.locator(publisher(key))
    assert link.get_attribute('href') == annexes['url'] + '#page=13', \
        link.get_attribute('href')
    check_archived(page, url, page.locator(archived(key)), annexes, staged, '#page=13')

    report_id = 'idn-jetp-progress-report-2025'
    report = next(row for row in registry if row['id'] == report_id and row['local_path'])
    ledger = page.request.get(url + '/data/observations/IDN.json').json()
    cited = [row for row in ledger if row['source_id'] == report_id]
    counts = Counter(row['project_id'] for row in cited)
    project_id = max(sorted(counts), key=counts.__getitem__)  # ties: smallest id
    served = [row for row in ledger if row['project_id'] == project_id]
    from_report = next(row for row in served if row['source_id'] == report_id)
    row_id = (from_report.get('event_id') or from_report.get('implementation_event_id')
              or from_report['link_id'])

    page.goto(url + '/#project/' + project_id)
    page.wait_for_selector('#project-evidence details[data-evidence-count]')
    fold = page.locator('#project-evidence details[data-evidence-count]')
    assert fold.get_attribute('data-evidence-count') == str(len(served))
    fold.locator('> summary').click()
    assert page.locator('#project-evidence tbody tr').count() == len(served)
    key = f'#project-evidence a[data-observation-id="{row_id}"]'
    link = page.locator(publisher(key))
    link.wait_for()
    # A download link, not a PDF page: the origin takes no fragment.
    assert link.get_attribute('href') == report['url'], link.get_attribute('href')
    check_archived(page, url, page.locator(archived(key)), report, staged, exact=False)


def check_observations(page, url, staged):
    """Exercise the ledger observations tab: the counts, a facet, and a search.

    Recipe VN of ticket 0834, adjusted to what the ledger holds: Viet Nam's
    only rows are seven project-source links, and none of the three tables
    carries a funder column for them, so the European Investment Bank package
    is reached by the free-text field and not by the funder facet.
    """
    rows = page.request.get(url + '/data/observations/ZAF.json').json()
    page.goto(url + '/#statements/ZAF')
    page.wait_for_selector('#observations-filters')
    assert str(len(rows)) in page.locator('#observations-count').inner_text()
    # The head-of-tab figures are per table and per country, never pooled.
    for table in ('events', 'implementation-events', 'project-source-links'):
        served = [row for row in rows if row['table'] == table]
        metric = page.locator(f'.metric[data-observation-table="{table}"]')
        assert str(len(served)) in metric.inner_text(), table

    # The table is paged at 50 rows, so the count line carries the filtered
    # total and the tbody carries the page.
    page.locator('#observations-filter-table').select_option('project-source-links')
    links = [row for row in rows if row['table'] == 'project-source-links']
    assert page.locator('#observations-results tbody tr').count() == min(50, len(links))
    assert f'{len(links)} of {len(rows)}' in page.locator(
        '#observations-count'
    ).inner_text()
    page.locator('#observations-filter-table').select_option('')
    page.locator('#observations-filter-verification').select_option('official_register')
    registered = [row for row in rows if row['verification'] == 'official_register']
    assert page.locator('#observations-results tbody tr').count() == min(
        50, len(registered)
    )
    assert f'{len(registered)} of {len(rows)}' in page.locator(
        '#observations-count'
    ).inner_text()

    # Recipe VN: the Bac Ai package, found through the source identifier.
    vietnam = page.request.get(url + '/data/observations/VNM.json').json()
    page.goto(url + '/#statements/VNM')
    page.wait_for_selector('#observations-filters')
    assert str(len(vietnam)) in page.locator('#observations-count').inner_text()
    page.locator('#observations-search').fill('eib')
    eib = [row for row in vietnam if 'eib' in row['source_id']]
    assert len(eib) == 1, len(eib)
    assert page.locator('#observations-results tbody tr').count() == len(eib)

    # Recipe SA: a row read from the Q1 2026 register opens that register's
    # archived snapshot, at the page the locator names where it names one.
    page.goto(url + '/#statements/ZAF')
    page.wait_for_selector('#observations-filters')
    registry = page.request.get(url + '/data/documents.json').json()['documents']
    register = next(row for row in rows
                    if row['source_id'] == 'zaf-jet-investment-register-q1-2026')
    entry = next(row for row in registry
                 if row['id'] == register['source_id'] and row['local_path'])
    assert register['sha256'] == entry['sha256']
    page.locator('#observations-search').fill(register['source_id'])
    key = f'a[data-observation-id="{register.get("event_id") or register.get("link_id")}"]'
    link = page.locator(publisher(key)).first
    link.wait_for()
    assert link.get_attribute('href').startswith(entry['url'])
    check_archived(page, url, page.locator(archived(key)).first, entry, staged,
                   exact=False, opens=False)


def check_facts(page, url, staged):
    """Exercise stage three: a fact's fold-out, its descent, and a document's climb.

    Recipe VN of ticket 0834: from Bac Ai, the fold-out lists its ledger rows
    verbatim and a source card opens MOIT bulletin 5 (July 2025); the Viet Nam
    page shows the RMP 2023 table and the 2025 portfolio side by side, with the
    sentence that no link is established. Recipe SA: from a register project,
    the descent reaches its ledger row and opens the Q1 2026 register snapshot.
    From the RMP on the Documents page, the climb lists the 279 positions and
    no fact of 2025.
    """
    documents = page.request.get(url + '/data/documents.json').json()['documents']
    tables = served_tables(page, url)
    vietnam = page.request.get(url + '/data/VNM.json').json()
    bac_ai = next(p for p in vietnam['projects']
                  if p['id'] == 'vnm-project-bac-ai-pumped-hydro')
    observations = page.request.get(url + '/data/observations/VNM.json').json()
    served = [row for row in observations if row['project_id'] == bac_ai['id']]
    # The fact's evidence is the observations view's own rows, read from that
    # view in the browser and never copied into the country view (0855).
    assert 'evidence' not in bac_ai and len(served) == 3, len(served)

    page.goto(url + '/#project/' + bac_ai['id'])
    page.wait_for_selector('#project-evidence details[data-evidence-count]')
    assert bac_ai['coverage'] in page.locator('h1 [data-review-state]').inner_text()
    # The fold-out itself, not the per-row detail elements nested inside it.
    fold = page.locator('#project-evidence details[data-evidence-count]')
    assert fold.get_attribute('data-evidence-count') == str(len(served))
    fold.locator('> summary').click()
    assert page.locator('#project-evidence tbody tr').count() == len(served)
    # The ledger's own words, one pill per row, never recoded.
    assert page.locator('#project-evidence tbody .pill').all_inner_texts() == [
        row['verification'] for row in served
    ]
    # Every ledger row whose document the registry knows links to the
    # publisher's page — by fingerprint, or by source id where the collection
    # kept no bytes; an archived link joins it only where this server holds
    # the copy those bytes name.
    by_sha = {row['sha256']: row for row in documents if row['sha256']}
    ids = {row['id'] for row in documents}
    assert page.locator(publisher('#project-evidence a[data-observation-id]')).count() == sum(
        1 for row in served
        if (row['sha256'] in by_sha if row['sha256'] else row['source_id'] in ids)
    )
    assert page.locator(archived('#project-evidence a[data-observation-id]')).count() == sum(
        1 for row in served
        if row['sha256'] and by_sha.get(row['sha256'], {}).get('local_path') in staged
    )
    # The bulletin is reached through the source card, the one place the
    # record names it: its host and fingerprint, and the archived PDF where
    # this server holds it.
    assert page.locator('.sources > li').count() == len(bac_ai['sources'])
    bulletin = next(row for row in documents
                    if row['id'] == 'vnm-moit-newsletter-05-2025-07' and row['local_path'])
    facts = page.locator('[data-document-facts="vnm-moit-newsletter-05-2025-07"]')
    assert 'jetp.moit.gov.vn' in facts.inner_text(), facts.inner_text()
    assert facts.locator(f'[data-sha256="{bulletin["sha256"]}"]').count() == 1
    check_archived(page, url,
                   page.locator('a[data-archived-source="vnm-moit-newsletter-05-2025-07"]'),
                   bulletin, staged)

    # Side by side, no link: the two figures come from the M1a manifest and the
    # country view, and the page counts stay 3 named + 21 unpublished.
    manifest = page.request.get(url + '/data/m1a/manifest.json').json()
    page.goto(url + '/#funding/VNM')
    page.wait_for_selector('#vnm-side-by-side')
    block = page.locator('#vnm-side-by-side')
    assert str(manifest['countries']['VNM']['row_count']) in block.locator(
        '[data-side="rmp-2023"]'
    ).inner_text()
    assert str(vietnam['record_count']) in block.locator(
        '[data-side="portfolio-2025"]'
    ).inner_text()
    assert 'No link between the 2023 table and the 2025 portfolio' in block.inner_text()
    assert page.locator('.metrics .metric strong').all_inner_texts()[:2] == ['3', '21']

    # Recipe SA: from a register project, the fold-out row opens the snapshot.
    zaf = page.request.get(url + '/data/observations/ZAF.json').json()
    register = next(row for row in zaf
                    if row['source_id'] == 'zaf-jet-investment-register-q1-2026')
    entry = next(row for row in documents
                 if row['id'] == register['source_id'] and row['local_path'])
    page.goto(url + '/#project/' + register['project_id'])
    page.wait_for_selector('#project-evidence details[data-evidence-count]')
    page.locator('#project-evidence details[data-evidence-count] > summary').click()
    key = f'#project-evidence a[data-observation-id="{register["event_id"]}"]'
    link = page.locator(publisher(key))
    link.wait_for()
    assert link.get_attribute('href') == entry['url'], link.get_attribute('href')
    copy = page.locator(archived(key))
    if entry['local_path'] in staged:
        assert copy.get_attribute('href').startswith(entry['local_path'])
        with page.expect_popup() as popup:
            copy.click()
        opened = popup.value
        opened.wait_for_load_state()
        assert opened.url.endswith(entry['local_path'])
        opened.close()
    else:
        assert copy.count() == 0

    # The climb: the RMP lists its 279 positions and no fact of 2025, joined
    # at read time from the served VNM views (ticket 0858).
    linked = climb(tables, 'vnm-rmp-2023', 'VNM')
    assert linked['facts'] == [] and linked['ledger'] == []
    assert len(linked['m1a']) == 279
    page.goto(url + '/#documents')
    page.wait_for_selector('#documents-filters')
    page.locator('#documents-search').fill('vnm-rmp-2023')
    # The link is keyed by the attempt's row key (ticket 0853), not by the
    # source identifier: the RMP has two attempts, and either row climbs.
    rmp = next(row for row in documents if row['id'] == 'vnm-rmp-2023' and row['local_path'])
    row = page.locator('#documents-results tbody tr').filter(
        has=page.locator(publisher(f'a[data-document-id="{rmp["row_key"]}"]'))
    ).first
    extracted = row.locator('details[data-extracted-count]')
    assert extracted.get_attribute('data-extracted-count') == '279'
    facts = row.locator('details[data-facts-count]')
    assert facts.get_attribute('data-facts-count') == '0'
    extracted.locator('summary').click()
    assert extracted.locator('li').count() == 279
    assert facts.locator('a[href^="#project/"]').count() == 0
    # A registry row nothing cites says so, rather than showing empty lists.
    uncited = next(row for row in documents
                   if not any(climb(tables, row['id'], row['country']).values()))
    page.locator('#documents-search').fill(uncited['id'])
    # The note lands once the row's country views have loaded.
    page.locator(f'[data-uncited="{uncited["id"]}"]').first.wait_for()

    # A reviewed record's pedigree links to the publisher's page of the bytes
    # it pins, and opens those bytes where this server holds them.
    page.goto(url + '/#statements')
    page.wait_for_selector('[data-reviewed-evidence-id]')
    evidence = page.request.get(url + '/data/reviewed-evidence.json').json()
    proofs = [proof for record in evidence['records'] for proof in record['evidence']]
    assert page.locator(publisher('a[data-reviewed-source]')).count() == sum(
        1 for proof in proofs if proof['sha256'] in by_sha)
    assert page.locator(archived('a[data-reviewed-source]')).count() == sum(
        1 for proof in proofs
        if by_sha.get(proof['sha256'], {}).get('local_path') in staged)


def check_paper_trail(page, url):
    """Walk the paper trail both ways on the organisation of ticket 0881.

    The navigation reads the paper trail, The tallies and About (Glossary,
    Methods, Who we are in About's sub-bar) — earlier: Glossary and How we
    did this, each at its label's slug, and the addresses of earlier previews
    forward there (author's cold read, 2026-09-23). From Bac Ai, each step
    toward the documents lands one step
    down — what is on the record for Viet Nam, its entries, the Documents
    page — and each step toward the projects climbs back. A Viet Nam count
    is marked as counted by us and opens what it counted.
    """
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')
    labels = page.locator('header nav a[data-section]').all_text_contents()
    assert labels == ['The paper trail', 'The tallies', 'About'], labels
    # Old addresses forward in place, deep links and tabs included, and the
    # back button does not bounce between the two names.
    for old, new, ready in (
        ('countries', 'funding', '.country-grid'),
        ('country/IDN', 'funding/IDN', '.markdown h2'),
        ('evidence', 'statements', '[data-reviewed-evidence-id]'),
        ('comparison?country=IDN', 'non-jetp-energy-operations?country=IDN', '#history-table'),
        ('how-we-did-this', 'methods', '.method-list'),
        ('numbers', 'counts', 'table.counts'),
        ('by-the-numbers', 'counts', 'table.counts'),
        ('the-tallies', 'counts', 'table.counts'),
        ('historical-comparison', 'non-jetp-energy-operations', '#history-table'),
        ('comparisons?country=IDN', 'non-jetp-energy-operations?country=IDN', '#history-table'),
        ('on-the-record/VNM', 'statements/VNM', '#observations-filters'),
        ('entries/VNM?row=22', 'document-rows/VNM?row=22', '[data-inventory-focus="22"]'),
        ('whos-who?country=SEN', 'organisations?country=SEN', '#parties-filters'),
        ('inventory/VNM?tab=record', 'statements/VNM', '#observations-filters'),
        ('inventory/VNM?row=22', 'document-rows/VNM?row=22', '[data-inventory-focus="22"]'),
    ):
        page.goto(url + '/#overview')
        page.wait_for_selector('.country-grid')
        page.goto(url + '/#' + old)
        page.wait_for_selector(ready)
        assert page.url.endswith('#' + new), (old, page.url)
        page.go_back()
        page.wait_for_selector('.country-grid')
        assert page.url.endswith('#overview'), (old, page.url)
    assert page.evaluate('location.hash') == '#overview'

    # The step bar is the position indicator: the current step is marked, its
    # neighbours are links, the country rides along as a removable chip, and
    # the header keeps the paper trail's tab selected throughout.
    def at_step(label, address):
        page.wait_for_selector(f'#step-bar a[aria-current="page"]:text-is("{label}")')
        assert page.url.endswith('#' + address), (label, page.url)
        tab = page.locator('header nav a[data-section].active')
        assert tab.count() == 1 and tab.get_attribute('href') == '#the-paper-trail'
        assert page.locator('main .eyebrow, main nav.trail, main [role="tablist"]').count() == 0

    def step(label):
        page.locator(f'#step-bar a[data-step]:text-is("{label}")').click()

    page.goto(url + '/#project/vnm-project-bac-ai-pumped-hydro')
    at_step('Projects', 'project/vnm-project-bac-ai-pumped-hydro')
    assert 'Viet Nam' in page.locator('#step-bar .scope-chip').inner_text()
    step('Statements')
    at_step('Statements', 'statements/VNM')
    page.wait_for_selector('#observations-results tbody tr')
    assert 'According to' in page.locator('#observations-results tbody tr').first.inner_text()
    step('Document rows')
    at_step('Document rows', 'document-rows/VNM')
    page.wait_for_selector('#panel-inventory')
    step('Documents')
    at_step('Documents', 'documents?country=VNM')
    page.wait_for_selector('#documents-results')
    assert page.locator('#documents-filter-country').input_value() == 'VNM'
    step('Organisations')
    at_step('Organisations', 'organisations?country=VNM')
    assert page.locator('#parties-filter-country').input_value() == 'VNM'
    step('Funding')
    at_step('Funding', 'funding/VNM')
    step('Projects')
    at_step('Projects', 'projects?country=VNM')
    page.wait_for_selector('#results tbody tr')
    # Removing the chip opens the same step for the whole site.
    page.locator('#step-bar [data-scope-remove="VNM"]').click()
    at_step('Projects', 'projects')
    # The hash changes before the step bar is redrawn: wait for the chip to go.
    page.wait_for_selector('#step-bar .scope-chip', state='detached')
    assert page.locator('#country-filter').input_value() == ''
    # The longer explanation is folded under the one-sentence lede.
    page.goto(url + '/#documents')
    about = page.locator('main .page-head details.about')
    about.wait_for()
    assert about.get_attribute('open') is None
    assert page.locator('main .page-head .lede').count() == 1

    page.goto(url + '/#funding/VNM')
    page.wait_for_selector('.metric.computed')
    counted = page.locator('.metric.computed[data-unit="named projects"]')
    assert 'Our calculation' in counted.text_content()
    assert 'As published' in page.locator('.callout.published').text_content()
    counted.locator('a').click()
    page.wait_for_selector('#results tbody tr')
    assert page.locator('#country-filter').input_value() == 'VNM'



def check_sections(page, url):
    """About's sub-bar, the tallies' table and the Who's who count (ticket 0881)."""
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')
    # About's sub-bar: plain siblings, the current page marked, the release
    # history under Methods and in no bar.
    page.locator('header nav a[data-section="about"]').click()
    page.wait_for_selector('#step-bar [data-sub-bar="about"]')
    assert page.locator('#step-bar a[data-sub]').all_text_contents() == [
        'Glossary', 'Methods', 'Who we are']
    page.locator('#step-bar a[data-sub="who-we-are"]').click()
    page.wait_for_selector('[data-who-we-are]')
    assert page.locator('#step-bar a[aria-current="page"]').inner_text() == 'Who we are'
    page.locator('#step-bar a[data-sub="methods"]').click()
    page.wait_for_selector('.method-list')
    page.locator('.method-list a[href="#release-history"]').click()
    page.wait_for_selector('main table')
    assert page.locator('#step-bar a[aria-current="page"]').inner_text() == 'Methods'
    assert page.locator('header nav a[data-section].active').get_attribute('href') == '#about'
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')
    # The step bar belongs to the paper trail only.
    assert page.locator('#step-bar').is_hidden()
    # The tallies: one table grouped by country, then two numbered figures,
    # and no second copy of the landing page's stat grid.
    page.locator('header nav a[data-section="the-tallies"]').click()
    page.wait_for_selector('table.counts')
    assert page.locator('header nav a[data-section].active').get_attribute('href') == '#counts'
    assert page.locator('table.counts tbody[data-country]').count() == 4
    assert page.locator('main .stat-grid, main .metrics').count() == 0
    assert page.locator('.counts-figure figcaption strong').all_text_contents() == [
        'Figure 1.', 'Figure 2.']
    page.locator('tbody[data-country="VNM"] tr[data-computed-figure="Named projects"] a').click()
    page.wait_for_selector('#results tbody tr')
    assert page.locator('#country-filter').input_value() == 'VNM'
    # Who's who counts each name's projects once.
    page.goto(url + '/#organisations')
    page.wait_for_selector('#parties-results tbody tr')
    assert page.locator('#parties-results tbody tr').count() > 0
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')



def check_header_menus(page, url):
    """The three header dropdowns (author, fifth batch, 2026-09-23).

    Each tab's label links to its landing page; its button opens a
    disclosure of the section's pages, so any page is two clicks away. Open
    by click and by keyboard (Enter, ArrowDown), close by Escape and by a
    click outside; hover opens one as an enhancement. At phone width the
    three stack inside one collapsible nav.
    """
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')
    trail = page.locator('#toggle-the-paper-trail')
    trail.focus()
    page.keyboard.press('Enter')
    assert trail.get_attribute('aria-expanded') == 'true'
    menu = page.locator('#menu-the-paper-trail')
    assert menu.is_visible()
    assert menu.locator('a').all_text_contents() == [
        'Documents', 'Document rows', 'Statements', 'Projects', 'Funding', 'Organisations']
    page.keyboard.press('Escape')
    assert trail.get_attribute('aria-expanded') == 'false' and menu.is_hidden()
    about = page.locator('#toggle-about')
    about.focus()
    page.keyboard.press('ArrowDown')
    assert about.get_attribute('aria-expanded') == 'true'
    assert page.evaluate('document.activeElement.textContent') == 'Glossary'
    page.keyboard.press('Escape')
    assert about.get_attribute('aria-expanded') == 'false'
    assert page.evaluate('document.activeElement.id') == 'toggle-about'
    # One menu at a time, and a click outside closes it.
    about.click()
    page.locator('#toggle-the-tallies').click()
    assert about.get_attribute('aria-expanded') == 'false'
    assert page.locator('#menu-the-tallies').is_visible()
    page.locator('main h1').first.click()
    assert page.locator('#toggle-the-tallies').get_attribute('aria-expanded') == 'false'
    # Two clicks to a sub-page, from anywhere.
    page.locator('#toggle-the-tallies').click()
    page.locator('#menu-the-tallies a[data-sub="comparisons"]').click()
    page.wait_for_selector('#history-table')
    assert page.url.endswith('#non-jetp-energy-operations')
    assert page.locator('#toggle-the-tallies').get_attribute('aria-expanded') == 'false'
    assert page.locator('#menu-the-tallies').get_attribute('hidden') is not None
    assert page.locator('#step-bar a[aria-current="page"]').inner_text() == 'Non-JETP energy operations'
    # Hover opens a menu as an enhancement; the button's state is untouched.
    page.locator('li.section:has(#toggle-about)').hover()
    assert page.locator('#menu-about').is_visible()
    assert about.get_attribute('aria-expanded') == 'false'
    page.mouse.move(5, 900)

    # Phone width: one collapsible nav, the menus stacked inside it.
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')
    toggle = page.locator('#nav-toggle')
    assert toggle.is_visible() and page.locator('#section-list').is_hidden()
    toggle.click()
    assert toggle.get_attribute('aria-expanded') == 'true'
    assert page.locator('#section-list').is_visible()
    page.locator('#toggle-about').click()
    page.locator('#menu-about a[data-sub="who-we-are"]').click()
    page.wait_for_selector('[data-who-we-are]')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.set_viewport_size({'width': 1440, 'height': 1100})


def check_glossary(page, url):
    """The generated Glossary (ticket 0882): one entry per term in force, and a
    link to a term opens its entry, marked and scrolled into view. The ZAF
    register's own completion word follows ticket 0887's status crosswalk."""
    terms = page.request.get(url + '/data/ontology/terms.json').json()
    page.goto(url + '/#glossary')
    page.wait_for_selector('[data-glossary-group]')
    assert page.locator('dl.glossary > dt').count() == len(terms['in_force'])
    finances = page.locator('dt[data-term="relation/finances"] + dd')
    finances.locator('[data-range] a').click()
    page.wait_for_selector('dt[data-term="class/project"][data-targeted]')
    assert page.url.endswith('#glossary?term=class%2Fproject'), page.url
    assert page.locator('dt[data-term="class/project"]').is_visible()
    in_view = ('(() => { const r = document.querySelector(\'dt[data-term="class/project"]\')'
               '.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })()')
    assert page.evaluate(in_view)
    # A status word on the record links to its term.
    page.goto(url + '/#statements/ZAF')
    page.wait_for_selector('#observations-results')
    assert page.locator('#observations-results a[data-term-link="money/signed"]').count() > 0
    page.goto(url + '/#entries/ZAF')
    status = page.locator('a[data-term-link="delivery/finalisation"]:visible').first
    status.wait_for()
    assert status.inner_text() == 'D. Completed'
    status.click()
    page.wait_for_selector('dt[data-term="delivery/finalisation"][data-targeted]')
    entry = page.locator('dt[data-term="delivery/finalisation"] + dd')
    assert 'IATI' in entry.locator('.term-mapping').inner_text()
    assert 'D. Completed' in entry.locator('[data-crosswalk]').inner_text()


def check_projects(page, url):
    """Exercise the catalogue search, a project page, and its adjudicated links."""
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
    assert 'Document published' in report.inner_text()


def check_ticket_0902(page, url):
    """Cold-reader labels, financial table, names, and document-text links."""
    page.goto(url + '/#the-paper-trail')
    page.wait_for_selector('.page-head h1')
    assert 'Follow a number back to its document' in page.locator('main h1').inner_text()
    for route, title in (('document-rows', 'Rows selected from the documents'),
                         ('statements', 'What the documents say'),
                         ('organisations', 'Organisations named in the documents')):
        page.goto(url + '/#' + route)
        page.wait_for_selector('.page-head h1')
        assert title in page.locator('main h1').inner_text()

    page.goto(url + '/#funding/SEN')
    page.wait_for_selector('#funding-statements-results tbody tr')
    assert page.locator('#funding-statements-results th').all_text_contents() == [
        'Project or programme', 'Reported milestone', 'Original amount',
        'Funder · instrument', 'Date and its role', 'Document and location']
    assert 'Inside the portfolio' not in page.locator('main').inner_text()
    assert 'Financing needs stated' in page.locator('main').inner_text()
    initial = page.locator('#funding-statements-results tbody tr').count()
    funders = page.locator('#funding-statements-filter-funder option').all_text_contents()
    assert len(funders) > 1
    page.locator('#funding-statements-filter-funder').select_option(index=1)
    assert 0 < page.locator('#funding-statements-results tbody tr').count() <= initial
    page.locator('#funding-statements-filter-funder').select_option('')
    page.locator('#funding-statements-filter-status').select_option(index=1)
    assert 0 < page.locator('#funding-statements-results tbody tr').count() <= initial
    assert page.locator('#funding-statements-results a[href^="#project/"]').count() > 0
    assert page.locator('#funding-statements-results td:last-child a').count() > 0

    page.goto(url + '/#organisations')
    page.wait_for_selector('#parties-results tbody tr')
    # Senelec has a reviewed recorded form in the served party-name table.
    page.locator('#parties-search').fill('Senelec')
    name = page.locator('#parties-results .organisation-aliases').first
    name.wait_for()
    name.locator('summary').focus()
    page.keyboard.press('Enter')
    assert name.get_attribute('open') is not None
    assert 'SENELEC' in name.inner_text()
    projects = page.locator('#parties-results .organisation-projects').first
    assert projects.locator('> a').count() == 3
    projects.locator('details > summary').click()
    assert projects.locator('details[open] a[href^="#project/"]').count() > 0
    page.locator('#parties-filter-roles').select_option('Operator')
    assert page.locator('#parties-results tbody tr').count() > 0

    page.goto(url + '/#document-rows/ZAF?row=1')
    page.wait_for_selector('[data-inventory-focus="1"]')
    url_link = page.locator('#inventory-results dd a[href^="https://w05.international.gc.ca/"]').first
    assert url_link.count() == 1
    assert url_link.get_attribute('rel') == 'noopener noreferrer'
    assert url_link.get_attribute('target') == '_blank'
    page.goto(url + '/#non-jetp-energy-operations?country=IDN')
    page.wait_for_selector('#history-table')
    assert page.url.endswith('#non-jetp-energy-operations?country=IDN')

    page.set_viewport_size({'width': 390, 'height': 844})
    for route in ('document-rows/ZAF?row=1', 'statements/ZAF', 'funding/SEN',
                  'organisations', 'non-jetp-energy-operations'):
        page.goto(url + '/#' + route)
        page.wait_for_selector('.page-head h1')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
    page.set_viewport_size({'width': 1440, 'height': 1100})
    page.goto(url)
    page.wait_for_selector('.country-grid')


def check_historical_pool(page, url, count):
    """Check the historical operations filters and their published count."""
    page.goto(url + '/#non-jetp-energy-operations')
    page.wait_for_selector('#history-country')
    assert page.locator('#history-table tbody tr').count() == count
    page.locator('#history-country').select_option('IDN')
    assert 0 < page.locator('#history-table tbody tr').count() < count
    page.locator('#history-instrument').select_option('Investment Project Financing')
    assert page.locator('#history-table tbody tr').count() > 0
    page.locator('#history-search').fill('no-such-operation-12345')
    assert page.locator('#history-table .empty').count() == 1


def check_site(url, output, ticket_0902_only=False):
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
        check_ticket_0902(page, url)
        if ticket_0902_only:
            assert not errors, errors
            assert not external_requests, external_requests
            print('Ticket 0902 desktop and phone browser checks passed')
            return
        assert page.locator('.country-card').count() == 4
        with page.expect_response('**/data/comparison.json') as response:
            page.reload()
        count = len(response.value.json()['projects'])
        page.wait_for_selector('.country-grid')
        page.screenshot(path=str(output), full_page=True)
        staged = staged_copies(page, url)
        print(f'Archived copies served: {len(staged)}'
              + ('' if staged else ' (public site: publisher links only)'))
        check_projects(page, url)
        check_historical_pool(page, url, count)
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
        check_documents(page, url, staged)
        check_documents_row_height(page, url)
        check_inventory(page, url, staged)
        check_senegal_and_indonesia(page, url, staged)
        check_observations(page, url, staged)
        check_facts(page, url, staged)
        check_paper_trail(page, url)
        check_sections(page, url)
        check_header_menus(page, url)
        check_glossary(page, url)
        for code in ('ZAF', 'IDN', 'VNM', 'SEN'):
            page.goto(url + '/#funding/' + code)
            page.wait_for_selector('.markdown h2')
            assert page.locator('.markdown').inner_text().strip()
        # Hash routes must remain usable with a keyboard and expose the current
        # location to assistive technology.
        page.goto(url + '/#funding/IDN')
        page.wait_for_selector('.page-head h1')
        active = page.locator('#step-bar a[aria-current="page"]')
        assert active.count() == 1
        assert active.get_attribute('href') == '#funding/IDN'
        section = page.locator('header nav a[data-section][aria-current]')
        assert section.count() == 1 and section.get_attribute('href') == '#the-paper-trail'
        page.locator('.skip').focus()
        page.keyboard.press('Enter')
        assert page.evaluate('document.activeElement.id') == 'main'
        # Skipping moves focus, never the page (#main is not a route).
        assert page.url.endswith('#funding/IDN'), page.url
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.tagName') == 'A'
        page.set_viewport_size({'width': 390, 'height': 844})
        for route in ('overview', 'the-paper-trail', 'funding', 'documents', 'projects',
                      'comparisons', 'documents?country=VNM', 'whos-who?country=SEN',
                      'entries/SEN', 'funding/VNM', 'entries', 'on-the-record',
                      'on-the-record/ZAF', 'whos-who', 'counts', 'glossary', 'about',
                      'who-we-are',
                      'release-history', 'project/vnm-project-bac-ai-pumped-hydro',
                      'methods'):
            page.goto(url + '/#' + route)
            page.wait_for_timeout(150)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
            # Without the index, no page may point into documents/ (ticket 0915).
            if not staged:
                assert page.locator('a[href^="documents/"], a[data-link="archived"]').count() == 0, route
        assert not errors, errors
        assert not external_requests, external_requests
        browser.close()
        print(f'Browser checks passed; {count} historical records; screenshot: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--screenshot', type=Path, default=Path('/tmp/jetp-overview.png'))
    parser.add_argument('--ticket-0902-only', action='store_true')
    args = parser.parse_args()
    check_site(args.url.rstrip('/'), args.screenshot, args.ticket_0902_only)
