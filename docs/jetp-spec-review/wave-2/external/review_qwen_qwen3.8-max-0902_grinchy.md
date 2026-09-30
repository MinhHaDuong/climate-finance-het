# Peer review — qwen/qwen3.8-max-0902, persona: grinchy

## Verdict

**Major revision — borderline “not ready” for a public, citable M3b release.**  
The specification is unusually disciplined for a one-person project: it separates ontology, data, evidence, and presentation; it obsesses over traceability; and it anticipates many legal and operational failure modes. But it is not yet safe to treat as a trustworthy, citable dataset because it relies on under-specified LLM judgement, weak calibration/statistics, unresolved legal/institutional premises, incomplete bitemporal/entity-resolution semantics, and an operational model that is likely to collapse under its own complexity.

I would not accept this as “ready” until the five priority changes at the end are made.

---

# Prioritized objections

## 1. The in-force/supersession semantics are contradictory and untestable as written

**Where:** `JETP ledger storage contract §1`, especially the “in-force rule”; `JETP information fusion §2`; `JETP Observer: results and releases §9`.

**Problem:**  
The storage contract states one rule for decision rows: an accepted row remains in force while its only successor is a candidate. Then it immediately admits:

> “The DDL's in-force views still apply the earlier rule, under which any successor ends an accepted row; they are to follow this one.”

That is not a minor gap. It means the normative text and the executable validator disagree about what is true. Since the entire bitemporal claim — “results at knowledge cutoff K” — depends on this rule, this contradiction undermines reproducibility, correction releases, and the entire audit trail.

**Fix:**  
Freeze one in-force semantics, implement it in the DDL/views, and add explicit time-travel tests:

- accepted row before K, candidate successor before K, accepted successor after K;
- accepted row before K, rejected terminal successor after K;
- correction overlay applied to rows recorded before K but superseded after K.

Until this is done, claims about frozen releases and knowledge cutoffs are not demonstrably met.

---

## 2. The “no human review of high-impact items” rule is methodologically unsound

**Where:** `Requirements §6.2 Q5`, `Constraints C1`; `Extraction §6.3`; `Fusion §3`.

**Problem:**  
The design says no person reviews admitted items one by one, including high-impact items. The only human check is held-out reference answers. That is not enough for a dataset whose stated purpose is to support journalists, researchers, and negotiators in quoting dated financial statements.

Two LLM readers plus an arbiter can all be wrong in correlated ways:

- shared training data;
- similar multilingual weaknesses in Indonesian, Vietnamese, French;
- prompt brittleness;
- table-structure misreading;
- numeric scale errors;
- prompt injection from hostile documents.

The spec acknowledges “agree-but-wrong rate”, but then uses that as a reason not to review live high-impact items. That is backwards. Calibration tells you the error rate; it does not locate the errors that matter.

**Fix:**  
Add a **risk-based human audit/escalation queue**, even if small and batched:

- any statement/judgement that changes a headline country total;
- any amount above a declared materiality threshold;
- any low-confidence or reader-disagreement item that affects a released figure;
- any statement used in a paper or Observatory headline claim.

This does not require reviewing everything. It does require admitting that a trustworthy citable dataset needs some human verification of consequential items. If you refuse, weaken the claim from “trustworthy” to “machine-assisted documentary index with published error rates”.

---

## 3. Calibration and recall statistics are too weak to support the quality claims

**Where:** `Extraction §6.3`; `Fusion §1`; `Collection §§5–6`; `Requirements Q10`.

**Problem:**  
The statistical basis is thin:

- known-item list minimum: 40 items;
- recall gate: 90% point estimate, e.g. 36/40;
- pooled recall because per-country lists are “too small”;
- strata with fewer than 30 held-out items are “uninformative”;
- likelihood terms are calibrated from LLM self-scores;
- no minimum sample size for calibration per language/classification is enforced.

A 36/40 recall point estimate has a wide Wilson interval. The spec publishes the interval, but then uses the point estimate as the gate. That is statistically irresponsible for a claim of discovery coverage.

Similarly, LLM “likelihood” terms are not probabilities unless calibrated on enough representative gold items. The spec says calibration is recorded, but does not define minimum power, acceptable calibration error, or what happens when a stratum is uninformative except to say so.

**Fix:**

1. Increase the known-item list substantially, or stop calling the result “recall” without qualification.
2. Require per-country and per-language known-item diagnostics, even if only descriptive.
3. Define minimum gold-set sizes for calibration strata; if below threshold, the method is “uncalibrated” for that stratum and cannot be used unattended.
4. Use lower bounds or pre-declared error budgets for stopping/acceptance, not point estimates.
5. Publish confusion matrices, inter-reader agreement, arbiter overturn rates, and agree-but-wrong rates by stratum.

---

## 4. The legal basis is still conditional in ways that can block the entire public release

**Where:** `Legal note §§1–6`; `Requirements C6, F27, F30`; `Results and releases §7`; `Operation §5`.

**Problem:**  
The legal note is candid, but the system specification still proceeds as if the unresolved legal questions are merely “go-live” paperwork. They are not. They affect whether the dataset can be:

- collected lawfully;
- sent to hosted LLMs;
- redistributed;
- licensed;
- maintained under GDPR;
- exposed as a public website with right-of-reply obligations.

Key unresolved issues:

- whether the Observer is formally inside CNRS research activity for the TDM exception;
- database right over investment-plan tables;
- terms of OECD, IATI publishers, World Bank, secretariats, news sites;
- GDPR controller identity;
- processor/transfer agreements for OpenRouter/hosted arbiters;
- personal data inside whole documents sent to hosted models;
- right of reply within three days under LCEN/SREN.

The note says “human legal review is a go-live gate”, but the technical design does not yet enforce hard stops.

**Fix:**  
Make legal review a **hard dependency** of M3b publication:

- no public release until CNRS/institutional responsibility is documented;
- no redistribution of complete plan tables until database-right assessment is done;
- no hosted LLM call for documents containing personal data until minimisation and processor/transfer safeguards are documented;
- no public Observatory until legal notice, privacy notice, controller, publication director, and reply procedure are filled, not `[TO CONFIRM]`;
- treat “terms unknown” as “no redistribution” and, where risk is high, “no automated fetch”.

---

## 5. Entity resolution is under-specified and reinvents record linkage without using standard practice

**Where:** `Fusion §3`; `Ontology §3`; `Storage §1`; `Results §3`.

**Problem:**  
The matching model is mostly pairwise, LLM-driven, and thresholded per result. That is not state of the art for entity resolution. The spec also misuses `same_as` in places. For example, the storage contract says:

> “A value printed in three places is three lines related by same_as.”

That is dangerous. Three printed occurrences of the same value are not necessarily the same assertion, the same event, or the same referent. They may be repetition, restatement, corroboration, or copying. `same_as` should be used very carefully, usually for referents, not for raw statement occurrences.

Other issues:

- equality is bounded to depth one, but referents still need clusters;
- rejected `same_as` inside a would-be cluster creates conflicts, but no human queue is allowed;
- no probabilistic Fellegi-Sunter-style scoring;
- no explicit blocking recall requirements beyond a sentence;
- no treatment of near-duplicate copying not captured by document relations;
- no canonicalization policy for names, aliases, and identifiers.

**Fix:**  
Rewrite the identity section with standard entity-resolution practice:

- separate **occurrence linkage** from **referent identity**;
- use `same_as` only for referents, not raw lines, unless a judgement explicitly says the assertions are identical;
- define blocking, candidate generation, pairwise scoring, cluster formation, and conflict handling;
- cite/use Fellegi-Sunter or probabilistic record linkage, even if simplified;
- publish pairwise precision/recall, blocking recall, B-cubed, and cluster conflict counts;
- for high-impact clusters, require human audit or conservative non-merging.

---

## 6. The bitemporal model is conceptually right but implementation-incomplete

**Where:** `Fusion §8`; `Storage §1`, “Times per table”; `Results §2`; `Requirements F10`.

**Problem:**  
The spec distinguishes world time and knowledge time. That is correct. But the implementation relies on target columns:

- `line-referents` gains `recorded_at`;
- `relations` gains `recorded_at`;
- adjudications gain method/stance/likelihood/confidence;
- lines gain `run_id`, method, method_version;
- observations gain `run_id`.

Until those exist, the as-of rule uses `decided_at` as a stand-in. That is not good enough for reproducible results at knowledge cutoff K.

Also, the spec does not clearly separate:

- valid time start/end;
- transaction time;
- decision time;
- publication time;
- retrieval time;
- report cutoff time.

It has pieces, but not a formal temporal model.

**Fix:**  
Before M3b:

- add `recorded_at` to all decision tables;
- add explicit valid-time bounds for observations/timings;
- document a bitemporal query rule: “state at knowledge cutoff K” means transaction time ≤ K and in-force chain evaluated as of K;
- include automated tests for correction overlays;
- freeze ontology version hashes with every result.

Do not release results whose reproducibility depends on target schema columns that do not exist.

---

## 7. The result model is over-built for the stated milestone and one-person operation

**Where:** `Fusion §7`; `Ontology §4`; `Results §2`; `Presentation`; `Operation §11`.

**Problem:**  
The spec wants accounts with openings, movements, closings, residuals, coverage gaps, disjoint-cover tests, marker coefficients, macro indicators, transition functions, deflators later, RO-Crate later, SKOS exports, Dolt options, etc. Much of this is theoretically attractive but operationally excessive for M2/M3.

The user need is already hard enough:

- find documents;
- extract statements;
- match them to projects/agreements/parties;
- produce citable counts by financial state;
- show CRS/IATI gaps;
- provide timelines and excerpts;
- keep provenance.

Full reconstruction accounts are a research problem in themselves. They will produce many “blocked” results and consume enormous judgement effort.

**Fix:**  
Define a minimal M3b result set and defer the rest:

M3b should contain:

- counts by country, financial state, currency, scope;
- simple timelines;
- operation-level statement excerpts;
- CRS/IATI matching coverage and reporting-lag diagnostics;
- unresolved conflict lists;
- provenance and calibration reports.

Defer:

- full account reconstruction;
- marker coefficients;
- macro indicators;
- deflators;
- advanced transition-function analytics;
- SKOS/RO-Crate unless externally required.

This is not dumbing down; it is making the first release trustworthy.

---

## 8. CSV-in-git plus pull-request-per-run will not scale to the projected ledger

**Where:** `Storage §1`, `Storage §3`, `Operation §4`.

**Problem:**  
The spec acknowledges volume growth but tries to preserve git diff review for everything. That will fail when:

- bulk comparator draws add thousands of rows;
- assisted readings produce hundreds or thousands of rows per run;
- living documents are refetched weekly;
- text layers and raw responses live in DVC;
- each run opens a PR.

Reviewing run output through a manifest is sensible for bulk ingestion, but the spec still treats CSV-in-git as the system of record while SQLite is only a build artifact. This creates awkward dual authority:

- CSV files are canonical;
- SQLite validates and builds;
- Dolt is deferred to M4;
- git file ceiling forces shard directories;
- reviewers are expected to inspect manifests, not rows.

This is a fragile halfway architecture.

**Fix:**  
Either:

1. move to Dolt/SQLite with versioned exports and deterministic CSV snapshots earlier, or  
2. explicitly reduce git’s role to metadata, manifests, and small decision tables, while bulk data is stored as immutable DVC artifacts with manifests and hashes.

In either case, define:

- maximum PR row count before manifest-only review;
- sampling audit rules for bulk rows;
- deterministic export hashes;
- validator reports as release gates.

---

## 9. The cost and human-effort model is implausibly optimistic

**Where:** `Operation §7`, `Operation §8`, `Requirements Q15`, `DA2`, `Extraction §6.3`.

**Problem:**  
The budget section gives useful numbers, but the assumptions are fragile:

- 4 million tokens for held documents is a floor;
- Vietnamese and Indonesian tokenization increases token counts;
- largest PDF text layer is ~950,000 characters;
- local throughput on long documents is unmeasured;
- two local readers must be from different families and fit on 16 GB/12 GB cards;
- arbiter escalation may be frequent;
- calibration requires hand-made reference answers;
- parsers must be maintained per publisher series;
- discovery, triage, matching, release validation, legal review, and error reports all require attention.

The spec’s answer to human scarcity is “no machine judgement is routed to the author”. That is not a cost model; it is a hope.

**Fix:**  
Produce an M2–M3b workload model:

- expected documents by class;
- expected tokens by language and format;
- expected disagreement/arbiter rate from prototype runs;
- expected gold-set creation hours;
- expected parser maintenance hours;
- expected release validation hours;
- expected legal/rights review effort;
- monthly LLM and GPU-hour ceilings with stop behaviour.

If the model shows the author cannot sustain it, cut scope before M3b.

---

## 10. Many terms are still too vague to be testable

**Where:** `Requirements §2.1`, `Language`, `Extraction §6.3`, `Fusion §1`, `Operation §4`.

**Problem:**  
The specification says requirements must be testable, but several key terms are not defined precisely enough:

- “agent”;
- “development agent”;
- “cross-family reviewer”;
- “stronger model”;
- “arbiter”;
- “panel”;
- “calibrated likelihood”;
- “acceptance level”;
- “high-impact item”;
- “method version”;
- “run”;
- “material error”;
- “recorded search”;
- “public access route”;
- “appropriate security”;
- “institutional record”.

Some are defined locally, but not enough for an external auditor to run the tests.

**Fix:**  
Add a normative testability glossary:

- exact meaning of model family;
- exact acceptance thresholds;
- exact calibration metrics;
- exact sampling seeds and sample sizes;
- exact run report schema;
- exact evidence required for “recorded search”;
- exact security controls satisfying “appropriate security”.

If a rule cannot be tested, move it from requirement to principle.

---

## 11. Collection rules are too permissive relative to terms of use and robots rules

**Where:** `Collection §1`, `Requirements C6, F27`, `Legal note §1`.

**Problem:**  
The spec distinguishes automated link-following from single fetches and says a single fetch of a known public document can proceed “whatever those rules say”, while recording the site’s position. That may be defensible under a research TDM theory in some cases, but it is risky for a public dataset that wants to be citable and legally clean.

Free registration does not necessarily grant scraping, bulk extraction, or third-party processing. The spec acknowledges this legally, but operationally it still allows the fetch.

**Fix:**  
Introduce a source permission matrix:

- public open;
- public registered, terms permit research use;
- public registered, terms forbid automation;
- terms unknown;
- robots forbids;
- explicit TDM reservation;
- paywall/closed.

Then enforce:

- no automated fetch where terms forbid it;
- manual fetch only where legally cleared;
- local-only reading where third-party processing is reserved;
- no redistribution where terms unknown.

This should be machine-checkable from the register.

---

## 12. Personal-data minimisation is not actually implemented before hosted calls

**Where:** `Legal note §3`, `Legal note §4`, `Extraction §6.3`, `Operation §5`.

**Problem:**  
The legal note says whole documents are sent to readers before extraction and that minimisation must act on the input. But the extraction rules still send the text layer to hosted arbiters when local readers disagree or are uncertain. That may include names, contact details, political opinions, or other personal data.

The release validation screen is after the fact and “reports, it does not block”. That is insufficient for GDPR accountability.

**Fix:**

- default to local reading for any document flagged as personal-data-risky;
- add a redaction/minimisation step before hosted calls;
- block hosted calls for documents with unresolved personal-data flags;
- make the validation screen blocking for contact details unless an exception is recorded;
- document the GDPR basis, controller, processor relationships, and transfer mechanism before hosted calls are used.

---

## 13. The specification underestimates prompt injection and adversarial-document risk

**Where:** `Extraction §6.3`, `Extraction §12`, `Collection §9`.

**Problem:**  
The spec treats documents as untrusted input and includes a planted-instruction control. Good. But the controls are still narrow. Documents may contain:

- instructions to LLM readers;
- misleading hidden text;
- invisible HTML text;
- bogus locators;
- fake totals;
- manipulated tables;
- secondary claims designed to look primary.

The system relies heavily on LLM readers not being fooled. The red tests are useful but not sufficient.

**Fix:**  
Add an adversarial-document protocol:

- prompt-injection fixtures per language;
- hidden-text fixtures beyond `hidden`/`display:none`;
- table-header spoofing;
- numeric-scale traps;
- fake citation traps;
- secondary-source impersonation;
- mandatory quarantine for documents with detected instruction-like text.

Also publish the false-positive/false-negative behaviour of the injection screen.

---

## 14. The state-of-the-art mapping is partial and sometimes decorative

**Where:** `Requirements FAIR assessment`, `Ontology §0`, `Ontology §5`, `Results §5`.

**Problem:**  
The spec mentions W3C PROV, PREMIS, SKOS, FAIR, DataCite, Frictionless, OC4IDS, IATI, CRS, GEM. But several mappings are deferred or not operational:

- PROV mapping exists as a table, but no PROV export until M4;
- SKOS export is M4;
- RO-Crate is M4;
- bibliographic/document modelling is bespoke rather than using common models;
- entity resolution does not cite standard record-linkage literature;
- uncertainty communication uses IPCC terms but not standard psychometric or visualization practice.

The result is a system that claims alignment with established practice but does not yet produce the interoperable artifacts that make that alignment real.

**Fix:**  
For M3b, include at least:

- JSON-LD or CSV provenance sufficient to reconstruct the PROV chain;
- external vocabulary mappings for country, currency, organisation identifiers, CRS/IATI codes;
- SKOS or simple glossary export from terms table;
- explicit comparison with related models: PROV, PREMIS, DataCite, Frictionless, OC4IDS, IATI, schema.org/Dublin Core;
- citation of record-linkage practice in Fusion §3.

Do not claim interoperability unless the release contains the mapping artifacts.

---

## 15. Presentation specification includes too much UI detail that does not earn its place

**Where:** `JETP Observatory: presentation`, especially “Organisation and vocabulary”.

**Problem:**  
The presentation document spends considerable space on dropdown keyboard behaviour, aria attributes, sub-bars, chips, slugs, and page labels. Some of this is useful, but it is implementation detail and will rot quickly. It also distracts from the more important presentation requirements:

- traceability from figure to statement;
- clear “As published” vs “Our calculation” markers;
- uncertainty display;
- release identification;
- correction/supersession visibility;
- plain-language definitions.

**Fix:**  
Move UI mechanics to a separate implementation guide. Keep only normative presentation requirements:

- every number resolves to a result/statement;
- every page states release ID and cutoffs;
- computed and published numbers are distinguishable;
- ranges are labelled as sensitivity, not probability;
- evaluative words are banned outside quotes;
- correction status is visible.

---

# Fitness for purpose

The intended users are think tanks, journalists, researchers, and negotiators. For those users, the spec’s strengths are real: dated statements, publisher attribution, snapshot locators, frozen releases, and correction trails. But the current design risks producing a dataset that is:

- too complex to audit;
- too dependent on unreviewed LLM judgements;
- too legally fragile to redistribute;
- too operationally heavy to maintain to 2030;
- too statistically weak to support coverage claims.

The most urgent fix is not more ontology. It is assurance.

---

# State of the art assessment

## What it does well

- Uses external vocabularies: CRS purpose codes, IATI transaction types, OC4IDS project statuses, GEM asset states, DAC modality codes.
- Separates publisher vocabulary from shared axes via crosswalks.
- Recognises PROV, PREMIS, FAIR, DataCite, Frictionless.
- Uses bitemporal thinking.
- Treats uncertainty explicitly with IPCC likelihood/confidence language.

## What it ignores or underuses

- Standard probabilistic record linkage / entity resolution.
- Active learning and human-in-the-loop auditing for high-impact extraction.
- Standard uncertainty visualization and communication.
- Persistent identifiers for individual statements before release.
- Web Annotation / W3C Annotation style locators.
- ODRL or rights metadata for redistribution constraints.
- RO-Crate earlier than M4.
- Formal preservation metadata beyond a nod to PREMIS.

The specification should not merely name these models; it should either implement a minimal subset or explicitly state why they are deferred.

---

# Implementation realism

This is the weakest area after methodology.

The current plan expects one researcher, two machines, local GPUs, API budgets, git/DVC, CSV shards, run PRs, LLM calibration, discovery campaigns, multilingual extraction, entity resolution, release validation, legal compliance, and public site maintenance through 2030.

That is too much.

Specific risks:

- local readers may not fit or may be too slow;
- long documents will explode token and time costs;
- arbiter escalations may dominate;
- git PR review will become ritualistic;
- DVC objects and backups will grow;
- source sites will change;
- model vendors will change pricing or terms;
- legal requests may arrive when the author is unavailable.

The spec needs a realistic “minimum survivable system”:

- fewer result types;
- stronger hard stops;
- smaller release cadence;
- explicit institutional backup owner;
- external handover beyond the author.

---

# Dead angles and failure modes

The spec mentions many, but not forcefully enough as release blockers:

1. **Model deprecation or repricing**  
   A reader or arbiter disappears. The spec says replacement is a new method version, but does not say what happens to pending work if no budget exists.

2. **Source disappearance or login-wall expansion**  
   The spec records loss of visibility at M4. It should be visible earlier as a risk register.

3. **Single-person bus factor**  
   The handover note is good, but not enough. There should be an institutional owner, not only a note.

4. **Backup silent failure**  
   The spec itself records a restic failure. Backup monitoring must be a release gate, not an afterthought.

5. **Legal takedown after release**  
   Withdrawal is specified, but third-party mirrors, deposits, and backups complicate removal. The spec needs a realistic withdrawal capability statement.

6. **Prompt injection or malicious documents**  
   Partially addressed, but needs a stronger adversarial protocol.

7. **Registration-account ban**  
   If public portals depend on the author’s account, loss of the account can block collection. The spec should record dependency and alternatives.

8. **Multilingual LLM weakness**  
   Vietnamese and Indonesian legal/financial text is hard. Calibration must be language-specific and large enough.

---

# Five most important changes, in priority order

## 1. Add risk-based human verification for consequential statements and judgements

Revise Q5 and C1. Do not allow a released headline figure to depend solely on unreviewed LLM agreement unless the calibration evidence is strong and the item is low-risk. Introduce a small, batched human audit queue for:

- high monetary values;
- country totals;
- conflicting statements;
- low-confidence matches;
- statements used in papers or Observatory headlines.

Without this, the “trustworthy, citable” claim is not defensible.

---

## 2. Make legal and redistribution constraints hard gates

Before M3b publication:

- confirm institutional basis for TDM;
- identify GDPR controller;
- complete database-right assessment for plan tables;
- fill all legal notice placeholders;
- obtain provider/transfer safeguards for hosted LLM calls;
- implement per-document redistribution flags enforced by the release build.

If legal status is unknown, the release should cite, not redistribute.

---

## 3. Fix the bitemporal and entity-resolution core before adding analytics

Implement and test:

- in-force chain semantics;
- `recorded_at` for all decision rows;
- knowledge-cutoff queries;
- correction overlays;
- referent identity separate from statement occurrence;
- conservative handling of unresolved clusters;
- standard record-linkage metrics and methods.

This is the foundation. Accounts and dashboards are secondary.

---

## 4. Cut M3b scope to the minimum citable documentary release

Defer full accounts, markers, macro indicators, deflators, and advanced presentation features. M3b should deliver:

- frozen register and discovery report;
- extracted statements with locators;
- basic referents;
- counts by financial state, currency, and scope;
- timelines;
- CRS/IATI comparison;
- provenance and calibration reports;
- legal/redistribution manifest.

That is already a large deliverable.

---

## 5. Produce a realistic cost, storage, and maintenance plan

Before proceeding:

- measure local token throughput on long multilingual documents;
- estimate arbiter escalation rates;
- estimate gold-set creation and maintenance effort;
- set storage limits for DVC/raw responses;
- define when to move from CSV/git to Dolt/SQLite;
- define backup monitoring and restore tests;
- define model/vendor fallback policy and budget caps.

If the plan does not close, reduce scope or cadence.

---

# What is excellent and should be kept

Despite the objections, several design decisions are strong and should not be diluted:

1. **ODEM separation**  
   Keeping Ontology, Data, Evidence, and Models apart is conceptually sound and protects the documentary record from causal overclaiming.

2. **Statement-level traceability**  
   Requiring every statement to resolve to snapshot bytes and a locator is the right core principle.

3. **Publisher’s words preserved**  
   Keeping `own_status`, `own_sector`, verbatim fields, and crosswalks separate is excellent. It prevents silent harmonisation.

4. **Append-only and supersession model**  
   The intent to never erase, and to correct by supersession, is exactly right for a citable record. It just needs consistent implementation.

5. **Neutrality rules**  
   Banning evaluative language and distinguishing “documentary finding” from “world fact” is important for trust.

6. **Known-item recall and stopping rules**  
   The ambition to declare search protocols and measure recall is good. The statistics need strengthening, but the instinct is correct.

7. **Legal note**  
   The legal note is unusually frank for a technical specification. It should remain, but its open points must become hard gates.

8. **Release freezing and citation model**  
   Frozen releases, persistent identifiers, DataCite metadata, Frictionless descriptors, and correction releases are the right outward-facing architecture.

---

# The three things that most threaten the paper’s central claim

The central claim is that this will produce a **trustworthy, citable documentary dataset** on JETPs. The three biggest threats are:

1. **Undetected material errors from LLM-only judgement**  
   If headline financial figures rest on two agreeing LLMs with no human audit of consequential items, the dataset may be citable but not trustworthy.

2. **Legal/rights exposure**  
   If TDM status, database right, GDPR controller, provider transfers, or redistribution of plan tables are not resolved, the dataset may not be safely publishable or reusable.

3. **Operational over-complexity for one researcher**  
   The combination of multilingual extraction, entity resolution, bitemporal correction, legal compliance, release management, and site maintenance is likely to exceed sustainable capacity, leading to drift, silent failures, or abandoned releases.
