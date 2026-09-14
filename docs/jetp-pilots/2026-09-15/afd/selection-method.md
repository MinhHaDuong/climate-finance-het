# Prospective selection and acquisition freeze

Country mapping is published in country-label-mapping.json. Frame: all 224 legacy
financing IDs in those exact seven labels. Exclude every mandatory challenge ID.
Use the exact-ID matched XML DAC vocabulary 1 codes and raw default-finance-type
code for stratification; preserve legacy sector labels and product labels in units.
This uses current classification metadata, not current outcome/date eligibility;
source disagreement is retained. A missing XML join is mixed-or-unmapped/missing.
Order country, sector class, raw instrument code lexically, then financing ID;
cycle one per stratum per round. selection.csv includes all 210 candidates and
all challenge identities, ranks and selected flags. No replacement after failure.

Allocation amendment BEFORE retrieval: route 1 has eight named requests; transfer
its four unused units to originals (16 instead of 12). Reserve six units unchanged
for verification or discriminating follow-up; no broad discovery. The last two
sample cases remain not attempted if no suitable reserve follow-up is justified.
Each HTTP request including redirects/failures consumes a unit. Disable automatic
redirects. Archive every response body, including HTTP error/redirect bodies.
Stop each named route at response/failure; do not retry broad financing searches.

Original acceptance requires explicit exact financing ID plus dated instrument or
decision meaning. A project-parent fiche, related component, shared title or budget
cannot establish the financing event. Inspect contrary identity evidence separately.
No external request has occurred before this freeze (GitHub startup checks are
repository administration, not evidence acquisition).
