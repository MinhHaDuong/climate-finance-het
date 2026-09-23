# Response to Astra round 1

All five findings accepted and applied in commit `9bbcbe45` to `docs/jetp-ontology.md`.

| Finding | Disposition | Where |
|---|---|---|
| P1-a retrieval vs content identity | Accepted. `manifest.csv` becomes `retrievals` (314, nullable fingerprint) and `snapshots` (264). Vocabulary gains Retrieval; relations gain `retrieval_of` and `yields`. Migration row states the 41 failed retrievals and the 9 shared fingerprints. | §2, §3, §5, §6 |
| P1-b supersession semantics | Accepted. A decision is in force only as the terminal row of a linear chain with status `accepted`; a terminal `rejected` row revokes with no replacement; `candidate` is pending. Applies to document `same_as` too. | §5 rules, §11 |
| P2-a party role | Accepted. `relations` gains a `role` column; `party_in` is one row per role. | §3, §5 |
| P2-b timing | Accepted. Observations carry no date; a `timings` table holds one row per date role with precision and bounds. `event-timing.csv` (451) migrates to it. | §2, §3, §5, §6 |
| P2-c line membership | Accepted. `member_of` accepts a line as subject; the 230 unmatched RUPTL lines keep their membership without an identity. | §3, §6 |
