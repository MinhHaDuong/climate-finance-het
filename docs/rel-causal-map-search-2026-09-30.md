# REL causal-map lane: OpenAlex and EconLit searches, 2026-09-30

Ticket 1652, child of 0700. Protocol rows "Carte causale" and "OpenAlex et
EconLit" of `conception/rel-audit-finalisation-corpus.md`, outside the Sud
stratum (1530, 1653). Harvest before filtering: this lane delivers candidates
with provenance; it does not decide ICF inclusion (1655 screens the whole pool
once). All counts below come from the archived run; derived quantities are
labelled as such.

Archive (outside the repo): `~/data/projets/climate-finance-het/rel_causal/2026-09-30/`
on padme, copied to doudou at the same path. `MANIFEST.sha256` (raw runs, judge,
hand validation, configs, logs; SHA-256 of the manifest file
`aa7e2a34062ed16ff02ebd89d4e7f565149d74ddfa92b3b8c21fd474c082880a`) and
`MANIFEST_analysis.sha256` (yields, sentinel recall, delivery). Both manifests
verified on doudou after the copy.

## Families of the causal map

`config/rel_causal_families.yaml` groups the 126 arcs of Annex A of
`conception/carte-causale-icf-co2.md` into 22 mechanism families, each arc in
exactly one family (`tests/test_rel_causal_families.py` parses Annex A and fails
on an unassigned, duplicated or unknown arc). The expectation of each family was
recorded before any search.

| Group | Families (arcs) |
|---|---|
| 1: routing to grid, cost of capital, private investment, capacity; debt and spending substitution | grid (2), cost_of_capital (5), private_mobilisation (5), implementation_capacity (9), debt (4), fiscal_substitution (4) |
| 2: emissions outside electricity; induced land effects | construction_emissions (3), end_use_efficiency (4), land_spillovers (7) |
| 3: comparators and leakage | fossil_finance (4), carbon_credits (4), forest_leakage (3) |
| Not priority, empirical | allocation (10), measurement (7), donor_additionality (4), growth_scale (7), policy_channel (3), renewable_deployment (4), redd_results_payments (8) |
| Not priority, theoretical a priori | confounding (9), physical_identities (17), deforestation_drivers (3) |

Map-free themes, searched so that the map does not hide what it does not draw:
total effect (a path, not an arc), transport and other sectors, adaptation,
forest beyond the drawn paths, loss and damage, justice, critical approaches,
accounting categories and governance, private finance, international carbon
markets.

## Query matrix

`config/rel_causal_search.yaml`, fixed before the run; the exact strings of every
row are in the archive (`runs/*/registry.csv`, `runs/openalex_20260930/matrix.csv`)
and in the delivery registry.

- Priority families: intervention + mediator (IM), intervention + outcome (IO),
  synonyms (SY) and country/sector (CS) in English; IM and IO in French and
  Spanish; sentinel identifiers (SI) as a citation search on the family's tuning
  sentinels (OpenAlex `cites:`). Other families: one English IO string (SI when a
  tuning sentinel exists). Themes: one English string each; the Sud lane already
  ran French, Spanish and other-language theme strings.
- 132 OpenAlex rows (12 families x 8 strings, 10 other families, 10 themes, 16
  citation searches); every row has an EconLit twin, plus 22 JEL rows and 12
  working-paper rows written for EconLit only (166 EconLit strings).
- Sentinels: `config/rel_causal_sentinels.csv`, 49 works fixed before the run,
  17 tuning, 31 hold-out, 1 without DOI. Hold-outs never enter a query (a test
  enforces it). Seeds: works named in the causal map (Kretschmer et al. 2013,
  Kim 2018, Roopsind et al. 2019, Kling et al. 2018, Toetzke et al. 2022,
  Zoungrana et al. 2024, West et al. 2023, Stadelmann et al. 2011, the aid-growth
  papers), others from knowledge and a pre-run OpenAlex title probe, and six Sud
  sentinels for the themes. Every DOI resolved to its title in OpenAlex before the
  run; two DOIs recalled from memory were wrong and corrected (Steffen and
  Schmidt 2018 ends in `-3`; Pfeiffer and Mulder 2013 is `eneco.2013.07.005`).
  No sentinel was found for grid, fiscal substitution or construction emissions.

## Runs

| Run | Rows | Received | Completed | Stopped |
|---|---|---|---|---|
| OpenAlex, full matrix, cap 800 records | 132 | 34,183 | 100 | 26 record cap, 6 HTTP 500 |
| OpenAlex b, the 6 failed rows, cap 800 | 6 | 4,222 | 2 | 4 record cap |
| OpenAlex c, 12 capped priority rows, uncapped | 12 | 11,484 | 10 | 2 HTTP 500 |
| bibCNRS EDS, EconLit strings on RePEc and ECONIS, cap 500 | 295 | 11,352 | 291 | 4 record cap |

A later run supersedes an earlier one for a row unless it is unfinished and
received fewer records (implementation_capacity-IM keeps the first run's 800).
After supersession, 26 OpenAlex rows remain incomplete, all recorded in the
registry and in the delivery manifest (`coverage: incomplete`): broad synonym,
country/sector and theme strings whose counts run to thousands (carbon_credits-SY
announced 66,426). The cap is a budget choice, not saturation.

**OpenAlex spend** (sum of `x-ratelimit-cost-usd`, measured): pre-run budget and
sentinel probes 0.054 USD, main run 0.224, run b 0.022, run c 0.062: **0.362 USD**,
under the lane cap of 0.40. The shared daily remaining never fell below 0.63 USD,
so the 0.30 floor was not reached. A search page costs 0.001 USD, a `cites:`
page 0.0001.

## Yield

Works are joined by DOI, then OpenAlex id, then normalised title and year.
"Absent" is tested against the refined corpus (`refined_works.csv`), the raw
merged pool (`unified_works.csv`) and the Sud search results (runs f and g of
1530).

| Lane | Raw hits | Unique works | Absent refined | Absent from all three | Not found by the other lane | Judge-relevant | of which absent from all three |
|---|---|---|---|---|---|---|---|
| OpenAlex | 40,289 | 28,531 | 22,994 | 19,981 | 26,149 | 8,034 | 3,754 |
| bibCNRS EDS | 11,352 | 7,397 | 6,232 | 5,892 | 5,015 | 1,808 | 1,001 |

By formulation (OpenAlex; "only" = works no other formulation of the lane
retrieved):

| Formulation | Unique works | Absent from all three | Only this formulation | Judge-relevant | Relevant, only this formulation |
|---|---|---|---|---|---|
| IM en | 7,789 | 5,929 | 5,028 | 2,222 | 1,093 |
| IO en | 8,608 | 4,556 | 4,890 | 2,972 | 1,440 |
| SY en | 4,660 | 3,937 | 3,784 | 956 | 560 |
| CS en | 3,929 | 2,862 | 2,952 | 874 | 504 |
| SI (citations) | 2,431 | 1,903 | 1,967 | 563 | 293 |
| TH en | 6,517 | 2,646 | 3,961 | 2,782 | 1,427 |
| IM fr / IO fr | 97 / 35 | 79 / 15 | 89 / 30 | 27 / 23 | 23 / 20 |
| IM es / IO es | 766 / 110 | 709 / 58 | 741 / 84 | 52 / 36 | 47 / 30 |

Every formulation adds works no other formulation found, including the French
and Spanish strings (138 judge-relevant works between them, 120 found by no
other formulation) and the citation searches (293). EDS JEL rows returned nothing: RePEc and ECONIS records
in EDS carry no `CC` field. Per-family and per-search yields:
`analysis/yield_by_question.csv`, `analysis/yield_by_search.csv`.

### The family-relevance judge

"Relevant" = the record addresses the mechanism of the family whose search
retrieved it, with international climate, energy or forest finance or aid as the
treatment. This is a family-relevance judgment for lane yield, **not** the ICF
inclusion screen. Model: Claude Haiku 4.5 (575 pairs through OpenRouter, then
`claude-haiku-4-5` through the Anthropic API after OpenRouter refused with HTTP
402); prompt `config/rel_causal_judge.yaml` (SHA-256 in `judge/judge_runs.jsonl`),
labels `judge/labels.jsonl`: 45,254 (work, family) pairs, 12,253 relevant,
24,170 not, 8,834 unsure (counts before the 8 pairs relabelled after a DOI fix).
Tokens through the Anthropic API: 5.92 M in, 0.44 M out, about 8 USD at list
prices (derived, not billed amount).

**Validation.** A blind stratified sample of 60 pairs (25 judged relevant, 25
not, 10 unsure; seed 1652) was read by hand (by the executing agent, Claude
Opus, not by the author): `hand_validation/`. Agreement 37 of 60. The judge's
"not" is reliable: 24 of 25 confirmed, none of them relevant by hand. Its
"relevant" is generous: 12 of 25 confirmed, 5 unsure by hand, 8 not (typically a
REDD+ or climate-finance paper that does not address the family's mechanism).
Its "unsure" is mostly "not" (8 of 10). **Read the relevant counts as upper
bounds; the sample suggests about half are relevant to the mechanism** (derived
from 25 records, wide interval). The outcomes below rest on reading, not on
these counts.

## Sentinel recall

| Set | Sentinels | Found by any search | Found by own family | OpenAlex | EDS | In refined corpus |
|---|---|---|---|---|---|---|
| Tuning | 17 | 17 | 17 | 14 | 13 | 10 |
| Hold-out | 31 | 28 | 21 | 28 | 11 | 16 |
| Other source (no DOI) | 1 | 0 | 0 | 0 | 0 | 0 |

Missed hold-outs: C09 (debt-for-climate swaps for small islands: the debt strings
pair climate finance with debt terms, the paper says neither "climate finance"
nor "cost of debt"), C13 (hydropower dams and deforestation in Brazil: no
international-finance term), C15 (Banking on coal: "Chinese overseas
investments" is not in the fossil-finance block). They are reported, not used to
change a query. Seven hold-outs were found only under another family's strings.
Tuning sentinels are found by the text strings, not by their own citation
search.

## Outcomes per family

The corpus keyword probe redoes the protocol's indicative co-occurrence count
per family: a short climate-finance term set AND the family's mediator phrases,
English, on titles and abstracts of the refined corpus
(`analysis/family_outcome_inputs.csv`). For every empirical family the search
found relevant works that the probe misses, most of them absent from the
refined corpus; the outcome was decided after reading the most-cited
judge-relevant candidates of each low-visibility family.

| Family | Group | Probe hits (refined) | Judge-relevant (absent from refined) | Outcome | Evidence read |
|---|---|---|---|---|---|
| grid | 1 | 30 | 128 (104) | present, not recognised | World Bank/GEF solar home systems (Martinot 2001), World Bank off-grid solar lending, energy aid to SIDS and Pacific; electrification and off-grid, not transmission: no study found for the integration arc Reseau -> Prod_zero |
| cost_of_capital | 1 | 83 | 596 (435) | present, not recognised | Schmidt 2014, Ameli et al. 2021, Polzin et al. 2019 review; C03 on ICF and cost of capital |
| private_mobilisation | 1 | 103 | 619 (427) | present, not recognised | renewable PPP determinants, mobilisation studies; C04, C05 |
| implementation_capacity | 1 | 327 | 814 (410) | present, not recognised | Kim 2018 absent from refined and unified; disbursement panels (C07) |
| debt | 1 | 39 | 397 (319) | present, not recognised (partly non-ICF) | Kling et al. 2018 and 2020 (vulnerability -> cost of capital, not ICF-treated); debt-for-climate swaps; Chinese finance and debt; no estimate of ICF loans' effect on sovereign debt among the candidates read |
| fiscal_substitution | 1 | 26 | 369 (324) | present, not recognised (general aid only) | aid fungibility literature (Pack and Pack 1990/1993, Feyzioglu et al. 1998, Remmer 2004), all absent from refined; no climate-finance-specific fungibility study found |
| construction_emissions | 2 | 94 | 259 (207) | no study found after traced searches | candidates are general climate-finance or BRI trade-embodied-emissions papers; none measures construction or process emissions of ICF-financed projects |
| end_use_efficiency | 2 | 102 | 392 (280) | present, not recognised | Kretschmer et al. 2013; energy aid and CO2 intensity (C12, absent); efficiency financing in developing countries |
| land_spillovers | 2 | 209 | 104 (89) | present, not recognised (weak) | roads and deforestation (Congo Basin, BR-163), BRI environmental impacts, conservation aid and deforestation in SSA; hold-out C13 missed |
| fossil_finance | 3 | 30 | 168 (156) | present, not recognised | Chinese and bilateral overseas coal finance (Steffen and Schmidt 2018, "new coal champion", "carbon lock-in"), 93% absent from refined |
| carbon_credits | 3 | 120 | 1,615 (799) | present, not recognised | West et al. 2020 and 2023, Calel et al., Probst et al. 2024; 816 in refined but 10 recognised by the probe (the literature does not say "climate finance") |
| forest_leakage | 3 | 82 | 797 (604) | present, not recognised | Alix-Garcia et al. 2012 (slippage), Atmadja and Verchot 2012, REDD+ leakage reviews |
| allocation | 0 | 463 | 362 (170) | present, largely recognised | Betzold and Weiler 2017, Weiler et al. 2018; 103 of 192 in-corpus relevant recognised |
| measurement | 0 | 393 | 298 (101) | present, largely recognised | Toetzke et al. 2022, Michaelowa and Michaelowa 2011 |
| donor_additionality | 0 | 174 | 211 (82) | present, not recognised | Stadelmann et al. 2011 |
| growth_scale | 0 | 852 | 166 (131) | present, not recognised (general aid only) | aid-growth papers of the map; no ICF-specific growth study among those read |
| policy_channel | 0 | 319 | 246 (89) | present, largely recognised | ICF and NDCs (C34) |
| renewable_deployment | 0 | 44 | 91 (62) | present, not recognised | CDM and renewable deployment, Chinese official finance for renewables, Pfeiffer and Mulder 2013 |
| redd_results_payments | 0 | 95 | 579 (447) | present, not recognised | Roopsind et al. 2019 absent from refined; Amazon Fund studies |
| confounding | 0 | 672 | 163 (86) | theoretical arc, not meant for direct evidence | candidates are allocation-determinant and general climate-finance papers |
| physical_identities | 0 | 4 | 10 (2) | theoretical arc, not meant for direct evidence | panels on "load capacity factor", carbon-credit datasets |
| deforestation_drivers | 0 | 8 | 256 (205) | theoretical arc, not meant for direct evidence | large drivers literature framed for REDD+ (Hosonuma et al. 2012) without ICF as treatment |

"Largely recognised" marks the three families where the probe finds more than
half of the in-corpus relevant works; they still have relevant works absent from
the corpus. Themes (both lanes): every map-free theme returned judge-relevant
works absent from the refined corpus, for example forest beyond the map 483 of
629, private finance 150 of 232, loss and damage 130 of 302, adaptation 221 of
415 but only 29 absent from all three reference sets, since the Sud lane already
harvested adaptation.

## EconLit

<!-- EconLit section: filled from the parallel bibCNRS probe, 2026-09-30. -->

**Access.** Automated Janus login to bib.cnrs.fr works without MFA (domains
INSHS and INEE) and the bibCNRS article-search API runs end to end, with RIS
export available. EconLit is **not licensed** for these profiles: database codes
`ecn`/`eoh` return 0 hits where HAL returns 4,209 on the same restriction, the
EconLit content-provider filter is rejected ("Invalid Content Provider"; HAL,
ECONIS and RePEc accepted), EconLit is absent from the profile's 232 providers and
from the 152 bibCNRS databases, the EBSCOhost route through the proxy gives
"Authentication Error Code 108", and ProQuest EconLit is not licensed either. Ovid
was not tried. Access through bibCNRS is impossible for this account; the access
question goes to the author (needs-human).

**Adaptation.** Every OpenAlex row has an EconLit twin in EBSCOhost syntax: each
boolean group searched in `TI`, `AB`, `SU` and `KW`, date limiter `DT
199001-202612`; SI twins search the tuning sentinels' titles (EconLit has no
citation index); 22 JEL rows (`CC` codes with wildcard, for example `CC Q54*`,
AND the family's mediator group) and 12 working-paper rows (`PT "Working
Paper"`). Syntax verified by the probe against the AEA and EBSCO guides; a test
checks every string (balanced parentheses and quotes, allowed field codes).
Export: RIS, one file per search id. The 166 strings are archived in the
registry as "not run: not licensed via bibCNRS (2026-09-30)".

**Substitute run.** The same strings were replayed through bibCNRS EDS against
the RePEc and ECONIS content providers (`scripts/catalog_rel_causal_eds.py`), the
working-paper indexes that profile carries; the date limiter stays in the query
text (`DT 1990-2026`) because the API ignored its limiter parameter. 295 searches,
11,352 records (RePEc 6,120, ECONIS 5,232), 7,397 works, of which 5,015 were not
retrieved by the OpenAlex lane and 1,001 judge-relevant works are absent from all
three reference sets. The live parser accepted every twin; the JEL rows return 0
there (no `CC` field in these records), which is a property of RePEc and ECONIS in
EDS, not a test of EconLit. EDS list records rarely carry an abstract, so their
judge labels lean to "unsure".

## Delivery to the pool (1655)

In the intake-contract format of `docs/rel-intake-contract.md` (ticket 1730,
PR #1604): `data/rel_intake/t1652-causal-econlit/2026-09-30/`
(`records.csv`, `registry.csv`, `excluded.csv`, `manifest.json`), tracked by DVC
(`data/rel_intake/t1652-causal-econlit.dvc`, pushed to the padme remote from
padme). 33,531 records (one per work, OpenAlex retrieval preferred), 18,095
further retrievals listed as `duplicate_in_lane`, 15 untitled OpenAlex works as
`not_retrievable`; the contract's checker `scripts/qa_rel_intake.py` passes
(the PR's version on padme, and the stricter version merged on `main`). Extra columns carry families, formulations, every search id and the
family-relevance labels as information, never as a filter. Coverage is
`incomplete` (capped rows, the two HTTP 500 rows, the unrun EconLit strings);
`needs_human` lists EconLit access. The per-retrieval table with archive path
and manifest hash is `analysis/delivery.csv` in the archive.

## Limits

- Record caps leave 26 OpenAlex rows incomplete; broad strings (carbon credits
  synonyms, themes) were not paginated to the end within the 0.40 USD cap.
- The relevance judge over-labels "relevant" (about half confirmed on 25
  records); counts of relevant works are upper bounds.
- French and Spanish strings were written by the assistant and not read by a
  native speaker; they return few works outside Spanish-language repositories.
- The EDS substitute covers RePEc and ECONIS, not EconLit's journal coverage.
