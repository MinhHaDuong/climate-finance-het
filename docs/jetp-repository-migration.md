# JETP repository migration

The active JETP programme moved to
[MinhHaDuong/JETP-observer](https://github.com/MinhHaDuong/JETP-observer).
Its extraction baseline is source commit
`388109775f0a4bcd00aef5b7e1cd4758951688cc`; standalone bootstrap PR #1
merged there as `a74e2fef`.

The destination manifest in `docs/migration/source-cleanup-manifest.json`
records 1,295 identical source/extracted Git blob pairs. This cleanup removes
only verified JETP-owned paths. Shared ticket tooling, the general OECD finance
design ticket 0828, infrastructure tickets 1060/1700, and closed infrastructure
tickets 0810/1200 stay here. Shared Python helpers and generic LaTeX utilities
are retained. The omitted AFD pilot tests are preserved in the destination.

JETP-only Make targets, DVC stages, configuration, test-domain declarations and
snapshot provisioning are removed. Remaining corpus and literature search
terms mentioning JETP are retained because they belong to those research
programmes. Historical references in remaining tickets are not rewritten.

The legacy `gh-pages` branch and site at
https://minhhaduong.github.io/climate-finance-het/ are preserved. Deployment
and relocation of that site are separate operations.

The destination default DVC store is `/data/projets/dvc/jetp-observer` on padme.
Its 550 current objects were independently recovered into an empty cache with
the legacy remote removed (557 workspace files). Historical-only objects
remain in `/data/projets/dvc/oeconomia-climate-finance`; neither store is
garbage-collected by this cleanup.
