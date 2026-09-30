# JETP Observer: legal note (France)

Supporting document of the [specification](jetp-spec.md). Commissioned by
the author on 2026-09-30 under review finding W1-29
([ledger](jetp-spec-review/wave-1/ledger.md)) and requirement Q21. Drafted
by a language model (Fable), to be reviewed by a second model, then by a
human lawyer. **This note is not legal advice.** It states, for each activity
of the Observer, the rule it relies on under French law and EU law as applied
in France, how the Observer complies or what it must change, a residual risk
rating, and what the specification must say. Every legal claim carries its
article; every claim the drafter could not verify is marked *to verify*.
Jurisdiction: France. Publisher: a researcher of the CNRS working at CIRED.

Abbreviations: CPI, *Code de la propriété intellectuelle*; CRPA, *Code des
relations entre le public et l'administration*; LCEN, *Loi n° 2004-575 pour
la confiance dans l'économie numérique*; LIL, *Loi n° 78-17 Informatique et
Libertés*; DSM, Directive (EU) 2019/790 on copyright in the digital single
market; GDPR, Regulation (EU) 2016/679; TDM, text and data mining (*fouille
de textes et de données*).

## Summary of risk ratings

| # | Activity | Residual risk | Condition |
|---|---|---|---|
| 1 | Collecting and holding copies | low | research TDM under L122-5-3 II; secure storage; opt-outs recorded |
| 2 | Redistributing extracts | medium | short quotations with attribution; no document bytes without terms; per-source terms table |
| 3 | Personal data in documents | low | names of officials in their public role; minimisation; information notice |
| 4 | Sending content to LLM providers | low–medium | public documents only; provider terms and transfer basis recorded |
| 5 | Website obligations | medium until the legal notice is complete | LCEN art. 6-III notice; takedown route; no tracking |
| 6 | Licensing the releases | low once labelled | CC BY 4.0 on the Observer's own contributions only, third-party material marked |

## 1. Collecting and holding copies

**Rule.** Reproducing a document is a restricted act (CPI art. L122-3,
L122-4); so is extracting a substantial part of a database (L342-1). Two
exceptions transpose DSM arts 3 and 4 (Ordonnance n° 2021-1518 of 24
November 2021):

- **Research TDM**, CPI art. L122-5-3 II (copyright) and L342-3 (database
  right; the paragraph numbering after the 2021 ordinance is *to verify*):
  copies and reproductions made for TDM by research organisations and
  cultural heritage institutions, for scientific research, from content to
  which they have *lawful access*. The rights holder cannot opt out (DSM art.
  7(1): contractual provisions contrary to art. 3 are unenforceable; the
  French text of this rule at L122-5-3 is *to verify*). Copies are stored with
  an appropriate level of security and may be retained for scientific
  research purposes, including verification of results (DSM art. 3(2); CPI
  L122-5-3 II). The research organisations covered are defined by Décret
  n° 2022-928 of 23 June 2022 (CPI art. R122-28 et seq., *to verify*); the
  CNRS, a public research establishment (*établissement public à caractère
  scientifique et technologique*, Code de la recherche art. L321-1), is one.
- **General TDM**, L122-5-3 III and L342-3 (DSM art. 4): copies of lawfully
  accessible works by anyone, for any purpose, unless the rights holder has
  reserved the right *in an appropriate manner, such as machine-readable
  means in the case of content made publicly available online* (DSM art.
  4(3); French text: "de manière appropriée, notamment par des procédés
  lisibles par machine"). Copies may be kept only as long as necessary for
  the mining (DSM art. 4(2)).

Both are subject to the three-step test (DSM art. 7(2), Directive 2001/29
art. 5(5); CPI L122-5 last paragraph).

**What counts as a machine-readable opt-out.** DSM recital 18 names
"metadata and terms and conditions of a website or a service". Neither the
directive nor the CPI names a protocol. The instruments used in practice:
`robots.txt` (*Disallow*, and agent-specific rules for AI crawlers), the W3C
TDM Reservation Protocol (`tdm-reservation` HTTP header, `tdmrep.json`,
HTML meta), `ai.txt`, and terms of use written in natural language. The
Regional Court of Hamburg (LG Hamburg, 27 September 2024, 310 O 227/23,
*LAION*) held that natural-language terms of use *may* be machine-readable
when a program can understand them, and applied the research exception to a
non-profit dataset builder; a German first-instance judgment, persuasive
only, appeal status *to verify*. The AI Act (Regulation (EU) 2024/1689, art.
53(1)(c)) obliges providers of general-purpose AI models to honour art. 4
reservations "including through state-of-the-art technologies", and the
Commission's Code of Practice (July 2025) lists `robots.txt` as one; this
binds model providers, not the Observer, but fixes what "machine-readable"
is coming to mean.

**How the Observer complies.** The Observer is a CNRS research activity, so
art. L122-5-3 II is its primary basis and no opt-out defeats it. The
Observer nevertheless records every site's stated position (requirements C6;
collection §access rules) because (a) the research exception requires
*lawful access*, and a site that forbids automated access in its terms may
argue that access by a program was not lawful; (b) a single fetch of a known
public document, as opposed to link-following, is the ordinary act of a
reader and needs no exception at all when it makes no copy beyond the
browser's, but the Observer *keeps* the copy; (c) the record is the proof
F27 requires. The archive (DVC store, on the author's machines) is not
served to the public; the local preview's `documents/` directory is
git-ignored and never published (observatory README). This is the "secure
storage" of art. 3(2). Retention for verification of results is exactly the
Observer's fingerprint-and-locator design (results §7).

**Login-gated sites with free registration.** Registration creates a
contract; its terms bind the registrant. Under the research exception, a
clause forbidding TDM is unenforceable (DSM art. 7(1)), but a clause
forbidding *automated access* or *redistribution* is a separate obligation,
not a copyright reservation, and its breach is a contractual matter with the
site, not an infringement. Lawful access is satisfied by a registration
anyone can obtain. The Observer's rule that the author passes logins in
person, never by automation (collection; C6), keeps the fetch within the
terms of an ordinary registered user. The registration used is recorded
without credentials (F27).

**What must change.** Nothing in the collection rule. The specification
must say the legal basis. *Residual risk: low.* A rights holder could
contest lawful access on a site whose terms forbid programmatic access;
the record of the site's position and the in-person login rule answer it.

**Spec.** Collection §"Public access only" and §"Crawler rules": one
sentence naming L122-5-3 II as the basis for holding copies and the
site-position record as its lawful-access proof. Storage contract: the
`terms_position` and `robots_position` columns of W1-29 are the evidence.

## 2. Redistributing extracts

**Rule.**

- *Short quotation*, CPI art. L122-5 3° a): short quotations justified by the
  critical, polemical, educational, scientific or informative character of
  the work into which they are incorporated, with the author's name and the
  source clearly indicated. French courts read "short" relative to both the
  quoted work and the quoting work, and require the quotation to serve the
  quoting work rather than replace the quoted one (Cass. 1re civ., 13
  November 2003, *to verify the reference*). A label of a plan line, a
  sentence stating an amount, or the printed fields of a table row, each
  attributed and each pointing to its locator, is within the exception; a
  page of prose is not. An amount, a date or a name is a fact, not a work
  (Cass. 1re civ., 30 June 1998, *Microfor / Le Monde* line of cases on
  bibliographic and factual extraction, *to verify*).
- *Sui generis database right*, CPI arts L341-1 (a producer who shows a
  substantial investment in obtaining, verifying or presenting the
  contents), L342-1 (prohibition of extraction or re-use of a qualitatively
  or quantitatively substantial part), L342-2 (repeated and systematic
  extraction of insubstantial parts that exceeds normal use). A lawful user
  may extract insubstantial parts (L342-3 1°). Fifteen years from completion
  (L342-5). Held only by producers established in the EU or EEA (L341-2), so
  the Secretariat's tables, the OECD's and the World Bank's databases have
  no sui generis right in France unless their producer is EU-established;
  their protection is contractual (terms of use) or copyright on the
  presentation. A national ministry of South Africa, Indonesia, Viet Nam or
  Senegal has none. A French or EU-based publisher (AFD, EIB, the European
  Commission, a French news site) does.
- *Re-use of public-sector information*, CRPA arts L321-1 et seq.: freely
  re-usable information in documents produced or received by an
  *administration* (L300-2), attribution and non-alteration (L322-1),
  intellectual-property rights of third parties reserved (L321-2, L321-3).
  It covers French administrations only. It has no bearing on foreign
  ministries, and none on international organisations. It does, however,
  cover the Observer's *own* output: the ledger produced by a CNRS
  researcher in a public research mission is an administrative document,
  and Code de la recherche art. L533-4 II makes research data produced with
  public funds freely re-usable once published (Loi n° 2016-1321 art. 30),
  which supports the open licence of section 6.
- *Foreign official texts.* Berne Convention art. 2(4) lets each state
  decide the protection of "official texts of a legislative, administrative
  and legal nature". In France, laws, decrees, court decisions and similar
  acts are unprotected by constant case law; what protection a foreign
  official text has in France is decided by French law (Berne art. 5(2),
  *lex loci protectionis*). Three of the four countries exclude such texts
  at home: South Africa Copyright Act 1978 s. 12(8)(a); Indonesia Law
  28/2014 art. 42; Viet Nam IP Law 2005 (amended 2022) art. 15; Senegal Loi
  n° 2008-09 (*article to verify*). A **decision** or a **decree** approving
  a plan is an official text; the **plan itself** (JET-IP, CIPP, RMP, the
  Senegal investment plan) is a report written by a ministry or a
  secretariat, which is a work. For those, quotation and TDM apply, not the
  official-text exclusion.
- *International organisations and their data licences.* What the drafter
  knows, each entry *to verify* against the current terms before release:

  | Publisher | Terms as known | What to check |
  |---|---|---|
  | OECD (CRS, DAC statistics) | OECD Terms and Conditions moved its data and publications to CC BY 4.0 (announced 2024) | that CRS bulk exports fall under it, and the attribution text it asks for |
  | IATI | The registry lists each publisher's own licence; the Standard requires an open licence but the publisher chooses (CC BY, ODbL, OGL, public domain) | the licence of each publisher whose activities the Observer serves; ODbL is share-alike and cannot be relicensed CC BY |
  | World Bank | Open Data terms: CC BY 4.0 for datasets and the Projects & Operations API; publications in Documents & Reports mostly CC BY 3.0 IGO | project page text and project documents (PADs, ISRs) carry their own notice; some are "restricted" |
  | JETP Secretariats (South Africa IPMO, Indonesia JETP Secretariat, Viet Nam, Senegal) | no licence stated, as far as known | the terms of each site; "unknown" means bytes are cited, not served (results §7) |
  | Development banks (AfDB, ADB, AIIB, EIB, KfW, AFD, JBIC) | each has a disclosure policy and a website terms page; AfDB and ADB state open-data licences for datasets, not for documents | per bank; EIB, KfW and AFD are EU-established, so the sui generis right applies to their databases |
  | News sites | rights reserved; often a press-agency licence | quotation only; no bytes; a headline and a sentence at most |

**How the Observer complies.** Results §7 already serves verbatim labels,
short excerpts and the printed fields of tables with attribution, document
and locator, serves document bytes only where terms allow, and treats
unknown terms as forbidding (C6). What tips a serving from quotation into
substantial extraction is volume: the whole of a plan's project table,
re-served as the Observer's document-rows view, reproduces a substantial
part of that table. Two arguments keep it lawful: the table's producer is
not EU-established (no sui generis right); the fields served are facts
(names, amounts, dates), and their selection and arrangement are the
Observer's, not the publisher's. Both hold for the four governments; the
second alone holds for an EU-established publisher, and a full re-serving of
an EU publisher's table is *medium* risk.

**What must change.** Add a per-source terms table (the `terms_position`
column of W1-29, served on the site's legal page as "Publishers and their
terms"). Cap what a document-rows export reproduces from an EU-established
publisher to the fields that carry a statement (the label, the amount, the
date), or obtain the publisher's licence. *Residual risk: medium*, driven
by volume and by EU-established publishers, not by the four governments.

**Spec.** Results §7: replace the pending W1-29 comment with the basis
(quotation L122-5 3° a) for text; facts for fields; no sui generis right
for non-EEA producers, L341-2; terms table served). Requirements C6: add
"and its licence, where stated" to the site position record.

## 3. Personal data in documents

**Rule.** A name in a document is personal data (GDPR art. 4(1)) even when
the person acts in an official capacity (CJEU C-92/09 and C-93/09 *Schecke*,
9 November 2010). Processing needs a basis (art. 6): for a public research
body, art. 6(1)(e), a task in the public interest, the CNRS research mission
(Code de la recherche art. L321-1 and L112-1), is the usual basis, not
consent. Research safeguards: art. 89(1) (minimisation, pseudonymisation
where the purpose allows); art. 5(1)(b) (further processing for research is
compatible); art. 14(5)(b) (the information duty toward persons whose data
were not collected from them is lifted where it is impossible or would
involve disproportionate effort, with a public notice instead); art. 17(3)(d)
(erasure may be refused where it would render the research impossible).
French law: LIL art. 78 (derogations for archival and research purposes,
*article number to verify* after the 2018–2019 renumbering) and the CNIL's
research guidance. The academic-expression clause, GDPR art. 85 and LIL art.
80, covers the Observatory's published statements as academic expression.

**How the Observer complies.** The ledger records organisations, not
persons, as parties (ontology §2). Names of officials appear only inside
archived documents and, where a statement is attributed to a signatory,
in the verbatim label. No contact detail (email, phone) of a natural person
is extracted into any table; none is served. The Observer keeps nothing
about visitors (section 5). A DPIA (art. 35) is not required: no large-scale
processing of special categories, no systematic monitoring of persons.

**What must change.** (i) State the basis (art. 6(1)(e)) and the safeguards
in the privacy statement of the legal page; (ii) add a rule in extraction:
a person's name enters a table only as the signatory or author of a
statement, never a contact, and the LLM readers are instructed not to
extract personal contact details; (iii) register the processing in the CNRS
record of processing activities (art. 30) through the CNRS data-protection
officer (*DPO contact to confirm*). *Residual risk: low.*

**Spec.** Extraction §3 (what a line carries): the minimisation rule.
Presentation: the privacy statement lives on the legal page. Operation: the
art. 30 record and the DPO contact.

## 4. Sending document content to LLM providers

**Rule.** Sending a document's text to a hosted model makes a copy on the
provider's servers. For the Observer this is a reproduction for TDM, covered
by L122-5-3 II when the Observer makes it (the provider is its processor
under a contract); the provider's own retention is governed by the
provider's terms, and a provider that trains on inputs makes a copy the
exception does not cover for the Observer. Personal data in the text
(section 3) sent to a provider outside the EU is a transfer (GDPR chap. V):
the EU–US Data Privacy Framework (Commission Decision (EU) 2023/1795, upheld
by the General Court in T-553/23 *Latombe*, 3 September 2025, *appeal to
verify*) covers certified US providers; otherwise standard contractual
clauses (Decision (EU) 2021/914). Public documents carry no confidentiality
obligation.

**How the Observer complies.** Operation §5–§7: readers are open-weight
models run locally on padme (no transfer) with the same models through
OpenRouter as a fallback, and a hosted arbiter through OpenRouter. OpenRouter
is a US company that routes to sub-providers in several countries; it offers
per-request routing to "zero data retention" providers and a setting to
refuse providers that train on prompts (*to verify in the current terms
and privacy policy*). Every document sent is public (F27), so the harm of a
leak is nil; the residual questions are the contractual (training on inputs)
and the transfer basis for the few names inside the text.

**What must change.** Operation must state: hosted calls carry only public
document text; the account is set to exclude providers that train on
inputs; the routing prefers EU-hosted or zero-retention providers; the
provider's terms in force and the transfer basis (DPF certification or SCC)
are recorded once per provider in `decisions.md`. *Residual risk: low to
medium* (medium only if the training-on-inputs setting is not enforced).

**Spec.** Operation §7 (models and calls): the three settings above.
Operation §11 (budgets and accounts): the provider record.

## 5. The website's obligations

**Rule.** LCEN art. 6-III (renumbered by Loi n° 2024-449 *SREN* of 21 May
2024; the current paragraph structure is *to verify*): every online public
communication service makes available to the public (1°) for a legal
person, its name, registered office, telephone, registration; for a natural
person publishing professionally, name, address, telephone; the name of the
*directeur de la publication*; the name, address and telephone of the host.
A non-professional natural person may stay anonymous toward the public
provided the host's identity is given and the host holds the publisher's
identity (6-III-2). Whether a CNRS researcher's project site is published
by the CNRS (legal person) or by the researcher (natural person, in the
course of his profession) is the first *open point*; CNRS practice for
laboratory websites is to name the CNRS as publisher and the laboratory
director or the researcher as *directeur de la publication* (*to confirm
with CNRS DAJ*). The host is GitHub, Inc. (GitHub Pages); its postal address
and telephone must be copied from GitHub's own legal page, never guessed.

*Cookies and tracking*: LIL art. 82 (ePrivacy art. 5(3)) requires consent
for non-essential cookies and trackers. A static site with no analytics, no
embedded third-party scripts and no fonts loaded from third parties sets
none; the CNIL's exemption for audience-measurement cookies is not needed.
GitHub, as host, logs visitors' IP addresses under its own privacy
statement; the page says so.

*Takedown and correction*: LCEN art. 6-I-5 (notification to a host);
Regulation (EU) 2022/2065 (DSA) art. 16 for hosts. The Observer is an
editor, not a host, so no statutory notice-and-action procedure binds it;
but a takedown route is its best defence (good faith, prompt removal), and
results §9 already provides a correction and withdrawal procedure for
releases. A press-law right of reply (Loi 29 July 1881 art. 13, LCEN art.
6-IV) applies to statements naming a person; the Observer names
organisations and cites publishers, so the exposure is small.

*Accessibility*: Loi n° 2005-102 art. 47 and Décret n° 2019-768 (RGAA)
bind public bodies' online services; if the CNRS is the publisher, the site
owes an accessibility statement (*open point*).

**How the Observer complies.** The MVP carries a Who we are page with the
author's name, institution and ORCID, and no legal notice. This commit adds
a Legal page under About with the notice, the licence and attribution
statement, the publishers-and-terms table, the takedown and correction
route and the privacy statement, with `[TO CONFIRM]` placeholders for
every fact the author must supply.

**What must change.** Fill the placeholders; decide publisher identity.
*Residual risk: medium until the notice is complete* (the LCEN sanction for
a missing notice is one year and €75,000, art. 6-VI-2, rarely applied to a
non-commercial site), *low afterward*.

**Spec.** Presentation §Navigation: the Legal page under About, in sub-bar
order after Who we are. Operation: who answers a takedown notice and within
what time (proposal: acknowledged within five working days, decided within
one month, the decision recorded in `decisions.md`).

## 6. Licensing the releases

**Rule.** CC BY 4.0 licenses the *Licensed Rights* the licensor holds in the
*Licensed Material* (section 1, section 2(a)), copyright and sui generis
database rights alike (section 4). It cannot license rights the licensor
does not hold: third-party text quoted under an exception, third-party
tables re-served as facts, and third-party documents served under their
own terms remain under those terms. CC BY 4.0 section 3(a)(1)(A) requires
downstream users to keep the attribution the licensor supplies; the
licensor must therefore mark what is not its own (Creative Commons
guidance "Marking third party content", *to verify*). Zenodo requires a
licence on each deposit and shows it in the metadata record. CRPA L323-1
and Décret n° 2017-638 list the licences a French administration may use
for public information (Licence Ouverte 2.0 and ODbL; another licence
needs homologation by decree): if the CNRS is the licensor of an
administrative document, CC BY 4.0 is *not* on the list and Licence
Ouverte 2.0, which is CC BY-compatible, is; *open point*.

**How the Observer complies.** Results §6 states an attribution-only
licence; results §7 separates what is redistributed from what is cited.

**What must change.** Label at three levels: (i) a `LICENSE` file in each
release and on Zenodo naming CC BY 4.0 (or Licence Ouverte 2.0, see the
open point) for "the tables, results, dictionary, provenance, reports and
pages produced by the JETP Observer"; (ii) a `THIRD-PARTY.md` (the
redistribution list of results §7) stating, per document, its publisher,
its terms and whether bytes are served; (iii) in every served table, the
`publisher`, `document_id` and `locator` columns that already carry the
attribution, with a data-dictionary line saying the verbatim label is the
publisher's text quoted under CPI L122-5 3° a). The code stays under its
own open-source licence (F30). *Residual risk: low once labelled.*

**Spec.** Results §6 "Licence": the sentence "The licence covers the
Observer's own contributions; a publisher's text is quoted under CPI art.
L122-5 3° a) and remains its publisher's, and a document's bytes are served
under that document's terms, stated in the redistribution list." Results
§7: the three labels.

## Open points for a human lawyer or the CNRS legal service (DAJ)

1. Publisher identity of the Observatory (CNRS as legal person, or the
   researcher), and hence who is *directeur de la publication* and whether
   RGAA applies (section 5).
2. Licence of the Observer's own output: CC BY 4.0 versus Licence Ouverte
   2.0 under CRPA L323-1, if the ledger is an administrative document
   (section 6).
3. Whether re-serving the complete project table of a plan published by an
   EU-established body (AFD, EIB, European Commission) exceeds quotation
   and substantial-extraction limits, and whether a licence should be asked
   (section 2).
4. The exact French text of the lawful-access condition and of the
   unenforceability of contrary contract terms at CPI L122-5-3, and the
   paragraph numbering of L342-3 after Ordonnance 2021-1518 (section 1).
5. The transfer basis for OpenRouter and its sub-providers, and whether the
   art. 30 record must list them (sections 3–4); the CNRS DPO's contact.
6. The terms of OECD, IATI publishers, World Bank documents and each
   secretariat, checked at release time and recorded in the terms table
   (section 2).
7. Whether a takedown procedure should be formalised as a CNRS-approved
   text (section 5).

*This note is not legal advice. It was drafted by a language model from its
training knowledge, with the references marked "to verify" unchecked
against primary sources, and it binds no one until a qualified lawyer has
reviewed it.*
