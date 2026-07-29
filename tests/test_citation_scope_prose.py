"""The data paper's citation-network quantities carry their denominators (0333).

Three of four external reviewers found the citation-network description
internally ambiguous: §2.3 said 1,087,209 pairs "where both works belong to
the refined corpus" cover 80% of corpus DOIs, while §4's Figure 2 was
introduced "at full-corpus scale" yet maps 13,112 works — 39% of the corpus.
The two could not be reconciled because they count different things: the pair
table constrains only the *citing* side (`corpus_align.py` filters
`source_doi` to refined works; the cited work may be any literature), while
the figure's graph keeps only DOI-matched links whose *both* endpoints are
corpus works. The prose claimed the first set had the second's property.

Guards follow the project polarity rule: negative pins on the two wrong
claims, structural presence for the disclosures the ticket requires. All
text-only: fast tier.
"""

import os
import re

BASE = os.path.join(os.path.dirname(__file__), "..")
QMD = os.path.join(BASE, "deliverables", "data-paper", "data-paper.qmd")


def _text():
    with open(QMD, encoding="utf-8") as fh:
        return fh.read()


def _section(name):
    """Body of `## <n>.` up to the next `## ` heading."""
    text = _text()
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(f"## {name}"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


def test_figure2_is_not_captioned_full_corpus():
    """The map shows the connected DOI-linked subgraph, not the corpus.

    Red before ticket 0333: §4 introduced @fig-global-map "at full-corpus
    scale" while the graph holds 13,112 of 33,344 works.
    """
    assert "full-corpus scale" not in _text(), (
        "the figure maps the connected subgraph of DOI-matched corpus-internal "
        "links; calling it full-corpus scale is what made 13,112 vs 33,344 "
        "irreconcilable for three reviewers"
    )


def test_refined_pairs_are_not_claimed_corpus_internal():
    """The 1,087,209 pairs constrain the citing side only.

    Red before ticket 0333: §2.3 read "links where both works belong to the
    refined corpus yields {{< meta cite_refined_rows >}}". corpus_align.py
    filters source_doi to refined works and leaves ref_doi unconstrained, so
    the claim was false — at ~53 references per covered work the set is
    plainly all outgoing references, not internal ones.
    """
    assert "both works belong to the refined corpus" not in _text(), (
        "refined_citations.csv restricts only source_doi to corpus works; "
        "say which side is constrained instead of claiming both are"
    )


def test_connected_subgraph_share_is_a_macro():
    """The 13,112 must arrive with its share of the corpus, as a var.

    The reviewers' arithmetic (39% of works, 52% of DOI-bearing) should not
    be theirs to do: the share ships as a computed variable next to the count.
    """
    assert re.search(r"{{<\s*meta\s+gm_connected_pct\s*>}}", _text()), (
        "state the connected works' share of the corpus as the "
        "gm_connected_pct macro, beside gm_n_connected"
    )


def test_no_doi_exclusion_is_stated_for_targets_too():
    """§3 must say no-DOI works are absent from the graph in both directions.

    The schema is (source_doi, ref_doi): a corpus work without a DOI can
    appear on neither side, and GROBID's fuzzy matching resolves into the
    pair table only when the matched work carries one. Saying only the
    citing-source half implies the target half works, and it does not.
    """
    data_section = _section("3.")
    assert re.search(r"cited targets?|as a (cited )?target|either side|both directions", data_section), (
        "§3 states the citing-source exclusion; state the cited-target "
        "exclusion too — the graph excludes no-DOI works in both directions"
    )


def test_crossref_check_states_its_sampling_and_scope():
    """§2.3 must say how the 300 links were drawn and what the check measures.

    qa_citations.py draws a simple random, unstratified, seeded sample of
    rows with both DOIs; and confirmation against Crossref is partly circular
    for links that originate from Crossref/OpenAlex deposits.
    """
    quality = _section("2. Method")
    assert re.search(r"unstratified|simple random", quality), (
        "state the sampling design of the verification sample"
    )
    assert re.search(r"circular", quality), (
        "state that confirming Crossref-derived links against Crossref "
        "metadata is partly circular — the check measures agreement with "
        "the source, not ground truth"
    )


def test_abstract_dependent_products_are_named():
    """§3's abstracts caveat must name the products computed from them.

    Embeddings and reranker relevance scores depend on abstracts that are
    not deposited; a reuser re-fetching from a live index cannot exactly
    regenerate them. Naming the affected products is the one honest sentence
    two reviewers asked for. (The semantic-outlier flag left the list with
    flag 5's deactivation — five-flag decision, author 2026-07-29.)
    """
    data_section = _section("3.")
    for product in ("embedding", "relevance"):
        assert product in data_section, (
            f"§3 must name {product!r} among the products computed from "
            "non-deposited abstracts"
        )
