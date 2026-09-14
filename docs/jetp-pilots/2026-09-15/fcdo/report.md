# FCDO programme/component feasibility pilot

**NARROW to individually documented programme starts; DEFER approval–procurement–start transitions and historical risk-set designs.** This 14 September 2026 pilot completes ticket 0739's evidence probe. It does not select a causal design or estimate an effect.

The archived query delivers 7,327 programmes and 17,955 components: 25,282 distinct activity IDs, matching `response.numFound`. These are two hierarchy levels, not additive independent financings. Programme status counts are 6 pipeline, 551 implementation and 6,770 post-completion; component counts are 7, 4,200 and 13,748 respectively. The source is FCDO/legacy reporting under GB-GOV-1, including legacy identifier prefixes; it does not cover all UK finance.

## Source and selection freeze

[Input manifest](input-manifest.json) records the merged audit PR head, pinned selection-audit inputs, environment and verified DVC hashes. Base main already contained the updated audit PR and prospective protocol. Commit `b7457964` froze [selection](selection.csv) and [routes](acquisition-routes.md) before research retrieval. The first failing-test commit is `969c4c50`.

All 462 single-country programme candidates are retained: AL 25, MA 25, IN 166, SN 16, ZA 76, ID 89 and VN 65. Lexicographic stratum round robin selects 12. Completed programmes remain eligible. The 7 challenge programmes and 1 challenge component are separate and do not increase sample N. Regional/multi-country records remain separately profiled and are not replicated into country totals.

A material projection limitation governs this selection: the acquired catalogue omits sector vocabulary and finance type. DAC-looking numeric codes alone do not justify a vocabulary assignment, so every frozen candidate is `mixed-or-unmapped` and instrument `missing`. Later structured payloads permit some DAC mappings in units.csv but never alter selection. Missing projected fields do not establish that the publisher never supplies them. A future energy/instrument-stratified sample requires a new full-field freeze.

## Documentary coverage and stages

| Coverage | Fixed 12 programmes | Separate challenges |
|---|---:|---:|
| Structured payload locally available after acquisition | 8/12 | 7/7 programmes + 1/1 component |
| New structured-payload attempts | 8/12 | 5/7 programmes; other originals reused |
| Payload exposes any document links | 2/8 inspected | 1/7 programmes; completion-review pointer only |
| At least one document actually fetched and reviewed | 1/12 | 0/7 programmes |
| Approval stage corroborated | 0/12 | 0/7 programmes |
| Procurement stage corroborated | 0/12 | 0/7 programmes |
| Programme start corroborated by a document | 1/12 | 0/7 programmes |

Coverage is purposive; these fractions are not population availability estimates. Four selected programmes (ranks 9–12) remain unattempted; no replacements. Only one sample programme had documents fetched: the external-document-attempt denominator is **1 programme**, with two originals retrieved through four HTTP/HTTPS requests. Three stages were examined in those originals; a document retrieved for inspection does not automatically validate a stage. Thus start corroboration is 1/1 among document-attempted programmes and 1/12 across the fixed sample; approval/procurement corroboration is 0/1 and 0/12 respectively. [Document coverage](document-coverage.csv) retains each sample/challenge/stage and distinguishes payload inspection, document retrieval and stage validation. Uninspected/absent links are not evidence of absent underlying documents.

For **GB-1-107859, National AIDS Control Programme Phase III**, the [completion review](https://iati.fcdo.gov.uk/iati_documents/3716713.odt), opening header, reports a start on **5 July 2007** and a review in **March 2012**. Its exact structured document link and programme title establish linkage; the structured actual-start value agrees. The link's 6 April 2014 publication date is a third date, not the start or review date. The review discusses tendering and contract award but lacks a dated award milestone/contract identifier. The linked [Intervention Summary](https://iati.fcdo.gov.uk/iati_documents/3735372.odt) describes £102m support over 2007–2012 without a dated approval instrument. Neither supplies the missing transition pair. This supports an individual retrospective programme activity start, not a legal financing start or first physical delivery.

All eight inspected sample payloads report an actual start; the historic challenge parent and component add two distinct unit-level dates. Entry cohorts preserve these source-reported dates separately from the one document-corroborated start. No flattened date arrays are positionally paired. Most catalogue records consequently retain an unvalidated/missing start, rather than receiving a manufactured clock.

## Mandatory challenges

- **GB-1-112151 / GB-1-112151-101:** explicit related-activity records establish the parent/component link. Parent actual start is 9 March 2007; component actual start is 1 February 2007. The component's earliest positive type-4 entry is £300,000 on 31 March 2007, described as aggregated FY2006 Q4 expenditure. Its first observed positive type-3 entry is £785,211 on 11 August 2010. The latter cannot be first spending; complete prior coverage and intra-period onset are unknown. Zero commitment and subsequent positive commitment are retained, without imputing approval.
- **GB-GOV-1-400032, 400142, 400343, 400397, 400542 and 400717:** every mandatory pipeline programme has a structured payload, planned start/end dates and no linked document field. No actual start or programme transaction is claimed from that absence. Status 1 means scoped/planned; it does not mean approved-but-unsigned. The explicitly related 400397-301 catalogue title refers to business-case design, not an approval decision. A separately dated decision and procurement instrument remain required for every programme.

[Anomalies](anomalies.csv) gives a disposition and next document for each selected/challenge case, including unattempted cases. Current catalogue status 4 does not prove continuous retention or explain disappearance. Negative transaction corrections remain raw events; none are interpreted as physical reversal.

## Acquisition and historical observation

Exactly **20/20 external research units** were used: 17 HTTP200 responses, two HTTP301 failures and one HTTP403 failure. Three retention requests preceded ten documentary payload requests; three unused retention units moved to the next sample ranks, then the four reserved requests fetched the two linked documents. Redirects were not followed invisibly and there were no unlogged retries. [Log](acquisition-log.csv), [amendments](acquisition-amendments.md) and [byte manifest](source-byte-manifest.json) preserve outcomes; originals are in the separate 0739-pilot DVC bundle.

The archived [FCDO guidance](https://devtracker.fcdo.gov.uk/docs/Guidance-and-FAQ-on-FCDO-Data.docx) describes monthly publication with arrears and exceptional exclusion/redaction for sensitive material. The current [about page](https://devtracker.fcdo.gov.uk/about) is an update policy, not an observed snapshot history. The attempted publisher-dashboard route returned 403. No independent historical catalogue snapshots, cancellation/removal policy, or complete earlier transaction coverage were obtained. Old event dates and current metadata cannot establish pre-JETP membership, pending status, cancellation or nonpayment.

Coverage.csv retains all four countries' three baseline alternatives and aligns comparator records to each target calendar. Source-reported starts before a cutoff count only as retrospective observations. Historical member/pending counts, their missingness counts and lost-visibility counts are blank where unsupported; measured source-date omissions are counted only for the retrospective clock. IN remains negotiation-exposed; AL/MA remain exposure-unassessed. Multi-country allocation and unknown dates remain separate. Country-sector presence is not JETP attribution.

## Design matrix return

[Matrix inputs](design-matrix-inputs.csv) retain all five candidate families. Incumbent acceleration is DEFERRED for lack of historical membership/pending evidence; new financing/signature throughput lacks a legal-financing unit and signature series. Energy/non-energy contrasts lack a fully mapped frozen population and admissible comparison, with possible spillovers. Country synthetic controls and support-allocation designs remain DEFERRED for stable pre-period series, comparable exposure and allocation evidence. Numerous projects do not create additional independent treated countries.

Missing stage documents and unknown date precision are measurement limitations. Exchangeability, negotiation exposure, concurrent support and interference are separate counterfactual problems; better documents alone do not solve them. No automatic descriptive substitution is proposed. An author scope decision under 0729 remains necessary before a primary design or estimation under 0730.

The next discriminating evidence is a programme-ID-linked dated approval/business-case decision and procurement award/contract instrument, plus independently retained historical snapshots and removal policies if an incumbent risk set is pursued. At this cap, further public retrieval stops.

## Offline reproduction

DVC-tracked large tables are delivered at their protocol paths via adjacent `.dvc` pointers; `dvc pull` restores them and the separate originals bundle. No canonical data are changed. Run from the repository root with the verified audit environment (or equivalent project environment):

```bash
python docs/jetp-pilots/2026-09-15/fcdo/calculate.py \
  --input data/jetp/audit-evidence/0735-round3 \
  --new-archive data/jetp/audit-evidence/0739-pilot \
  --assessment docs/jetp-pilots/2026-09-15/fcdo/document-assessment.csv \
  --reviewed-evidence docs/jetp-pilots/2026-09-15/fcdo/reviewed-evidence.csv \
  --output /tmp/fcdo-offline-reproduction
```

The calculation has no network dependency. Acquisition code is separate and must not be invoked for reproduction. Reviewed assessment/evidence CSVs are explicit human-readable inputs, not title-based automated adjudications. Report, anomalies and matrix inputs are authored synthesis; the common numeric tables, selection, profile and cohorts are regenerated. [Verification](verification.md) records acceptance tests, independent original inspection and repository gates.
