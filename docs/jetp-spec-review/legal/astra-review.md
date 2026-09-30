**Verdict: needs corrections.** The note identifies the right legal frameworks, but it is not yet a reliable basis for declaring the project compliant. Its most consequential weaknesses concern eligibility for research TDM, database extraction, outsourced LLM processing, and website obligations.

I read the entire note and checked the principal French and EU provisions against official sources. No files were modified. This review assesses the design described in the note; it does not verify the actual software, contracts, source documents or CNRS authorisation.

**Risk ratings**

These are assessments of the arrangements described, including unresolved conditions—not numerical estimates of litigation probability.

| Activity | Note’s rating | My assessment |
|---|---|---|
| 1. Collecting and retaining copies | Low | **Medium pending institutional and security checks; potentially low afterward.** Manual login and recording terms do not establish compliance. |
| 2. Redistributing extracts | Medium | **Medium overall; potentially high for unlicensed republication of a substantial protected database.** Restricting exports to factual fields does not solve that problem. |
| 3. Personal data | Low | **Conditionally low** for limited, necessary public-role identification. **Medium while controller identity, safeguards and rights handling remain unresolved.** |
| 4. Hosted LLM processing | Low–medium | **Medium pending contracts and transfer mapping.** Disabling training alone cannot justify low risk; an established unlawful transfer would warrant high compliance concern. |
| 5. Website obligations | Medium, then low | **Medium is reasonable now.** Completing the notice alone does not resolve reply deadlines, accessibility and hosting-related privacy obligations. |
| 6. Release licensing | Low once labelled | **Medium pending ownership and licence decisions; potentially low afterward.** Labels cannot cure missing rights or an unsuitable licence. |

**Numbered corrections**

1. **Passage: “The Observer is a CNRS research activity, so art. L122-5-3 II is its primary basis.”**

   **Problem:** This assumes the decisive institutional fact.

   **Correct statement:** CNRS is a qualifying research institution, but the project must actually operate within that institution’s research activity. A researcher’s affiliation does not automatically bring every independently operated website within the exception. Record the institutional connection, scientific purposes and responsibility for the processing. DSM Article 2(1) also excludes organisations controlled by commercial undertakings enjoying preferential access to results; the French provision contains a related exclusion. Sources: [DSM Directive, Articles 2–3](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=oj%3AJOL_2019_130_R_0004), [CPI L122-5-3 II](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044363192).

2. **Passage: “The research organisations covered are defined by … R122-28 et seq.”**

   **Problem:** Wrong regulatory reference and description.

   **Correct statement:** The relevant regulations are **R122-23–R122-28**. R122-23 expressly covers institutional personnel, affiliated researchers and persons acting on an institution’s behalf and request. R122-28 concerns general-TDM reservations, not institutional eligibility. Code de la recherche L321-1 describes EPSTs generally; **R322-1 specifically identifies CNRS as an EPST**. Sources: [Decree 2022-928, Article 1](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045960058), [Code de la recherche R322-1](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000048770314).

3. **Passage: “L342-3 … paragraph numbering … to verify”; contractual unenforceability “at L122-5-3 … to verify.”**

   **Problem:** These should be resolved rather than passed to counsel as elementary citation questions.

   **Correct statement:** **L342-3, 6°** applies the TDM regime to database extractions and copies. Its following paragraph expressly nullifies clauses contrary to 1° or 6°. DSM Article 7(1) makes contractual provisions contrary to Article 3 unenforceable, but does not extend that rule to Article 4. L122-5-3 itself contains no equivalent express contractual-nullity sentence. Do not invent one; the precise domestic route for enforcing the copyright-side rule against a contractual restriction merits counsel’s analysis. Sources: [CPI L342-3](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044365654/2026-04-10), [DSM Article 7](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=oj%3AJOL_2019_130_R_0004).

4. **Passage: “Lawful access is satisfied by a registration anyone can obtain”; manual login “keeps the fetch within the terms.”**

   **Problem:** Both statements are too categorical. A manual login says nothing conclusive about subsequent automated requests, account permissions or downloading restrictions.

   **Correct statement:** Public availability or a valid subscription/registration can support lawful access. Verify the actual account entitlement and access method. A clause labelled “no automated access” may function as a prohibited restriction on research TDM; conversely, proportionate measures protecting network integrity remain permissible. Contractual breach and infringement cannot be separated categorically without analysing the particular clause and conduct. Sources: [DSM Articles 3 and 7, recital 14](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=oj%3AJOL_2019_130_R_0004), [CPI L122-5-3 II](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044363192).

5. **Passage: private DVC storage and a git-ignored directory constitute “secure storage”; retention is “exactly” justified by fingerprinting.**

   **Problem:** Neither feature establishes appropriate security or a justified retention regime.

   **Correct statement:** Document access controls, backups, device protection, remote stores, authorised users and retention purposes. R122-25 requires evidence of appropriate security and exclusively scientific retention when rightsholders request it. External storage may require the deposit agreement described in R122-24. Retaining source copies for verification is permitted, but is not permission for unrestricted permanent archiving or publication. Sources: [CPI L122-5-3 II](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044363192), [Decree 2022-928, R122-24–R122-25](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045960058).

6. **Passage: general-TDM copies may be kept “only as long as necessary”; ordinary fetching “needs no exception at all.”**

   **Problem:** The first paraphrases the directive without stating the French operational rule; the second overlooks temporary reproductions.

   **Correct statement:** L122-5-3 III requires appropriate security and destruction when mining ends. Ordinary browsing may rely on permission or the temporary-copy exception in **L122-5, 6°**; it is not legally copy-free. Persistent project copies need their own basis. L122-3 and L122-4 are correctly cited for reproduction rights. Sources: [CPI L122-5-3 III](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044363192), [CPI chapter containing L122-3–L122-5](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006069414/LEGISCTA000006161637/).

7. **Passage: robots.txt, ai.txt and natural-language terms; the AI Code “fixes what ‘machine-readable’ is coming to mean.”**

   **Problem:** It conflates practical signals, legally sufficient reservations and voluntary compliance commitments.

   **Correct statement:** **R122-28 expressly mentions website/service terms and machine-readable methods**, without prescribing a protocol. Whether a particular signal validly reserves the relevant rights depends on its wording, scope and authority. AI Act Article 53(1)(c) imposes a copyright-policy obligation on GPAI providers; the Code of Practice is voluntary and does not settle French copyright interpretation. Sources: [R122-28](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000045960687/2024-05-29), [Commission explanation of the Code](https://digital-strategy.ec.europa.eu/en/news/general-purpose-ai-code-practice-now-available), [Commission explanation of reservation protocols](https://digital-strategy.ec.europa.eu/en/consultations/commission-launches-consultation-protocols-reserving-rights-text-and-data-mining-under-ai-act-and).

8. **Passage: LAION is a “German first-instance judgment”; appeal status unverified.**

   **Problem:** Outdated.

   **Correct statement:** The Hamburg appellate court dismissed the appeal on **10 December 2025, 5 U 104/24**. Its announcement states that further appeal was permitted and the decision was not final. This remains foreign authority, not binding French precedent. I have not independently established the latest subsequent Bundesgerichtshof procedural position. Source: [Hamburg court announcement](https://justiz.hamburg.de/gerichte/oberlandesgericht/gerichtspressestelle/ki-und-urheberrecht-hanseatisches-oberlandesgericht-weist-berufung-zurueck-1126528).

9. **Passage: a label, sentence or table row “is within the exception”; “a page of prose is not.”**

   **Problem:** These are unsupported safe harbours and prohibitions.

   **Correct statement:** **L122-5, 3° a)** exists and is the correct quotation provision. There is no fixed permitted number of sentences, rows or pages. Assess brevity relative to both works, the scientific/informative or other statutory purpose, incorporation into the Observer’s contribution, clear author/source identification and the three-step test. A standalone export containing many quotations needs its own assessment. A publisher field does not necessarily identify the author. Source: [CPI L122-5](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000048603495/2026-05-13).

10. **Passage: the 13 November 2003 quotation decision and “30 June 1998, Microfor / Le Monde.”**

    **Problem:** The first authority is insufficiently identified and supports a narrower point; the second is misidentified.

    **Correct statement:** **Cass. 1re civ., 13 November 2003, 01-14.385** concerns complete reproductions of Utrillo paintings, not a general row-or-sentence threshold. The leading Microfor judgment is **Cass. ass. plén., 30 October 1987, 86-11.918**, concerning a documentary index and short extracts. Facts themselves are not copyright expression, but accompanying wording or selection may be protected. Sources: [Utrillo judgment](https://www.legifrance.gouv.fr/juri/id/JURITEXT000007048573/), [Microfor judgment](https://www.legifrance.gouv.fr/juri/id/JURITEXT000007019548/).

11. **Passage: serving facts in the Observer’s own arrangement keeps an EU publisher’s table lawful; cap exports to labels, amounts and dates.**

    **Problem:** This is the note’s most serious IP error.

    **Correct statement:** Database rights can protect collections of **unprotected facts**. Reordering or selecting only factual columns does not defeat those rights. Quantitative substantiality concerns the amount taken relative to the protected database; qualitative substantiality concerns the relevant investment. Repeated systematic small extractions may also infringe under L342-2. TDM permission does not authorise public republication of the mined database. Obtain a suitable licence or establish a genuinely applicable exception/non-protection analysis. Sources: [CPI L342-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006279247/2026-08-13), [CJEU C-203/02, British Horseracing Board](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=celex%3A62002CJ0203), [French government explanation of L342-2](https://formations-geomatiques.developpement-durable.gouv.fr/NAT009/ADL/Aspects_Juridique/co/10d2_Le_droit_du_producteur.html).

12. **Passage: an EU-established publisher “does” have database protection; “Fifteen years from completion.”**

    **Problem:** Establishment alone is insufficient, and the duration rule is incomplete.

    **Correct statement:** L341-1 requires a producer bearing the initiative and investment risk and substantial investment in obtaining, verifying or presenting contents. Investment in **creating the data itself** does not suffice. A qualifying database is not automatically every table in a report. L342-5 calculates expiry from the following 1 January and contains additional rules for first public availability and new substantial investment. Sources: [L341-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006279245/2026-04-27), [British Horseracing Board](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=celex%3A62002CJ0203), [L342-5](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006279256/2026-04-08).

13. **Passage: only EU/EEA-established producers qualify; all four governments therefore lack protection.**

    **Problem:** This is an over-simple geographical test.

    **Correct statement:** L341-2 distinguishes nationality/residence and company formation plus establishment, and permits protection under specified international agreements. Identify the actual producer, possible co-producers and rights chain—not merely the report’s issuing ministry. International organisations require specific analysis; an OECD address in Paris does not settle the statutory test either. The note’s conclusion may hold for a particular database, but has not been established collectively. Source: [CPI L341-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006279246).

14. **Passage: CRPA L321-1 et seq.; L321-2 and L321-3 presented principally as third-party-rights reservations.**

    **Problem:** It misses an important restriction on administrations’ own database rights.

    **Correct statement:** L321-1 is correctly cited for reuse of public information. L321-2 excludes relevant third-party IP. **L321-3 also prevents specified administrations from using database rights to block reuse of databases published under L312-1-1, 3°**, subject to its exceptions. It cannot be reduced to a third-party-rights caveat. L322-1 additionally requires the source and **last-update date**, and prohibits alteration/distortion absent administrative agreement. Sources: [L321-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033219044/2024-01-01), [L321-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033218992/2026-05-11), [L321-3](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033205561), [L322-1](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000032255220/2026-05-28).

15. **Passage: L533-4 II makes publicly funded research data freely reusable “once published.”**

    **Problem:** Material conditions are omitted.

    **Correct statement:** The research must be financed **at least half** by the listed public funding sources; the data must not be protected by a specific right or particular regulation; and they must have been made public by the researcher, institution or research organisation. This does not remove third-party copyright, database rights or GDPR obligations. Administrative-document status also does not establish ownership of every incorporated contribution. Source: [Code de la recherche L533-4 II](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033205794).

16. **Passage: “Three of the four countries” exclude official texts; a plan is necessarily a protected report.**

    **Problem:** Senegal is unresolved despite having an express provision; the classification of plans is too categorical.

    **Correct statement:** Senegal’s **Law 2008-09, Article 9** excludes official legislative, administrative and judicial texts and official translations. The cited South African section 12(8)(a), Indonesian Article 42 and Vietnamese Article 15 also exist, though their wording differs. Berne Articles 2(4) and 5(2) are relevant, but a plan’s status must be assessed document by document, especially where annexed to a binding act. Other passages require originality to attract copyright. Sources: [Senegal](https://www.wipo.int/wipolex/en/text/498404), [South Africa](https://www.wipo.int/wipolex/en/text/474815), [Indonesia](https://www.wipo.int/wipolex/fr/text/578067), [Vietnam—WIPO judicial guide](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-1081-3-en-intellectual-property-adjudication-in-viet-nam.pdf), [Berne Convention](https://www.wipo.int/wipolex/en/text/283698%3B).

    I would not certify the four investment plans’ legal status without examining their publication instruments and annexes.

17. **Passage: OECD and World Bank licence summaries; “ODbL … cannot be relicensed CC BY.”**

    **Problem:** Organisation-wide summaries are insufficient.

    **Correct statement:** OECD distinguishes written content published before and from **1 July 2024**, and has separate data provisions and exceptions. World Bank CC BY 4.0 is a default for specified Bank-produced open datasets, with additional terms; it is not a licence for everything on its website. IATI’s publisher-specific approach is correctly described. ODbL obligations depend on whether the output is a derivative database, collective database or produced work; separate original contributions can still have their own licence. Sources: [OECD terms](https://www.oecd.org/en/about/terms-conditions.html), [World Bank data licensing](https://datacatalog.worldbank.org/public-licenses), [IATI licensing guidance](https://reference.iatistandard.org/en/guidance/publishing-data/what-data-to-publish/how-to-license-your-data/), [ODbL text](https://opendatacommons.org/licenses/odbl/1-0/).

18. **Passage: GDPR Article 6(1)(e) is the basis because the author is a CNRS researcher.**

    **Problem:** Plausible, but the controller and necessity analysis are missing.

    **Correct statement:** Article 6(1)(e), read with 6(3), is a suitable candidate for necessary processing within CNRS’s legally grounded research mission. Identify whether CNRS, another CIRED institution, joint controllers or the researcher determines purposes and means. Article 89 supplies safeguards, **not an independent legal basis**. Public availability and official capacity do not remove GDPR protection. Sources: [GDPR Articles 5–6](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre2), [Article 89](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre9), [CNIL research legal-basis guidance](https://www.cnil.fr/recherche-scientifique-hors-sante/base-legale).

19. **Passage: Article 14 information duties are “lifted … with a public notice instead”; erasure may be refused; LIL Article 78 unverified.**

    **Problem:** The exceptions are presented as almost automatic.

    **Correct statement:** Document why individual information is impossible or disproportionate; a public notice alone does not establish Article 14(5)(b). Article 17(3)(d) requires necessity and likely impossibility or serious impairment of research, with safeguards. **LIL Article 78 is the correct number**, but distinguish its archives paragraph from research derogations implemented by **Decree 2019-536, Article 116**. Article 79 is also relevant to indirect collection. Sources: [GDPR Articles 14 and 17](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre3), [LIL Articles 78–79](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000886460/2026-05-23), [Decree Article 116](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000038568052/2022-04-11).

20. **Passage: GDPR Article 85 and LIL Article 80 “cover” the published statements.**

    **Problem:** This suggests a blanket academic exemption.

    **Correct statement:** Article 80 does expressly include academic expression. Its listed derogations apply only where necessary to reconcile expression and information with data protection. Assess the particular publication and derogation; do not extend that conclusion automatically to collection, provider outsourcing or unrelated processing. Sources: [LIL Article 80](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000886460/2026-05-23), [GDPR Article 85](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre9).

21. **Passage: “A DPIA … is not required”; excluding contact details from extraction establishes minimisation.**

    **Problem:** Article 35’s examples are not exhaustive, and full documents have already been processed before extraction.

    **Correct statement:** A DPIA probably is unnecessary for the narrowly described activity, but document screening against the general likely-high-risk test and applicable CNIL criteria. Inspect full inputs, signatures, annexes and prompts—not just output tables. Where feasible, remove unnecessary personal information **before** hosted calls. A name attached to an author or signatory is not automatically necessary. Sources: [GDPR Articles 25, 32 and 35](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre4), [CNIL research guidance](https://www.cnil.fr/fr/recherche-scientifique-hors-sante-les-questions-reponses-de-la-cnil).

22. **Passage: the LLM provider is the Observer’s processor; its retention is governed by its terms.**

    **Problem:** Neither GDPR processor status nor lawful outsourced TDM follows merely from using a service contract.

    **Correct statement:** Determine the provider’s actual purposes and instructions. An Article 28 processing agreement is required where it acts as processor. Separately, **R122-23 II** requires an agreement addressing access, security and return/deletion for outsourced research-TDM copies. Provider terms must satisfy these requirements; they cannot replace them. Provider training or other independent reuse needs a separate rights analysis, including the law applicable where copies occur. Sources: [GDPR Article 28](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre4), [R122-23 II, introduced by Decree 2022-928](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045960058).

23. **Passage: “Every document … is public … the harm of a leak is nil”; “public documents carry no confidentiality obligation.”**

    **Problem:** Both absolutes are wrong.

    **Correct statement:** Public availability may reduce confidentiality concerns, but does not eliminate privacy, contextual misuse, erroneous attribution, contractual or rights risks. Accidentally exposed documents may remain protected. Sending entire documents can disclose more personal data than the intended public output. Further processing still requires purpose, necessity and security assessments. Source: [GDPR principles, particularly Article 5](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre2).

24. **Passage: record “DPF certification or SCC” once per provider; prefer EU hosting or zero retention.**

    **Problem:** Incomplete transfer assessment and insufficient routing controls.

    **Correct statement:** Map OpenRouter, actual model endpoints, subprocessors, logging, support access and onward transfers. DPF coverage must match the recipient legal entity and relevant processing. Otherwise, appropriate SCCs require a transfer-impact assessment and any necessary supplementary measures. Zero retention does not eliminate a transfer; EU server location alone does not settle all access questions. Review changes rather than recording the basis once indefinitely. Sources: [GDPR Chapter V](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre5), [CNIL transfer-impact guidance](https://www.cnil.fr/fr/analyse-dimpact-des-transferts-des-donnees-la-cnil-publie-la-version-finale-de-son-guide-aitd).

    The cited Decisions **2023/1795** and **2021/914** are correctly numbered. The Latombe appeal is **C-703/25 P**, lodged on 31 October 2025 and shown as pending in the court’s register. Source: [Court register](https://infocuria.curia.europa.eu/tabs/redirect/juris/liste.jsf?num=C-703%2F25+P).

25. **Passage: OpenRouter privacy settings adequately address hosted-provider risk.**

    **Problem:** Settings are useful technical controls, not a complete contractual solution.

    **Correct statement:** Current documentation provides `data_collection: "deny"` and `zdr: true`; dedicated EU routing has its own availability conditions. Enforce approved endpoints and fail closed when none qualifies. Review OpenRouter’s own terms as well as endpoint policies: its terms include input-categorisation and associated licensing provisions beyond model training. I have not verified an executed CNRS agreement or certification covering the proposed account. Sources: [OpenRouter routing documentation](https://openrouter.ai/docs/guides/get-started/sovereign-ai), [OpenRouter terms](https://openrouter.ai/terms/).

26. **Passage: LCEN Articles 6-III, 6-IV and 6-VI-2.**

    **Problem:** Obsolete numbering after the SREN reorganisation.

    **Correct statement:** The publisher notice is now **Article 1-1 I–II**, online right of reply **Article 1-1 III**, and the missing-notice offence **Article 1-2**. The stated maximum of one year’s imprisonment and €75,000 remains correct for the specified natural person/responsible officer; “rarely applied” needs evidence and is not a compliance argument. The former Article 6-I-5 host-notification citation must also be updated to the current hosting/DSA framework. Source: [Current LCEN text](https://www.legifrance.gouv.fr/codes/id/LEGISCTA000006089778).

27. **Passage: the notice fields and appointment of the laboratory director or researcher as publication director.**

    **Problem:** Missing fields and an unsupported assumption about the responsible person.

    **Correct statement:** Article 1-1 requires, as applicable: publisher identity, address and telephone; relevant registration and company capital; publication director and any editorial manager; host identity, address and telephone; and identity/address of relevant additional data-storage providers under **I, 5°**. Company registration/capital requirements do not apply indiscriminately to CNRS. Under **Law 82-652, Article 93-2**, the publication director follows the legal publisher’s status; this is not simply an editorial appointment. Sources: [LCEN Article 1-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049568614), [Article 93-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000033971722/2026-04-30).

28. **Passage: organisations being named means little right-of-reply exposure; acknowledge within five working days and decide within a month.**

    **Problem:** Legal persons can have reply rights. The proposed timing misses the statutory deadline.

    **Correct statement:** A qualifying online reply must be inserted **within three days of receipt**; the request ordinarily must be made within three months of publication. Distinguish replies, GDPR requests, ordinary corrections and urgent illegality complaints. Being the editor rather than a hosting intermediary does not remove direct liability for published content; subsequent removal does not automatically cure it. Source: [LCEN Article 1-1 III](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049568614).

29. **Passage: “The Observer keeps nothing about visitors”; accessibility requires a statement.**

    **Problem:** Both descriptions are incomplete.

    **Correct statement:** GitHub expressly logs Pages visitors’ IP addresses. Describe the real processing and respective responsibilities, including relevant transfers. LIL Article 82 is correctly cited for trackers, but verify actual browser behaviour. Accessibility obligations under Article 47 and Decree 2019-768 extend beyond a statement to accessibility itself, conformity information, feedback arrangements and links to the relevant multiannual scheme and annual plan. Sources: [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started/with-github-pages/what-is-github-pages), [official RGAA obligations](https://accessibilite.numerique.gouv.fr/obligations/schema-pluriannuel/).

30. **Passage: “CRPA L323-1 … list[s] the licences”; another licence needs “homologation by decree.”**

    **Problem:** Wrong provision and approval mechanism.

    **Correct statement:** **L323-1** permits licensing and requires it for fee-based reuse. The approved-list rule is **L323-2**; **D323-2-1** lists Licence Ouverte and ODbL for non-software information. **D323-2-2** provides a request procedure and approval by Prime Ministerial decision for the specified information—not individual homologation by decree. Licence Ouverte 2.0’s compatibility with CC BY does not make the licences identical or automatically authorise an administration to choose CC BY initially. Sources: [CRPA licensing chapter](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000031366350/LEGISCTA000032255228/), [Licence Ouverte 2.0](https://www.etalab.gouv.fr/wp-content/uploads/2017/04/ETALAB-Licence-Ouverte-v2.0.pdf).

31. **Passage: “low once labelled”; all third-party factual material “remain[s] under those terms.”**

    **Problem:** Ownership, licence scope and legal exceptions are conflated.

    **Correct statement:** CC BY 4.0 sections 1, 2, 3 and 4 are correctly identified. It licenses only relevant rights the licensor can grant; it does not manufacture rights over bare facts or require compliance where an exception independently applies. Third-party exclusions are good practice, but attribution does not validate unlawful reproduction. Check ownership separately: researchers can retain copyright under the public-agent exception in **L111-1**, while database-producer rights may belong elsewhere. Sources: [CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode.en), [CPI L111-1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000042814694/2026-05-28).

**Additional missing points**

- **A separate legal basis for each operation:** acquiring a copy, mining it, retaining it, sending it abroad, publishing extracts and licensing outputs are distinct acts. Permission for one does not establish permission for all.
- **A representative export review:** inspect actual CSV/JSON downloads, document-row pages and cumulative releases. Assess the material a user can reconstruct across them, not just each displayed row.
- **A complete privacy notice:** controller and DPO contacts, purposes, legal basis, categories and sources, recipients, transfers, retention, applicable rights and CNIL complaint route. Sources: [GDPR Articles 13–14](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre3).
- **Sensitive-data screening:** public reports can contain political opinions, union membership or allegations about individuals. “Public document” is not a general Article 9 or 10 exemption. Source: [CNIL guidance on sensitive data in public research](https://www.cnil.fr/fr/traitements-de-donnees-des-fins-de-recherche-scientifique-hors-sante-quand-saisir-la-cnil).
- **Rights and incident procedures:** assign responsibility for access/objection/erasure requests, prompt deletion, provider changes and security incidents, including copies already deposited or mirrored.
- **Human editorial responsibility:** at the review date, assess AI Act Article 50(4) if AI-generated public-interest text is published. Its human-review/editorial-control exception should be considered explicitly. Source: [AI Act](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=OJ%3AL_202401689).
- **Verification of implementation claims:** the note’s assertion that “this commit adds” a legal page is not legal evidence that the page exists, its placeholders are filled or its information is correct.

**Questions for the CNRS legal service and DPO**

1. Is JETP Observer formally conducted within CNRS’s research mission, and which institution assumes responsibility given CIRED’s institutional structure?
2. Who is the legal publisher, publication director, GDPR controller and database producer? Who may execute provider contracts and grant release licences?
3. Does the proposed activity and outsourcing arrangement satisfy L122-5-3 II and R122-23, including institutional control and any commercial-partner conditions?
4. Are the researcher’s machines, DVC storage, backups and external services acceptable for TDM retention and CNRS security requirements?
5. Which access restrictions require specific negotiation, and how should the project handle clauses purporting to prohibit all automated access?
6. Which source tables are protected databases, who produced them, and which planned complete or cumulative exports need permission?
7. Which outputs fall under the CRPA licensing regime, which remain researcher-owned works, and should the dataset use Licence Ouverte 2.0?
8. Are OpenRouter and each permitted endpoint contractually approved, with appropriate processing agreements, transfer mechanisms and enforceable retention restrictions?
9. What documented Article 14 exemption, retention schedule, rights derogations and DPIA screening does the DPO accept?
10. Which institutional accessibility scheme and publication-response procedure cover this site?

The principal unresolved legal judgments are the project’s institutional status, individual source/database protection, the treatment of particular access restrictions, foreign-server copying and the actual provider contracts. Those cannot be settled from this note alone.