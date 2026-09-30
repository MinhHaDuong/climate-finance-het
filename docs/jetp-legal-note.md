# JETP Observer: legal note (France)

Supporting document of the [specification](jetp-spec.md). Commissioned by
the author on 2026-09-30 under review finding W1-29
([ledger](jetp-spec-review/wave-1/ledger.md)) and requirement Q21. Drafted
by a language model (Fable), reviewed by a second model (Astra, GPT-6,
verdict "needs corrections", review archived at
[`jetp-spec-review/legal/astra-review.md`](jetp-spec-review/legal/astra-review.md))
and revised on the same day. A human legal review is a go-live gate, not a
build gate: no one is consulted while the Observatory is undeployed. **This note
is not legal advice.** It states, for each activity of the Observer, the
rule it relies on under French law and EU law as applied in France, how the
Observer complies or what it must change, a residual risk rating, and what
the specification must say. Every legal claim carries its article; a claim
neither drafter nor reviewer checked against a primary source is marked
*to verify*. Jurisdiction: France. Publisher: a researcher of the CNRS
working at CIRED.

Abbreviations: CPI, *Code de la propriété intellectuelle*; CRPA, *Code des
relations entre le public et l'administration*; LCEN, *Loi n° 2004-575 pour
la confiance dans l'économie numérique*, as renumbered by Loi n° 2024-449
(*SREN*); LIL, *Loi n° 78-17 Informatique et Libertés*; DSM, Directive (EU)
2019/790; GDPR, Regulation (EU) 2016/679; TDM, text and data mining
(*fouille de textes et de données*).

**One basis per act.** Acquiring a copy, mining it, retaining it, sending
it to a provider abroad, publishing extracts and licensing the output are
six distinct acts. Permission for one establishes nothing for the others;
each section below covers one or two of them.

## Summary of risk ratings

Ratings assess the arrangement as described, with its unresolved
conditions; they are not litigation probabilities.

| # | Activity | Residual risk | Condition |
|---|---|---|---|
| 1 | Collecting and holding copies | medium pending the institutional and security checks, low afterward | research TDM under L122-5-3 II and R122-23 to R122-25; the project recorded as a CNRS research activity; storage documented |
| 2 | Redistributing extracts | medium; high for any unlicensed re-serving of a substantial part of a protected database | quotation assessed per use; database producer and protection identified per table; licence where needed |
| 3 | Personal data in documents | medium until the controller and the safeguards are documented, low afterward | art. 6(1)(e) with art. 6(3); minimisation before hosted calls; art. 14 exemption documented; privacy notice complete |
| 4 | Sending content to LLM providers | medium pending the provider agreement and the transfer mapping | R122-23 II agreement; art. 28 contract where the provider is a processor; approved endpoints enforced, fail closed |
| 5 | Website obligations | medium | LCEN art. 1-1 notice; three-day right of reply; host logging described; accessibility scheme |
| 6 | Licensing the releases | medium pending the ownership and licence decisions, low afterward | who holds the rights; CC BY 4.0 or Licence Ouverte 2.0; third-party material marked |

## 1. Collecting and holding copies

**Rule.** Reproducing a work is a restricted act (CPI L122-3, L122-4).
Ordinary browsing is not copy-free: it rests on the publisher's implied
permission or on the transient-copy exception of L122-5 6°. A persistent
copy held by the project needs its own basis. Two exceptions transpose DSM
arts 3 and 4 (Ordonnance n° 2021-1518 of 24 November 2021, Décret
n° 2022-928 of 23 June 2022):

- **Research TDM**, CPI L122-5-3 II (copyright) and L342-3 6° (database
  right): copies made for TDM for scientific research by research
  organisations and cultural heritage institutions, from content to which
  they have *lawful access*. R122-23 covers the institution's personnel,
  affiliated researchers and persons acting on its behalf and at its
  request; R122-23 II requires, where copies are held by a third party, an
  agreement on access, security and return or deletion. R122-24 provides
  the deposit agreement for external storage; R122-25 lets a rights holder
  ask for evidence of appropriate security and exclusively scientific
  retention. Copies may be kept for research, including verification of
  results (DSM art. 3(2)); this is not a licence for unrestricted permanent
  archiving, nor for publication. The CNRS is an EPST (Code de la recherche
  R322-1). DSM art. 2(1) excludes organisations under the decisive
  influence of a commercial undertaking with preferential access to
  results; the French text carries a related exclusion (*to verify*).
- **General TDM**, L122-5-3 III and L342-3 6°: copies of lawfully
  accessible works by anyone, unless the rights holder has reserved the
  right appropriately, including by machine-readable means for content
  online (DSM art. 4(3); R122-28 names a website's or service's terms and
  machine-readable methods, and prescribes no protocol). Copies are stored
  securely and destroyed when the mining ends (L122-5-3 III).
- **Contract terms.** DSM art. 7(1) makes contractual provisions contrary
  to art. 3 unenforceable, and does not extend that to art. 4. On the
  database side, the paragraph following L342-3 nullifies clauses contrary
  to its 1° and 6°. L122-5-3 carries no equivalent sentence on the
  copyright side; how a research organisation enforces the art. 3 rule
  against a contractual restriction in France is a point for counsel.

Both exceptions are subject to the three-step test (DSM art. 7(2), CPI
L122-5 last paragraph).

**What counts as a machine-readable opt-out.** R122-28 and DSM recital 18
accept terms of a website or service and machine-readable methods, without
naming one. Signals in use: `robots.txt` (including agent-specific rules),
the W3C TDM Reservation Protocol (`tdm-reservation` header, `tdmrep.json`,
HTML meta), `ai.txt`, and natural-language terms. Whether a given signal
validly reserves the right depends on its wording, scope and authority.
The Hamburg courts (LG Hamburg, 27 September 2024, 310 O 227/23; OLG
Hamburg, 10 December 2025, 5 U 104/24, appeal dismissed, further appeal
permitted, not final) held that natural-language terms may be machine
readable and applied the research exception to a non-profit dataset
builder: foreign authority, persuasive only. The AI Act (Regulation (EU)
2024/1689 art. 53(1)(c)) obliges general-purpose AI providers to honour art.
4 reservations; the Commission's Code of Practice is voluntary and settles
no French copyright question. None of this binds the Observer; it matters
because under the research exception no reservation defeats the copy, so
the record of the site's position is *evidence of lawful access and good
faith*, not a condition of the exception.

**How the Observer complies, and what must change.** The research
exception is the primary basis *if* the Observer operates within the
CNRS's research activity: a researcher's affiliation does not by itself
bring an independently operated website inside it. The institutional
connection, the scientific purpose and the responsibility for the copies
must be recorded (operation §1, the "who runs the Observer" section, *to
add*). Storage: the archive is a DVC store on the author's machines, not
served to the public, and the local preview's `documents/` directory is
git-ignored (observatory README). That is a design fact, not proof of
"appropriate security": the operation document must describe access
control, device protection, backups, remote stores, authorised users and
the retention purpose, so that an R122-25 request can be answered; any
remote store held by a third party needs the R122-24 deposit agreement.

**Login-gated sites with free registration.** Public availability or a
registration anyone can obtain supports lawful access; the actual account
entitlement (what a registered user may download, and how) must be
verified per site. A clause forbidding *all* automated access may be a
restriction on research TDM that art. 7(1) makes unenforceable; a
proportionate measure protecting the network's integrity remains
permissible; which side a clause falls on is decided clause by clause.
The Observer's rule that the author passes logins in person (collection;
C6) is good practice and does not by itself settle the lawfulness of
subsequent automated requests under that account. The registration used
is recorded without credentials (F27).

**Spec.** Collection §"Public access only" and §"Crawler rules": name
L122-5-3 II and R122-23 as the basis for holding copies, conditional on
the institutional record, and the site-position record as evidence of
lawful access. Operation: the storage description above and the
institutional record. Storage contract: `terms_position`,
`robots_position`, `registration_used` (W1-29).

## 2. Redistributing extracts

**Rule.**

- *Short quotation*, CPI L122-5 3° a): short quotations justified by the
  critical, polemical, educational, scientific or informative character of
  the work into which they are incorporated, with the author's name and
  the source clearly indicated. There is no fixed permitted number of
  sentences or rows. Each use is assessed on brevity relative to both
  works, the statutory purpose, incorporation into the Observer's own
  contribution, identification of the author (the publisher field does
  not always name the author) and the three-step test. A standalone
  export holding many quotations needs its own assessment, and so does
  what a user can reconstruct across the exports of a release. Cass. 1re
  civ., 13 November 2003, 01-14.385 (*Utrillo*) refused the exception to
  complete reproductions; Cass. ass. plén., 30 October 1987, 86-11.918
  (*Microfor c. Le Monde*) admitted a documentary index of short extracts.
  Facts (an amount, a date, a name) are not expression; the wording around
  them and their selection may be.
- *Sui generis database right*, CPI L341-1 (a producer who took the
  initiative and the risk of a substantial investment in obtaining,
  verifying or presenting the contents; investment in *creating* the data
  does not count, CJEU C-203/02 *British Horseracing Board*), L342-1
  (extraction or re-use of a qualitatively or quantitatively substantial
  part), L342-2 (repeated and systematic extraction of insubstantial parts
  exceeding normal use), L342-3 1° (a lawful user may extract insubstantial
  parts). Fifteen years from 1 January following completion, reset by a
  new substantial investment (L342-5). Beneficiaries: L341-2 (nationality
  or residence, or company formation plus establishment, in the EU or EEA,
  and international agreements). **Database rights protect collections of
  unprotected facts; selecting factual columns or re-arranging them does
  not defeat them, and a TDM permission authorises mining, not
  republication.** Not every table in a report is a protected database;
  the producer, possible co-producers and the rights chain must be
  identified per table, not read off the issuing ministry, and an
  international organisation's Paris address settles nothing under
  L341-2.
- *Re-use of public-sector information*, CRPA L321-1 et seq.: information
  in documents produced or received by an *administration* (L300-2) is
  freely re-usable; third-party intellectual property is excluded
  (L321-2); L321-3 also bars the listed administrations from using their
  database right to block re-use of databases published under L312-1-1
  3°; L322-1 requires the source and the last-update date and forbids
  alteration. It covers French administrations only: nothing for foreign
  ministries or international organisations. For the Observer's *own*
  output produced within the CNRS mission it is the regime of section 6.
  Code de la recherche L533-4 II makes research data freely re-usable
  when the research is at least half publicly funded, the data are not
  protected by a specific right or regulation, and they were made public
  by the researcher or institution; it removes no third-party copyright,
  database right or GDPR obligation.
- *Foreign official texts.* Berne art. 2(4) leaves protection of official
  texts to each state; in France laws, decrees and court decisions are
  unprotected by constant case law, and a foreign work's protection in
  France is decided under French law (Berne art. 5(2)). All four countries
  exclude such texts at home: South Africa Copyright Act 1978 s. 12(8)(a);
  Indonesia Law 28/2014 art. 42; Viet Nam IP Law 2005 (amended 2022) art.
  15; Senegal Loi n° 2008-09 art. 9. A decree or decision approving a plan
  is an official text; whether the plan (JET-IP, CIPP, RMP, Senegal's
  investment plan) is a protected report or an annex to a binding act must
  be assessed document by document from its publication instrument; other
  passages need originality to be protected at all.
- *International organisations and their data licences.* As known, each
  entry *to verify* against the terms in force at release time:

  | Publisher | Terms as known | What to check |
  |---|---|---|
  | OECD (CRS, DAC statistics) | Terms and Conditions: written content published from 1 July 2024 under CC BY 4.0; separate data provisions and exceptions | that CRS bulk exports fall under the data provisions; the attribution text |
  | IATI | The registry lists each publisher's own licence; the Standard requires an open licence, the publisher chooses (CC BY, ODbL, OGL, public domain) | the licence of each publisher served; under ODbL, whether the Observer's output is a derivative database, a collective database or a produced work |
  | World Bank | CC BY 4.0 is the default for specified Bank-produced open datasets, with additional terms; not a licence for the whole website; documents carry their own notice | project pages, PADs, ISRs, and the "restricted" mark |
  | JETP secretariats (South Africa IPMO, Indonesia, Viet Nam, Senegal) | no licence stated, as far as known | site terms; unknown terms mean bytes are cited, not served (results §7) |
  | Development banks and agencies (AfDB, ADB, AIIB, EIB, KfW, AFD, JBIC) | disclosure policies and site terms; open-data licences for datasets, not documents | per bank; EIB, KfW and AFD are EU-established, so their databases are candidates for the sui generis right |
  | News sites | rights reserved | quotation only; no bytes |

**How the Observer complies.** Results §7 serves verbatim labels, short
excerpts and the printed fields of tables with attribution, document and
locator, serves document bytes only where terms allow, and treats unknown
terms as forbidding (C6). The exposure is the document-rows view: it
re-serves the project table of a plan, which for a protected database is a
substantial extraction whatever columns are kept. Whether the four plans'
tables are protected databases (producer, investment in obtaining and
verifying rather than creating, L341-2 beneficiary) is the open question
that decides the rating; the Observer's own selection and arrangement
protects its contribution, not the re-served content.

**What must change.** (i) A per-table protection assessment (producer,
investment, beneficiary status, licence) recorded in the terms table and
served on the Legal page; (ii) a licence or a written non-protection
finding before any complete or cumulative export of a table whose
producer may hold the right; (iii) a representative export review at each
release: the CSV and JSON downloads, the document-rows pages and what a
user can reconstruct across them, not each displayed row alone.

**Spec.** Results §7: replace the pending W1-29 comment with the basis per
case (quotation assessed per use; database right assessed per table and
producer; public-sector re-use for French administrations only; terms
table served) and the export review as a release gate. Requirements C6:
add "and its licence, where stated" to the site position record.

## 3. Personal data in documents

**Rule.** A name in a document is personal data (GDPR art. 4(1)), official
capacity or public availability notwithstanding (CJEU C-92/09 and C-93/09
*Schecke*). Basis: art. 6(1)(e) read with art. 6(3), processing necessary
for a task in the public interest laid down by law, the CNRS research
mission (Code de la recherche L321-1, L112-1), once the *controller* is
identified: the CNRS, another CIRED tutelle, joint controllers, or the
researcher, according to who decides purposes and means. Art. 89(1)
supplies safeguards (minimisation, pseudonymisation where the purpose
allows), not a basis. Art. 5(1)(b): further processing for research is
compatible. Art. 14(5)(b): individual information may be replaced by a
public notice where it is impossible or disproportionate, which must be
documented, not assumed. Art. 17(3)(d): erasure may be refused only where
it would render the research impossible or seriously impair it. French
law: LIL art. 78 (archives paragraph distinct from research), art. 79
(indirect collection), Décret n° 2019-536 art. 116 (research derogations);
art. 80 with GDPR art. 85 (academic expression) applies derogation by
derogation to the published statements, and not to collection or
outsourcing. Art. 9 and 10: a public report can carry political opinions,
union membership or allegations; "public document" is no exemption, so
inputs are screened.

**How the Observer complies.** Parties in the ledger are organisations
(ontology §2). Names of officials appear inside archived documents and,
where a statement is attributed to a signatory, in the verbatim label. No
contact detail of a natural person is extracted or served. Whole documents
are sent to readers before extraction (section 4), so minimisation must
act on the input, not only the output table.

**What must change.** (i) Identify the controller and record the
processing in its art. 30 register through the CNRS DPO; (ii) an
extraction rule: a name enters a table only as the author or signatory of
a statement when that identification is necessary, never as a contact;
readers are instructed accordingly; where feasible, personal information
not needed for the reading is removed before a hosted call; (iii) a
documented DPIA screening against the art. 35 test and the CNIL criteria
(probably not required, but written down); (iv) the art. 14(5)(b)
justification written; (v) a privacy notice with controller and DPO
contacts, purposes, basis, categories and origin, recipients, transfers,
retention, rights and the CNIL complaint route (arts 13–14); (vi) a
procedure assigning who answers access, objection and erasure requests and
security incidents, including copies already deposited or mirrored.

**Spec.** Extraction §3: the minimisation rule. Presentation: the privacy
notice on the Legal page. Operation: the register, the DPO contact, the
requests-and-incidents procedure.

## 4. Sending document content to LLM providers

**Rule.** Sending a document's text to a hosted model makes a copy on the
provider's servers. For research TDM, R122-23 II requires an agreement
with the third party holding the copies covering access, security and
return or deletion; provider terms may satisfy it, and cannot replace it.
A provider that trains on inputs or re-uses them makes copies the
exception does not cover, under the law of the place where they occur.
Where the provider processes personal data on the Observer's instructions
it is a processor and an art. 28 contract is required; whether it is one
depends on its actual purposes. Transfer outside the EU (GDPR chap. V): the
EU–US Data Privacy Framework (Decision (EU) 2023/1795, upheld by the
General Court in T-553/23 *Latombe*, 3 September 2025; appeal C-703/25 P
pending) for the certified recipient entity and processing; otherwise
standard contractual clauses (Decision (EU) 2021/914) with a transfer
impact assessment and supplementary measures. Zero retention does not
remove a transfer; an EU server location does not settle access questions.
Public availability of a document lowers, and does not remove, privacy,
misattribution and rights risks: an accidentally exposed document remains
protected, and a whole document discloses more personal data than the
intended output.

**How the Observer complies.** Operation §5–§7: readers are open-weight
models run locally on padme (no transfer), the same models through
OpenRouter as fallback, and a hosted arbiter through OpenRouter. OpenRouter
documents `data_collection: "deny"` and `zdr: true` request parameters and
a sovereign (EU-hosted) routing option with its own availability
conditions; its terms also carry input-categorisation and licensing
provisions beyond training. No executed CNRS agreement with OpenRouter is
known to the drafter.

**What must change.** Operation must state: hosted calls carry only public
document text after the minimisation of section 3; approved endpoints are
enforced in code and the call fails closed when none qualifies; OpenRouter,
the endpoints, sub-processors, logging, support access and onward
transfers are mapped, and the map is reviewed when the provider's terms
change, not recorded once; the R122-23 II agreement and, where applicable,
the art. 28 contract and the transfer mechanism are obtained through the
CNRS.

**Spec.** Operation §7 (models and calls): the settings and the fail-closed
rule. Operation §11: the provider map and its review.

## 5. The website's obligations

**Rule.** LCEN art. 1-1 (since Loi n° 2024-449 *SREN*): every online public
communication service makes available, as applicable, the publisher's
identity, address and telephone, registration and capital where the
publisher is a company (not the CNRS), the *directeur de la publication*
and any editorial manager, the host's identity, address and telephone, and
the identity and address of any other data-storage provider (I, 5°); a
non-professional natural person may stay anonymous toward the public if
the host holds its identity (II). The publication director follows the
publisher's legal status (Loi n° 82-652 art. 93-2); it is not an editorial
appointment. Missing notice: art. 1-2 (one year, €75,000, for the
responsible natural person). Right of reply online, art. 1-1 III: a
qualifying reply, from a natural or legal person named, is inserted within
three days of receipt, the request being made within three months of
publication. Host notification: the DSA (Regulation (EU) 2022/2065 art.
16) and the current LCEN hosting provisions (*paragraph to verify*). The
Observer is an editor, directly liable for what it publishes; removal
after the fact does not cure it, and a takedown route is good practice,
not a safe harbour.

*Trackers*: LIL art. 82 (ePrivacy art. 5(3)). A static site with no
analytics, no third-party script or font sets none; actual browser
behaviour is verified at each release. GitHub logs Pages visitors' IP
addresses under its own privacy statement: the notice describes that
processing, the respective responsibilities and the transfer it implies.

*Accessibility*: Loi n° 2005-102 art. 47 and Décret n° 2019-768 (RGAA)
bind public bodies' online services: accessibility itself, a conformity
declaration, a feedback route, and links to the multiannual scheme and
annual plan of the responsible body.

*AI-generated text*: AI Act art. 50(4) (from 2 August 2026) requires
disclosure of AI-generated text published to inform the public on matters
of public interest, except under human review and editorial responsibility;
the Observatory's pages are authored and reviewed, the LLM readings are
data with a recorded human check (operation §5); the exception is to be
stated explicitly.

**How the Observer complies, and what must change.** PR #1617 adds a
Legal page under About with the notice fields, the licence statement, the
publishers-and-terms table, the corrections, reply and takedown route and
the privacy statement, each unsupplied fact a visible `[TO CONFIRM]`. The
publisher identity (CNRS or the researcher) decides the notice, the
publication director and whether RGAA applies. Right-of-reply handling
must meet the three-day deadline; GDPR requests, ordinary corrections and
urgent illegality complaints are distinguished from it.

**Spec.** Presentation §Navigation: the Legal page under About. Operation:
who answers a reply request within three days, a GDPR request within one
month (art. 12(3)), a correction or takedown request, and how the decision
is recorded in `decisions.md`; the accessibility scheme the site is
attached to.

## 6. Licensing the releases

**Rule.** CC BY 4.0 licenses the rights the licensor holds in the licensed
material (sections 1, 2(a)), copyright and sui generis database rights
alike (section 4); it manufactures no right over bare facts, requires
nothing where an exception independently applies, and validates no
unlawful reproduction by attribution. Third-party material is marked as
such (Creative Commons guidance on marking third-party content). Ownership
is separate: a researcher may retain copyright in his writing under the
public-agent rule of CPI L111-1, while a database producer's right may lie
with the institution; who may grant the licence follows from that. If the
licensor is an administration, CRPA L323-1 permits licensing (and requires
it for fee-based re-use), L323-2 requires a licence from the approved list,
D323-2-1 lists Licence Ouverte 2.0 and ODbL, and D323-2-2 provides a
request procedure decided by the Prime Minister for another licence;
Licence Ouverte 2.0 is compatible with CC BY 4.0 and not identical to it.
Zenodo requires a licence per deposit.

**How the Observer complies.** Results §6 states an attribution-only
licence; results §7 separates what is redistributed from what is cited.

**What must change.** Decide who holds the rights and which licence
applies (CC BY 4.0 if the researcher licenses his own work; Licence
Ouverte 2.0 if the CNRS licenses an administrative document). Then label
at three levels: (i) a `LICENSE` file in each release and on Zenodo,
naming the licence and its scope, "the tables, results, dictionary,
provenance, reports and pages produced by the JETP Observer"; (ii) the
redistribution list of results §7 stating, per document, publisher, terms
and whether bytes are served; (iii) in every served table the `publisher`,
`document_id` and `locator` columns, with a data-dictionary line saying a
verbatim label is the publisher's text quoted under L122-5 3° a). The code
stays under its own open-source licence (F30).

**Spec.** Results §6 "Licence": "The licence covers the Observer's own
contributions, granted by whoever holds the rights in them; a publisher's
text is quoted under CPI L122-5 3° a) and remains its publisher's; a
document's bytes are served under that document's terms, stated in the
redistribution list." Results §7: the three labels.

## Open points for a human lawyer, the CNRS legal service (DAJ) and the DPO

These points are raised only when the author decides to deploy the
Observatory publicly [M3b go-live gate]; until then the Observer runs on the
basis stated above and no legal service is consulted.

1. Is the Observer formally conducted within the CNRS research mission,
   and which institution assumes responsibility given CIRED's structure
   (sections 1, 3)?
2. Who is the legal publisher, the publication director, the GDPR
   controller and the database producer; who may sign provider agreements
   and grant release licences (sections 3–6)?
3. Do the activity and the outsourcing satisfy L122-5-3 II and R122-23,
   including institutional control and the commercial-partner exclusion;
   and by what domestic route is a contractual clause restricting research
   TDM set aside on the copyright side (section 1)?
4. Are the researcher's machines, the DVC store, its backups and any
   external store acceptable for TDM retention (R122-24, R122-25) and CNRS
   security rules (section 1)?
5. Which access restrictions need negotiation, and how to treat a clause
   forbidding all automated access on a free-registration site (section 1)?
6. Which source tables are protected databases, who produced them, and
   which complete or cumulative exports need a licence, in particular the
   four plans' project tables and any EU-established publisher's table
   (section 2)?
7. Which outputs fall under the CRPA licensing regime and which remain the
   researcher's works; CC BY 4.0 or Licence Ouverte 2.0 (section 6)?
8. Are OpenRouter and each permitted endpoint approved, with the R122-23
   II agreement, an art. 28 contract where needed, a transfer mechanism
   and enforceable retention limits (section 4)?
9. What art. 14(5)(b) justification, retention schedule, rights
   derogations and DPIA screening does the DPO accept (section 3)?
10. Which accessibility scheme and which publication-response procedure
    (right of reply, takedown, GDPR requests) cover the site (section 5)?
11. Whether the four investment plans are protected reports or annexes to
    binding acts, from their publication instruments (section 2).
12. The terms of OECD, each IATI publisher, World Bank documents and each
    secretariat, checked at release time (section 2).

## Review by Astra: points not adopted

- Rating for topic 2: Astra proposes "potentially high". Kept at medium
  with a high branch for unlicensed re-serving of a substantial part of a
  protected database, because the high case is conditional on a
  protection finding not yet made, and the note says so in the table.
- "Verification of implementation claims": the Legal page is in the same
  PR as this note and is checked by a render test; the note now says what
  the page holds and where, and leaves whether its placeholders are filled
  to the author, which is what Astra asked.
- Every other correction (1–31) and every missing point is adopted above;
  Astra's ten questions are merged into the open points, deduplicated.

*This note is not legal advice. It was drafted and reviewed by language
models; the references marked "to verify" are unchecked against primary
sources, and it binds no one until a qualified lawyer has reviewed it.*
