# JETP collection: how documents are found and fetched

Status: draft for author review, 2026-09-30.

Collection is how the documents the ledger reads are found, judged worth
reading and fetched, when discovery stops, and how much of what exists it
found. It fills the register, the first step of Data in the
[language](jetp-language.md) document. Its output feeds
[extraction](jetp-extraction.md), which reads statements from what collection
holds; the [fusion](jetp-fusion.md) rules then weigh those statements. What
the ledger is for, and so what is in scope, is the
[purpose and requirements](jetp-requirements.md) document.

Its rules are conceptual. They name what must happen, not how the repository
does it: commands, schedules, machines, budgets in numbers and the place where
bytes are kept belong to the operation document and to the
[storage contract](jetp-ledger-storage.md). The words document, retrieval,
snapshot, publisher and edition have the meaning the
[ontology](jetp-ontology.md) gives them (section 2 and the relations of
section 3); this document does not restate them.

**Milestones.** Every rule ends with the milestone that needs it:
[M2] the extraction pipeline over what is held, [M3a] one discovery campaign
to a cutoff and the freeze of the register, [M3b] extraction of the new
documents and reconciliation, [M4] recurring operation, [later] beyond M4. M2
does no new discovery. M3a is one campaign, not a service. Recurring refresh,
link rot and the tracking of living documents and series are M4. A rule tagged
M4 or later is not built before that milestone.

## 1. Principles

**Discovery proposes, review admits.** A document enters the register only
by a recorded judgement that it is in scope. Finding it, by any route, makes
it a candidate and nothing more. No search, crawler, agent or watch admits a
document on its own. [M3a]

**Every attempt is recorded.** Each fetch is a retrieval with its outcome,
failures included. Each search is recorded with its routes, the identifiers
and terms it used, its date, its effort and its yield, and a search that finds
nothing is recorded as such. A failed route means "not found through this
route on this date", never "does not exist". A silent run is not an all-clear.
[M2 for retrievals, M3a for searches]

**Within the author's own rights.** Collection uses only the access the
author has: public pages, and pages the author's own browser session opens.
It never passes a paywall or a login the author does not hold, and never
circumvents a technical measure that a person with the author's access could
not pass. A site's stated position on automated access (its terms of use,
its crawler rules) is recorded with the attempts made there, and any change in
it is reported, never passed over. [M3a]

**Crawler rules.** Automated link-following, where a program walks a site
from page to page, obeys the site's crawler rules (robots.txt). A single fetch
of a known document that the author could open in a browser goes ahead
whatever those rules say, and the site's stated position is recorded with the
retrieval. [M3a]

**The route does not colour the document.** A decree found through a news
article is the ministry's decree. A document's pedigree in the sense of
[fusion](jetp-fusion.md) section 1 attaches to its publisher and to how it was
produced, not to the channel that led to it. Channels have a pedigree of their
own only in one sense: some lead more often, and faster, to documents close to
the event. That guides where to search first; it never ranks a statement.
[M3a]

**Secondary documents are leads.** A tracker, a news article or a study that
reports a figure points toward the primary document behind it. Collection
follows the lead. Whether the secondary document may stand alone is decided
by fusion section 5, on the strength of the search recorded here (section 7).
[M3a]

**Structured channels have no precedence.** OECD CRS and IATI are channels
like others: they point to documents and supply comparator records. They
report late, and that lag is measured at reconciliation, not assumed. [M3b]

**Budgeted and declared in advance.** Discovery effort is budgeted per round
and per campaign, and spent effort is logged beside yield. The protocol of a
campaign (frame, known-item list, thresholds, caps) is declared before its
first round. A change after the start is a recorded revision with its reason,
reported with the results. [M3a]

**Storage and presentation independence.** No rule here depends on where
bytes are kept or how the register is shown. A change of document store
changes nothing in these rules. [M3a]

## 2. What collection handles

Collection handles four things. Their definitions are the ontology's.

- A **candidate** is a pointer to something that may be a document in scope:
  a URL, a title with a publisher, a reference printed in another document.
  It is not in the register. [M3a]
- A **document** is admitted by triage (section 9) and then sought.
  Admission and fetching are distinct: a document can be admitted and remain
  unfetched, and it then carries its access outcome (section 8). [M3a]
- A **retrieval** is one attempt to fetch one document. [M2]
- A **snapshot** is the bytes a successful retrieval returned. The bytes kept
  are the server's response. A rendered page is kept beside it only when the
  response alone does not carry the content (tabs built by a script, for
  example). [M2]

Duplicates are settled before anything is read, by the document judgements of
fusion section 3: one publication under two addresses is one document
(`same_as`), a later issue is an `edition_of`, the same text in another
language is a `translation_of`. A mirror kept by a third party, such as a web
archive copy or a partner's re-hosting, names that party in a hosting role.
[M3a]

The register held before the M3a campaign is its round zero. Those documents
were not found under this protocol; their routes are recorded where known, and
later rounds measure their yield against them. [M3a]

## 3. The authority frame

For each country, the campaign declares in advance which authorities are
expected to publish about its partnership. The starting frame is:

1. the national JETP portal or the responsible ministry;
2. the co-leads of the International Partners Group and every public partner
   named in the package;
3. the multilateral and private financing windows named in official
   financing tables;
4. the national electricity operator and the named project operators;
5. every project in an official plan, pipeline or progress list.

Each expected authority, and each listed project, ends the campaign with one
terminal verdict. [M3a]

A listed project gets one bounded round of its own, on the disclosure sites
of the partners named for it (partner disclosure, section 4), beside what the
other rounds find about it. Deeper searches for a single project are later
work. [M3a for the bounded round, later for deeper searches]

| Verdict | Meaning |
|---|---|
| collected | at least one admitted document is held. For a listed project, a document other than the list that names it |
| not published | the recorded search (section 7) covered the channels where it would appear and found none |
| blocked | a document or channel exists and could not be fetched within the author's rights; it enters the unreachable list |
| not applicable | the authority or project turns out to be outside the frame, with the reason |

"Not published" is a finding about the authority, not a gap in collection.
"Blocked" is a gap, and it is published as one (section 8). [M3a]

## 4. Channel classes

A channel is a way of finding documents. The frame of a campaign is a fixed
list of channel classes for each country, and each is searched in each of the
country's languages that it serves. The classes are:

| Class | What it covers | Closeness it tends to lead to |
|---|---|---|
| authority portals | the national secretariat, ministries, regulators | primary |
| partner disclosure | the project databases and disclosure pages of IPG members, development banks and funds | primary |
| operator sites | the electricity operator and named project operators | primary |
| structured reporting | CRS and IATI records, as pointers to documents | primary, late |
| references in held documents | documents cited by documents already held | mixed |
| secondary trackers and news | the declared list of trackers, think-tank reports, the press | leads (section 6) |
| general web search | search engines, per language | whatever the result is |
| web archives | archived copies of pages that moved or disappeared | the archived document's |

Languages at M3a are, per country, its official language and English:
Indonesian, Vietnamese and French beside English, and English for South
Africa. A partner's own language is searched only on that partner's
disclosure channel. [M3a]

Every channel class of the frame is searched at least once per country and
language before the stopping rule may fire (section 5). A class may be
declared not applicable to a country, with the reason, before the first
round. [M3a]

Search beyond the channels and sites already known, run periodically by a
local agent, is M4. Its candidates join the same triage and are never
admitted automatically. [M4]

## 5. Rounds and the stopping rule

A **round** is one bounded search, in one channel class, for one country and
language, with its routes declared, its effort budget stated and its
candidates triaged before the next round's yield is counted. [M3a]

**The round log** records for each round: country, language, channel class,
routes and terms, date, effort spent, candidates found, and the number newly
admitted after triage. Rounds that admit nothing are logged like the others.
[M3a]

**Yield.** A round's yield is the number of documents it newly admits.
Duplicates and mirrors of held documents add nothing. A translation of a held
document adds nothing. A new edition is a new document and counts. A
candidate kept as context only (section 9) does not count. [M3a]

**Stopping rule.** Stopping is judged per country. A country's discovery
stops when all three conditions hold. [M3a]

1. **Frame covered.** Every channel class of the frame has been searched in
   every language it serves, and every expected authority and listed project
   has a terminal verdict.
2. **Quiet tail.** The last two rounds, in two different channel classes,
   were each quiet. A round is quiet when its yield is at most 2 % of the
   country's admitted documents at the start of the round, and at most one
   document when that 2 % is below one.
3. **Recall.** The campaign's known-item recall (section 6) is at least 90 %.

The recall condition is computed on the pooled known-item list, since a list
per country is too small to estimate from; per-country shares are reported
beside it. [M3a]

**Backstop.** The campaign declares a date cap and an effort cap before its
first round. When either is reached, discovery stops wherever it stands, the
results say "stopped by cap", and they report which conditions were unmet.
[M3a]

**Tunable numbers.** The 2 %, the two rounds, the 90 % and the caps are
starting values, fixed for a campaign when it is declared and tuned between
campaigns on what the round log shows. [M3a]

**Acceptance.** The author accepts the protocol before the first round, and
accepts the recall estimate and the unreachable list before M3b starts. [M3a]

## 6. Known items and the recall estimate

**The known-item list** is a list of documents that ought to be found, built
and frozen before the first round from outside the channel frame:
the reference lists of academic and grey literature on the partnerships, and
documents named by the author or by people who know the field. It is never
drawn from the declared secondary trackers, which the secondary-to-primary
pass searches (section 7): recall measured on them would be circular. Each
item is identified well enough to decide whether a held document is it. The
list holds at least 40 items across the four countries, so that its interval
(below) is informative; the size is tunable upward. [M3a]

**Blind use.** Those who search do not see the list. It is compared with the
register only at declared checkpoints and at the end. [M3a]

**Recall.** Recall is the share of known items found by the campaign's
rounds, admitted or held from round zero, reported with its 95 % Wilson
interval, for example "36 of 40, 90 % (77 to 96 %)". [M3a]

**A missed item is a diagnosis.** At a checkpoint, a missed item is examined
for the channel that would have found it. If that channel is missing from the
frame, the frame is revised (a recorded revision) and the new channel is
searched like the others. An item fetched by looking it up from the list
enters the register if in scope but never counts as recovered. [M3a]

**Limits stated.** Known items are more visible than the average document,
since someone cited them, so known-item recall tends to overstate recall. The
results say so. A second estimate from the overlap between two independent
channel classes (capture and recapture) is later work. [M3a for the caveat,
later for the second estimate]

## 7. The secondary-to-primary pass

The campaign declares, before its first round, the main secondary trackers
of the four partnerships. The pass takes each quantitative claim they make
about a partnership, a project or a financing, and follows it to its primary
document. Each claim ends with one outcome. [M3a]

| Outcome | Meaning |
|---|---|
| traced, held | a held primary document carries the claim |
| traced, admitted | the pass found the primary document and triage admitted it |
| traced, unreachable | a primary document is identified and could not be fetched; it enters the unreachable list |
| untraced | the recorded search found no primary document |
| secondary only | the claim cites another secondary document, followed once more before it ends here |

**Traceability rate.** The share of claims examined that are traced
(held, admitted or unreachable), reported with its interval and published at
M3a. When a tracker makes more claims than the budget allows, the pass
examines a random sample drawn before it starts, and says so. [M3a]

**The recorded search.** "No primary document found", here and in fusion
section 5, means a search that covered at least the publisher's own channel,
the partner disclosure channel when a partner is named, and one general web
search in each relevant language, with the routes and terms recorded. A
claim is untraced only after that search. [M3a]

The pass is a channel class like the others: its admissions count as yield
in the stopping rule. [M3a]

## 8. Access and unreachable documents

**Access ladder.** A document that refuses a plain automated request is
retried, rung by rung, within the author's own rights. [M3a]

1. A plain automated request.
2. The same request carrying the author's own browser session, for that
   site only.
3. An automated browser, with the author clearing a check or logging in
   with the author's own credentials when needed.
4. The author opens and saves the document by hand; the saved copy is
   matched to its document by the address it came from, never by name.
5. A web archive copy, which is a snapshot of the archived document with the
   archive named as host.

Each retrieval records the rung it used. A site whose certificate is invalid
is still fetched, and the error is recorded with the retrieval. Credentials,
cookies and tokens never appear in any record. Sending a request for a
document to its publisher needs the author's explicit authorisation, case by
case. [M3a]

**Unreachable documents are data.** The unreachable list is released with
the frozen register. Each entry names what is missing (an expected document,
or a channel of an expected authority), why it is expected, the rungs tried
with their dates, and the reason it stopped: login required, paywall, bot wall
not cleared, certificate or server failure, removed with no archive copy,
declared but not published. It is a result: it tells the reader where the
register is blind. [M3a]

## 9. Candidate triage

Each candidate gets one disposition. [M3a]

| Disposition | Meaning |
|---|---|
| admit | in scope as the requirements document defines it; it becomes a document of the register and extraction reads it |
| context only | kept and citable, not extracted: a general news item, background reading, a document about the partnership but with no statement the ledger records |
| reject | out of scope, with the reason |
| duplicate | the same document as one held, judged as in fusion section 3; recorded against the held document |

**Who decides.** A disposition is a judgement, recorded with the candidate,
a quoted basis, who or what judged, by which method and version, and when,
as fusion section 3 requires of identity judgements, with a likelihood and
a confidence on the calibrated scales of fusion section 1. [M3a]

**Checking at M3a.** One reader proposes each disposition. A second reader,
from another vendor and blind to the first answer, checks every candidate.
Where both agree, the disposition is in force. The author sees only the
disagreements and a random sample of the agreements, sorted by likelihood and
confidence, and may overturn any of them. A disposition counts, for yield and
for the register, once it is in force. The same checking applies to every
other language-model judgement collection makes at M3a: a document's class, a
claim's outcome in the secondary-to-primary pass, a duplicate. [M3a]

**Checking at M4.** The full reader panel of fusion section 3, with positive
controls run first and readers who miss them weighted out. [M4]

A disposition is defeasible like any judgement: a rejected candidate can be
admitted later by a judgement that says why. [M3a]

## 10. Document classes

Each admitted document is classed, as a dated judgement, in one of three
classes. [M3a for the class, M4 for what each class needs over time]

| Class | Examples | At M3a | At M4 |
|---|---|---|---|
| frozen | a signed agreement, a board report, a plan once issued | fetched once | its address is checked periodically; a disappearance triggers an archive capture or retry (link rot) |
| living | a project data sheet updated as disbursements come, a portfolio portal, a ministry dashboard | fetched once at discovery; earlier snapshots held are kept | refetched at a declared frequency; each changed version is a new snapshot, so the document becomes a dated series of snapshots |
| series | annual and quarterly reports, secretariat progress reports | each issue found is its own document, linked by `edition_of`; the series' publisher and stated periodicity are recorded | the date of the next issue is expected, and a late issue is reported |

A figure read in a living document's snapshot is a statement of that date,
like any other; the next version is a new statement beside it (fusion section
2). [M3a]

## 11. Two published dates and the freeze

**Discovery cutoff.** The date of the last round counted in the campaign.
[M3a]

**Newest document date.** The latest publication date, as its publisher
dates it, among the admitted documents. [M3a]

Both dates are published with the register. They differ from the knowledge
cutoff of fusion section 1 ("two times"), which is the date up to which
admissions and judgements count, here the date of the freeze. [M3a]

**The freeze.** When the author accepts the recall estimate and the
unreachable list, the register is frozen: its documents, their dispositions
and their access outcomes are fixed for M3b. After the freeze: [M3a]

- a candidate found by any route, including a reference read during M3b
  extraction, is recorded as a document not held and waits for the next
  campaign;
- a document published after the discovery cutoff does not enter the frozen
  register, even when found before the freeze;
- a ledger error (a document wrongly admitted, a wrong address) is corrected
  by supersession, as fusion section 2 allows for the ledger's own errors,
  and the correction is reported with the release.

**M2 before the campaign.** M2 discovers nothing. It may retry, on the access
ladder, the retrieval of documents already registered that have no snapshot,
because that is fetching, not discovery; every such document ends with a
snapshot or a recorded access outcome. [M2]

**After M3.** Recurring discovery, the weekly watch beyond known sites,
link-rot checks and the tracking of living documents and series each run on
their own cadence, not under this campaign's stopping rule. Their stopping and
coverage rules are to be written when M4 opens. [M4]

## 12. What M3a must produce

The minimum that yields a citable recall estimate:

1. A declared protocol: authority frame, channel classes per country and
   language, known-item list (frozen, hidden), tracker list, thresholds and
   caps.
2. The round log, empty rounds included, with effort and yield per round.
3. A checked judgement on every candidate: two readers from different
   vendors, the author seeing their disagreements and a random sample.
4. Terminal verdicts for every expected authority and listed project.
5. The recall estimate with its interval, the traceability rate, the
   unreachable list, the discovery cutoff and the newest document date.

Everything else in this document tagged M4 or later is not needed for it.

## 13. Checks a protocol must pass

Each check is a constructed situation and the outcome a correct protocol
produces.

| Situation | Correct outcome |
|---|---|
| A search finds a report that looks relevant; nobody has judged it yet. | It is a candidate: not in the register, not extracted, no yield. |
| A web search round returns twelve hits, all mirrors or duplicates of held documents. | Yield zero; the round is quiet and logged with its effort. |
| A round finds nothing at all. | It is logged with routes, terms, date and effort, and counts as quiet. |
| Two consecutive quiet rounds are both general web searches. | The quiet-tail condition is not met: the two rounds must be in different channel classes. |
| Two quiet rounds in different classes, but the operator channel was never searched for that country. | Discovery does not stop: the frame is not covered. |
| A known item was missed; examining it shows a partner portal missing from the frame. | The frame is revised with a recorded reason and the portal searched; the item looked up directly does not count as recovered. |
| The effort cap is reached with 34 of 40 known items found. | Discovery stops; the results publish 85 % with its interval, "stopped by cap", and the unmet conditions; the author decides whether to accept. |
| A ministry decree is found through a newspaper article. | The decree is a primary document of the ministry; the route is recorded but does not lower its pedigree. |
| A tracker reports a disbursement and cites nothing; the recorded search finds no primary document. | The claim is untraced and lowers the traceability rate; the event may stand on the secondary document only as fusion section 5 allows, marked as such. |
| A page opens only after a login the author does not have. | No bypass; the document enters the unreachable list with "login required", after the web archive rung is tried. |
| A page behind a bot wall opens in the author's browser. | It is fetched with the author's session; the retrieval records that rung; the bytes kept are the server's response. |
| A site's crawler rules forbid automated access; the needed report's address is known and opens in the author's browser. | The report is fetched once and the site's position recorded; no program walks the site's other pages. |
| The two readers disagree on whether a candidate is in scope. | The candidate goes to the author with both answers; it adds no yield until a disposition is in force. |
| A site's certificate is invalid. | The document is fetched and the certificate error recorded with the retrieval. |
| A secretariat publishes nothing that any channel can find. | Its verdict is "not published", backed by the recorded search; it is not on the unreachable list. |
| A listed project appears in no document other than the plan that lists it. | Its verdict is "not published"; the plan's line stays the only document about it. |
| A project data sheet changes a week after the M3a fetch. | The register holds the M3a snapshot; the new version is M4's to fetch, as a new snapshot beside the old. |
| During triage, a report dated after the discovery cutoff turns up. | It stays out of the frozen register and waits for the next campaign. |
| During M3b, a held document cites a plan not held. | The plan is recorded as a document not held; the register is not reopened. |
| An IATI activity links to an appraisal report. | The report is a candidate like any other; the IATI record is a comparator record fetched for reconciliation, with no precedence. |
