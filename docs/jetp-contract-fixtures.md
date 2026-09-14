# Candidate JETP contracts (0762)

`jetp._contracts.read_contract(document, supported_versions={'jetp-core-v1'})`
validates an in-memory JSON-compatible document containing `schema_version` and
`records`. Every record has `record_kind`, `record_id`, immutable `recorded_at`
(with timezone), and `recorded_by`. `REQUIRED` in the module declares the supported
kinds and their fields. References are exact objects with `record_kind` and
`record_id`; financial and implementation IDs occupy separate namespaces.
`store.to_dict()` returns an independent lossless copy suitable for JSON encoding.
Decimals are strings in whole currency units; original values, scales, labels,
uncertainty bounds and date roles remain separate fields.

`store.at(evidence_cutoff, policy_version=...)` projects admitted dependencies and
review decisions under an explicit policy version. Both review and recording time
must precede the cutoff. Pending decisions do not erase operative decisions;
accepted immutable replacements supersede their ancestors. Ambiguous accepted
forks, review conflicts and occurrence assignments raise `ContractError`.
`accepted(reference)` reports review state, not metric eligibility: an explicit
evidence/coverage gap remains a gap. No account engine or coverage certification
is implemented; `closing_status()` always returns unavailable closing and residual.
The financial reconciliation work remains ticket 0768.

`view.relations_at(world_date)` applies half-open world-validity intervals after
knowledge selection and validates active cycles/cardinality. `open` is an explicit
unbounded relation endpoint; `unknown` blocks resolution. Aliases cannot chain.
`view.frozen_frame(frame_reference)` uses the frame's own evidence cutoff and
frozen protocol; later membership decisions cannot rewrite it. A completed-only
population is not a reconstructed historical frame. Failed observation attempts
remain distinct from a `not_sought` coverage assessment.

The schema is a fixture/candidate boundary, not a new canonical store. It supports
only the core kinds exercised here, including small evidence-acquisition and
study/frame/coverage records. Source revision/watch/sweep ingestion, complete
metric dictionaries, accounting and publication ownership remain the subsequent
tickets' work. It creates no empty registries and performs no writes. Saved-byte
hashes and extraction locators are validated against supplied manifests, not by
retrieving documents; full material acquisition/crosswalks belong to 0763.

The independent `jetp._compatibility.read_mvp_view(root, view,
supported_versions={'mvp/1'})` negotiates the legacy public contract without
injecting fields into its payload. It reads the existing CSV authority and returns
one of `overview`, `comparison`, `ZAF`, `IDN`, `VNM` or `SEN`. No renderer or
publication path changes. Candidate-core records are not an alternative writer.

## Acceptance fixtures

- `test_typed_collision_late_duplicate_and_pending_replacement`: the first
  discriminating fixture; equal raw IDs, September occurrence review and an
  unaccepted correction preserve August's accepted state.
- `test_late_acceptance_withdrawal_and_review_admission_are_distinct`,
  `test_late_alias_replacement_preserves_earlier_canonical_target`, and
  `test_transitive_replacement_does_not_resurrect_accepted_ancestor`: immutable
  decision/assertion history on both query axes.
- `test_active_containment_and_alias_cycles_rejected`,
  `test_multiple_active_parent_or_alias_targets_rejected`,
  `test_supersession_cycle_and_active_fork_rejected`: invalid structural fixtures.
- `test_evidence_tuple_round_trips_matching_bytes_edition_extraction_and_locator`
  and the corruption/late-dependency cases in `test_jetp_evidence_contracts.py`:
  exact byte, edition, acquisition, locator and typed-target agreement.
- `test_money_scale_and_date_roles_round_trip_without_float_conversion`,
  `test_money_normalization_cannot_disagree_with_original_scale` and
  `test_exact_coverage_is_an_interval_and_typed_event_roles_remain_separate`:
  USD 3.92 billion, rounding bounds and independent temporal roles.
- `test_frozen_frame_retains_active_and_cancelled_units_despite_later_exclusion`:
  retain the two historical units while rejecting a completed-only population.
- `test_unsupported_closing_and_residual_remain_unavailable`: no undocumented
  exact account is inferred from these foundational fixtures.
- `test_all_mvp_views_match_authoritative_builder_and_frozen_baseline` (six views): legacy
  builder equality and frozen 0761 output equivalence. Only the overview's two
  checkout revision fields are excluded from the frozen-byte comparison.

The immutable reference is `data/jetp/releases/mvp-baseline-0761.zip`, SHA-256
`dbdc45b8f6d5dccce1c378b15a3d92a766f87ad26231751fca7ebf963716f574`.
Input base: `040ca89615ded1b20c0aeeda62a56e34152cfe6d`.
The PR records the output implementation commit and local gate results.
