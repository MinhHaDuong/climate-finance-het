# External review synthesis: JETP Observer specification draft v0.1

Inputs: four reviews in `wave1/external2/`. Abbreviations: GG = GPT-5.5 grinchy, GS = GPT-5.5 student, MG = Mistral Large 2512 grinchy, MS = Mistral Large 2512 student. G0 = the earlier GPT-5.5 grinchy run in `wave1/external/`, used only to note agreement. Ledger ids are W1-01 to W1-71 from `wave1/ledger.md`. The reviewers saw the ten documents on main after the wave-1 fixes, before the two author decisions listed at the end.

## 1. Verdict

All four reviewers say the draft is not ready to freeze as the implementation contract.

- GG: "not ready", major revision.
- GS, MG, MS: "major revision".
- G0: "not ready".

The split is only in tone. No reviewer rejects the architecture. All four praise the same core: append-only records, snapshot hash plus locator, frozen citable releases, publisher statements kept apart from Observer calculations, and unknown kept distinct from zero.

Substantive splits:

- **LLM-as-judge.** MG names it the top threat. GG and GS call it methodologically inadequate. MS lists it as a strength and asks only for a cap on the author sample. Weight MS low.
- **Size of the spec.** GG and GS call parts of it over-built for one maintainer. MG and MS do not. G0 wanted M2 split into M2a and M2b.
- **Claim index.** G0 said to serve the provenance/claim index. GG now says full claim traceability is overbuilt and should be staged. The same model and persona gave opposite advice, so treat this as an author call (see X-26).
- **Human review of high-impact items.** GG, GS and G0 ask for it. Author decision 1 removes routing of machine judgement to the author, so the reference-answer set becomes the only human check (see X-01).

MS has several misreadings, listed in section 6.

## 2. Convergent themes

Count is out of the four reviewers. "New" means not in the ledger.

| # | Theme | Raised by | Count | In ledger? |
|---|---|---|---|---|
| A | LLM-as-judge validation: sample size, strata, calibration, correlated errors, gold set, drift | GG, GS, MG, MS (weak) | 4 | Yes: W1-04, W1-30, W1-50, W1-71, W1-01 (raw responses). Residual is new: X-01 |
| B | Author review load and cost model | GG, GS, MG, MS | 4 | Yes: W1-05, W1-39, W1-46, W1-52. Largely moot after decision 1 |
| C | Legal, terms, licence layers, personal data, takedown | GG, GS, MG, MS | 4 | Partly: W1-29, W1-56, W1-36, W1-37. New parts: X-07 to X-10 |
| D | One-person continuity: backups, succession, credentials, drift to 2030 | GG, GS, MG, MS | 4 | Partly: W1-22 (second copy), W1-21 (adapter pin), W1-71 (model retirement). New: X-24, X-25 |
| E | Provenance standard (PROV, RO-Crate, DataCite, Frictionless) | GG, GS, MG, MS | 4 | Partly: W1-65 (Frictionless, DataCite). PROV mapping new: X-12 |
| F | Time model: more than two times, K eligibility per row type, overlays | GG, GS, MS (recorded_at), MG (event-time uncertainty) | 4 | Partly: W1-06, W1-34, W1-36, W1-66, W1-67. New: X-13, X-14, X-28 |
| G | Entity resolution: depth-one equality, clusters, external id trust | GG, GS, MG (thresholds only) | 3 | Mostly: W1-31, W1-33, W1-62, W1-30. New: X-15 |
| H | Recall estimate weak (n=40, visibility bias, blind list, strata) | GG, GS, MG | 3 | Partly: W1-27. New: X-16, X-17 |
| I | Soft tests not testable; neutrality wording | GG, GS, MS | 3 | Barely: W1-54 (C8 only). New: X-19, X-20 |
| J | Document/edition/translation/mirror model | GG, GS, MG | 3 | Mostly: W1-44, W1-14, W1-18, W1-51, W1-38 |
| K | Target-schema dependence; milestone tags | GG, GS | 2 | Yes: W1-01, W1-10, W1-54. Recurrence rule new: X-27 |
| L | Publisher missing on `lines` (F1 "carries" vs storage) | GG, GS | 2 | Only speaker (W1-12, W1-49). New: X-04 |
| M | Reproducibility overclaimed when bytes cannot be redistributed | GG, GS | 2 | Partly: W1-28. New: X-18 |
| N | Storage too intricate for one maintainer | GG, GS | 2 | Partly: W1-53, W1-08. New specifics: X-22 |
| O | "No automatic judgement" vs deterministic and LLM admission | GG (GS on neutrality) | 1-2 | Yes: W1-24. Table form new: X-02 |

Agreement from G0: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O all appear there too, plus a security threat model and cost-model variables.

## 3. Sharp individual catches

| Catch | Who | In ledger? |
|---|---|---|
| A prose sentence carrying several assertions collides with the `(sha256, locator)` uniqueness rule in storage §1 | GS | New: X-03 |
| `lines` has no publisher column, so joint publications, commissioned reports, annexes and quoted speakers cannot be attributed at line level | GG, GS | Speaker only (W1-12); publisher new: X-04 |
| Finance model omits guarantees, mobilised private finance, co-financing, repayment, refinancing, cancellation, grant element; "pledge" is not an IATI transaction type; agreement, operation and tranche are conflated; cross-currency totals will often be impossible | GG | Partly: W1-35 (states and 'reported'), W1-68. New: X-06 |
| Storage contradictions: `projects.aliases` is a list although no column may hold a list; `groups` is a single foreign key though a line can sit under several headings and notes; `GLB` as a pseudo-country; country-year sharding for rows whose country is inferred | GG | List-column class seen in W1-08 (justification_line_ids); these four are new: X-22 (verify first) |
| Equality that is not transitive is "pairwise evidence", not equality: store pairwise judgements, cluster at a threshold, version clusters | GG, GS | W1-31 keeps depth one with a validator; the challenge to the rationale is new: X-15 |
| "An external identifier decides" is too strong (IATI ids reused for umbrella programmes, LEI branches, ROR gaps) | GS (G0) | New. Conflicts with W1-24, which blesses "same external identifier" as an adoptable rule. X-15 |
| Can a correction overlay include a line extracted after K from a snapshot retrieved before K? | GS | New: X-14 |
| Document text goes to LLM vendors: retention, training, source terms; per-source "do not send" flag | GG, GS (G0) | New: X-07 |
| Adversarial fixtures beyond one planted instruction: hidden text, white-on-white, overlays, annotations, OCR versus text-layer conflict | GS (G0 adds sandboxing) | W1-55 covers one planted instruction only: X-11 |
| Weekly snapshots to 2030 multiply restatements; use adaptive cadence | GS | W1-14 handles no-op detection, not cadence: X-25 |
| Public page called "Statements" shows D3 observations while builders call D2 lines statements | GS (G0) | New: X-21 |
| Normative text holds machine details (`~/.local/bin/uv`, ssh host names, named llama service) | GG | New: X-23 |
| Q16 "no findings in own voice" contradicts F8 and collection §3 findings (not published, stopped by cap, traceability rate) | GS | New: X-20 |
| Layered licence (own contributions open; publisher text as quoted data; bytes under source terms) | GS | Yes: W1-29, W1-56 |
| Distinguish restatement (same content) from correction (changed content) | MG | Yes: W1-14, W1-38 |
| Recall: use capture-recapture or channel overlap as a second estimator | GG, MG (G0) | New: X-17 |
| Inclusive threshold "any confidence" is a stress test, not an estimate | GS, MG (thresholds) | Yes: W1-30 |
| Published figure may lose caveats; show exclusions beside affected figures | GG | New: X-26 |
| Single-fetch past robots rules, and the author's browser session or cookies, need human-approved policy | GG (G0) | W1-29 (C6 conflict) partly: X-08 |
| Containerise dependencies | MG | Contradicts W1-21 ("no container"); author call, not listed |

## 4. Moot or reshaped by the two author decisions

Decision 1 (no machine judgement routed to the author; two local readers of different families, arbiter on OpenRouter; stance, likelihood, confidence on every item, served sorted by confidence; readers selected and calibrated on held-out reference answers):

- Moot or mostly moot: external asks for an author sample size and cap (GG #5, GS 2.2, MS "10% with floor 10", G0); the open question in extraction §14; MG's "outsource adjudication to experts"; MS "at least two vendors" (met by two families plus arbiter); MG's "benchmark before M3b" (met in intent by calibration before use); GS's local versus paid pilot.
- Ledger rows to reword: W1-04 (disagreement becomes arbiter escalation; the audit set becomes the reference set), W1-05 (author hour totals and deferral as the only valve lose force; GPU and arbiter time replace them), W1-20 (the row-level argument changes; the run-output gate stays), W1-39 (M3b queue is machine time and spend), W1-52 (hosted-reader cost figure replaced by local readers plus arbiter and calibration spend; the ledger header records only USD 0.36 left on OpenRouter, so calibration and arbiter budget needs an explicit line), W1-24 (N4 and F7 now say the panel, not the author, is the gate in almost every case).
- Not mooted, sharper: correlated error. Two local families plus an arbiter still share training-data overlap. The reference set must measure agree-but-wrong directly (X-01). Document text still reaches OpenRouter providers (X-07).
- Reviewers' "human review of all high-impact items" (GG, GS, G0) cannot be met; say so in requirements and put the compensating control in X-01.

Decision 2 (fixed field lists per class; classification gains target, event, decision and grows by panel proposal; amounts as printed at M2):

- Resolves the author-decision part of W1-12 and the typed-span question. Keeps W1-40 and W1-13 open.
- Leaves GS's multi-assertion sentence (X-03) and opens an adoption rule for panel-proposed classes (X-05).
- Defers GG's currency and finance points to M3b (X-06 is M3b).

## 5. New findings for the ledger

Severity is blocker, major or minor. "Verify" means the reviewer's claim was not checked against the current text.

| ID | Files | Sev | Milestone | Fix (one line) | Sources |
|---|---|---|---|---|---|
| X-01 | jetp-extraction.md §6.3, §12; jetp-requirements.md Q5, Q17; jetp-operation.md §5 | major | M2 | Specify the held-out reference-answer set as the only human check: size, strata (country, language, class), frozen per method version, refresh after any model change, disjoint from prompt tuning, and report agree-but-wrong rate and calibration error in every release. Decision-derived; extends W1-04, W1-30, W1-71 | GG, GS, MG, MS, G0 |
| X-02 | jetp-requirements.md N4, F7, Q5; jetp-fusion.md §1, §3; jetp-collection.md §9; jetp-operation.md §5 | major | M2 | Add one decision-authority table (decision type by: adopted deterministic rule, panel with arbiter, author; state that counts as in force; what each downstream use accepts; how reversed) and reword N4 to match. Extends W1-24 | GG (G0) |
| X-03 | jetp-extraction.md §3, §4; jetp-ledger-storage.md §1 (lines, locator uniqueness) | major | M2 | Define one prose line per span with the class's fixed field list, or an assertion index in the locator when one span carries several assertions; add a validator test | GS |
| X-04 | jetp-requirements.md F1; jetp-ledger-storage.md §1 (lines, document-publishers); jetp-ontology.md §2 Document; jetp-extraction.md §4 | major | M2 | Say F1 "carries" means derived through document-publishers; add nullable line-level publisher for joint documents, annexes and commissioned reports, and a speaker column; validator requires it when a document has more than one publisher | GG, GS, G0 |
| X-05 | jetp-extraction.md §3, §6.3; jetp-ledger-storage.md §1 (lines.classification) | major | M2 | Set the adoption rule for panel-proposed classes: proposals are candidates, adoption bumps the method version and lists earlier lines for re-read, list stays closed between bumps. Decision-derived; no external source | decision 2 |
| X-06 | jetp-ontology.md §2 Agreement, §4; jetp-fusion.md §5, §7; jetp-requirements.md F14, F19 | major | M3b | Add a finance-instruments section (guarantee exposure, mobilised private finance, co-financing, repayment, cancellation, refinancing, grant element) mapped to IATI and CRS or declared out of scope; separate agreement, operation and tranche; state that cross-currency totals are often impossible. Verify | GG |
| X-07 | jetp-extraction.md §6.3; jetp-operation.md §5, §6; jetp-collection.md §1 | major | M2 | Add a per-source flag `llm_send` taken from the terms position of W1-29; sources that forbid third-party processing go to local readers only; record provider retention and training policy for the arbiter route | GG, GS, G0 |
| X-08 | jetp-collection.md §1, §8; jetp-requirements.md C6 | minor | M3a | Permit archive capture and registered-session fetches only where the recorded terms position allows; log the route; human-approve the robots-override policy once | GS, GG, G0 |
| X-09 | jetp-extraction.md §3, §4; jetp-results.md §5 | minor | M2 | Extend W1-56: release screen also lists person-like names in speaker and verbatim fields; record office, not name, unless printed as signatory; name the takedown route (W1-37) | GG, GS, G0 |
| X-10 | jetp-collection.md §9; jetp-extraction.md §7; jetp-requirements.md N13 | minor | M3a | Add a disposition for a document later found non-public or leaked: bytes removed from store and release, hash and reason kept, note the git-history limit | MS |
| X-11 | jetp-operation.md §2, §3, §6; jetp-extraction.md §5, §12 | minor | M2 | Run parsers and renderers without network and outside the credential environment, disable macros and external links; add §12 fixtures for hidden text, white-on-white, overlays, annotations, OCR versus text-layer conflict | GS, G0 |
| X-12 | jetp-ontology.md §0, §5; jetp-language.md (ODEM); jetp-results.md §5 | minor | M3b | Add one table mapping ledger objects to PROV Entity, Activity, Agent and the core relations (run as Activity, method as Agent); no PROV engine, no RDF | GG, GS, MG, MS |
| X-13 | jetp-ledger-storage.md §1; jetp-fusion.md §8; jetp-results.md §2, §4, §9; jetp-collection.md §11 | minor | M2 | Add a temporal contract table: per ledger table and result, which of event, publication, retrieval, recorded_at and decided_at it holds, and whether it is eligible for K and for a correction overlay. Extends W1-06, W1-34, W1-36 | GG, GS, G0 |
| X-14 | jetp-fusion.md §8; jetp-results.md §9; jetp-requirements.md F10 | minor | M3b | State that an overlay admits only supersession rows on rows recorded on or before K; a line extracted after K from a snapshot retrieved before K belongs to the next release; add a check row | GS |
| X-15 | jetp-fusion.md §3; jetp-ontology.md §2 External identifier; jetp-requirements.md F12 | minor | M3b | Give the reason for depth-one equality (pairwise evidence, clustering at threshold, chains raised as conflicts); make an external identifier decisive only for schemes declared compatible in granularity (resolves the clash with W1-24); name the cluster metric (for example B-cubed) | GG, GS, G0 |
| X-16 | jetp-collection.md §6; jetp-requirements.md Q10, DA8 | minor | M3a | Hash the known-item list before round one, compiled apart from the searches; report recovery per country, publisher class, type and language; call the public figure "known-item recovery", not recall. Extends W1-27 | GG, GS, MG, G0 |
| X-17 | jetp-collection.md §7; jetp-requirements.md Q10 | minor | M3b | Decide whether a second estimator (capture-recapture or overlap across independent channels) moves from later into M3b; author call | GG, MG, G0 |
| X-18 | jetp-results.md §4, §7; jetp-requirements.md Q8, F27, F30 | minor | M3b | Report per result and per release the share of support by public-copy kind (redistributed bytes, archive capture, live only, login only, none); reword "reproducible" to internal reproducibility plus external inspectability. Extends W1-28 | GG, GS, G0 |
| X-19 | jetp-requirements.md F26, Q13, Q16, Q18, Q21, C8, §6 | minor | M3b | Give each soft test a finite checklist or sampled audit with size and failure rule, or demote it to a principle; define "substantive narrative claim" | GG, GS, MS, G0 |
| X-20 | jetp-requirements.md Q16, F8; jetp-collection.md §3; jetp-results.md §4 | minor | M3a | Reword Q16 to "asserts only documentary, procedural and declared-calculation findings; no compliance, blame, merit or cause", with allowed and disallowed wording for gaps | GS, GG |
| X-21 | jetp-presentation.md (Statements page); jetp-language.md | minor | M3b | Rename the public page (for example "Attributed observations") or state the D2/D3 mapping in the glossary; author naming call | GS, G0 |
| X-22 | jetp-ledger-storage.md §1 (projects.aliases, groups, GLB, shard rule) | minor | M2 | Verify, then: alias rows instead of a list column; allow a parent group or group chain; declare GLB as a scope code; shard by the row's own field. W1-08 is the same class | GG |
| X-23 | jetp-operation.md §2, §3, §9 | minor | M2 | Move host names, binary paths and named services to a runbook; keep roles (bulk readers, arbiter route, backup host) in the spec | GG |
| X-24 | jetp-requirements.md C1, C10; jetp-operation.md §9, §11; jetp-results.md §12 | minor | M3b | Require a handover note before the first release identifier: credential locations, ownership of repository, Zenodo and domain, restore steps; a named deputy for takedown and withdrawal only | GG, GS, MG, MS |
| X-25 | jetp-operation.md §11; jetp-collection.md §10; jetp-requirements.md DA11 | minor | M4 | Add a drift register (sources, schemas, models, terms, ontology) reviewed each release, and adaptive snapshot cadence by observed change rate | GS, MG, MS |
| X-26 | jetp-presentation.md; jetp-results.md §8, §10; jetp-requirements.md Q6, Q7 | minor | M3b | Show "what this dataset does not say" beside affected figures; limit M3b traceability to tables, figures and headline metrics; decide once whether the display-to-result map is served | GG (G0 opposite) |
| X-27 | jetp-ledger-storage.md §1 (target list); jetp-requirements.md §2.2, C8 | minor | M2 | Rule: no requirement counts as met for a milestone while a column or table it needs is still tagged target; add a "needed by" column. Stops W1-01 recurring | GG, GS |
| X-28 | jetp-fusion.md §7; jetp-results.md §2 | minor | M3b | Label an account's residual by cause (overlapping intervals with no decomposition, open lower bound) and count each cause. Extends W1-67 | MG |
| X-29 | jetp-requirements.md §4 | minor | M3b | Add one paragraph placing the Observer against CPI and other climate-finance trackers, OECD CRS, IATI, and PREMIS and PROV for preservation and provenance; author may decline | MG |
| X-30 | jetp-ontology.md §3 party_in; jetp-fusion.md | minor | M3b | Verify that a partner's withdrawal or a lapsed partnership is a dated end of a `party_in` row and a documentary event; add a test case | MS |
| X-31 | jetp-language.md | minor | M2 | Check that locator, knowledge cutoff, referent and match threshold are defined there and add any missing | MS |

## 6. Low weight or discard

MS points the ledger should not import:

- "Add a rule that external identifiers decide party identity": it already exists; GG, GS and G0 say it is too strong (X-15).
- "Add non-requirement N14: legal review out of scope": opposite of GG, GS, MG and W1-29.
- "Up to 11,500 disagreements (100 per document)": misreads 100 items per run.
- "Revise the LLM budget to USD 0.50 per document": USD 3 is a per-document cap, not an estimate (W1-52).
- "doudou launches a deferred run when padme is down": data flows padme to doudou only.
- "Locator circularity": W1-02 already puts the rule in extraction §5.
- "Export the ledger as PROV-O": overshoots; X-12 asks for a mapping table only.

MG points outside the ledger's direction: "containerise" (W1-21 chose no container), "known-item list at least 100" (W1-27 already ties a lower-bound gate to about 80 items), "deputy makes decisions" (conflicts with decision 1; X-24 limits the deputy to takedown).

G0 only, not listed as X: split M2 into M2a and M2b (an author scoping choice; W1-01, W1-05 and X-27 already reduce the dependency), "authoritative version is itself a translation" edge case.
