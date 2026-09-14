# Bounded audit source evidence

Each bundle is a provisional source archive tracked with DVC. These original
bytes support evidence audits, not the adjudicated JETP ledger or website.
The corresponding audit report records URLs, retrieval dates and SHA-256 hashes.

For round 2 of 0735, use `dvc pull data/jetp/audit-evidence/0735-round2.dvc`.
The separate bundle avoids rewriting the existing `documents.dvc` from a partial
checkout (219 local objects versus257 in that tracked directory). Original
source formats and metadata are preserved. Public redistribution of complete
source payloads is not part of this audit; release terms remain a later check.

Current replication status (14 September2026): the configured padme remote
refused its SSH connection. The round2pointer is versioned, but remote pull is
not yet available. Payloads and directory metadata are preserved in the primary
local DVC cache; retry the existing push when the remote is available.
