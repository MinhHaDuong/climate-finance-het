# Data-science review of observatory PR #1343

14 September 2026. Reviewed the branch after merging Senegal PR #1332,
with generated inputs pinned to `5945a42d`. This is a focused scientific
review, not the full Imperial Dragon merge gate. Verdict: **changes requested**.
The Senegal refresh is complete; the issues below are reported, not repaired.

## 1. High priority: date provenance is being mistaken for event timing

Location: `scripts/jetp/_observatory_data.py:20–31`.

`public_event` treats every dated row other than `official_register` and
`official_report` as a source event date. Source authority and the meaning of
a date are independent properties. Three Indonesian `official_portal_snapshot`
approvals therefore become events on 2026-09-12 even though their notes explicitly
identify retrieval dates from undated profiles. The affected IDs are
`idn-portal-gecs-kfw-2026`, `idn-portal-nagajaya-norfund-2026` and
`idn-portal-hululais-jica-2026`.

The new Senegal `sen-puelec-three-villages-reported-20251109` similarly exports
2025-11-09 as a source event date, although the source row says this is publication
date and exact commissioning days are not established. Several ANER planned-status
API observations on 2026-09-13 have the same problem. Notes retain the caveat,
but structured downloads and the timeline's main date contradict it.

Required correction: encode date role and precision explicitly, separately
from verification status; keep event time unknown or interval-valued when only
an observation date exists. Preserve reporting and collection dates separately.
First regression cases should use these real rows, rather than only synthetic
`official_report` examples. No lifecycle duration should consume the current
exported `date` field without this correction.

## 2. Medium priority: source-link adjudication is lost in publication

Location: `scripts/jetp/build_observatory.py:62–79`.

The builder reads `project-source-links.csv` but exports only the union of source
IDs. It drops each link's `relationship`, `review_status`, `locator` and `notes`.
It also drops `match_status` from source claims. Thus source availability survives,
but the evidence for accepting or refusing the entity join does not.

Reproducible example: link `round4-boad-linguere` joins
`sen-boad-linguere-loan-2026` to `sen-project-qw-02` as `possible_match` /
`provisional`. Its note explicitly says that the exact physical site and loan
are known, but the Champions Nationaux vehicle and JETP attribution are not.
The public project includes the source but no structured link object carrying
that decision. Broad project caveats cannot replace source-specific adjudication.
This matters particularly because the latest Senegal research is about those joins.

Required correction: export and render the typed links and claim verdicts,
including rejected/contextual candidates where appropriate. Keep confirmed
identity, partial component, possible match and context separate in downloads.
A regression should assert that `round4-boad-linguere` remains provisional from
CSV through JSON to its source card.

## 3. Medium priority: acquisition dates must come from acquisition records

Location: `scripts/jetp/build_observatory.py:118–132`.

`comparison_data` assigns `retrieved_on` from the observatory edition cutoff,
ignoring retrieval metadata in the four frozen World Bank snapshots. The dates
happen to agree today (2026-09-13). Advancing the monthly cutoff without refreshing
the historical snapshots will falsely announce a fresh World Bank retrieval.
This is a reproducible latent error: changing only `config['cutoff']` changes
`comparison_data(... )['retrieved_on']` while snapshot bytes remain identical.

Required correction before monthly publishing: expose each snapshot's actual
retrieval date and query/page hashes; distinguish observation cutoff, acquisition
date, edition date and substantive source update. Test an edition later than its
unchanged snapshots.

## Scientific interpretation and strengths

The 383 named records are portfolio identities, including programmes and
components, not a census of distinct assets. The current UI says this. The
Senegal 21/43 direct-corroboration count measures evidence coverage, not progress.
The 301 sources include access failures and contextual evidence; it is a
registry size, not a count of independent confirmations.

National financing headlines preserve source-specific stages and reporting dates.
The code does not add needs, approvals and signatures together, mix currencies
into a false total, or turn unpublished Vietnamese identities into named assets.
These are appropriate boundaries. The Senegal follow-up correctly refrains from
promoting conditional budgets, advance orders or a nearby solar financing package
into attributed JETP disbursements.

The financing-stage chart needs cautious interpretation. Its South African
register category combines 235 rows coded signed, 21 announced and one approved,
whereas other countries are classified by substantive financing status. It
therefore partly measures coding/source regimes. It must not become a ranking
of country implementation performance. Prefer separate views of evidence coverage
and financial stage when the underlying stage/date coding is reconciled.

The 97 World Bank closed operations meet the requested historical browsing need.
They are explicitly administrative closures, and the chart discloses closed-only
selection, mixed instruments and additional financing. This is acceptable
*descriptive* context. It is not a control group: selecting only finished
operations omits slow and unfinished cases, while approval-to-closing measures a
different interval from JETP preparation-to-approval. The next analytical sample
needs common units, instruments, entry periods and early-stage endpoints, and
must retain censored active operations. Construction need not be an outcome.

## Validation boundary

The refreshed preview passes 1,545 fast tests (seven skipped), lint and Chromium
navigation/filter/download/mobile checks. Those checks do not validate the
scientific meaning of every date or entity join. The review's real-record
counterexamples explain why a green software suite is insufficient. The earlier
full-suite results remain documented in `jetp-observatory-mvp-validation.md`;
no new full-suite run or independent review panel is claimed here.
