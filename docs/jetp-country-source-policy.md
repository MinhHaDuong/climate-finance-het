# Country-box source policy

Author decision, 14 September 2026: the country-box source link should open the
latest official state-of-JETP report issued by the local Secretariat (or its
institutional successor). Prefer a comprehensive implementation/progress report.
Keep the headline and its date faithful to that source. A newer news article or
newsletter does not silently supersede a comprehensive report; show it separately
as an interim update. If no such report is located, identify the fallback type,
issuer, reporting period and any mirror explicitly.

## Selection at 14 September 2026

| Country | Country-box source | Qualification / next check |
|---|---|---|
| South Africa | Q1 2026 JET PMU progress report | Official indexes checked; replace with Q2 when published and reviewed |
| Indonesia | 2025 JETP Secretariat Progress Report | Latest comprehensive report located; JDU newsletter of 8 September 2026 is a newer interim update |
| Viet Nam | MOIT Secretariat newsletter 13, March 2026 | Official local fallback; comprehensive progress report not located |
| Senegal | Ministry investment plan via Vie-Publique mirror | Plan fallback, not a progress report; prefer Secretariat report/direct hosting when located |

## Discovery and verification

Bounded check: ten web calls maximum; six used for Indonesia, Viet Nam and
Senegal in this turn. The obsolete Indonesian domain and guessed report routes
failed; they do not establish absence. The current official homepage and report
landing page confirm the 2025 report and a newer newsletter. The Vietnamese
homepage lists newsletter 13 as its latest issue; its contents were independently
checked against the already archived PDF. Direct page/PDF routes failed through
the browsing tool, so no claim of successful live PDF retrieval is made. The
Senegal candidate domain failed; retain the accepted plan fallback without claiming
an exhaustive new Senegal search. South Africa's Q2 check is recorded separately
in `jetp-zaf-q1-baseline-2026-09-14.md`.

- Indonesia report index: https://jetp.id/news/jetp-reports-2025
- Indonesia official homepage: https://jetp.id/
- Newer interim update: https://jetp.id/news/jdu-newsletter-first-edition
  (8 September 2026; reports USD 3.92bn approved, not payments).
- Viet Nam official homepage: https://jetp.moit.gov.vn/
- Newsletter archive: source `vnm-moit-newsletter-13-2026-03`, SHA-256
  `fa7d149b3d8165b85b7090584a3df3d35fbd6b097bb8a08844df330a3410fc39`.

At each observatory refresh, recheck official report indexes, archive and review
new editions, then update country metadata and rebuild the static exports. Keep
older editions and claims. This rule does not create a scheduled monitoring job.
