# Raw pool storage and overlap validation (Zenodo package README, ed04 kit)

Displaced from data-paper.qmd §2.1 by cut-plan v2 condensation #6
(ticket-ref 0274). Destination: the Zenodo package README.

Raw API responses are stored in an append-only pool as compressed JSONL
files, preserving complete responses for future re-extraction without
re-downloading. The bibCNRS aggregates are Gale, Wanfang, and NewsBank.
The inclusion of the two hand-harvested sources is validated by multi-source
overlap: 62% of SciSpace records and 9% of bibCNRS records also appear in
automated sources, confirming retrieval consistency.
