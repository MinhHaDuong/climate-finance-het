# Specification review wave 1: findings ledger

Specification at commit 7f3368b5 (main, 2026-09-30). Seven lenses (within-file, cross-file, state of the art, data held, data to come, implementation, dead angles), reviewers on Sonnet, each lens verified by a skeptic on Fable, deduplicated by a Fable ledger agent; the throwaway prototype report (branch `spike-spec-prototype`, `spike/REPORT.md`) was an input. The external cross-vendor pass could not run then, the project OpenRouter account having USD 0.36 left; it ran later the same day, and its findings are batch 2 (section "Batch 2: external review").

## Summary

1. The M2 storage contract is the weak point: it cannot hold what extraction, requirements and the pending list require (method and version, dispositions, readings and rejected proposals, run provenance, status and supersedes on lines), and the locator check that gates F1 has no definition; both are blockers to fix before any DDL is written.
2. Twenty further M2 majors cluster into four groups: vocabulary and set definitions (held vs registered, pending list, ordinal, as-of rule, candidate-over-accepted), the assisted-reading loop (disagree undefined, sample without purpose or estimator, unbounded author minutes with deferral as the only valve), the prose and field-list shape the holdings contradict, and operational safety (text-layer retention, single-site backups, run-output gates).
3. M3a is under-specified rather than wrong: the collection records have no tables, the M3a deliverable has no vehicle, admission scope is undefined, the recall estimate reuses its test set, and the legal position on copies and redistribution is unstated.
4. M3b carries consistent but unbuilt machinery: judgements need stance, likelihood and basis on calibrated terms with cluster semantics; party roles, name forms, chronology, cutoff and correction releases each have two contradictory readings; error reports and publisher corrections have no home.
5. About a fifth of the rows need an author decision (sample and precision floors, attention totals, scan transcription, comparator scope at M2, admission scope, recall gate, licence note, inclusive threshold floor, report channel, PR gate for run outputs); the rest are agent-applicable wording, table and cross-reference fixes whose proposals converge across lenses.

## Rows

| ID | Severity | Milestone | Author? | Lenses | Files |
|---|---|---|---|---|---|
| W1-01 | blocker | M2 | yes | within-file, cross-file, state-of-the-art, implementation, data-to-come | jetp-ledger-storage.md §1, §4; jetp-extraction.md §3, §6.3, §7, §9; jetp-requirements.md F1, F2, F5, Q4, Q9, Q17, F23; jetp-language.md D2 |
| W1-02 | blocker | M2 | no | data-held | jetp-extraction.md §5, §6.3, §12; jetp-ledger-storage.md §1 (locator rule) |
| W1-03 | major | M2 | no | within-file, cross-file | jetp-extraction.md §1, §2, §7, §10, §12, §13, §15; jetp-collection.md §2, §11; jetp-language.md (held, disposition); jetp-requirements.md F2, F5, DA2 |
| W1-04 | major | M2 | yes | within-file, cross-file, state-of-the-art, dead-angles | jetp-extraction.md §6.3, §12, §14; jetp-collection.md §9; jetp-operation.md §5, §7.2, §8; jetp-requirements.md Q5, Q17, C1, DA3 |
| W1-05 | major | M2 | yes | within-file, cross-file, data-held, data-to-come, implementation | jetp-extraction.md §6.3, §7 (deferred); jetp-operation.md §7.2, §8, §10, §13; jetp-requirements.md §2.2 M2 row, DA2, DA11, C1; jetp-results.md §4 |
| W1-06 | major | M2 | no | within-file, state-of-the-art | jetp-ledger-storage.md §1 (recorded_at rule, as-of rule, decision tables); jetp-fusion.md §8, §9; jetp-collection.md §9; jetp-requirements.md F10, Q8 |
| W1-07 | major | M2 | no | within-file | jetp-ledger-storage.md §1 (decision row in force); jetp-fusion.md §2, §8, §9; jetp-ontology.md §5 |
| W1-08 | major | M2 | no | within-file, cross-file | jetp-ledger-storage.md §1 (line-referents, relations, adjudications), §4; jetp-fusion.md §3; jetp-results.md §2, §3; jetp-requirements.md F11, Q5, Q11 |
| W1-09 | major | M2 | no | cross-file | jetp-extraction.md §1, §3 (Ordinal), §9; jetp-ledger-storage.md §1 (line_id) |
| W1-10 | major | M2 | no | cross-file, implementation | jetp-requirements.md Q5, Q9, F3; jetp-operation.md §5; jetp-fusion.md §3 Documents; jetp-ledger-storage.md §4; jetp-collection.md §2, §9; jetp-extraction.md §2 |
| W1-11 | major | M2 | no | within-file, implementation | jetp-requirements.md DA2, Q1; jetp-operation.md §7.1; jetp-ledger-storage.md §3 |
| W1-12 | major | M2 | yes | data-held | jetp-extraction.md §3, §4, §6.3; jetp-ledger-storage.md §1 (line-field-specs) |
| W1-13 | major | M2 | no | data-held | jetp-extraction.md §3 (Verbatim fields), §11, §12; jetp-ledger-storage.md §1 (line-field-specs); jetp-requirements.md Q1 |
| W1-14 | major | M2 | no | data-held, data-to-come | jetp-extraction.md §8, §13; jetp-fusion.md §3 (proposer 2); jetp-ledger-storage.md §1, §3, §4; jetp-requirements.md F4, F13, DA11 |
| W1-15 | major | M2 | yes | data-held | jetp-extraction.md §5, §6.2, §10, §12, §13; jetp-requirements.md DA2, DA10, Q1, Q3 |
| W1-16 | major | M2 | yes | data-held | jetp-ledger-storage.md §5; jetp-extraction.md §6.4, §7, §15; jetp-requirements.md DA4, DA5, F1, OBS-1 |
| W1-17 | major | M2 | no | data-held, implementation | jetp-extraction.md §3, §4, §6.2, §6.3, §9, §12; jetp-operation.md §5 |
| W1-18 | major | M2 | no | state-of-the-art, data-held | jetp-fusion.md §3 Documents (proposers), §5; jetp-extraction.md §2, §7, §13, §15; jetp-requirements.md F3, DA5 |
| W1-19 | major | M2 | no | implementation | jetp-requirements.md Q1, Q4, Q17, DA2; jetp-extraction.md §3, §10; jetp-ledger-storage.md §1 (identifier families) |
| W1-20 | major | M2 | yes | implementation | jetp-operation.md §4 (Gates); jetp-ledger-storage.md §3; jetp-requirements.md Q19 |
| W1-21 | major | M2 | no | implementation, dead-angles | jetp-extraction.md §1, §5, §9, §12; jetp-operation.md §2, §9; jetp-ledger-storage.md §1 (derived); jetp-requirements.md F1, Q1, Q8, C10 |
| W1-22 | major | M2 | yes | dead-angles | jetp-operation.md §9; jetp-requirements.md C2, N13, F1, Q1, Q8 |
| W1-23 | major | M3a | no | within-file | jetp-ledger-storage.md §1 (coverage, dry-searches, retrievals.collection_method, documents); jetp-collection.md §3, §8, §9, §10; jetp-requirements.md DA6, F27, C6 |
| W1-24 | major | M3a | no | within-file | jetp-fusion.md §1 (Judgement, not automation), §3 (Organisations, Documents proposers); jetp-collection.md §1, §9; jetp-requirements.md N4, F7; jetp-operation.md §4; jetp-extraction.md §8; jetp-ledger-storage.md §4 |
| W1-25 | major | M3a | no | within-file, cross-file | jetp-requirements.md §2.2, F9, DA9, C6, Q10; jetp-results.md §4, §13; jetp-collection.md §5, §7, §11, §12 |
| W1-26 | major | M3a | yes | cross-file | jetp-collection.md §9; jetp-requirements.md §2, N2, N12, N13, F13, DA12, F2, F27; jetp-extraction.md §7 (out_of_scope); jetp-language.md |
| W1-27 | major | M3a | yes | state-of-the-art | jetp-collection.md §5, §6; jetp-requirements.md Q10, DP-1 |
| W1-28 | major | M3a | no | dead-angles | jetp-requirements.md F27, C6, DA9, Q8, DP-4; jetp-results.md §7; jetp-operation.md §11; jetp-extraction.md §8; jetp-collection.md §10 |
| W1-29 | major | M3a | yes | dead-angles, cross-file | jetp-results.md §6, §7; jetp-requirements.md F27, F30, C6, DA9, Q21; jetp-ledger-storage.md §1 (documents, retrievals, line-fields); jetp-language.md (public access route) |
| W1-30 | major | M3b | yes | state-of-the-art, cross-file | jetp-fusion.md §1 (Calibrated language), §3; jetp-results.md §3; jetp-requirements.md F11, Q5, Q11; jetp-ledger-storage.md §1 |
| W1-31 | major | M3b | no | state-of-the-art | jetp-fusion.md §3 (candidate match, proposers, tiers); jetp-ledger-storage.md §1, §3, §4; jetp-extraction.md §3 |
| W1-32 | major | M3b | no | within-file | jetp-ontology.md §2 (Party, Asset), §3 (party_in, role_in); jetp-ledger-storage.md §1 (assets.operator_party_id); jetp-requirements.md F17, F20, SP-2 |
| W1-33 | major | M3b | no | within-file | jetp-ontology.md §2 (party name forms); jetp-fusion.md §3 Organisations; jetp-ledger-storage.md §4 (fold, routes); jetp-requirements.md F12 |
| W1-34 | major | M3b | no | cross-file | jetp-collection.md §11; jetp-fusion.md §1; jetp-results.md §2, §4, §6; jetp-requirements.md F10 |
| W1-35 | major | M3b | no | within-file, cross-file | jetp-fusion.md §4 (bullet 5), §7, §9; jetp-ontology.md §4; jetp-requirements.md F14, F19; jetp-results.md; jetp-language.md ('reported'); jetp-extraction.md §11 |
| W1-36 | major | M3b | no | within-file, data-to-come, dead-angles | jetp-results.md §1, §4, §6, §9, §10, §14; jetp-ledger-storage.md §1 (as-of rule); jetp-fusion.md §8; jetp-requirements.md F10, F25, F28, F29, Q7, Q8, BK-2 |
| W1-37 | major | M3b | yes | cross-file, data-to-come, dead-angles | jetp-requirements.md F25, OBS-7, N2, N13, F23; jetp-ledger-storage.md §1; jetp-operation.md §4; jetp-results.md §9; jetp-fusion.md §2; jetp-presentation.md |
| W1-38 | major | M3b | no | data-to-come, dead-angles | jetp-fusion.md §2, §5, §8; jetp-ledger-storage.md §1 (adjudications.decision_type); jetp-ontology.md §3, §4; jetp-collection.md §10; jetp-requirements.md F6, F22, LP-2, OBS-5 |
| W1-39 | major | M3b | yes | implementation | jetp-extraction.md §11 (Methods); jetp-fusion.md §3; jetp-operation.md §7; jetp-requirements.md F11, DA12, C1 |
| W1-40 | minor | M2 | no | within-file | jetp-extraction.md §1, §3 (Classification), §6.1; jetp-ledger-storage.md §1 (lines.classification) |
| W1-41 | minor | M2 | yes | within-file | jetp-spec.md (Structure); jetp-ontology.md §0, §5; jetp-ledger-storage.md §1 |
| W1-42 | minor | M2 | no | within-file | jetp-ontology.md §3 (same_as, cites rows), §5; jetp-ledger-storage.md §1 (relations.relation) |
| W1-43 | minor | M2 | yes | within-file | jetp-spec.md (State column); jetp-language.md; jetp-ontology.md; jetp-ledger-storage.md §1; jetp-presentation.md (header); jetp-requirements.md (dated status, DA note) |
| W1-44 | minor | M2 | no | cross-file, state-of-the-art | jetp-ontology.md §2 (Document), §3 (edition_of); jetp-collection.md §5, §10; jetp-extraction.md §2, §8; jetp-fusion.md §2, §3; jetp-ledger-storage.md §1 (documents.edition_of), §4; jetp-language.md (retired terms) |
| W1-45 | minor | M2 | no | cross-file | jetp-collection.md §1, §2, §8, §11; jetp-operation.md §10; jetp-ledger-storage.md §1 (retrievals.collection_method); jetp-extraction.md §5; jetp-requirements.md F27, C6 |
| W1-46 | minor | M2 | no | cross-file | jetp-operation.md §8; jetp-collection.md §10; jetp-requirements.md DA6, Q15, AED-3; jetp-results.md §4 |
| W1-47 | minor | M2 | no | data-held | jetp-requirements.md DA3; jetp-extraction.md §4, §6.1, §6.3 |
| W1-48 | minor | M2 | no | data-held | jetp-extraction.md §3 (own status word and axis); jetp-ontology.md §4 (status-crosswalk) |
| W1-49 | minor | M2 | no | data-held, data-to-come | jetp-extraction.md §4 (page furniture), §11 (Timings); jetp-collection.md §11; jetp-ledger-storage.md §1 (documents.published_date, snapshots); jetp-requirements.md F9, F16, OBS-1 |
| W1-50 | minor | M2 | no | data-to-come | jetp-requirements.md Q17, §3.7 AEDIST, DP-2; jetp-extraction.md §6.3; jetp-operation.md §8 |
| W1-51 | minor | M2 | no | data-to-come | jetp-ledger-storage.md §1 (lines.sha256 validator rule, documents.url); jetp-extraction.md §2, §7; jetp-collection.md §10, §11 |
| W1-52 | minor | M2 | yes | implementation | jetp-operation.md §5, §7.1, §7.2, §13; jetp-requirements.md C3 |
| W1-53 | minor | M2 | no | implementation | jetp-ledger-storage.md §1 (file ceiling, line-fields), §3 |
| W1-54 | minor | M2 | no | implementation | jetp-requirements.md Q14, Q15, DA4, DA6, C8, §9; jetp-operation.md §1, §8, §10; jetp-extraction.md §6.4; jetp-ledger-storage.md §1 (documents) |
| W1-55 | minor | M2 | no | dead-angles | jetp-extraction.md §5, §6.3, §12; jetp-collection.md §9 |
| W1-56 | minor | M2 | no | dead-angles | jetp-extraction.md §3 (Verbatim fields), §4 (Declared scope); jetp-results.md §5; jetp-requirements.md N2, F25 |
| W1-57 | minor | M3a | no | within-file, cross-file | jetp-collection.md §1, §3 (verdict table), §5, §7, §8, §13; jetp-requirements.md F8, DA9; jetp-extraction.md §7 |
| W1-58 | minor | M3a | no | within-file | jetp-collection.md §4 (class table), §5 (stopping rule), §6, §7 |
| W1-59 | minor | M3a | no | cross-file, dead-angles | jetp-collection.md §7 (traceability rate); jetp-requirements.md Q10, F19, DP-1; jetp-results.md §2, §4; jetp-fusion.md §5 |
| W1-60 | minor | M3b | no | within-file, cross-file | jetp-requirements.md Q20, §9 table; jetp-presentation.md; jetp-operation.md §8, §11; jetp-results.md §5, §10; jetp-ledger-storage.md §4 |
| W1-61 | minor | M3b | no | within-file | jetp-ontology.md §2 (timings), §4, §5; jetp-extraction.md §11; jetp-ledger-storage.md §1 (date_role rule) |
| W1-62 | minor | M3b | no | state-of-the-art | jetp-results.md §3, §14 (check 3); jetp-presentation.md |
| W1-63 | minor | M3b | no | state-of-the-art | jetp-fusion.md §1 (Pedigree; Independence of publishers), §5; jetp-requirements.md C8, F19 |
| W1-64 | minor | M3b | no | state-of-the-art | jetp-ontology.md §5 (status-crosswalk, sector-crosswalk, terms, Traceability); jetp-results.md §2; jetp-requirements.md F14 |
| W1-65 | minor | M3b | yes | state-of-the-art | jetp-results.md §5, §6; jetp-requirements.md F29, F31 |
| W1-66 | minor | M3b | no | cross-file | jetp-requirements.md F16, §9 table; jetp-extraction.md §11; jetp-fusion.md §4, §7 |
| W1-67 | minor | M3b | no | data-held | jetp-ontology.md §4 (flow, timings); jetp-extraction.md §11, §15; jetp-fusion.md §4, §7; jetp-requirements.md OBS-1, F19 |
| W1-68 | minor | M3b | no | data-held | jetp-extraction.md §11 (How many); jetp-ledger-storage.md §1 (rates); jetp-requirements.md F14, F15 |
| W1-69 | minor | M3b | no | data-to-come | jetp-results.md §8, §9 (check table); jetp-presentation.md (provenance index); jetp-requirements.md N11, BK-2, Q7, F29, F23 |
| W1-70 | minor | M3b | yes | implementation | jetp-results.md §2; jetp-fusion.md §7; jetp-ledger-storage.md §1 (marker-coefficients, deflators, flow_coverage roles); jetp-presentation.md (Money page); jetp-requirements.md §4.4, C8, OBS-1, F14, F19, Q11 |
| W1-71 | minor | M3b | no | dead-angles | jetp-operation.md §5, §7.1; jetp-extraction.md §1, §6.3, §12; jetp-requirements.md Q4, Q9, Q17, Q18, Q19 |

### W1-01 (blocker, M2)

**Finding.** The M2 tables cannot hold what the M2 rules require. `lines` has no method, method_version, run, adapter version, hidden flag, status or supersedes although extraction §3 and §9 require them; no table holds dispositions (extraction §7, the pending list, F2, F5, DA2), reader and checker readings, rejected proposals with reason and step at fault (§6.3, Q17), or the run record that makes an LLM reading replayable (dated model, routed provider, prompt hash, sampling, cost). A builder would invent columns.

**Fix.** In storage §1 [M2]: (a) `lines` gains method, method_version, run_id, adapter_version, hidden, status, supersedes; (b) a `dispositions` table (disposition_id, document_id, sha256 nullable, kind, reason, method, method_version, decided_by, decided_at, recorded_at, status, supersedes) under the in-force rule; (c) a `readings` table (reading_id, run_id, sha256, line_id nullable, role reader|checker|author, llm_id, prompt_version, proposed locator and label, stance, likelihood, confidence, quoted basis, outcome, rejected_step, recorded_at); (d) a `runs` table as the structured twin of operation §8's run report (run_id, job, commit, machine, start, end, method, method_version, prompt hash, LLM and provider, sampling, adapter version, spend, review minutes), with run_id on observations and decision tables; raw responses under their hash in the document store. Validator: an assisted-reading line has one reader and one checker row. Update language D2, storage's M2 tag list and F23.

**Author decision.** Where do readings and run records live? (a) ledger CSV tables served or named not-served under F23, with a `runs` table; (b) DVC-tracked JSONL per run with only a run_id column on `lines` and the run report as the record; (c) tables for readings, no `runs` table (operation §8's committed report suffices). Recommended: (a); Q17 serves readings and AED-2/3 need them joinable, and a `runs` row is cheap.

**Outcome.** decided by the author 2026-09-30: option (a): `readings` and `runs` as append-only journals in the storage contract's target schema, `run_id` plus method and version on lines, observations and decision tables, raw model responses stored under their hash beside the document bytes; exit criteria added to ticket 1702; applied in "docs(jetp): storage contract gains readings and runs journals and the ontology tables" and "docs(jetp): no ticket numbers or dates in normative text; History lines and index states" (language). Parts (a) and (b) landed by half: the `dispositions` table and the `status`, `supersedes`, `hidden` and `adapter_version` columns of `lines` were written in wave 2 ([W2-01](../wave-2/ledger.md)).

### W1-02 (blocker, M2)

**Finding.** The locator check, the gate of F1 and of the planted-item control, is undefined: no window, no normalisation, no rule for page furniture or folio, an 80-character cap LLMs miscount, no handling of labels split by a footer box. Rejections happen before the checker sees them, so 22 of 28 'missed' items in one spike run were the pipeline's own rejections. 185 of 13,092 existing locators exceed 80 characters and 261 hand-made lines have paraphrase locators that cannot resolve.

**Fix.** State the rule once in extraction §5 and cite it from storage §1: a prose locator is page index plus start and end anchors derived by code from the reader's verbatim quote after whitespace normalisation and declared furniture removal, unique in the text layer or carrying an occurrence index; folio recorded only when the adapter reads it. Reorder §6.3: reader, derived locator, one repair call, checker sees every proposal with failures marked, missed list de-duplicated against proposals and rejections. Locators admitted before the rule stay valid under their method version and replay lists them as outside its reach; the validator enforces the new syntax on new lines only.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-03 (major, M2)

**Finding.** 'Held' is defined as admitted with a snapshot, yet extraction gives a held document with no bytes the disposition `no_snapshot`, so the 23 snapshot-less documents of the 392 are outside every rule and DA2's test ('every one of the 392 satisfies F2') cannot be decided. Collection §11 names the same state a third way ('recorded access outcome'). The pending list is defined on snapshots, but `duplicate`, `translation_not_canonical`, `out_of_scope` and `no_snapshot` are document-level, so a duplicate's snapshot never leaves the pending list and F5 and idempotence cannot hold.

**Fix.** Use 'registered' in extraction §1, §7, §10, §13 and the §15 row ('A registered document has no bytes'); 'held' only for having a snapshot. Widen §7's opening and language's 'disposition' row to 'a registered document, or a snapshot of a held one'. Collection §11: the recorded access outcome is the disposition `no_snapshot` whose reason cites the latest retrieval status. Define pending once in §2: a snapshot with no statements, no snapshot-level disposition, whose document has no document-level disposition; cite from §7, §12 and F5; add the §12 control that a run over a `duplicate` document leaves nothing pending.

**Outcome.** fixed in fd7c1f4c.

### W1-04 (major, M2)

**Finding.** 'Disagree', the trigger of the author's review, is defined nowhere (the spike invented 'stance other than right, or likelihood below likely'). The random sample of agreed rows has no size rule, no stated purpose, no estimator and no acceptance criterion, and a sample that is the residue of a 100-item cap is zero when disagreements fill it. Two-vendor agreement is treated as accuracy although LLM errors are correlated and the checker ratifies rather than reads; the agree-but-wrong rate is unmeasured. DA3 says 'row-by-row review' while Q5 says a bounded share.

**Fix.** In extraction §6.3: (a) disagree = checker stance not 'right', or likelihood below `likely`; (b) the sample is a method parameter with a stated default (fixed-size audit per document class, floor per document, seed recorded in the run report), and the author's decisions on it are a labelled audit set from which each run reports the precision of the agreed stratum with a Wilson interval, per language and class, feeding the M3b cost record and AED-2; (c) a reopen rule sends the agreed stratum to full review or defers when the lower bound falls under a declared floor; (d) de-duplicate the checker's missed list against proposals and rejections; (e) add to §12 a planted misreading the checker must flag and a small author-read sample of in-scope passages for recall. Point collection §9 and operation §5 at §6.3; reword DA3; close §14; drop the kappa clause.

**Author decision.** Set the audit parameters: sample floor per document (options: 3, 10, or a share such as 10% with floor 3) and the per-class precision floor that reopens a stratum (options: 90%, 95%). Recommended: floor 3 per document drawn to a target interval width, precision floor 95% lower bound per class, revisited after the first two logged sittings.

**Outcome.** resolved by the author's rule of 2026-09-30 (autonomy; no author audit), in the commit "docs(jetp): autonomy correction, no machine judgement routed to the author" (branch `t1710-autonomy-correction`). Its item (e), a sample for recall, went with that rule; recall is measured on the held-out set from wave 2 ([W2-08](../wave-2/ledger.md)).

### W1-05 (major, M2)

**Finding.** Author attention is the binding constraint and nothing bounds it. The spike projects 7,000 to 12,000 proposals and 58 to 210 author hours for the 115 pending documents against 3 hours a week and 100 items per run priced at 30 seconds (measured: 1.0 to 1.5 minutes). The only valve is `deferred`, which counts as accounted for with no ceiling, reason list or deadline, so the M2 definition ('every document ends with statements or a recorded disposition') is satisfiable by deferring most of the corpus. DA11 (ten times the volume) is tested by a limit no document names.

**Fix.** Operation §7.2: replace 30 s with provisional rates per item class (disagreement, missed, audit row, class-template approval) until two logged sittings replace them; add a per-document cap and a per-milestone attention total; operation §8 adds an attention ledger line (hours spent, remaining) to every run report. Extraction §6.3 adopts the mechanical filters of W1-02 and W1-04. Requirements §2.2 M2 row and DA2's test: 'the list of deferred documents, by country and type, is part of what the author accepts'; results §4 lists deferred in-scope documents on the coverage report. Add a DA11 test in author minutes at 10x under C1.

**Author decision.** Fix the M2 attention total and the deferral stance. Options: (a) a milestone total (e.g. 40 h) with residue deferred by part and accepted by list; (b) no total, accept the deferred list at milestone review; (c) add a third reader with a two-of-three rule to cut disagreements before setting a total. Recommended: (a) with 40 h provisional, re-set after the first two sittings; (c) goes to a later round once real minutes are logged.

**Outcome.** resolved by the author's rule of 2026-09-30 (autonomy; no author audit), in the commit "docs(jetp): autonomy correction, no machine judgement routed to the author" (branch `t1710-autonomy-correction`).

### W1-06 (major, M2)

**Finding.** The as-of rule is stated wrongly and its key is missing. 'Rows with recorded_at on or before K that are in force' applies in-force on the whole chain and then filters, so a row in force at K but superseded after K vanishes; fusion §8 states it correctly. `line-referents` and `relations` carry `decided_at` and no `recorded_at`, so judgement time and ledger time are conflated; `documents`, `retrievals` and `snapshots` have no admission time or decision row, so 'only what was admitted on or before K' (F10) cannot be evaluated.

**Fix.** Rewrite storage §1: a row is in the as-of state at K when its recorded_at is on or before K and no row with recorded_at on or before K supersedes it; the status test applies to the chain as it stood at K. Add recorded_at (ledger write time, what K uses) to `line-referents` and `relations`; define decided_at as descriptive judgement time. For documents, make admission at M3a a defeasible decision row (status, supersedes) per collection §9; at M2, holding is dated by the earliest retrieval that yielded the snapshot (extraction §3). Add a fusion §9 row and a DDL test: A accepted, B superseding A after K, returns A at K.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-07 (major, M2)

**Finding.** 'An accepted row that any row supersedes is no longer in force' plus 'a terminal candidate is pending' means a proposed revision blanks the adopted judgement before it is adopted, contradicting fusion §2 and §8 ('a proposed revision leaves the judgement in place'). Ontology §5 repeats the gap. A folded document would become pending again and figures would change on any LLM proposal.

**Fix.** In storage §1 and ontology §5: an accepted row is no longer in force once a row that supersedes it is itself accepted or rejected; while its only successor is a candidate, the accepted row stays in force and the candidate is pending. Add a validator test (candidate over accepted: accepted still in force) and a fusion §9 check row.

**Outcome.** fixed in fd7c1f4c.

### W1-08 (major, M2)

**Finding.** Fusion §3 defines a judgement as stance, likelihood, confidence, quoted basis, statements it rests on, who, method, version and time; the decision tables hold one `confidence` column and no stance, likelihood or basis, and `adjudications` has no method, method_version, confidence or justification. Thresholds such as 'likely or more, medium confidence or more' are conjunctions on two scales one column cannot carry. Document judgements are M2 `relations` rows, so the gap is live now. `justification_line_ids` is a list column the no-list rule forbids.

**Fix.** Add stance, likelihood, basis to `line-referents` and `relations` [M2] and to `adjudications` with method, method_version and justification [M3b]; keep `confidence`; keep `status` as the separate workflow axis (an accepted 'different' row is meaningful). Make justification_line_ids rows. State in storage §4 that triage outcomes (collection §9) and checker stances use the same shape, in the M3a triage table and the readings table of W1-01.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-09 (major, M2)

**Finding.** The ordinal is 'position in reading order counted from one', yet extraction never renumbers and a missed item is appended 'under the next ordinal', so a mid-document item must take a duplicate or out-of-sequence ordinal. `line_id` is minted as `<document_id>-<table>-<ordinal>`, so the identifier suffix and the column can diverge. Prose has no defined ordinal or `<table>` segment.

**Fix.** Adopt storage's meaning: `ordinal` is the mint counter in extraction order, never reassigned; delete 'in reading order' from extraction §3 and let the locator carry position. Name the `<table>` segment for prose (for example `text`) in storage §1 so the family covers the 44 pending PDFs.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-10 (major, M2)

**Finding.** Document duplicate, edition and translation judgements carry four milestones: M2 in fusion §3, storage §4, extraction §2 and F3; M3a in collection §2 and §9; M3b in Q5, Q9 and operation §5. Fusion lists proposers 4 and 5 (LLM first-page reading, person) as M2 while storage builds only tiers 1 to 3 at M2. An implementer cannot tell what M2 must fold before extraction.

**Fix.** Adopt storage §4's split as the one tagging: M2 tiers 1-2 deterministic, tier 3 as a bounded candidate list to the author (at most about 30 pairs, sorted by likelihood); tiers 4-5 M3a with the §6.3 checker when discovery brings mirrors. Retag fusion §3 Documents and collection §2; add 'document identity judgements' to the M2 list of Q5 and operation §5; Q9 becomes 'M2 for extraction methods and document judgements, M3a for triage, M3b for the rest'.

**Outcome.** fixed in fd7c1f4c.

### W1-11 (major, M2)

**Finding.** The population counts do not reconcile: DA2 has 254 documents from 253 snapshots and 115 pending with a snapshot; operation §7.1 measures 278 store objects; storage §3 says 'about 8 000 rows today' against 13,089 statements. Cause not established. Q1, DA2's test, the operation budget and the pending list all hang on these figures.

**Fix.** Publish one reconciliation table from a script (documents, documents with snapshot, distinct snapshots, shared snapshots, store objects, snapshots without a store object and their retrieval method, lines, statements per snapshot) and cite it from DA2, operation §7.1 and storage §3; say where `local-record` bytes live; replace 'about 8 000 rows' and 13,089 with the script's figures.

**Outcome.** partly fixed in fd7c1f4c; the counts are reconciled in requirements DA2 and cited, the script that regenerates them is code and left to the implementation.

### W1-12 (major, M2)

**Finding.** About 100 of the 115 pending documents are prose or semi-prose, and the spec has no statement shape for prose: §3 wants a per-document field list, a closed classification and a status word with axis, and never says who declares the field list. In the spike the reader declared it every time; one field name change moved a document from 57/59 kept to 13/46, and two issues of one series got different names so every cross-issue pair read as a change. The speaker of a quoted assertion has no column. `unclassified` was never used in 88 statements. 261 hand-made prose lines already in the record have composed labels and paraphrase locators.

**Fix.** (1) §6.3: scope and field list are set by the method version per document class or series, never proposed by the reader; `line-field-specs` stays keyed per document with the value copied from the class. (2) §4: for prose, the label is the shortest verbatim span carrying the assertion, fields are the class's fixed list (speaker, date, amount as printed), each a verbatim substring; no typed value spans at M2. (3) The reader may answer 'cannot classify'; that is the review-wait state (see W1-41); the closed list grows only by author decision. (4) The reader never sets own_status_axis (W1-49). (5) The 261 legacy lines keep their identifiers under a named legacy method and are re-anchored by supersession when re-read.

**Author decision.** Two scope calls: should the classification list grow now with `target`, `event`, `decision` (the spike's uncovered cases) or only after the author sees cases in the first sittings; and are typed value spans excluded from M2 prose extraction (typing deferred to M3b reading)? Recommended: grow by decision after cases are seen; no typed spans at M2.

**Outcome.** decided by the author 2026-09-30: field lists fixed per document class or series by the method, never by the reader; prose label the shortest verbatim span carrying the assertion, fields verbatim; the line classification list gains `target`, `event` and `decision` now (terms in force), and a reader may answer "cannot classify", the panel proposing new classes that only the author adopts; amounts and dates as printed at M2, typed at M3b; applied in "docs(jetp): prose statement shape, comparator replay, scan transcription and M3b scope".

### W1-13 (major, M2)

**Finding.** The holdings contradict 'under the publisher's own field names as printed': four documents (two Indonesian, two Senegalese annexes) share one parser-chosen list including `estimated_investment_usd_mn`, and vnm-rmp-2023's spec is the union of at least three tables' headers. Replay would flag every field of about 2,300 lines, the admission check against the declared list is vacuous for a union, and the §11 scale check can never pass for an invented name.

**Fix.** Key the field list by (document, table), as `<document_id>-<table>-<ordinal>` already anticipates; allow a parser-declared, versioned mapping from printed header to field name, keep the printed header (with unit and scale wording) beside the mapped name; the §11 scale check reads the printed header; replay treats a mapped rename as explained. A mapping shared across publishers (the Senegal annexes reusing Indonesian names) is a defect corrected by a new spec row, not an explained difference.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-14 (major, M2)

**Finding.** The only no-op test between snapshots is byte identity, yet the one held document with two snapshots (zaf-ntcsa-transmission-plans, retrievals 9 s apart, different bytes) is a per-request nonce page, not a revision. Under §8 it is extracted in full, yielding phantom restatements; every refresh of the 175 held HTML snapshots would do the same at M4, each needing review. The restatement link shape (chain or star) is unstated, a chain of weekly restatements breaks storage's depth-one bound, and F13 would count each restatement again. F4's M2 test meets no genuine change.

**Fix.** §8: a new snapshot whose normalised text of the declared scope, under a named adapter version and furniture rule, equals the last extracted snapshot's is treated as identical bytes (persistence dated by the retrieval, recorded as a whole-snapshot restatement carrying the adapter version so replay regenerates the verdict). A restatement links to the origin line (star, depth one). Define 'statements of a document' as origin lines, restatements counted apart. §13 and F4: the M2 test runs on a fixture (a held snapshot with one value changed) plus this document. Storage §1: `line-fields/<document_id>` of a living document shards by year of recorded_at.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-15 (major, M2)

**Finding.** 10,452 of 13,092 lines (80%) are CRS, IATI and World Bank comparator records in 83 CSV snapshots. DA2 counts them among the 254 extracted and Q1 requires their replay at M2, while extraction §5 and DA10 tag comparator records M3b. Nothing says whether replay, the bulk-run statement of §6.2 and the Q3 red test cover them at M2, nor whether a later draw of the same query is a new document or a new snapshot of a living one.

**Fix.** State in §13 item 3 and DA2 that the held comparator snapshots are read at M2 by the ingestion run of §6.2 and replayed, and that 'comparator, M3b' means new draws and their use in matching and results. Add to §12 an ingestion control: the record count read equals the count the API or file states, else the run fails. A draw of a query slice is a new document dated by the draw, related by `edition_of` to the previous draw (what the record does today; a living-document reading would re-key 10,452 lines).

**Author decision.** Scope: is replay of the 10,452 comparator lines part of M2 acceptance? Options: (a) yes, by the ingestion run with the count control; (b) no, retag them M3b and exclude from Q1. Recommended: (a); they are held bytes and the replay is mechanical.

**Outcome.** decided by the author 2026-09-30: option (a): M2 replays the 10,452 comparator lines by the bulk-ingestion method with a count control per snapshot; applied in "docs(jetp): prose statement shape, comparator replay, scan transcription and M3b scope".

### W1-16 (major, M2)

**Finding.** Storage §5 makes transcription of the scan (Decision 458, the newest Vietnamese plan, 23 pages, 149 characters of text, language unknown) an M2 rule, while extraction §7 allows `deferred` ('a scan awaiting transcription') and §15 says 'transcribed or deferred'. If deferred, M2 is accepted with the current Vietnamese plan holding no statements. §6.4's automatic locator check proves nothing against an OCR layer.

**Fix.** Write one rule in both places. Preferred: transcribe at M2 by a recogniser, lines carry the recogniser as method and version, the locator is page plus region, the check is the author's inspection of the image for every statement (one sitting), the language is set by the operator (DA5). If deferral is chosen, storage §5 says 'or deferred' and the M2 acceptance names the document and reason.

**Author decision.** Transcribe Decision 458 at M2 (one author sitting over 23 pages, recogniser as method) or defer it to M3b with the deferral named in the M2 acceptance? Recommended: transcribe at M2; OBS-1 for Viet Nam depends on it and the cost is one sitting.

**Outcome.** decided by the author 2026-09-30: Decision 458 transcribed at M2 without an author sitting (recogniser, two vision-capable readers, arbiter on escalation, locator page and region, likelihood and confidence recorded); general collection rule: search for a born-digital copy before transcribing any scan, and record the search; applied in "docs(jetp): prose statement shape, comparator replay, scan transcription and M3b scope".

### W1-17 (major, M2)

**Finding.** Twelve pending documents exceed 100,000 characters and the ZAF plan runs to 304 pages; at about 110 statements per call, splitting is routine, but §6.3 says only 'split into parts with their own scope'. Nothing says how parts are cut, whether they overlap, what a part inherits (group headings, method notes), how an item straddling a seam is handled, what the checker sees, or how printed-total controls covering the whole list are applied per part. Two JavaScript portal bundles hold 5.0 million characters and their route is not fixed.

**Fix.** Add one rule to §6.3, not a size gate: a part is a declared scope part (§4: appendix, section, page range), so parts do not overlap; the page-break rule extends to part boundaries (one statement, locator spans, owned by the part where it starts); seam de-duplication keys on the code-derived locator of W1-02; the checker lists missed items within its part only; each part's queue counts against the document cap; printed totals covering several parts are checked after merging. State in §6.2 that the portal verdict precedes any LLM call. Add a §12 red test: a fixture cut so an item straddles the seam yields one statement.

**Outcome.** fixed in fd7c1f4c.

### W1-18 (major, M2)

**Finding.** `translation_of` and near-identical `same_as` are asserted on metadata agreement (title, date, page count) with no content check, and only one member is extracted. An English version of a Vietnamese decision is often an abridgement or a later revision with a different annex, and a re-export can carry a corrected figure that disappears when the member is `duplicate`. An annex published alone and inside a bundle has no relation and is extracted twice. The three held document `same_as` rows are `candidate` (not in force) yet their outcome is a precondition of extraction, and the canonical default can name a member with no snapshot (the SSL-failed Senegal copy).

**Fix.** Fusion §3: before a `translation_of` or non-identical `same_as` judgement reaches 'likely', compare the multiset of numerals with units, dates, percentages and printed identifiers plus page and table counts, recorded as the quoted basis; beyond a declared tolerance the judgement is 'different' (`edition_of` for a changed re-export), both members are extracted and §5's same-publisher rule handles non-independence. Extraction §2: the canonical member is chosen among members holding a snapshot; a bundle's declared scope excludes an annex held alone and names where it was extracted. §13 item 1: the three pending document judgements are decided and in force before the first run. Add a §15 row: an English version with a different annex is its own document.

**Outcome.** fixed in fd7c1f4c.

### W1-19 (major, M2)

**Finding.** 13,089 statements exist from before this specification. The spec never says how many come from parsers, LLM reading or hand, what legacy rows carry in the new method and reader columns, or how far Q1's replay reaches (extraction §10 binds only parsers). Porting old parsers is probably the largest M2 build item and is not sized.

**Fix.** Derive the method of each existing line from its identifier family in storage §1 (extractor-minted keys: script name and commit; API keys: ingestion run; decision-scoped keys: person or assisted reading, exempt from checker-stance fields). Require the first M2 replay report to count lines per family and method; phrase Q1's test as 'zero unexplained differences for extractor-minted and ingested lines; locator-and-text check for the others, listed by method'. Add the per-method count to DA2 once measured.

**Outcome.** fixed in fd7c1f4c.

### W1-20 (major, M2)

**Finding.** Run outputs are 'changes like any other', each with cross-vendor LLM review and full `make check`. M2 produces 115 documents' statements and dispositions; per-document or per-batch PRs each get a loop priced at tens of minutes and about 1M tokens, and row-level LLM review of a 10,000-row data PR duplicates the §6.3 checker while giving false assurance. Storage §3's 'row by row in a pull request' cannot hold at 7,000 to 12,000 rows.

**Fix.** Operation §4: distinguish a run-output PR from a code PR; its gate is the validator, the planted-item and fabricated-locator controls, replay and idempotence over the run, and the run report; the cross-family review (Q19) reads the report and a sampled trail, not the rows. Batch by run. Storage §3: assisted-reading rows are reviewed through the §6.3 queue and the run report, parser and bulk output through the manifest diff.

**Author decision.** Accept a lighter gate for run-output PRs (validator, controls, report and a sampled trail instead of full cross-family row review)? Options: (a) yes as proposed; (b) keep the full loop but batch one PR per run; (c) keep full loop per document. Recommended: (a); the real row check is the §6.3 queue.

**Outcome.** decided by the author 2026-09-30: option (a) with one PR per run: lighter gate for run-output PRs (validator, planted-item and fabricated-locator controls, replay and idempotence, run report), the cross-family reviewer reading the report and a sample of traceability chains; code PRs keep the full loop; ledger tables CSV in git, bulky raw material under DVC by hash, table-aware run summary; Dolt recorded as the M4 option; applied in "docs(jetp): run-output gate and two off-disk copies of the document bytes".

### W1-21 (major, M2)

**Finding.** Every locator resolves only against the text layer of one named adapter version, yet §5 treats the layer as a disposable cache 'discarded when either changes', and the adapter (poppler 24.02.0) is a system binary the spike found already decides whether statements exist. An OS upgrade silently turns thousands of admitted statements into non-statements ('a statement whose place cannot be found again is not a statement'); F1, Q1 and Q8 fail in year three with no ledger defect. The fast tier on doudou has no adapter.

**Fix.** §5: the text layer of every snapshot with admitted statements is retained as a DVC artifact keyed by (sha256, adapter, version, hash), listed in storage §1 as derived and in operation §9's table; a later adapter writes a second layer beside it and the §9 mapping is reviewed old-layer to new-layer; pin the adapter by exact version in the existing lockfile, no container. §12 red test: replay against a snapshot whose retained layer is deleted and whose adapter version is unavailable fails loudly. Operation §2: the fast tier on doudou does not resolve locators.

**Outcome.** fixed in fd7c1f4c.

### W1-22 (major, M2)

**Finding.** The system of record for all document bytes sits on one disk in one workstation, with the DVC remote on the same NVMe partition. The only other copy is a hand-made laptop pull that the spec says may be dropped, tested once at M2. Non-redistributable snapshots collected through manual browser steps exist nowhere else; publishers may have rewritten the originals, so 'refetched from its publisher' cannot restore what was said.

**Fix.** Rewrite operation §9: the second copy is retained, not droppable, verified against the DVC pointers after every push (`dvc status -c` or a hash walk in the push recipe); an external or institutional disk is preferred, the laptop acceptable only as an additional copy; the recovery test runs before each freeze and each release; location and custodian recorded in §9's table.

**Author decision.** Where does the retained second copy live? Options: (a) an external disk kept off-site or at the institution; (b) institutional storage (CNRS or lab NAS); (c) the laptop, upgraded to a retained and verified copy. Recommended: (b) if available, else (a), with the laptop as a third copy.

**Outcome.** decided by the author 2026-09-30: Zotero is the off-site copy now (one-way upload, sha256 in the item metadata), DVC the working store until the M4 move; padme's nightly restic backup to a Hetzner Storage Box stated, with its failure and repair of 2026-09-30; M2 test restore of one snapshot from each copy; ticket 1712 updated; applied in "docs(jetp): run-output gate and two off-disk copies of the document bytes".

### W1-23 (major, M3a)

**Finding.** The M3a records are not specified: `dry-searches` and `decisions.md` are 'as today' with no columns; the round log, candidates, triage judgements, document class, known-item list, tracker claims and outcomes, discovery and newest-document dates have no table. `coverage` is keyed on a referent, but collection §3 needs a terminal verdict for every expected authority and listed project before any project referent exists (projects are minted at M3b). `collection_method` has four values against five rungs (no automated browser, no web archive); no column records the site's robots or terms position or the free registration used.

**Fix.** Add the M3a tables with the collection fields, keyed without a new family: an authority is a `party_id` and a listed project is the `line_id` of the plan line listing it, so `frame-entries` keys on (kind, party_id or line_id). Map the four `collection_method` values onto the five rungs explicitly and add the web-archive rung (or state that an archive copy is a retrieval whose host party is the archive). Add a document-class column or relation for DA6. Terms, robots, registration and archive columns per W1-29.

**Outcome.** fixed in 2034d335; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-24 (major, M3a)

**Finding.** N4 ('No program admits a document, merges two identities, prefers a value') and fusion principle 1 ('No rule below selects a value or merges two things on its own') are absolute, yet fusion §3 merges on a shared external identifier and on case or diacritic variants, proposer 1 is 'virtually certain', extraction §8 pairs on a stable key, and collection §9 admits a document when two LLM readers agree with the author seeing only a sample. A reviewer finds N4 and F7 either met or breached depending on whether a checked LLM agreement or an adopted deterministic rule counts as 'a recorded decision'.

**Fix.** Keep N4 and principle 1. Fusion §3: a program records a judgement only under a rule the author adopted by version (identical bytes, same external identifier, case or diacritic variant), recorded `accepted` by that method under a decision in `decisions.md`; every other program or LLM proposal is `candidate` until the checking rule of operation §5 or the author accepts it; storage §4's 'registered as a same_as candidate' then applies to tiers 2 and up. N4: 'No program, and no rule without a recorded judgement, admits a document'; F7's test: 'until an admission decision, which may be a checked LLM judgement under Q5, exists'; operation §4: 'development agents'.

**Outcome.** fixed in 2034d335.

### W1-25 (major, M3a)

**Finding.** F9, DA9 and C6 are M3a with tests on 'the release', but the first release is the M3b slice. Collection says the traceability rate, the two dates, the recall estimate and the unreachable list are 'published' at M3a, and no document says what M3a publishes, where or under which identifier. Results §4's collection record omits the tracker traceability rate, the declared protocol, the round log, the 'stopped by cap' statement and the terminal verdicts of every authority and listed project (F8, OBS-6, LP-4).

**Fix.** Call the M3a product a collection report accepted by the author (collection §12, results §13); reword F9, DA9 and C6 tests as 'in the M3a report' and 'in the release and every product citing it' at M3b, no retag; extend results §4's collection record with the protocol, round log, verdict table, cap statement and tracker traceability rate.

**Outcome.** fixed in 2034d335.

### W1-26 (major, M3a)

**Finding.** Triage's 'admit' criterion refers to a document-level scope the requirements never define (N2, N12, N13 are exclusions; F13 is a counting scope). DA12 requires partner-lender operations without JETP attribution and pre-partnership milestones, but collection never says whether such documents are admitted or 'context only', and 'context only' overlaps the disposition `out_of_scope` without saying whether a context-only candidate is registered (so F2 and F27 do not know whether to count it). The two LLM readers cannot be given a stable question.

**Fix.** Add an 'in scope' definition to requirements §2: a document is admitted when it states something about a JETP partnership's projects, money, perimeters, parties or states, or belongs to the DA12 reference pool. Collection §9: 'context only' registers the document and it receives the disposition `out_of_scope`, keeping the language document's split between a candidate's triage outcome and a held document's disposition.

**Author decision.** Adopt the proposed admission scope (statements about a partnership's projects, money, perimeters, parties or states, plus the DA12 reference pool)? Options: (a) as proposed; (b) strict JETP attribution only, DA12 pool as context-only; (c) broader (any energy-transition finance in the four countries). Recommended: (a).

**Outcome.** decided by the author 2026-09-30: option (a): admission scope is statements about a partnership's projects, money, perimeters, parties or states, plus the DA12 reference pool in its own counting scope; a context-only candidate is registered with the disposition `out_of_scope`; applied in "docs(jetp): admission scope and point-estimate recall gate for discovery".

### W1-27 (major, M3a)

**Finding.** The known-item list is both the held-out test set and the diagnostic that edits the search frame at each checkpoint, so items recovered by a channel added after their miss count as found, and round-zero holdings assembled from the same literature count too. The recall estimate is biased upward beyond the visibility bias already admitted, and the stopping rule's point-estimate test on n=40 sits inside the interval (36 of 40 gives 77 to 96%).

**Fix.** Keep one frozen list but attribute recoveries: an item whose diagnosis triggered a frame revision counts as missed; report recall under the frame as declared before round one and under the frame as revised, with and without round-zero holdings and the round-zero share stated. State that the stopping condition is a point-estimate gate under the author's acceptance in §5. Reserve a held-out split if the list is enlarged.

**Author decision.** Is the 90% recall stopping condition a point-estimate gate or a lower-bound gate? Options: (a) point estimate at n=40 (36 of 40), with the biases reported beside it; (b) Wilson lower bound at 90%, which needs about 38 of 40 or a larger list. Recommended: (a) with the two-frame reporting; (b) only if the list grows past about 80 items.

**Outcome.** decided by the author 2026-09-30: option (a): point-estimate gate (36 of 40) with the Wilson interval and known biases published; items found only after the frame was widened because of them count as missed; recall reported under the declared and the widened frame; applied in "docs(jetp): admission scope and point-estimate recall gate for discovery".

### W1-28 (major, M3a)

**Finding.** Either a live address or an archive record satisfies F27, so the Observer's own archive capture is optional until M4's monthly retry, and frozen documents fetched once at M3a are not checked until M4. A publisher can silently replace or remove a PDF between the fetch and the release; a reader following the address concludes the Observer misread, and for a non-redistributable document the hash proves nothing to a third party, so Q8's independent reconstruction and DP-4 fail.

**Fix.** Record the capture address on the retrieval as the 'public archive record' F27 names; add a 'public copy' column to the release's redistribution list (redistributed bytes, archive capture, or none with reason); restate the Q8 and DP-4 tests over documents with a public copy; re-fetch frozen documents once at the freeze (identical bytes are free under extraction §8; different bytes are a new snapshot).

**Outcome.** fixed in 2034d335; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-29 (major, M3a)

**Finding.** Verbatim publisher text and every line-fields table are redistributed unconditionally under a licence F30 restricts to attribution, which cannot cover third-party text or database content; the spec names no legal basis for holding copies (TDM exception, quotation right, public-sector re-use). No column records the terms or robots position, the free registration used, or the public access route F27 requires at M2 (`documents` holds only `url`), and C6 lets a fetch proceed whatever robots say while DA9 expects documents 'excluded by robots rules'. Legal exposure is the likeliest way the Observatory is taken down.

**Fix.** Add to `retrievals`: terms_position (open licence, public-sector reuse, rights reserved, unknown), robots_position, registration_used (name, never a credential), archive_url; add to `documents`: access_route_kind (address, archive_record, registration) and registration; validator checks non-empty from M3a, columns tagged M2. Results §6: the open licence covers the Observer's own contributions; publisher text is reproduced under attribution as quoted data. Keep verbatim labels, excerpts and line-fields served. Reword DA9's test to 'documents reachable only through paths robots rules exclude'.

**Author decision.** Commission a one-page legal note under Q21 on the basis for holding and redistributing copies (TDM exception, quotation, public-sector re-use, per jurisdiction)? Options: (a) yes, before M3a, from the institution's legal service; (b) proceed on the stated attribution-as-quotation basis and note the risk. Recommended: (a); it is not a build gate but it precedes go-live.

**Outcome.** decided by the author 2026-09-30: the legal note is written on another branch; only the author-independent parts applied: terms, robots, registration and access-route columns as target columns, CC BY for the Observer's own contributions, publisher text reproduced under attribution as quoted data, jurisdiction France, DA9 listing documents reachable only through robots-excluded paths; applied in "docs(jetp): storage contract gains readings and runs journals and the ontology tables" and "docs(jetp): release licence position, report tickets, named formats and M3b accounts".

### W1-30 (major, M3b)

**Finding.** IPCC terms are applied to LLM output with no calibration step (the spike: 2 of 7 pairings false at 'likely' or above; 'same, very likely, high' on a 2-in-10 token overlap). Stance plus likelihood double-encode one quantity ('different, very likely' equals 'same, very unlikely') and collide with 'about as likely as not, very low confidence' for a know-nothing judgement and with the `undetermined` stance. The default inclusive threshold ('about as likely as not or more, any confidence') therefore admits every undecided candidate, hollowing F11's range. Confidence is defined as evidence plus reader agreement but the threshold is a conjunction with no stated order. The checker's stance appears at M2 and triage at M3a, so the rule must be fixed before M2.

**Fix.** (1) One judged quantity: the likelihood that the positive proposition holds ('same', 'right'); `undetermined` is an abstention with no likelihood and counts in no result. (2) Keep `confidence`, defined in fusion §1 as evidence quality plus agreement between readers. (3) State the threshold once as a conjunction: likelihood of sameness at or above the term and confidence at or above the level. (4) Extend 'tested against matches already judged by hand': per method version, the observed precision of each verbal term on the hand-judged set (257 register rows, 67 plan lines, the audit decisions of W1-04), published with the method version; a result translates its threshold into an expected error from the observed rate.

**Author decision.** Set the confidence floor of the default inclusive threshold. Options: (a) 'any confidence' as drafted, which admits know-nothing judgements; (b) 'low or more', which excludes them; (c) 'medium or more', close to the cautious end. Recommended: (b).

**Outcome.** decided by the author 2026-09-30: option (b): the inclusive threshold requires low confidence or more; the cautious threshold stays likely, medium confidence or more; calibration [M2] makes the terms meaningful; the fix's one judged likelihood and abstention for `undetermined` applied with it; applied in "docs(jetp): one judged likelihood, calibrated terms and a confidence floor on the inclusive threshold".

### W1-31 (major, M3b)

**Finding.** Matching is pairwise with no cluster semantics: nothing says what a referent is when A~B and B~C are accepted and A~C rejected, or how components form at a threshold; single-link chaining at the inclusive threshold can collapse project counts, and storage's 'bounded to depth one' has no enforcing rule. The tiers are an unnamed Fellegi-Sunter cascade with no blocking-recall figure or pair or cluster metric; tier 2 fails across languages (spike); tier-1 'virtually certain' on plan ordinals and operator codes ignores the gaps, repeats and reuse extraction §3 admits.

**Fix.** Fusion §3 and storage §1: (a) at a threshold a referent's members are the lines whose in-force `line-referents` row meets it; two referents joined by an in-force `same_as` meeting it are one; the validator enforces depth one (a source of an accepted `same_as` is never the target of another; `routes` redirects it), so a would-be chain is a conflict raised for review; (b) per method version, publish blocking recall (share of hand-judged true pairs the proposers surface), pairwise precision and recall on the hand-judged set, and one cluster metric; (c) tier 1 on a plan ordinal or operator code requires country agreement and one corroborating attribute for 'virtually certain', else 'very likely'.

**Outcome.** fixed in 9c8b3633; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-32 (major, M3b)

**Finding.** The party roles the ontology lists (funder, channel, promoter, implementing_entity, beneficiary, contractor, operator) have no relation to carry them: `party_in` is party-to-agreement only and `role_in`'s closed list holds mandates only. Storage realises an asset's operator as an `operator_party_id` column, bypassing attach-by-decision. Storage's rule that multi-name cells are minted 'through role_in or party_in rows' has no valid role for a funder named in a project row.

**Fix.** Extend `party_in` to project and asset with the Party roles as its closed list; keep `role_in` for mandates; state which roles attach to which subject kinds; drop `operator_party_id` (an asset's operator is a dated `party_in` row).

**Outcome.** fixed in 9c8b3633; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-33 (major, M3b)

**Finding.** `preferred` is one value of the same form-type list as `acronym` and `translation`, so a preferred form cannot also be an acronym (SENELEC). Fusion settles acronym-versus-expansion 'in a result whose match threshold the judgement meets', making identity depend on the result, while storage §4 physically folds the parties and redirects the old identifier for all results; after a fold two `preferred` rows exist where the rule allows one. F12's tests and the cautious and inclusive party sets diverge.

**Fix.** Make `preferred` a flag column and keep form_type a kind. Fold physically only under the deterministic rules fusion §3 calls 'never two parties' (same identifier, case or diacritic variant), the retained party's preferred form stated by supersession of the other's; every other party `same_as` stays a judgement, and each result computes its party view at its threshold. Reserve `routes` for identifiers retired in a published release.

**Outcome.** fixed in 9c8b3633; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-34 (major, M3b)

**Finding.** Collection §11 says the knowledge cutoff of fusion §1 is 'here the date of the freeze' of the register, while results treats K as a per-release date at which statements and judgements admitted on or before K count. Since all M3b extraction and matching is admitted after the freeze, a release whose K equalled the freeze would contain no M3b statements.

**Fix.** Delete 'here the date of the freeze'; say the freeze fixes the register's membership while K is declared per release at or after the discovery cutoff, as results §4 already requires.

**Outcome.** fixed in 9c8b3633.

### W1-35 (major, M3b)

**Finding.** Fusion §4 says signing, approval and disbursement are 'different measures, not successive states of one chronology'; §7 and F14 say 'need, announced, memorandum, approved, signed, disbursed form a chronology'. Neither list matches the ontology's money axis (announced, mou, approved, signed, cancelled, withdrawn as states; pledge, commitment, disbursement, expenditure as flows): 'need' and 'memorandum' are not terms, and 'reported' (F19, results, language) is in neither list. F14's test and F19's gaps depend on one closed list.

**Fix.** Rewrite §4 bullet 5 as 'an occurrence is never inferred from a state change; an observed later state implies no earlier one and no payment'; keep the chronology rule in §7 only, in ontology terms (agreement states of the money axis, IATI flow types, `estimate` or `envelope` for need, `mou` for memorandum); define 'reported' as the amount a comparator record (CRS or IATI) reports, or drop it from F19 and the language document; add one §9 check row.

**Outcome.** fixed in 9c8b3633.

### W1-36 (major, M3b)

**Finding.** Correction releases are not reconciled with frozen bytes and the as-of rule. The metadata record is listed inside the frozen package yet gains citations and supersession pointers; the check row says unchanged bytes 'point to the correction'. A correction of a ledger error is a supersession row recorded after K, so a `YYYY-MM-rN` release that keeps K cannot contain its correction and one that takes a new K also ships every statement discovered since. §9 has an error become `-rN` while F25 says it 'enters the next release'. There is no withdrawal or retraction state, and F28's 'even if the data must be withdrawn' has no procedure; a reader landing on an old deposit sees the wrong figure with no warning.

**Fix.** §4: list the descriptor only; the deposit's metadata record sits outside the frozen package and alone gains citations, supersession pointers and a status (current, superseded by rN, withdrawn with reason); reword the check row to 'bytes unchanged; the deposit record points to the correction'. Define the as-of state by cutoff K plus a named correction overlay (ledger-error supersession rows recorded after K whose superseded rows were recorded on or before K); a correction release keeps K, names its overlay rows in the descriptor, and rN is an ordinal; reword F10 so 'a later discovery' means a new record row, never a named overlay row; add the rule to fusion §8 and storage §1. §9: an accepted report that changes a released figure produces `-rN`, otherwise it enters the next regular release; align F25. Withdrawal removes the deposit's files and Observatory pages, keeps descriptor, hashes and reason, and the identifier resolves to that record; add the status column to `#release-history` and a §14 row. Banners on earlier-release pages stay M4.

**Outcome.** fixed in 9c8b3633; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-37 (major, M3b)

**Finding.** F25 and OBS-7 (M3b) require reported errors to be recorded and answered by a judgement, but no table, intake or channel exists: the requirements table points at fusion §2 (silent on reports), operation (no intake) and presentation (no channel). A report carries a natural person's identity in a public git ledger; a publisher's private correction is inadmissible (N13, F27), so 'true, but only the publisher can say so' has no outcome; a takedown or erasure request collides with append-only and frozen releases.

**Fix.** Operation: a public address or issue tracker linked from Methods; each report is a ticket whose number is the report identifier, reporter identity stays in the ticket, never in a ledger table; the accepted correction is a supersession row whose notes cite the report. State the three outcomes: ledger error accepted; rejected with reason; publisher's revision awaiting a public document. Correct the F25 and Q20 rows of requirements §9. Takedown: withdrawal under F28 (W1-36) plus a correction release, never a rewrite of history.

**Author decision.** Report record: (a) a ticket per report, the ticket number as identifier, cited from the supersession row (lighter, no personal data in the ledger); (b) a served `reports` table without reporter identity, with a report_id, target, claim, adjudication and outcome. Recommended: (a); a table can be derived from tickets at M4 if the volume warrants it.

**Outcome.** decided by the author 2026-09-30: option (a): one ticket per reported error, its number the identifier cited from the correction row; no personal data in the ledger; "reported, awaiting a public source" is a valid outcome; a table may be derived at M4; applied in "docs(jetp): release licence position, report tickets, named formats and M3b accounts".

### W1-38 (major, M3b)

**Finding.** Fusion §2 says the change between two publisher statements 'is a judgement, which says which' (development, late report, correction), but `adjudications.decision_type` is closed to four types with no revision or preference type, no relation carries an erratum, and the closed classification list has no correction notice. F22 (M4) attributes each changed figure to a reason, which can only be read from judgements recorded from M3b; collection §10 checks frozen documents at M4 only for disappearance, so a PDF silently replaced under the same address is never seen.

**Fix.** Add two decision types to `adjudications` as `terms` rows [M3b]: `revision` (members: earlier and later line; verdict: development, late_report, correction, rounded_restatement) and `preference` (members: candidate, accepted, excluded; verdict names the fusion §5 reason). Collection §10: the M4 check of a frozen document fetches and registers new bytes as a snapshot. Add `corrects` as a role of the line-to-line `cites` relation when the first correction notice is met, not before; no `erratum` document type or `withdrawn_by_publisher` status.

**Outcome.** fixed in 9c8b3633; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-39 (major, M3b)

**Finding.** The D3 reading and D4 matching queues at M3b have no size: tens of thousands of observations each with reader, checker and author sample, and 'every candidate match gets a judgement' against about 8,000 CRS rows and 1,301 IATI lines, with tier 2 failing across languages so most matches fall to LLM tiers. M3b inherits an author queue at least as large as M2's, and the budgets cover per-run minutes only.

**Fix.** Apply the bounded rule of W1-05 with an M3b attention ledger. Scope reading to statements that print a measure and belong to a declared counting scope (strict or DA12's reference pool); match only lines that feed a declared result, with deterministic blocking (country, technology, capacity) and a top-k per line; unjudged candidates are 'listed, not counted' under F11.

**Author decision.** Accept the M3b scoping (read only measure-bearing statements in a declared counting scope; match only lines feeding a declared result, top-k per line; the rest listed, not counted)? Options: (a) as proposed; (b) read everything, match everything, accept a longer M3b. Recommended: (a); it is what F11's 'listed, not counted' already allows.

**Outcome.** decided by the author 2026-09-30: option (a): M3b reads only measure-bearing statements in a declared counting scope and matches only lines feeding a declared result, top-k candidates per line, the rest listed, not counted; reading and matching on the local models, OpenRouter only as arbiter on escalation; applied in "docs(jetp): prose statement shape, comparator replay, scan transcription and M3b scope".

### W1-40 (minor, M2)

**Finding.** Classification is required on every statement, yet a statement may 'wait for review' without one; no state or column says whether an unclassified statement is admitted, pending or under a disposition, and assigning it later is an edit §1 forbids. The spike never used `unclassified` in 88 statements, so the rule may be dead, but it surfaces on the first document that uses it.

**Fix.** State in §3 and §1: a statement is admitted only with a classification; 'waits for review' means the proposal stays in the run's review queue (assisted reading: the author's queue; parser: the document is not admitted, per §6.1's no-partial rule). DDL: `lines.classification` NOT NULL; no candidate status on `lines`.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-41 (minor, M2)

**Finding.** jetp-spec.md says the conceptual documents 'name no storage', yet ontology §5 defines five M2 tables with keys, columns, file paths, a DDL test and build outputs, and the storage contract's table list omits them. A DDL builder reading the storage contract will not find `terms`, `status-crosswalk`, `sector-crosswalk`, `perimeters`, `marker-coefficients`.

**Fix.** Either state the one exception in jetp-spec.md (the ontology tables are defined in ontology §5 and incorporated by the storage contract), or move only the table rows and the path to storage §1 and leave definition, traceability, revision and the alignment test in the ontology.

**Author decision.** Keep the ontology tables in the ontology with a stated exception to the ground rule, or move the table rows to storage §1? Recommended: the stated exception; it is one sentence and keeps the ontology self-contained.

**Outcome.** decided by the author 2026-09-30: moved: the five ontology tables' keys, columns, paths and DDL test go to storage section 1, the ontology keeping their meaning and a pointer; the alignment test reads table rows from both documents and passes unchanged; applied in "docs(jetp): storage contract gains readings and runs journals and the ontology tables".

### W1-42 (minor, M2)

**Finding.** `same_as` has three rows with three meanings (document: folds and canonicalises extraction; line; generic: 'does not choose a route'), and `cites` has a line row and an observation row with different ranges, while §5 says a relation term states one domain and range and the alignment test matches each value to one term. The validator cannot tell 'folds' from 'asserts equality' on one relation value.

**Fix.** Keep one `same_as` term with domain 'any', range 'same kind', presenting the document and line rows as cases (the canonical-member rule is extraction's, not the relation's); state that the observation `cites` is the `line_id` column, not a relation row.

**Outcome.** fixed in fd7c1f4c.

### W1-43 (minor, M2)

**Finding.** The ground rule is no ticket numbers or dates inside spec text, yet the index's State column carries ticket and PR numbers and says Results and Operation are 'being drafted' though both are complete, and the other documents embed tickets and dated decisions in normative text (key families named for tickets 0970 and 1160, dated amendments). A reviewer cannot tell provenance from rule.

**Fix.** Fix the State column now (draft, reviewed, in force; correct the Results and Operation rows). Leave ticket pointers where they explain provenance; move dated decision narratives to the attic only if the author adopts a no-dates rule, written in jetp-spec.md.

**Author decision.** Adopt a no-dates, no-ticket-numbers rule in normative text (provenance pointers moved to an attic section) or keep pointers where they explain provenance? Recommended: keep provenance pointers, fix the State column, no attic move.

**Outcome.** decided by the author 2026-09-30: strict: no ticket numbers or dates in normative text, provenance in a History line at the end of the section it concerns; the index's State column fixed (no ticket or PR numbers; documents 0, 3, 4, 5, 7 and 9 reviewed); applied in "docs(jetp): no ticket numbers or dates in normative text; History lines and index states".

### W1-44 (minor, M2)

**Finding.** `edition_of` names three relations (a revised edition, an issue of a serial, the version history of a living page, which is already a snapshot). Issues of a series (the 13 pending MOIT newsletters) are filed as editions, but restatement is defined only between snapshots of one document and key-less pairing is M4, so no rule says whether issue 13 repeating issue 8's list is a restatement or corroboration (spike: 0 of 7 restatements, 2 false pairings). Storage gives `edition_of` two homes (a `documents` column and `relations` rows) and calls the Indonesian plan-to-progress-report link an edition relation.

**Fix.** Drop `documents.edition_of` or declare it a derived cache of the `relations` row. Extraction §8: restatement is judged between snapshots of one document only; pairing across editions or issues is a candidate match of fusion §3 [M3b], not a restatement. Qualify `edition_of` through the existing `relations.role` column (`issue`, `revision`); no `issue_of` term. Reword storage §4: the CIPP-to-progress-report pair is a tier-2 candidate-match test bed, not an edition relation.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-45 (minor, M2)

**Finding.** Collection §11 lets M2 retry the 23 snapshot-less documents 'on the access ladder', but the ladder, public-access-only and crawler rules are all tagged M3a. The rung vocabulary differs (collection five rungs, storage four values, operation two). Extraction §5 makes a rendered capture 'a separate snapshot' while collection §2 keeps it 'beside' the response with no table for it.

**Fix.** Restrict M2 retries to rungs 1 and 2 (script, browser-session) in collection §11; align `collection_method` with the five rung names at M3a (W1-23); state in collection §2 that a rendered capture is its own retrieval yielding its own snapshot.

**Outcome.** fixed in 2034d335; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-46 (minor, M2)

**Finding.** Operation logs author minutes at M2 by document class, but classes (frozen, living, series) are assigned as a dated judgement at M3a, so M2 documents have none. Q15 and results §4 ask spend per class while AED-3 asks cost per method; parser, assisted reading and transcription have different costs the class does not separate.

**Fix.** Operation §8: attribute minutes per run and per document (class and type joined later); Q15 and results §4: 'per document class, document type and extraction method'.

**Outcome.** fixed in 954d6e84.

### W1-47 (minor, M2)

**Finding.** 27 pending HTML project pages and 15 data portals are neither an issue series nor one-off: each publisher's pages share a template. DA3's test ('each document extracted by a dedicated parser belongs to a repeated series') forbids a template parser and sends them to the LLM route and its review cost. §4 has no statement shape for a record page (labelled fields plus a description).

**Fix.** Reword DA3's test to 'belongs to a repeated series or a repeated format of one publisher'; add 'or a page template' to §6.1's examples; add to §4: a record page is one item statement for its subject, its labelled fields are its verbatim fields under the printed labels, and its description follows the prose rule.

**Outcome.** fixed in fd7c1f4c.

### W1-48 (minor, M2)

**Finding.** Extraction copies 'the axis it belongs to' while the ontology says the crosswalk row carries the axis, so who sets `own_status_axis` is open. The spike's reader put a decision verb on `project_stage`; the record carries 2,677 `delivery` and 1 `money` axis values, including the ZAF register's letters, that replay will flag or bless depending on an undefined rule.

**Fix.** State in §3 that `own_status_axis` is set only by a parser's reviewed, versioned status list for its series (adopted as `status-crosswalk` rows at M3b) and is empty for assisted readings, transcriptions and a person's reading; an LLM reader is never asked for it; replay reproduces the 2,678 values from the parser configuration.

**Outcome.** fixed in fd7c1f4c.

### W1-49 (minor, M2)

**Finding.** The default scope throws away the masthead and dateline, so an item dated 'Ngày 27/3' has no year statement §11 can name, and a quoted speaker has no field. For living documents `snapshots` has no date column, so F9's 'newest document date' is defined only for publisher-dated documents and a release could state a date months older than the freshest page it relies on.

**Fix.** §4: page furniture carrying a date, issue number, period or publisher name that governs the statements is in scope by default (add 'dateline, masthead date or issue period' to the method-note examples); no completion from the register. Collection §11: for a living document the publication date of a snapshot is the date its publisher prints in it, else its retrieval date; the release states the latest retrieval date of living documents beside the newest document date. Speaker handling per W1-12.

**Outcome.** fixed in fd7c1f4c.

### W1-50 (minor, M2)

**Finding.** Q17's 'reference answers for research on machine reading' are produced by the readers AEDIST would benchmark and checked by a human only on disagreements, missed items and a sample; recall is unmeasurable since an item both LLMs skip is never listed. Used as a gold set they reward models resembling the Observer's own reader.

**Fix.** Q17: the reference answers are the human-decided subset (disagreements, missed items, sampled rows); machine-agreed-only rows carry that flag; the reader and checker LLMs are named so a benchmark can exclude them. Operation §8: the run report records the sample rate and seed.

**Outcome.** fixed in 954d6e84. An item both readers skip is counted from wave 2 by recall on the held-out set ([W2-08](../wave-2/ledger.md)).

### W1-51 (minor, M2)

**Finding.** A living document that moves address is found later as a second document and folded by `same_as`; the member already extracted stays canonical and the new one is `duplicate`, but every new snapshot is yielded only by retrievals of the new member, so the validator rejects any line citing it under the canonical document. Site migrations over three years are near certain; discovered at M4 this forces a change to the canonical rule and the identity model.

**Fix.** One rule in collection §10/§11 and storage §1, tagged M4 but written now: a relocation of a held document is a recorded change of its address (a `document-addresses` row with valid_from, or a superseded `documents` row), never a second document; a retrieval of any recorded address is a retrieval of that document, and the validator rule reads accordingly.

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-52 (minor, M2)

**Finding.** The M2 slice includes a local-LLM bulk-reader pilot, but money is not binding: the spike projects USD 14 to 26 for all 115 pending documents with hosted readers, while operation derives USD 42 to 55 for a full pass over 278 objects, the wrong population (the 254 extracted are replayed without an LLM). A local reader saves about USD 10, costs GPU days on a shared service, and adds a second method family to calibrate.

**Fix.** Correct operation §7.1/§7.2: the M2 pass is the 115 pending documents at USD 0.03 to 0.08 each plus margin for chunking and repair (about USD 15 to 30); keep the USD 3 per-document cap. Keep the local-reader pilot as a bounded M2 item (one long document, throughput and checker agreement).

**Author decision.** Keep the local-reader pilot at M2 (bounded to one long document) or defer it to M4? Recommended: keep it bounded at M2 since C3 asks for local compute first and the cost is one run; defer if GPU time on padme is contended.

**Outcome.** M2 cost corrected in 954d6e84; the rest resolved by the author's rule of 2026-09-30 (autonomy; no author audit), in the commit "docs(jetp): autonomy correction, no machine judgement routed to the author" (branch `t1710-autonomy-correction`): the local readers are the default, one model per GPU, selected and calibrated on OpenRouter before installation, and the hosted model is the arbiter.

### W1-53 (minor, M2)

**Finding.** The 512,000-byte ceiling and country-year shard rule cover tables, but `line-fields/<document_id>` has no shard rule, so a long document or bulk bundle exceeds the ceiling and the pre-commit hook rejects it at M2.

**Fix.** Storage §1: a per-document field file above the ceiling is split into `line-fields/<document_id>.d/NN.csv`, numbered, joined in order, with the same pending-marker rule (and the living-document year shard of W1-14).

**Outcome.** fixed in fd7c1f4c; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-54 (minor, M2)

**Finding.** Milestone tags disagree or cannot be audited: Q14 is M3a/M4 while operation tags 'one run, one report' M2; Q15 is M3b while operation §8's M2 minute logging cites it (an M2 rule citing an M3b requirement, failing C8's own test); DA6 records a class at M3a with no consumer and no column; extraction §6.4 builds transcription at M2 while DA4 accepts a disposition naming the format. Most rules carry no requirement id, so C8 cannot be checked.

**Fix.** Retag Q14 'M2 for hand-launched runs (C4), M3a discovery, M4 scheduled' and Q15 'M2 record, M3b state'. Add a `class` column to `documents` at M3a or move DA6's recording to M4 with the `series` flag kept for parser selection. Rephrase C8's test at section granularity and extend requirements §9 with a reverse map (section to requirements) for M2 and M3 sections; a section mapping to nothing moves to M4.

**Outcome.** fixed in 954d6e84; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-55 (minor, M2)

**Finding.** Documents written by interested parties are fed verbatim to LLM readers and checkers with no treatment as untrusted input. Text invisible to a human (CSS-hidden, white-on-white, comments) is read without distinction, and an injected statement passes the locator check because the text exists in the bytes and can steer reader and checker alike. The same exposure applies to triage at M3a.

**Fix.** State in §6.3 and collection §9 that readers and checkers are called without tools, network or file access and receive the text layer as quoted data. Add a planted instruction to the §12 control document that must not alter any proposal. Mark visibility only for the cheap unambiguous cases (HTML `hidden`, inline `display:none`), exclude OCR layers; finer marking is M4.

**Outcome.** fixed in fd7c1f4c.

### W1-56 (minor, M2)

**Finding.** N2 excludes natural persons only as a modelled class; verbatim fields and speaker attributions keep whatever the publisher printed (officials' names, contact emails and phones on project pages), committed in git and released immutably under persistent identifiers. Removal requests cannot be met and purging git history later is painful.

**Fix.** §3 and §4: contact columns (email, phone, personal address) are declared out of scope per document and not extracted; a quoted speaker is recorded as the office or institution as printed, the person's name only when the publisher prints it as signatory of an in-scope document. Results §5: a regex screen for emails and phone numbers in release validation lists hits for the author. Error-report contact details stay in the ticket (W1-37).

**Outcome.** fixed in fd7c1f4c.

### W1-57 (minor, M3a)

**Finding.** 'Not published' is a finding about an authority, but the recorded search that justifies it is defined only for a claim traced to a primary document (publisher channel, partner channel, one web search), so for an authority the channel being tested is the standard. Collection §8 lists 'declared but not published' on the unreachable list while §3 and §13 say not-published is not on it; DA9 expects 'excluded by robots rules' entries §8 has no reason for; F8's 'unreadable', 'not sought' and 'loss of visibility' have no home in collection.

**Fix.** Cross-reference §7's standard from §3 and say how its three parts read for an authority and for a listed project. Define §8's reason as 'a named document another document says exists, never found' or delete it; align DA9's test with §8's reasons. In F8 say where the other states are recorded: 'unreadable' in the extraction disposition, 'not sought' as a frame entry with no round (which the stopping rule forbids), 'loss of visibility' at M4, or drop them.

**Outcome.** fixed in 2034d335.

### W1-58 (minor, M3a)

**Finding.** The secondary-to-primary pass 'is a search channel class like the others', but it is not in the eight-row class table, runs per claim not per round, and the stopping rule does not say whether it counts for frame coverage or the quiet tail. The class table's row for secondary trackers points to 'leads (section 6)', which is known items.

**Fix.** State that the pass is how the 'secondary trackers and news' class is searched: its claims traced for one country in one language are that class's round and its admissions that round's yield; correct the cross-reference to §7; add a check row.

**Outcome.** fixed in 2034d335.

### W1-59 (minor, M3a)

**Finding.** 'Traceability rate' names two rates (collection §7 and Q10: share of tracker claims traced to a primary, M3a; F19 and results §2: coverage of the CRS and IATI matching, M3b), neither listed in results §4. The M3a rate counts 'identified, unreachable' as traced although nobody read the document, so it overstates support most where the primary is hidden.

**Fix.** Name them 'tracker traceability rate' (collection §7, Q10, results §4) and 'matching coverage rate' (F19, results §2, defined in fusion §5). Publish the distribution over the five outcomes; the headline tracker rate counts held and admitted only, with 'identified, unreachable' beside it; Q10 reads 'traced to a primary document read by the Observer'.

**Outcome.** fixed in 2034d335.

### W1-60 (minor, M3b)

**Finding.** Q20's M3b part (broken trails and pending judgements 'appear where the author looks') is assigned to Presentation and Operation, but presentation has no such page, operation puts supervision pages at M4, results puts the broken-trail check in the build, and results §10 says the Observatory shows exactly one release and computes nothing outside it. No document meets the requirement.

**Fix.** Reword Q20's M3b part: broken trails appear in the build and run reports (results §5, operation §8); pending judgements in the served candidate-status decision record storage §4 already promises, named in presentation as a page under About or the paper trail (a sorted list on Methods or document rows). Keep countries and documents without new statements, and cross-run flags, at M4; correct the §9 row.

**Outcome.** fixed in 9c8b3633.

### W1-61 (minor, M3b)

**Finding.** §2 lists six date roles; §4 adds `period_start`, `period_end` and a `target` timing; extraction §11 lists nine; storage's `date_role` rule takes values only from terms in force and §5's alignment test fails on any value not a term. Either the test rejects the ontology or the validator rejects flow intervals and targets.

**Fix.** One closed list of nine date roles in ontology §2, cited from §4 and from extraction §11 instead of repeated.

**Outcome.** fixed in 9c8b3633.

### W1-62 (minor, M3b)

**Finding.** 'The two figures are the low and the high end of the result's range' fixes the direction wrong for referent counts and de-duplicated sums (accepting more matches lowers them) and presents a two-point sensitivity analysis as if it were an interval on the true value.

**Fix.** Replace with: the range is the minimum and maximum of the two figures; which threshold gives which end depends on the result kind; it is the result's sensitivity to the declared thresholds, not a probability interval. Add the label 'sensitivity to matching' to presentation for such ranges; no grid computation.

**Outcome.** fixed in 9c8b3633.

### W1-63 (minor, M3b)

**Finding.** Pedigree and independence are principles with no data home and no rule: no column holds a pedigree, the NUSAP dimensions have no scale or anchors, independence requires copy detection the spec does not attempt, and no result reports independent supports. A rule nothing implements would be built as an unreviewed heuristic and shown as evidence quality, against C8.

**Fix.** Rewrite the paragraph: pedigree is not a stored score; it is what a judgement reads from the publisher category, document type, extraction method and the relations that fold copies, and the judgement records which it weighed in its basis. Independence: two statements are independent supports when, after folding `same_as`, `translation_of` and `cites`, they have different publishers; undetected copying is not excluded. Publish independent-support counts at M4, or M3b only if F19 needs them.

**Outcome.** fixed in 9c8b3633.

### W1-64 (minor, M3b)

**Finding.** Crosswalk rows are SKOS mappings with no mapping strength, although the Traceability paragraph requires `mapping_relation` and warns against `exactMatch` on similar labels; `D. Completed` to `closed` and `implementation` to `implementation` are stored alike, so counts by shared status mix exact and broad mappings. The planned SKOS export covers classes and relations, which SKOS does not model, and `terms` has no hierarchy column.

**Fix.** Add `mapping_relation` to both crosswalks, required at acceptance; a shared-status or sector result states the weakest mapping among the rows it used (results §2). Drop `broader_term_id`. State that the M4 SKOS export covers `kind = value` lists only, one ConceptScheme per `list`.

**Outcome.** fixed in 9c8b3633; the `broader_term_id` column the fix drops does not exist in the DDL or the contract; schema or validator change written as a storage-contract target and an exit criterion of ticket 1702.

### W1-65 (minor, M3b)

**Finding.** The descriptor reinvents an established manifest and leaves its format open, as do the data dictionary and the 'standard, harvestable' metadata record, so F29 and F31 are checkable only against a private format. The descriptor records the persistent identifier yet is hashed before the deposit that normally mints it.

**Fix.** Name in results §5 and §6: a Frictionless `datapackage.json` as the descriptor with a Table Schema per file generated from the DDL as the data dictionary; the DataCite record Zenodo produces as the metadata record, with IsNewVersionOf, IsPreviousVersionOf and IsSupplementTo for the release chain and code; the identifier is reserved before the build so the descriptor can name it.

**Author decision.** Adopt Frictionless Data Package plus DataCite via Zenodo as the named formats, or RO-Crate (JSON-LD, can carry the run record), or leave the format private? Recommended: Frictionless plus DataCite; both are lightweight, generated from the DDL, and need no heavy dependency.

**Outcome.** decided by the author 2026-09-30: Frictionless Data Package for files and data dictionary and DataCite metadata through Zenodo, both generated from the DDL, at M3b; RO-Crate with W3C PROV recorded as the M4 option; applied in "docs(jetp): release licence position, report tickets, named formats and M3b accounts".

### W1-66 (minor, M3b)

**Finding.** F16's test needs 'a milestone known only by the year of a report is an interval ending at the report date', and the §9 table names extraction §11, ontology and fusion §4 as its homes, but extraction gives only the timings printed and fusion §4 is Occurrence. No document derives event bounds from a report date.

**Fix.** Add the derivation as a fusion §7 timeline rule (Evidence, not reading): an event stated without its own date gets an upper bound equal to the statement's report or reporting-cutoff timing and an open lower bound; correct the F16 row of §9.

**Outcome.** fixed in 9c8b3633.

### W1-67 (minor, M3b)

**Finding.** A cumulative 'disbursements to date as of <date>' figure (ADB project pages) is a position, but money is typed only as a flow with a period or a single event timing, so it is read as a movement on the as-of date or a period with an invented start; successive snapshots double-count disbursement.

**Fix.** Extraction §11: a figure printed as cumulative or 'to date' is a flow whose `period_end` is the as-of date and whose `period_start` has precision `unknown`, bounded below by the agreement's earliest printed date when one exists. Fusion §7: such a flow is a closing-position candidate and never a movement. Add the case to §15.

**Outcome.** fixed in 9c8b3633.

### W1-68 (minor, M3b)

**Finding.** The ZAF Investment Register prints 'Amount: Pledged', 'Total US$' and 'Total ZAR' for one pledge; by §11's rule the row yields three `amount` observations, tripling every sum. Storage says a publisher's own conversion is a `rates` row citing the line, but extraction never mentions it.

**Fix.** Add to §11: a column the publisher derives from another by a printed rate is the same measure, not a second one; the reading rule declares which column is original and each derived column becomes a `rates` row citing the line when the rate can be recovered, else nothing. Add the red test 'a row with three money columns yields one `amount`' to §11's checks.

**Outcome.** fixed in 9c8b3633.

### W1-69 (minor, M3b)

**Finding.** §9 requires a correction's editorial note to list the paper figures it changes, but nothing holds which figures papers, the article or the book cite: N11 puts manuscripts outside the Observer, the provenance index is a build-time check never served, and BK-2 (pinned release) versus Q7 (correction reaches every claim) are not reconciled. The check is unsatisfiable as written.

**Fix.** Results §8: a product citing a release supplies a machine-readable list of (result_id, occurrence locator in the product), kept with the release's metadata under F29 and not served (F23); the list of §9 is produced from it.

**Outcome.** fixed in 9c8b3633.

### W1-70 (minor, M3b)

**Finding.** Results §2 lists 'accounts (fusion §7)' among the results the M3b release must contain, but no requirement names accounts, while the reconstruction machinery (opening, disjoint cover, closing, residual), the Markers account, `marker-coefficients`, `deflators` and the `flow_coverage` roles are all tagged M3b. This is C8's own test failing on the most expensive M3b machinery.

**Fix.** In results §2 cite OBS-1, F14, F19 and Q11 for accounts; retag `deflators` to later; tag Markers and `marker-coefficients` M3b only if the F19 comparison uses CRS climate-marked amounts, else M4; keep the presentation as is.

**Author decision.** Scope: are accounts (opening, movements, closing, residual) an M3b result, and does the F19 comparison use CRS climate-marked amounts (which would keep the Markers machinery at M3b)? Recommended: accounts at M3b under OBS-1 and F19 with `deflators` deferred; Markers to M4 unless F19 needs marked amounts.

**Outcome.** decided by the author 2026-09-30: accounts (opening, movements, closing, residual) are an M3b result serving OBS-1 and F19, deflators deferred; the Markers machinery moves to M4 unless F19 needs climate-marked amounts, stated as a condition; applied in "docs(jetp): release licence position, report tickets, named formats and M3b accounts".

### W1-71 (minor, M3b)

**Finding.** The design names specific LLMs and prices, the spike hit model churn (HTTP 429, three provider failures in 33 calls), and nothing says what happens when a reader or checker is retired, repriced or replaced between M2 and M3b or M4. A replacement reader silently changes statement counts between documents read at different times, and 'never switches vendor' leaves no sanctioned fallback mid-campaign.

**Fix.** Add one sentence to extraction §6.3 and operation §5: a replacement reader or checker is admitted after passing the §12 controls and reaching a stated minimum agreement with the author-checked statements of Q17 on a fixed sample stratified by language; the coverage report states which method version read each document class. Drop the coding-agent vendor clause, outside the specification.

**Outcome.** fixed in fd7c1f4c.

## Batch 2: external review

The cross-vendor pass on draft v0.1: OpenAI GPT-5.5 and Mistral Large 2512,
each as a critical and a sympathetic reviewer, reviewing the ten documents
as they stood on `main` after the fixes of batch 1 and before the author's
decisions on autonomy and on the prose statement shape. The reviews and the
synthesis that lists these findings are in [`external/`](external/README.md).
Each row was checked against the documents on `main` at the time of
application, not against the reviewed draft.

Of the 31 rows, 24 are applied, 2 were already fixed on `main` (a check or a
sentence added), 1 is moot under the author's rules, and 4 took the
author's recommended default on 2026-09-30 (two of them applied earlier in
their author-independent part). Every
external request for an author sample or an author review load is moot
under the rule that no machine judgement is routed to the author; the
compensating control is X-01.

| ID | Severity | Milestone | Author? | Outcome |
|---|---|---|---|---|
| X-01 | major | M2 | no | applied |
| X-02 | major | M2 | no | applied |
| X-03 | major | M2 | no | applied |
| X-04 | major | M2 | no | applied |
| X-05 | major | M2 | no | applied |
| X-06 | major | M3b | yes | default accepted by the author 2026-09-30 |
| X-07 | major | M2 | no | applied |
| X-08 | minor | M3a | no | moot |
| X-09 | minor | M2 | no | applied |
| X-10 | minor | M3a | no | applied |
| X-11 | minor | M2 | no | applied |
| X-12 | minor | M3b | no | applied (tagged M4) |
| X-13 | minor | M2 | no | applied |
| X-14 | minor | M3b | no | already fixed; check added |
| X-15 | minor | M3b | no | applied |
| X-16 | minor | M3a | no | applied |
| X-17 | minor | M3b | yes | default accepted by the author 2026-09-30 |
| X-18 | minor | M3b | no | applied |
| X-19 | minor | M3b | no | applied |
| X-20 | minor | M3a | no | applied |
| X-21 | minor | M3b | no | already fixed |
| X-22 | minor | M2 | no | applied |
| X-23 | minor | M2 | no | applied |
| X-24 | minor | M3b | yes | default accepted by the author 2026-09-30 |
| X-25 | minor | M4 | no | applied |
| X-26 | minor | M3b | yes | default accepted by the author 2026-09-30 |
| X-27 | minor | M2 | no | applied |
| X-28 | minor | M3b | no | applied |
| X-29 | minor | M3b | no | applied |
| X-30 | minor | M3b | no | applied |
| X-31 | minor | M2 | no | applied |

The four commits of this batch are cited by subject: (A) "docs(jetp):
reference answers as the one human check, one decision-authority table";
(B) "docs(jetp): assertion index, attributed party, times per table and
heading rows"; (C) "docs(jetp): local-only reading, closed-room adapters,
closed material, runbook and handover"; (D) "docs(jetp): known-item
recovery, finite tests, neutral wording, account causes and PROV reading".

### X-01 (major, M2)

**Finding.** With no machine judgement routed to the author, nothing
specified the held-out reference answers that are now the only human check:
their size, strata, freezing, refresh after a model change, separation from
prompt tuning, and the error that two agreeing readers share
(agree-but-wrong). Reviewers asked for human review of high-impact items,
which the author's rule excludes. (GG, GS, MG, MS)

**Fix.** Extraction 6.3: the reference answers are the hand-made lines,
split by recorded seed into a tuning and a held-out part, stratified by
country, language and classification, frozen per method version and
rescored on any change of reader, arbiter or prompt; each calibration
reports per-term precision with its interval, calibration error and the
agree-but-wrong rate; a stratum under 30 items is reported as uninformative.
Q5 states that no person reviews high-impact items and what is published
instead; releases carry the calibration record; a §12 check keeps tuning and
held-out apart.

**Outcome.** applied in (A).

### X-02 (major, M2)

**Finding.** "No automatic truth" (N4) read as forbidding what the panel of
LLM readers now does (admitting statements and documents); nowhere said who
decides each kind of decision, when it is in force and how it is reversed.
(GG)

**Fix.** One decision-authority table in fusion 3 (adopted rule, panel,
author; in force when; what downstream accepts; reversed by), cited by N4,
which is reworded to require a recorded judgement rather than a person.

**Outcome.** applied in (A).

### X-03 (major, M2)

**Finding.** A prose sentence carrying several assertions collides with the
uniqueness of (`sha256`, `locator`) under the shortest-span label rule. (GS)

**Fix.** One statement per assertion on the same anchors, told apart by an
assertion index in the locator; the admission check and a §15 row test it;
the locator syntax change is a storage target and an exit criterion of
ticket 1702.

**Outcome.** applied in (B).

### X-04 (major, M2)

**Finding.** F1 says a statement "carries" its publisher, but `lines` has no
publisher: joint publications, annexes by one partner and commissioned
reports cannot be attributed at line level. (GG, GS)

**Fix.** F1 defines the publisher as the document's publishers or the one
party the document attributes the statement's part to; extraction 3 and the
ontology gain the attributed party; target column `lines.attributed_party_id`
(nullable, empty meaning jointly). Not required when a document has several
publishers, as proposed, since extraction cannot always tell. The quoted
speaker was already a verbatim field.

**Outcome.** applied in (B); exit criterion of ticket 1702.

### X-05 (major, M2)

**Finding.** The author decided that the panel proposes new line classes
and only the author adopts them, but not how adoption takes effect.

**Fix.** A proposed class is a candidate and classifies nothing; adoption is
a new method version that rereads the statements recorded as unclassifiable;
the list is closed between versions (extraction 3, ontology 4).

**Outcome.** applied in (A).

### X-06 (major, M3b)

**Finding.** The finance model omits guarantees, mobilised private finance,
co-financing, repayment, refinancing and cancellation; agreement, operation
and tranche are conflated; "pledge is not an IATI transaction type";
cross-currency totals will often be impossible. (GG)

**Fix.** Author-independent part: pledge is an IATI transaction type since
standard 2.03 (incoming and outgoing pledge), so that claim is wrong; an
operation is an agreement and a tranche or successive loan an agreement of
its own under `tranche_of` (ontology 2); a total across currencies is often
impossible and a result then reports per currency (fusion 7). Cancellation
is already a money state, and refunds, repayments and cancellations already
stay their own measures (fusion 7).

**Author decision.** Which finance instruments enter the closed measure list
at M3b? (a) extend `flow_type` with IATI loan repayment and credit guarantee,
and record mobilised private finance and co-financing as `amount`
observations whose `party_in` roles say whose money it is (F17), refinancing
out of scope; (b) declare guarantees, mobilisation, co-financing, repayment
and refinancing out of scope at M3b, kept verbatim on lines; (c) a full
finance-instruments section mapped to IATI and CRS. Recommended: (a); F17
already requires mobilisation and co-financing kept apart, and the two IATI
codes cost two `terms` rows.

**Outcome.** applied in part in (D); the rest: default accepted by the author 2026-09-30; applied in "docs(jetp): apply the author's defaults for the last five decisions and the licence": option (a), two
`flow_type` terms (`loan_repayment`, `credit_guarantee`), mobilised and
co-financing amounts with their funding roles (ontology 4), fusion 7.

### X-07 (major, M2)

**Finding.** Document text goes to hosted LLM providers with no per-source
control and no record of the provider's retention and training settings.
(GG, GS)

**Fix.** A document whose terms forbid third-party processing by an explicit
reservation is read locally only, and what its readers leave open ends
undetermined (extraction 6.3, operation 5, collection 1; target column
`documents.hosted_reading`); every hosted call requests no collection and no
retention, uses only an endpoint that honours that and fails closed; `runs`
records the settings. The legal position stays with the legal note and the
review before go-live.

**Outcome.** applied in (C); exit criterion of ticket 1702.

### X-08 (minor, M3a)

**Finding.** Archive captures and registered-session fetches should be
permitted only where the recorded terms allow, the route logged, and the
robots-override policy approved once by a human. (GS, GG)

**Fix.** None applied.

**Outcome.** moot under the author's rules: the route of every retrieval is
already logged (its rung in `collection_method`), the robots-override policy
is the author's own C6, and whether a site's terms permit a
registered-session or archive fetch is a legal question for the legal review
that gates go-live (legal note §1); no legal service is consulted while the
Observer is undeployed.

### X-09 (minor, M2)

**Finding.** The release screen of W1-56 covers contact details only; names
of persons in speaker and verbatim fields, and a takedown route, are not
covered. (GG, GS)

**Fix.** Results 5: the screen also lists natural-person names other than
signatories in prose speaker and verbatim fields; results 9: a takedown is a
report, granted by supersession and, for released content, withdrawal and a
correction release. The office-not-name rule was already in extraction 4.

**Outcome.** applied in (C).

### X-10 (minor, M3a)

**Finding.** No rule for a held document later found non-public or leaked.
(MS)

**Fix.** Collection 9: an admission in error, superseded with its
statements; bytes removed from the store, the off-site copies and
unpublished releases; register row, hash and reason kept; published releases
withdrawn and corrected; the git-history and backup limits stated. N13
points to it. No new disposition kind was needed.

**Outcome.** applied in (C).

### X-11 (minor, M2)

**Finding.** Parsers and renderers run with network and credentials in
reach, and the adversarial fixtures stop at one planted instruction. (GS)

**Fix.** Extraction 5: adapters run without network or credentials and
execute nothing (macros, scripts, embedded objects, form actions, external
links). Extraction 12: a sandbox fixture, and hidden-markup fixtures at M2;
white-on-white, overlays, annotations and text-layer conflicts at M4, as
W1-55 decided for the finer detection.

**Outcome.** applied in (C).

### X-12 (minor, M3b)

**Finding.** No mapping from ledger objects to W3C PROV. (GG, GS, MG, MS)

**Fix.** A mapping table (Entity, Activity, Agent and the core relations) in
ontology 0, with no PROV engine and no RDF. Tagged M4, since the author
decided that RO-Crate with PROV is the M4 option (W1-65).

**Outcome.** applied in (D).

### X-13 (minor, M2)

**Finding.** No single statement of which times each table holds and which
are eligible for the cutoff K and for a correction overlay. (GG, GS)

**Fix.** Storage 1: a "Times per table" table (times held, what places a row
in the state at K, whether an overlay may correct it).

**Outcome.** applied in (B).

### X-14 (minor, M3b)

**Finding.** Can a correction overlay include a line extracted after K from a
snapshot retrieved before K? (GS)

**Fix.** Storage 1 now says outright that such a line is a new line, not a
supersession, and counts from the next regular release; results 14 gains the
check.

**Outcome.** already fixed on `main` (the overlay admits only supersession
rows on rows recorded on or before K; fusion 8 bars discoveries); sentence
and check added in (B).

### X-15 (minor, M3b)

**Finding.** Depth-one equality lacked its reason; "an external identifier
decides" is too strong (IATI identifiers reused for umbrella programmes, LEI
branches) and clashed with the adopted-rule list; no cluster metric named.
(GG, GS)

**Fix.** Fusion 3: the reason (pairwise likelihoods do not compose along a
chain); B-cubed named; an identifier decides only in a scheme declared as
naming exactly one organisation, other codes being strong proposers; F12,
the adopted-rule list and storage 4 follow.

**Outcome.** applied in (A).

### X-16 (minor, M3a)

**Finding.** The known-item list could be drawn up after the fact, recovery
is not stratified, and the public figure is called recall although known
items are more visible than average. (GG, GS, MG)

**Fix.** Collection 6: compiled apart from the searches, its hash recorded
before round one; recovery also per country, publisher category, document
type and language, as counts; published as known-item recovery. DA8's test
follows.

**Outcome.** applied in (D).

### X-17 (minor, M3b)

**Finding.** Known-item recovery is one estimator; capture-recapture over
independent search channels would give a second. (GG, MG)

**Fix.** None applied; collection 6 keeps it as later work.

**Author decision.** Does the second recall estimator (capture-recapture on
the overlap of independent search channel classes) move from later into an
earlier milestone? (a) keep it later, but have the M3a `candidates` table
record every round that found a candidate, not only the first, so the
estimate can be computed afterwards without new collection; (b) compute it
at M3a beside known-item recovery; (c) at M3b. Recommended: (a); with about
40 known items a second estimator adds little now, and recording every
finding round keeps the option open at almost no cost.

**Outcome.** default accepted by the author 2026-09-30; applied in "docs(jetp): apply the author's defaults for the last five decisions and the licence": option (a), collection 6 and the `candidates` table.

### X-18 (minor, M3b)

**Finding.** "Reproducible" is overclaimed when bytes cannot be
redistributed; nothing says how much of a result a third party can check.
(GG, GS)

**Fix.** Results 4: per result and per release, the share of supporting
statements by public-copy kind; Q8: reproducible from the release and the
archive, inspectable by others as far as a public copy exists.

**Outcome.** applied in (D).

### X-19 (minor, M3b)

**Finding.** Soft tests (F26, Q13, Q16, Q18, Q21, C8) cannot be decided:
samples without size or failure rule, reviews without a checklist,
"substantive narrative claim" undefined. (GG, GS, MS)

**Fix.** Requirements 2.1: sampled tests draw ten items by default with a
recorded seed, run by an agent or the reviewer, never the author, one
failure failing; review tests search a word list and read the hits; a test
that fits neither is a principle. Q6 defines the claim; F26 says three
sentences.

**Outcome.** applied in (D).

### X-20 (minor, M3a)

**Finding.** Q16 "no finding in its own voice" contradicts the documentary
findings the Observer does make (not published, stopped by cap, traceability
rate). (GS, GG)

**Fix.** Q16: three kinds of own finding (documentary, procedural, declared
calculation) and none of compliance, blame, merit or cause, with the wording
for gaps; the presentation holds the evaluative word list the build
searches.

**Outcome.** applied in (D).

### X-21 (minor, M3b)

**Finding.** The public page "Statements" shows observations (D3) while the
builders call lines (D2) statements. (GS)

**Fix.** None needed.

**Outcome.** already fixed on `main`: the language document ("Words that
span steps") and the presentation state that the Statements page shows
observations; the page name is the author's and stays.

### X-22 (minor, M2)

**Finding.** `projects.aliases` is a list column against the no-list rule;
`groups` holds one heading though a line can sit under several; `GLB` looks
like a pseudo-country; sharding may use an inferred country. (GG)

**Fix.** Verified: the first two hold and become targets (drop
`projects.aliases`; a `line-groups` relation table, with the heading chain
as the interim rule); `GLB` was already declared a storage bucket, not a
country; the shard key is the row's own `recorded_at` year and country (or
the cited line's), as the writer checks, now written.

**Outcome.** applied in (B); exit criteria of ticket 1702.

### X-23 (minor, M2)

**Finding.** Normative text holds machine details (`~/.local/bin/uv`, the SSH
command, the named llama service). (GG)

**Fix.** A runbook section at the end of operation holds them as facts, not
rules; sections 2 and 3, the agents' prohibitions and the checks name the
roles.

**Outcome.** applied in (C).

### X-24 (minor, M3b)

**Finding.** One-person continuity: no handover of credentials, ownership
and restore steps, and nobody who can act on a takedown or withdrawal when
the author cannot. (GG, GS, MG, MS)

**Fix.** Operation 9: a handover note before the first release identifier
(credential locations by provider, ownership of the repository, deposits
and domain, restore steps), reread at each release; C10's test checks it.

**Author decision.** Is a deputy named for takedown and withdrawal only?
(a) name the deputy at the legal review before go-live, together with the
legal publisher and the person who answers a reply request within three
days (legal note §5); (b) name a colleague now, before the M3b release;
(c) no deputy: withdrawal waits for the author, and the handover note
suffices. Recommended: (a); the legal review decides who the publisher is,
and the deputy follows from it.

**Outcome.** applied in part in (C); the deputy: default accepted by the author 2026-09-30; applied in "docs(jetp): apply the author's defaults for the last five decisions and the licence": option (a),
operation 9.

### X-25 (minor, M4)

**Finding.** Nothing tracks drift of sources, schemas, models, terms and
ontology to 2030, and weekly snapshots multiply restatements. (GS, MG, MS)

**Fix.** Operation 11: a drift register reviewed at each release, and an
adaptive refetch cadence set from the observed rate of change within N6's
weekly maximum.

**Outcome.** applied in (C).

### X-26 (minor, M3b)

**Finding.** A published figure may lose its caveats; full traceability of
every narrative claim at M3b may be overbuilt; whether the display-to-result
map is served was open. (GG; G0 argued the opposite on traceability)

**Fix.** None applied. Whether the map is served is already settled: it is a
build-time check, never served (W1-69).

**Author decision.** Traceability scope and caveats at M3b: (a) keep Q6 as
written (every number, status and substantive narrative claim traced at
M3b) and show, beside each affected figure, the exclusions and blocked parts
that bear on it; (b) limit M3b traceability to tables, figures and headline
metrics, narrative claims at M4, with the same caveat beside each figure;
(c) keep Q6, with exclusions only in the release's editorial note, as now.
Recommended: (a); X-19 now bounds what a substantive narrative claim is, and
results already carry their blocked parts and thresholds, so the caveat
renders data the release holds.

**Outcome.** default accepted by the author 2026-09-30; applied in "docs(jetp): apply the author's defaults for the last five decisions and the licence": option (a), requirements Q6.

### X-27 (minor, M2)

**Finding.** Nothing stops a requirement being counted as met while a column
it needs is still a target, which let W1-01 arise. (GG, GS)

**Fix.** Requirements 2.2 and storage 1: a requirement is not met at a
milestone while a table or column its rules need is still a target; the
target table's Milestone column already says when, so no new column.

**Outcome.** applied in (B).

### X-28 (minor, M3b)

**Finding.** An account's missing residual is not labelled by cause. (MG)

**Fix.** Fusion 7: an account that reaches no exact closing or residual names
its cause from one list, and results count accounts per cause.

**Outcome.** applied in (D).

### X-29 (minor, M3b)

**Finding.** The requirements do not place the Observer among climate-finance
trackers, CRS, IATI, and preservation and provenance models. (MG)

**Fix.** Requirements 1: a "Neighbours" paragraph.

**Outcome.** applied in (D).

### X-30 (minor, M3b)

**Finding.** A partner's withdrawal or a lapsed partnership had no stated
representation. (MS)

**Fix.** Fusion 9: a check row (the withdrawal is a dated event; the
partner's `party_in` rows end at its date by later judgements; nothing
earlier deleted).

**Outcome.** applied in (D).

### X-31 (minor, M2)

**Finding.** The language document should define locator, knowledge cutoff,
referent and match threshold. (MS)

**Fix.** Locator added under "Words that span steps"; the other three were
already defined there.

**Outcome.** applied in (B).
