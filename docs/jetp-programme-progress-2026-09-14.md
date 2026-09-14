# JETP programme progress audit — 14 September 2026

Assessment against the agreed programme and ticket exit criteria, not percentage
complete. PR #1343 is a draft implementation contribution, not delivery of the
whole programme. All public programme issues #1333–#1342 remain open at audit.

| Step | Evidence of progress | Remaining acceptance work | Ticket |
|---|---|---|---|
| Citable dataset | Four-country CSV registries, DVC source references, Markdown context, frozen preview JSON and hashes; 383 named identities, 21 unnamed slots, 301 registered sources | Scientific export fixes; reviewed financial-status mapping and identity hierarchy; auditable additive aggregates where possible; release descriptor, dictionary, validation and terms | 0726 / #1334 |
| Public observatory | Working static preview with synthesis, country/project views, filters, source timelines, downloads, and 97 closed historical operations | Scientific fixes and release acceptance; keyboard/deep-link review; hosting/URL decision and verified live site | 0727 / #1335; current slice 0734 / #1342 |
| Monthly editions | Storage conventions and an initial refresh exercised | Immutable first edition, owner/calendar, two-edition rehearsal, correction/late-report classification and public history | 0728 / #1336 |
| Lifecycle feasibility | Richer source corpus and a defined audit protocol | Execute the first three-case documentary check, then 10–15 JETP cases and a defined historical candidate frame; stage-specific go/narrow/defer memo | 0729 / #1337 |
| Comparative dataset | Historical World Bank snapshot provides a discovery/reference pool; older CRS work exists | Comparable early-stage endpoints, inclusion of active/cancelled cases, maturity-at-entry assessment, frozen selection rules and supported estimates | 0730 / #1338, after 0729 |
| Three manuscripts | Historical short/long conception material, old figures and stronger Senegal case evidence | New JETP data-paper manuscript; revised short/long arguments and figures; LaTeX scaffold and reproducible builds | 0731–0733 / #1339–#1341; scaffold 0711 |

The existing repository `deliverables/data-paper` is not the JETP data paper.
`deliverables/jetp-mesure` and `deliverables/jetp-econpol` do not yet exist.
Existing conception notes are inputs, not completed manuscripts or new results.
The old notes now explicitly link to the superseding programme decision.

## Direction of PR #1343

The PR is aligned with the intended programme: it delivers a synthetic country
view as well as project browsing; it preserves named versus unnamed identities;
it keeps historical administrative closures separate from physical completion;
and it does not manufacture a pooled disbursement total or acceleration estimate.
The Senegal update contributes identity adjudication and preparation evidence.

The scientific correction work is also in the right direction: date semantics
move into an explicit observation-timing registry independent of source authority;
typed source links and claim verdicts survive publication; historical acquisition
metadata is tied to actual frozen source snapshots. Actual-record regressions
exercise the previously misleading examples. Completion still requires regenerated
exports, validation and review of the pushed revision, not just inspection of
working-tree code. Final evidence belongs in the PR validation/review notes.

The next design pressure should be analytical validity and release reproducibility,
not more website features. In particular, South African register-derived categories
and other countries' financial stages are not directly comparable performance
metrics. This remaining release task is now explicit in 0726.

## Ticket audit and next short-paper action

No duplicate feature tickets are needed: 0726–0733 already cover release, website,
monthly maintenance and the papers. Their first tests and dependency graph are
substantive. This audit adds concrete remaining-work handoffs to 0726–0729 and
0732. Local ticket 0734 was reopened because review fixes are outstanding while
its public issue is still open; close it again only with resolution evidence.
The AEDIST experiment remains Imagine-only and has no authorised implementation
wave. The analytical acceleration study and the pipeline-methods experiment must
not be silently combined.

**Start 0729 next.** Its first deliverable is a source-audited three-case worksheet:
one JETP project already mature when admitted, one pending JETP proposal, and one
ordinary historical operation. Record project/operation identity, attribution,
entry and maturity, comparable endpoints with date roles/precision/bounds, source
locators and censoring. Use it to correct the protocol before scaling to the
agreed 10–15 JETP cases and historical candidate frame.

The resulting coverage matrix should show which intervals are observable on both
sides. Approval-to-signature is a candidate worth auditing, not a selected result;
identification-to-approval and signature-to-effectiveness/first payment remain
candidates too. Do not wait for construction, full website deployment or complete
four-country reconciliation. Do not use the closed-only pool as the analytical
sampling frame. The feasibility memo chooses the short paper's defensible scope;
0730 then estimates comparisons and 0732 builds the central figure/manuscript.
