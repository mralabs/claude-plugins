# Fixture 03 — Expected findings

Loose must-contain / must-NOT-contain assertions.

## Must contain

### Verdict and axes

- `verdict: block` — migration will fail on existing rows (50M of them) because they lack a value for the newly-required NOT NULL column.
- `correctness_severity: critical` or `high` — this is a production-outage-class migration as written.
- `design_debt_severity: none` or `low` — the issue is correctness, not structural debt.

### Findings

- At least one finding with `finding_type: correctness`.
- At least one finding with severity `critical` or `high`.
- The finding's `scope` is `in-diff` — the migration file is added by this diff, so the problem is caused by this change. This is the canonical `in-diff` + `correctness` + `block` combination.
- The finding's `reachability` is `reachable` (schema v1.13) — the migration fires on any `alembic upgrade head` or equivalent deploy step, which is a named entry point (CI deploy hook, manual ops command). The failure is not `requires-specific-config` (no environment-specific gate), not `hypothetical` (the 50M existing rows are concrete, the `NOT NULL` constraint is concrete). The canonical `in-diff` + `correctness` + `reachable` + `block` combination.
- The finding references `migrations/0042_add_tenant_id.sql` — file path must match exactly.
- The finding body names the core failure mode: `NOT NULL` column added without a default, applied to a table with existing rows that cannot satisfy the constraint.
- The finding's `recommendation` offers at least one of the canonical safe patterns: (a) add a default value in the same migration, (b) add the column as nullable first, then backfill, then a second migration flips it to NOT NULL, (c) a multi-phase deploy that populates values via application code before the NOT NULL enforcement.
- The finding's `test_coverage.why_missed` starts with `no-test` — there is no test file that covers migrations for destructive-pattern regression.

### Trace Log

- `trace_log.domains_loaded` contains `"data"` (possibly alongside `"api"`).
- `trace_log.ship_blocker_answer: "yes"` — this is the canonical `block` pattern.
- `trace_log.ship_blocker_reasoning` names the existing-rows-cannot-satisfy-NOT-NULL issue in one sentence.
- Domain classification is unambiguous (`.sql` + `migrations/` → data.md); no `classification:` scenario line is required (schema v2.0 — dedicated notes field removed).
- `trace_log.symbols_inspected` contains the `User` type (consumers traced).
- `trace_log.findings_dropped_in_verification` is **present** (schema v1.8 unconditional requirement). Empty `[]` or populated — both acceptable depending on whether the Claim verification pass narrowed/dropped any candidate claims during the review. Absence of the field is a regression.
- `trace_log.project_rules_loaded` is **absent** (schema v2.0 conditional — no rule files set up; `rules=0` in the `context:` line proves the attempt).
- `trace_log.external_claims_verified` is **absent** (removed in schema v2.0). The NOT-NULL-on-existing-rows failure is universally-known SQL semantics and needs no `evidence_sources` entry per the evidence gate's protocol-consensus exclusion.
- `findings[].evidence_sources` is **absent or empty `[]`** on the migration finding — the claim does not depend on version-specific external behavior. A populated array is not a regression per se, but expected to be absent given the finding's grounding in cross-vendor SQL semantics.
- `trace_log.rejections_loaded` is **absent** (schema v2.0 conditional — omitted when no `rejections.json` exists).
- `findings[].previously_rejected` is **absent** on the migration finding — fresh session, no prior rejection to match. The chain-of-rejections override (rule 0) cannot fire on this fixture because the resurface count is 0.
- The `scenarios_considered` list contains the single observability line `context: prior=absent rejections=absent rules=0` (schema v2.0).

### Decision block (schema v1.11)

- Top-level `decision` is **present** on every run.
- `decision.action: iterate` — verdict is `block`, so neither `ship` (requires approve) nor `stop-and-refactor` (requires patch_chain_detected + iteration ≥ 2) applies. Author must address the migration blocker before shipping.
- `decision.patch_chain_detected: false` — fresh run, no prior.
- `decision.iteration_count: 1` — fresh session.
- `decision.rationale` is a non-empty sentence referencing the migration blocker.
- `trace_log.prior_review_summary` is **absent**.
- `findings[].prior_relation` is **absent** (no prior loaded).

## Must NOT contain

- `verdict: approve` or `verdict: needs-attention` or `verdict: refactor-recommended` — this is a correctness ship-blocker, not debt or a suggestion.
- A `design_debt` finding on the migration — the category for "migration will fail" is `correctness`, not `design_debt`.
- A low-severity finding that doesn't trip the block test.
- `patch_chain_risk.detected: true` — no defensive-prefix history exists on this file.
- Findings that recommend "add a comment explaining the migration" — this is not a documentation issue.
- Hedged language ("might fail", "potentially cause issues") — the failure is certain given the preconditions; state it as fact.

## Notes

This fixture exercises the `block` verdict path end-to-end. If it ever returns anything other than `block`, the verdict escalation logic has regressed. Common regression causes:
- Loss of `data.md` domain checklist loading.
- Shift in the "ship-blocker question" threshold that makes critical migrations somehow not ship-blocking.
- A new methodology rule that wrongly downgrades migration findings to `design_debt`.
