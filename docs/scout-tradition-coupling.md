# Scout: cross-tradition citation coupling over time

**Verdict: NO SIGNAL.** No integration break around 2007–2009 survives the
density/composition control. Across three methods — the primary continuous
soft-membership coupling, an assumption-light embedding-distance cross-check,
and the hard-assignment assortativity comparison — the traditions do not
measurably merge in citation behaviour through crystallization. The one result
pointing toward integration (a marginal absolute decline in soft coupling) is
temperature-fragile and dissolves under the very control the author asked to
gate on. This is a follow-up to the static co-citation test that came back
DEMOTE (0182); the time-series reframing returns the same negative.

## What each method says

**1. Soft-membership coupling (primary).** Mean P(two coupled works share a
tradition) = m(A)·m(B) over each year's citation edges falls only from **0.388**
(pre-2007) to **0.372** (post-2009): diff 0.0168, 95% CI [0.0016, 0.0304] — a
tiny decline that barely clears zero. It is **temperature-fragile**: at softmax
T=0.05 the CI includes zero, at T=0.20 the decline shrinks to a trivial 0.0045.
And it **does not survive the density control**: against a permutation null that
shuffles membership vectors across the nodes present each year (graph fixed), the
z-score *rises* from 0.67 pre-2007 to 2.60 post-2009. Within-tradition coupling
*relative to the year's own composition* does not decline — the small absolute
drop is a composition shift, not more cross-tradition citing.

**2. No-scaffold embedding distance (cross-check, no traditions at all).** Mean
cosine distance between citing and cited works' embeddings rises only weakly
(0.337 → 0.350; diff −0.0131, 95% CI [−0.0357, 0.0071], includes zero). Against
its random-pair null the observed distance sits **far below** the null in every
year and the gap **widens** over time (z from −3.6 to −18): citations connect
increasingly closer-than-random works. Semantic homophily *intensifies* — the
opposite of "citations bridge wider gaps as traditions merge."

**3. Hard-assignment assortativity (comparison, the lossy baseline).** Newman
categorical assortativity is near zero and noisy throughout; pre-2007 mean 0.061
vs post-2009 0.044, diff 0.0166 with a wide 95% CI [−0.082, 0.131] that includes
zero. No break.

**Do the three agree?** On the *density-controlled* question — does any
integration survive the null? — **yes, all three agree: no.** On the raw
absolute trend they mildly diverge: soft coupling shows a fragile marginal
decline, distance a non-significant rise, hard assortativity nothing; all three
lean in the integration *direction* on the naive statistic, none robust to the
control. **Change point around 2007–2009:** none — every series is flat or noisy
across the shaded 2007–2014 window with no sustained regime shift.

## Numbers (reproducible, seed 20260708)

```
CLIMATE_FINANCE_DATA=$PWD/data HF_HOME=/home/haduong/data/cache/huggingface \
  HF_HUB_DISABLE_PROGRESS_BARS=1 TQDM_DISABLE=1 HF_HUB_OFFLINE=1 \
  uv run python scripts/scout_tradition_coupling.py \
  --output content/figures/scratch/scout_tradition_coupling.png
```

### Membership (content-based, all 30,987 works assigned)

Hard nearest-centroid counts (the pre-2007 degeneracy that gave 0182 zero nodes
for two traditions is avoided — all three have >100 pre-2007 members):

| Era | burden_sharing | env_econ | development | total |
|-----|---------------:|---------:|------------:|------:|
| pre-2007 (1990–2006) | 1006 | 129 | 180 | 1315 |
| crystallization (2007–2014) | 4813 | 705 | 852 | 6370 |
| established (2015–2025) | 16028 | 4665 | 1717 | 22410 |
| **full corpus** | **21848** | **6390** | **2749** | **30987** |

Soft (softmax T=0.10) mean membership mass over the corpus: env_econ 0.302,
development 0.250, burden_sharing 0.448. The global random-mixing floor for
soft coupling is Σ mass² ≈ 0.35, versus observed ~0.37–0.39 — coupling sits just
above the floor throughout, so there was never strong citation separation to
integrate away from.

### Contrast table (pre-2007 vs post-2009)

| Method | pre-2007 | post-2009 | diff (pre−post) | 95% CI | z pre | z post | integration? |
|--------|---------:|----------:|----------------:|--------|------:|-------:|:---|
| 1 soft coupling (T=0.10) | 0.388 | 0.372 | 0.0168 | [0.0016, 0.0304] | 0.67 | 2.60 | raw: marginal; controlled: **no** |
| 2 no-scaffold distance | 0.337 | 0.350 | −0.0131 | [−0.0357, 0.0071] | −3.6 | −18.0 | raw: NS; controlled: **no** |
| 3 hard assortativity | 0.061 | 0.044 | 0.0166 | [−0.082, 0.131] | 0.94 | 2.02 | **no** |

Soft-coupling temperature sweep (primary metric): T=0.05 diff 0.0431 CI
[−0.0021, 0.0844]; T=0.10 diff 0.0168 CI [0.0016, 0.0306]; T=0.20 diff 0.0045 CI
[0.0006, 0.0080]. Full per-year series print to stdout; the figure
(`content/figures/scratch/scout_tradition_coupling.png`) shows all three with
the 2007–2014 window shaded.

## Method (one paragraph)

Three tradition centroids are built from the @tbl-traditions key references in
bge-m3 embedding space: anchors present in the corpus (weitzman2007,
michaelowa2007, michaelowa2019, stadelmann2011) use their aligned
`refined_embeddings` vector; the 7 anchors absent as corpus works (e.g.
nordhaus1992, negishi1960) are embedded fresh from their title with the same
bge-m3 model, keeping every anchor in one space; each centroid is the
L2-normalised mean of its anchors' unit vectors. Membership is content-only,
assigned to all works, independent of the citation graph tested — avoiding the
degeneracy and Louvain-circularity of 0182. The graph uses `refined_citations`
edges whose source and target DOIs are both corpus works (44,852 edges), each
dated by the citing paper's year. Soft membership is softmax(cosine sims / T),
T=0.10 primary; soft coupling per edge is m(A)·m(B). The no-scaffold statistic
is the cosine distance between the two works' unit embeddings. Hard assortativity
uses argmax labels and the Newman categorical formula. Every method takes a
per-year z-score against 500 permutations of the node property (membership
vector / embedding / label) among the nodes present that year, holding graph
structure and composition fixed so a trend cannot be a mechanical artefact of the
corpus growing denser / better DOI-indexed (the 0071 confound). Loaders and DOI
normalisation go through `pipeline_loaders` / `pipeline_text` (architecture rule
9).

## Confounds not ruled out

- **z-magnitude is confounded by sample size.** The permutation-null σ shrinks as
  edges/year grow from ~30 (2001) to ~1850 (2018), so |z| inflates ~√n for any
  fixed effect. The plunging distance-z and rising coupling-z therefore partly
  track *power*, not effect size. The controlled verdict rests on the *direction*
  (no decline / intensifying homophily), not the z magnitude.
- **Pre-2007 citation power is very low.** Only 2001–2006 clear the 30-edge floor,
  thinly (30–107 edges/yr); 1990–2000 are essentially empty of corpus-internal
  citations. The "separated baseline" is measured on a handful of noisy years, so
  a null here is partly low power. The per-year permutation controls the *trend*
  but cannot manufacture the pre-2007 *level* the data lacks.
- **Temperature dependence of the only positive.** The soft-coupling absolute
  decline — the sole integration-direction result that reaches significance — is
  significant only in a narrow T band and shrinks to triviality at T=0.20. A
  finding that hinges on one tuning knob is not robust.
- **Centroid definition / fresh-embedding mismatch.** Corpus anchors encode
  title+abstract+keywords; the 7 fresh anchors are title-only, so their vectors
  are less specific. env_econ leans most on fresh anchors (5 of 6), the least
  robust centroid. A different anchor set or text basis could move the soft
  masses and the marginal contrast.
- **What `burden_sharing` denotes.** With 0.45 soft mass / 70% hard labels it
  behaves as a climate-finance / carbon-markets catch-all anchored on
  michaelowa2019 + stadelmann2011, not the historical equity/effort-sharing
  tradition (negishi welfare weights). The manuscript already separates that
  tradition's intellectual-history anchor from its co-citation anchor; the
  content clustering inherits the gap. The three content clusters approximate,
  but do not cleanly equal, the three historical constructs.

## Recommendation

Do not upgrade the manuscript separation-then-integration claim on citation
evidence. The continuous soft-membership test, the assumption-light distance
cross-check, and the hard-assignment baseline all agree that no integration
break survives the density/composition control, and the pre-2007 citation record
is too thin to establish the "separated" baseline in principle. The existing
manuscript framing — history-first, co-citation as corroboration, with an
explicit note that the effort-sharing tradition left no distinct co-citation
footprint — remains the honest reading. Throwaway scout: no production wiring
intended unless the author asks.
