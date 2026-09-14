# Verification of ticket 0739

## Acceptance and independent original check

First red commit `969c4c50` failed both the component/date and pipeline/financing
acceptance tests under `make check-fast`; a third test rejected flattened date
pairing. Green commit `b7457964` passed all three. The final suite additionally
checks status-independent sample selection and blank unsupported historical
membership denominators (`tests/test_jetp_fcdo_pilot.py`, five named tests).

A separate read-only scientific reviewer independently parsed the original
catalogue and structured payloads and reran the first three acceptance tests
(3 passed in 0.02 s). It reproduced 25,282 distinct IDs; hierarchy counts
7,327/17,955; programme status 4/2/1 counts 6,770/551/6; component counts
13,748/4,200/7. It reconstructed all 462 ranks independently from the export,
including the selected 12. Country frame counts: AL25 MA25 IN166 SN16 ZA76
ID89 VN65. No external reviewer retrieval consumed additional units.

The reviewer checked the component original's own start 2007-02-01 against the
parent's 2007-03-09, aggregated expenditure 2007-03-31 against first observed
transfer 2010-08-11, and confirmed first spending remains unknown. It inspected
both ODT originals as ZIP/XML: completion review `3716713.odt`, content.xml
zero-based text:p index 4, corroborates 5 July 2007 programme start and March
2012 review; paragraphs 289/338 discuss procurement without a dated award
milestone. Intervention Summary `3735372.odt`, paragraph 6, supplies an amount
and support period, not a dated approval. Document-link indices 1 and 3 in the
GB-1-107859 payload give exact document linkage and 2014-04-06 publication dates.

Original SHA-256 checks:

- Completion review: `b17b81a35f04b261fbbe7734a8f2253f77e81dcbe4212aa5053619ef42d063e0`.
- Intervention Summary: `ecf8c2b4ab257c6f3429c3d1ef95f1795cb861c22cf6e3112157348aea8a644c`.

The reviewer also inspected current update/status guidance, found no historical
retention/census support, and checked table uniqueness/count sums and acquired
hashes. Its verdict was NARROW for individual programme start, DEFER for
approval/procurement transitions and historical risk sets.

Two reviewer concerns were corrected: unsupported member/pending missing counts
are now blank (with an acceptance test), and final document-coverage flags now
read explicit reviewed assessments rather than preliminary placeholders.

## Offline and repository checks

Both input bundles' DVC directory objects and every local constituent MD5 were
verified against `6cd6406b227e6860cae66906cce21d9c.dir` and
`4b1a54b98d1ff7df92afe3e7b95ec07e.dir`. Input SHA-256s and pinned Git revisions
are in input-manifest.json. The final offline command in report.md regenerated
all eight outputs byte-for-byte in a separate directory; source originals were
reused, with no network. New originals have per-file SHA-256 and DVC manifests.

`make check-fast` passed 1,719 tests, with 12 skipped before the two additional
acceptance tests (which separately passed). Initial missing-document failures
were resolved by restoring local access to the existing canonical document
archive; no fixture or canonical bytes were edited.

The `/verify-adherence` mechanical gate used the verified audit interpreter and
writable lint caches as the protocol permits. No scripts/ module or manuscript
reference changes required import/reference scanning; five matching tests passed
in 0.03 s. The adherence suite (`make lint`) passed 330 tests, 15 skipped, after
splitting the calculation into smaller functions to satisfy complexity rules.
No rules or shared architecture changed, so semantic fallback was unnecessary.
No trace file was supplied. Result: `adherence: PASS`, no mechanical failures or
semantic findings. The existing ruff adherence test covers the new calculation.

Full-suite result is recorded below after the mandatory pre-PR run completes.
