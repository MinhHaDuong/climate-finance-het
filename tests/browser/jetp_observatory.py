"""Manual browser acceptance checks for a running static observatory preview.

Run with Playwright installed and Chromium available. This is deliberately not
collected by the Python unit suite: browser installation is a developer tool.
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
    # The filter carries the code as value and the name as label (ticket 0853).
    assert page.locator(
        '#documents-filter-country option[value="ZAF"]'
    ).inner_text() == 'South Africa'
    entry = next(row for row in registry
                 if row['id'] == 'zaf-jet-investment-register-q1-2026')
    # Addressed by the row key, not the source id: 21 identifiers carry more
    # than one collection attempt, so the id alone is not a selector.
    link = page.locator(f'a[data-document-id="{entry["row_key"]}"]')
    assert entry['local_path'], 'Archived ZAF register absent; run make jetp-observatory-documents'
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
    with page.expect_popup() as popup:
        link.click()
    opened = popup.value
    opened.wait_for_load_state()
    assert opened.url.endswith(entry['local_path'])
    assert hashlib.sha256(
        page.request.get(url + '/' + entry['local_path']).body()
    ).hexdigest() == entry['sha256']
    opened.close()

    # Ticket 0857, recipe VN step 1: from this page the RMP 2023 opens at
    # printed page 139 — PDF page 155, the first page its extracted positions
    # name — and each position links to its own inventory row and, where its
    # locator names one, to its own page: the 22nd (KN Tri An) to page 156.
    page.locator('#documents-filter-country').select_option('')
    page.locator('#documents-search').fill('vnm-rmp-2023')
    rmp = next(row for row in registry if row['id'] == 'vnm-rmp-2023' and row['local_path'])
    link = page.locator(f'a[data-document-id="{rmp["row_key"]}"]')
    row = page.locator('#documents-results tbody tr').filter(has=link).first
    fold = row.locator('details[data-extracted-product="m1a"]')
    # The page is set on the link once the VNM views have loaded, just before
    # the fold-outs land (ticket 0858): wait for those, then read the link.
    fold.wait_for()
    assert link.get_attribute('href') == rmp['local_path'] + '#page=155', link.get_attribute('href')
    with page.expect_popup() as popup:
        link.click()
    assert popup.value is not None
    popup.value.close()
    fold.locator('summary').click()
    position = fold.locator('li').nth(21)
    assert 'KN Tri An' in position.inner_text(), position.inner_text()
    pdf = position.locator('a[data-extracted-page="vnm-rmp-2023:annex-I.1:022"]')
    assert pdf.get_attribute('href') == rmp['local_path'] + '#page=156', pdf.get_attribute('href')
    with page.expect_popup() as popup:
        pdf.click()
    assert popup.value is not None
    popup.value.close()
    # The climb lands on the one row, not on the 279.
    position.locator('a[href="#inventory/VNM?row=22"]').click()
    page.wait_for_selector('[data-inventory-focus="22"]')
    assert page.locator('#inventory-count').inner_text().startswith('1 of 1 ')
    focused = page.locator('a[data-inventory-row="vnm-rmp-2023:annex-I.1:022"]')
    assert focused.get_attribute('href') == rmp['local_path'] + '#page=156'
    assert page.locator('#inventory-results details[open]').count() == 1


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
    # Scoped to the inventory panel: the ledger observations tab of the same
    # page carries its own per-table metrics, in the DOM though hidden.
    unknowns = page.locator('#panel-inventory .metrics .metric')
    assert unknowns.count() == len(sublayers)
    assert sublayers[0]['sublayer_id'] in unknowns.first.inner_text()


def check_senegal_and_indonesia(page, url):
    """Walk the two countries the recipe had never reached (ticket 0861).

    Senegal: row 1 of Annex 2 opens the archived annexes at PDF page 13 — on
    that file printed page N is PDF page N, measured at ticket 0861. Indonesia:
    the project the 2025 progress report is cited for most often descends to
    its ledger rows, and a row read from that report opens its archived copy.
    """
    registry = page.request.get(url + '/data/documents.json').json()['documents']

    annexes = next(row for row in registry
                   if row['id'] == 'sen-investment-plan-annexes-mirror' and row['local_path'])
    page.goto(url + '/#inventory/SEN?row=1')
    page.wait_for_selector('[data-inventory-focus="1"]')
    link = page.locator('a[data-inventory-row="sen-annex-received-01"]')
    assert link.get_attribute('href') == annexes['local_path'] + '#page=13', \
        link.get_attribute('href')
    with page.expect_popup() as popup:
        link.click()
    assert popup.value is not None
    popup.value.close()

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
    link = page.locator(f'#project-evidence a[data-observation-id="{row_id}"]')
    link.wait_for()
    assert link.get_attribute('href').startswith(report['local_path']), \
        link.get_attribute('href')
    with page.expect_popup() as popup:
        link.click()
    assert popup.value is not None
    popup.value.close()


def check_observations(page, url):
    """Exercise the ledger observations tab: the counts, a facet, and a search.

    Recipe VN of ticket 0834, adjusted to what the ledger holds: Viet Nam's
    only rows are seven project-source links, and none of the three tables
    carries a funder column for them, so the European Investment Bank package
    is reached by the free-text field and not by the funder facet.
    """
    rows = page.request.get(url + '/data/observations/ZAF.json').json()
    page.goto(url + '/#inventory/ZAF')
    page.locator('#tab-observations').click()
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
    page.goto(url + '/#inventory/VNM')
    page.locator('#tab-observations').click()
    page.wait_for_selector('#observations-filters')
    assert str(len(vietnam)) in page.locator('#observations-count').inner_text()
    page.locator('#observations-search').fill('eib')
    eib = [row for row in vietnam if 'eib' in row['source_id']]
    assert len(eib) == 1, len(eib)
    assert page.locator('#observations-results tbody tr').count() == len(eib)

    # Recipe SA: a row read from the Q1 2026 register opens that register's
    # archived snapshot, at the page the locator names where it names one.
    page.goto(url + '/#inventory/ZAF')
    page.locator('#tab-observations').click()
    page.wait_for_selector('#observations-filters')
    registry = page.request.get(url + '/data/documents.json').json()['documents']
    register = next(row for row in rows
                    if row['source_id'] == 'zaf-jet-investment-register-q1-2026')
    entry = next(row for row in registry
                 if row['id'] == register['source_id'] and row['local_path'])
    assert register['sha256'] == entry['sha256']
    page.locator('#observations-search').fill(register['source_id'])
    link = page.locator(
        f'a[data-observation-id="{register.get("event_id") or register.get("link_id")}"]'
    ).first
    link.wait_for()
    assert link.get_attribute('href').startswith(entry['local_path'])


def check_facts(page, url):
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
    # A ledger row links to its document only when the collection archived
    # its source; a row whose source was never archived shows its locator as
    # text, so the count of links says exactly how many were.
    assert page.locator('#project-evidence a[data-observation-id]').count() == sum(
        1 for row in served if row['sha256']
    )
    # The bulletin is reached through the source card, the one place the
    # record names it; it opens the archived PDF.
    assert page.locator('.sources > li').count() == len(bac_ai['sources'])
    bulletin = next(row for row in documents
                    if row['id'] == 'vnm-moit-newsletter-05-2025-07' and row['local_path'])
    link = page.locator('a[data-archived-source="vnm-moit-newsletter-05-2025-07"]')
    assert link.get_attribute('href') == bulletin['local_path'], link.get_attribute('href')
    with page.expect_popup() as popup:
        link.click()
    assert popup.value is not None
    popup.value.close()

    # Side by side, no link: the two figures come from the M1a manifest and the
    # country view, and the page counts stay 3 named + 21 unpublished.
    manifest = page.request.get(url + '/data/m1a/manifest.json').json()
    page.goto(url + '/#country/VNM')
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
    link = page.locator(
        f'#project-evidence a[data-observation-id="{register["event_id"]}"]'
    )
    link.wait_for()
    assert link.get_attribute('href').startswith(entry['local_path'])
    with page.expect_popup() as popup:
        link.click()
    opened = popup.value
    opened.wait_for_load_state()
    assert opened.url.endswith(entry['local_path'])
    opened.close()

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
        has=page.locator(f'a[data-document-id="{rmp["row_key"]}"]')
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

    # A reviewed record's pedigree opens the archived bytes it pins.
    page.goto(url + '/#evidence')
    page.wait_for_selector('[data-reviewed-evidence-id]')
    evidence = page.request.get(url + '/data/reviewed-evidence.json').json()
    archived = {row['sha256'] for row in documents if row['local_path']}
    expected = sum(1 for record in evidence['records'] for proof in record['evidence']
                   if proof['sha256'] in archived)
    assert page.locator('a[data-reviewed-source]').count() == expected


def check_paper_trail(page, url):
    """Walk the paper trail both ways on the organisation of ticket 0881.

    The navigation reads Glossary, the paper trail, By the numbers and How we
    did this. From Bac Ai, each step toward the documents lands one step
    down — what is on the record for Viet Nam, its entries, the Documents
    page — and each step toward the projects climbs back. A Viet Nam count
    is marked as counted by us and opens what it counted.
    """
    page.goto(url + '/#overview')
    page.wait_for_selector('.country-grid')
    labels = [t.strip() for t in page.locator('header nav a, header nav .nav-group-label')
              .all_text_contents()]  # the group label is upper-cased by CSS only
    assert labels == ['Glossary', 'The paper trail', 'Documents', 'Entries', 'On the record',
                      'Projects', 'Funding', "Who's who", 'By the numbers',
                      'How we did this'], labels

    page.goto(url + '/#project/vnm-project-bac-ai-pumped-hydro')
    page.wait_for_selector('.trail[data-trail-step="D4"]')
    page.locator('[data-trail-link="toward-documents"]').click()
    page.wait_for_selector('.trail[data-trail-step="D3"]')
    assert page.locator('#tab-observations').get_attribute('aria-selected') == 'true'
    assert page.locator('#panel-observations').is_visible()
    assert page.locator('nav a[aria-current="page"]').get_attribute('href') == '#evidence'
    assert 'According to' in page.locator('#observations-results tbody tr').first.inner_text()
    page.locator('[data-trail-link="toward-documents"]').click()
    page.wait_for_selector('.trail[data-trail-step="D2"]')
    assert page.locator('#panel-inventory').is_visible()
    # A tab click moves the address, the trail and the navigation with it.
    page.locator('#tab-observations').click()
    page.wait_for_selector('.trail[data-trail-step="D3"]')
    assert page.url.endswith('#inventory/VNM?tab=record'), page.url
    assert page.locator('header nav a[aria-current="page"]').get_attribute('href') == '#evidence'
    page.locator('#tab-inventory').click()
    page.wait_for_selector('.trail[data-trail-step="D2"]')
    assert page.url.endswith('#inventory/VNM'), page.url
    page.locator('[data-trail-link="toward-documents"]').click()
    page.wait_for_selector('.trail[data-trail-step="D1"]')
    assert page.locator('[data-trail-link="toward-documents"]').count() == 0
    page.locator('[data-trail-link="toward-projects"]').click()
    page.wait_for_selector('.trail[data-trail-step="D2"]')
    page.locator('[data-trail-link="toward-projects"]').click()
    page.wait_for_selector('.trail[data-trail-step="D3"]')
    page.locator('[data-trail-link="toward-projects"]').click()
    page.wait_for_selector('#results tbody tr')
    assert page.locator('.trail[data-trail-step="D4"]').count() == 1

    page.goto(url + '/#country/VNM')
    page.wait_for_selector('.metric.computed')
    counted = page.locator('.metric.computed[data-unit="named projects"]')
    assert 'Counted by us' in counted.text_content()
    counted.locator('a').click()
    page.wait_for_selector('#results tbody tr')
    assert page.locator('#country-filter').input_value() == 'VNM'


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
        check_projects(page, url)
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
        check_senegal_and_indonesia(page, url)
        check_observations(page, url)
        check_facts(page, url)
        check_paper_trail(page, url)
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
                      'inventory/SEN', 'country/VNM', 'entries', 'evidence',
                      'whos-who', 'numbers', 'glossary',
                      'project/vnm-project-bac-ai-pumped-hydro', 'methods'):
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
