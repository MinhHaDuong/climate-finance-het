# Senegal plan-position migration candidate

Ticket 0767 stages Senegal's two preserved plan inventories beside the legacy
MVP. It creates no admitted entity, payment, account total, public route, or
writer transfer. `data/jetp/releases/sen-migration-0767.json.dvc` points to the
3,405,806-byte unadmitted `country-migration/1` sidecar, DVC MD5
`060c15dcdfb6971c47564f78577e0e08` and SHA-256
`b9b13538809f8e95fe098a2af4fe62b99c36cb1648e361e801bf2849a55ba8bc`.

## Selected inventories and source limits

The selected sources are preserved public mirrors, not a claim that their
retrieval was from the official host:

| Inventory | Saved acquisition | SHA-256 | Rows |
|---|---|---|---:|
| Annex 2 received projects | 2026-09-12 08:27 UTC | `dcd4fd924f9e637d36beb192f509b7971b8b5dda0a76e3c17b799ba26ff43b21` | 38 |
| Main-plan Quick Wins | 2026-09-11 20:42 UTC | `97c36b242257462f024a934baee6bed3aa02fe0e4917f076d7b865701db65dca` | 11 |

The primary plan-host failures remain in the retained manifest. The candidate
uses the committed, source-pinned inventory transcription and records its
recipe hash and row locators; saved PDF bytes remain the source of record.
Annex 2 means submissions received for evaluation. Quick Win means a plan
priority. Neither label establishes finance, selection, implementation, payment,
or a one-to-one project identity.

## Candidate differences and writer-transfer report

The sidecar has 49 inventory positions: 38 received-project positions and 11
Quick-Win positions. Each legacy plan-table link becomes one of 49 explicitly
**provisional** links. It is neither an accepted identity join nor a component,
funding, or implementation assertion. Programme envelopes, component needs,
prospective allocations, and plan estimates retain their source fields and are
not added, netted, or promoted to an account total.

All **829** Senegal-linked legacy rows receive a retained-authority disposition:
178 project-source links, 125 manifest records, 116 source records, 90 dry
searches, 49 plan rows, 49 source claims, 46 implementation rows, 43 project
coverage rows, 43 projects, 39 event-timing rows, 39 financial events, and 12
authority-coverage rows. The 361 legacy evidence and 361 unresolved projections
remain explicit. Missing dates remain missing; no date is promoted to a
transition date.

The six MVP compatibility views are copied from the legacy reader and compared
against it during candidate construction. Public project IDs, financial event
additions, website semantics, and ownership changes are all zero.

**Transfer decision: none.** Existing CSVs and the existing legacy writer stay
authoritative. The sidecar is a reviewable candidate for later reconciliation
(0768) and controlled publication (0769), not a publication or account input.

## Recovery and safety

The DVC object was pushed to the configured local project archive and recovered
in an independent `/tmp` destination with identical SHA-256 bytes. The writer
uses the shared replacement guard: it rejects accepted files and direct,
symlinked, or hardlinked aliases before building; it only replaces a complete
recognized Senegal candidate atomically. Candidate output is too large for Git
and remains DVC-managed.

Focused tests include `test_programme_components_and_provisional_match_cannot_create_finance_total`,
`test_real_candidate_covers_pinned_inventories_and_keeps_mvp_legacy_owned`, and
`test_writer_rejects_accepted_route_or_alias_before_build`.
