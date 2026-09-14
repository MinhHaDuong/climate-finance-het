# Backend design revision 4: source management

The [design note](../jetp-backend-design.md) now specifies the source registry as
an operational input to update sweeps, alongside its role in documenting evidence.

- Section 2 adds stores for watch policies, frozen sweep plans, checks, discoveries
  and claim-specific evidence dependencies.
- Section 4 distinguishes channels from documents; preserves source identities
  through immutable metadata revisions; defines triage, watch and check fields;
  and separates publisher authority from claim-specific primary/secondary origin.
  Acquisitions pin the consulted source revision and actual URLs. Known but
  unacquired upstream citations remain distinct from archived evidence.
- Section 6 applies revision and knowledge-cutoff rules to source classifications,
  monitoring policies and origin/dependency decisions.
- Section 7 derives scheduling from policies and append-only check history.
  Frozen sweep plans account for every target, including failed and deferred
  checks. Successful no-change checks and blocked access have different effects.
- Sections 9–10 specify compatibility migration and substantive acceptance cases,
  including repeated discovery, inaccessible sources and copied reports.

The existing catalogue fields remain usable through compatibility readers;
priority allocates research effort and is not a credibility score. Origin defaults
guide discovery and triage, while evidence-link assessments determine the role
of a document for each claim. No source label automatically establishes truth,
independence, financial settlement or physical progress.

This is a design-only revision. No source data were reclassified, no watcher was
installed and no sweep was run. Verification covers document structure, links,
the JSON example and preservation of the accounting/reconciliation and future
migration sections from revision 3.
