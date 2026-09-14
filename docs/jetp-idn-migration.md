# Indonesian JETP candidate migration

Ticket 0766 stages an unadmitted country sidecar while the six MVP payloads and
their legacy writer remain authoritative. It creates no public IDs, payment
events, account total, or publication switch.

The candidate contains 1,579 complete plan-inventory positions: 437 rows from
the pinned CIPP PDF mirror and 1,142 rows from the official 2025 Progress
Report. The CIPP input is explicitly a Climate Policy Radar mirror; preserved
failed/unavailable official-endpoint attempts are not silently treated as an
official retrieval. The candidate also retains 62 complete approval positions
and 2,285 country-linked legacy rows with a disposition. Planning estimates,
approvals, implementation states, and portal observations remain separate
assertions; no sum across those meanings is permitted.

`data/jetp/releases/idn-migration-0766.json.dvc` points to the 15,050,778-byte
candidate (MD5 `c47c1dbda867005eeee76ee89443900e`; SHA-256
`8b5e499fdefa9aee832688fe53d623cb5c709b1f58df406b0ea53391a067a775`). The
recipe checks the selected CIPP bytes
`747283facac512780ad757313c493d1080c39705824e72c4b231e87ecb4102b5` and the
Progress Report bytes
`74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162` before
accepting their extraction. A local verified primary checkout supplied those
read-only inputs for this run; no DVC remote recovery is claimed.

The sidecar writer uses the shared replacement guard. It rejects accepted
assets and aliases, writes only a complete recognized candidate, and preserves a
prior candidate if extraction fails. Publication and financial-account
acceptance remain with tickets 0769 and 0768.
