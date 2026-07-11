# Ticket 0243 — Few-shot comparative set

Calibration pairs for the voice-alignment pass: for each manuscript section,
an anchor passage from `docs/style-anchor-v205.md` set against a current
manuscript passage, with a one-line note on the gap. Anchor numbering follows
the style-anchor file; per the sole-author weighting rule, anchors #3 (2009,
"What is the Price of Carbon?") and #5 (2001, "Transparency and control")
carry the most weight, the first-author co-authored anchors (#1, #2, #4, #6)
are secondary. Manuscript passages are cited by section and first words; line
numbers refer to `deliverables/manuscript/manuscript.qmd` at commit time.

## Introduction (@sec-intro)

**Pair 1a — anchor #3, passage 1 (sole author, 2009):**

> The scope of this range—from 5 to 80—gives reasonable cause for scepticism,
> or even a touch of sarcasm regarding the claims of models that they can
> provide insight into a future fraught with controversy. In fact, since
> information in this domain is in a state of considerable confusion, we feel
> that it would be more informative to clarify what is meant exactly by cost,
> price or value of carbon.

**× manuscript, "This paradox is what makes climate finance an interesting
object..." (l. 60):** the passage announces the object's interest in abstract
terms ("Yet its perimeter remains disputed") where the anchor earns the same
move with a concrete number range and one dry aside.

*Gap: concreteness and the licensed dry aside; the manuscript states the
paradox, the anchor lets the reader feel it.*

**Pair 1b — anchor #1, passage 1 (first author, 2009):**

> With leakage, storing carbon in the ground is like taking a loan at the
> bank. One gets a benefit today. Then one pays back in a sequence of small
> installments. Payments sum up to more than the borrowed amount.

**× manuscript, "Two operations run through this history. Commensuration
makes heterogeneous flows comparable..." (l. 70):** the two framework concepts
are introduced in definition-first academic cadence, without an image and
without a short sentence anywhere in the paragraph.

*Gap: sentence length and concreteness — the anchor explains an abstraction in
four sentences averaging nine words; the manuscript paragraph has none under
twenty.*

## Method

**Pair 2a — anchor #5, passage 2 (sole author, 2001):**

> Potential transparency remains, since anybody can get the model simply by
> asking. However, I find no reason to be satisfied with potential
> transparency when models source code can be published at low cost with
> today's information technology.

**× manuscript, "The proposed periodization follows from our reading of the
texts..." (l. 78):** the method is owned ("our reading", "seemed useful to
us") but the conviction is buried mid-sentence; the anchor states position
("I find no reason...") in main-clause position.

*Gap: person and placement of conviction — pending decision D1; the anchor
puts the judgment in the stressed slot, the manuscript tucks it into
qualifiers.*

**Pair 2b — anchor #6, passage 1 (first author, 2004):**

> However, when there are several risk factors and the uncertainty about some
> of them is large, such a procedure can lead to estimates for the numbers of
> cases attributable to the various factors that, summed, exceed the total
> number of cases actually observed.

**× manuscript, "This way of doing intellectual history may surprise. The
discipline usually reads a small number of canonical texts closely. Yet
climate finance has no canon." (l. 80):** already close to the anchored voice
— short declaratives, blunt reframing. Kept as a positive reference point: the
full pass should converge on this register, not flatten it.

*Gap: none to speak of — this is the in-voice calibration point for the
Method register.*

## Before climate finance (@sec-before)

**Pair 3a — anchor #4, passage 1 (first author, 2003):**

> The worldwide control on substances depleting the stratospheric ozone layer
> is often regarded as an exemplary success of global environmental policy. We
> would like to qualify this point of view, by observing that while scientific
> warning came as early as the mid seventies, corrective action came too late
> to prevent the infamous 'hole' over the antarctic.

**× manuscript, "The Clean Development Mechanism came closest to bridging the
gap..." (l. 102):** the narrative content is strong but the paragraph runs
~340 words with several 40+-word sentences; the anchor advances a contrarian
narrative in two readable moves.

*Gap: sentence length and paragraph budget — the CDM story wants shorter
sentences and a landing, not more matter.*

**Pair 3b — anchor #2, passage 2 (first author, 2007):**

> While these differences across WGs may be confusing to readers, they are in
> fact both legitimate and appropriate. A one-size-fits-all approach would
> obscure important differences in the type of uncertainties and in the
> methods.

**× manuscript, "Before 2007, then, the pieces exist but the object is not
assembled." (l. 116):** the section close is already declarative and
well-landed; what precedes it (the three-traditions synthesis) hedges less
crisply than the anchor's "they are in fact both legitimate and appropriate".

*Gap: the anchor takes a side plainly after conceding the confusion; the
manuscript's synthesis sentences concede and affirm in the same breath.*

## Crystallization (@sec-crystallization)

**Pair 4a — anchor #2, passage 1 (first author, 2007):**

> Looking back over three and a half Assessment Reports, we see that the
> Intergovernmental Panel on Climate Change (IPCC) has given increasing
> attention to the management and reporting of uncertainties, but coordination
> across working groups (WGs) has remained an issue. We argue that there are
> good reasons for working groups to use different methods to assess
> uncertainty...

**× manuscript, "It is in this limited sense that the Copenhagen commitment is
performative [@callon1998]..." (l. 128):** the theoretical claim is advanced
impersonally ("Calling this *institutional* performativity keeps MacKenzie's
insight...") where the anchor announces the claim as the authors' own ("We
argue that...").

*Gap: ownership of the thesis — pending D1; the anchor's claim-holder is
visible, the manuscript's is grammatically absent.*

**Pair 4b — anchor #3, passage 2 (sole author, 2009):**

> Even if it cannot be measured in the same way, as for instance, sea levels,
> stating that carbon does have a strictly positive social value is, in
> itself, an important step forward. It means that there is agreement on the
> fact that climate change is a real problem and that greenhouse gas emissions
> must be curbed.

**× manuscript, "The figure was not derived from an economic model or from an
estimate of needs; it emerged from last-minute diplomatic bargaining." (l. 126):**
close to the anchored voice already — plain claim about what a number socially
means. Second positive calibration point.

*Gap: minimal — the pass should preserve sentences like this verbatim.*

## Controversies and the Türkiye case (@sec-controverses)

**Pair 5a — anchor #1, passage 2 (first author, 2009):**

> From economic perspective, when CCS with leakage is assimilated to a carbon
> loan, accepting leaking systems is like taking increasing amounts of
> financial debt. Recent macroeconomic developments remind that this is not
> sustainable.

**× manuscript, "The difference is not technical in the weak sense: it decides
whether one is talking about a volume of financing or a net transfer." (l. 188):**
the manuscript lands its point but in negated form ("is not technical in the
weak sense"); the anchor lands positively and then stops.

*Gap: positive form and the hard stop — the anchor's two-sentence close is the
model for how each controversy paragraph should end.*

**Pair 5b — anchor #4, passage 2 (first author, 2003):**

> The early action scenario could also have been a rational choice. Is not
> this the essence of the precautionary principle? Our conclusion is that the
> Montreal Protocol was only a partially successful application of precaution.
> It might not be a bad idea to regulate global atmospheric environmental
> issues before surprising non-linearities occur.

**× manuscript, "Each of these debates reopens the boundary of the object."
(l. 214, section-final):** declarative close where the author's device would
plant a question; whether to use it is decision D4.

*Gap: the question-closing device — present in the anchors, absent from every
manuscript section ending.*

## Conclusion (@sec-conclusion)

**Pair 6 — anchor #5, passage 2 (sole author, 2001):**

> However, I find no reason to be satisfied with potential transparency when
> models source code can be published at low cost with today's information
> technology.

**× manuscript, "One might file all this under a familiar heading. ... The
description fits, and it is worth conceding. Yet it stops short of what this
history shows." (l. 236):** the concession-then-refusal move matches the
author's posture exactly, but the agent is "One might" where the anchor says
"I find".

*Gap: person under D1 — the argumentative shape is already the author's; only
the grammatical owner differs.*

## Appendix (methods register)

**Pair 7 — anchor #6, passage 2 (first author, 2004):**

> In this paper we have applied the Smets' Transferable Belief Model to
> estimate an upper bound on the fraction of lung cancers caused annually by
> the group of causes for which comprehensive longitudinal studies are
> lacking. Such a result is interesting from a risk management perspective.
> For example it might be used to infer the level of control effort these
> pollutants deserve.

**× manuscript, "To compare works by their meaning, and not by their exact
words alone, each title, abstract and keyword list is turned into a point in a
'space of meaning'..." (l. 270):** the appendix explains method in long
passive-leaning periods; the anchor reports method in short active sentences
and closes on the modest use of the result.

*Gap: sentence length and voice in methods prose — active constructions, one
idea per sentence, a plain so-what at the end.*
