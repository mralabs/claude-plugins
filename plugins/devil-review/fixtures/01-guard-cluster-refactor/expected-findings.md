# Fixture 01 — Expected findings

Loose must-contain / must-NOT-contain assertions. Verified by a human after each run. Not a diff-match.

## Must contain

### Verdict and axes

- `verdict: refactor-recommended` — this is the whole point of the fixture. The diff is not a correctness ship-blocker (the `loading` flag does prevent the race it targets), but it adds the fourth guard to a structure that needed a refactor three rounds ago.
- `design_debt_severity: high` or `critical` — rolls up from the guard-cluster finding.
- `correctness_severity: none` or `low` — the diff itself is not a correctness bug.

### Patch-chain detection

- `trace_log.patch_chain_risk.detected: true`
- `trace_log.patch_chain_risk.signals_fired` contains at least `fix-prefix-cluster`
- `trace_log.patch_chain_risk.chain_depth` ≥ 2 (last four commits on `src/session.ts` have ≥2 defensive-prefix matches: `fix:`, `guard:`, `patch:`, `fix:`)
- `trace_log.patch_chain_risk.theme_assessment` is non-empty and names the common root cause (concurrent-restore state machine fragmented across multiple flags)
- `trace_log.patch_chain_risk.recommendation` recommends structural refactor, not another guard

### Findings

- At least one finding with `finding_type: design_debt` — the guard cluster itself is the finding.
- The design_debt finding's `scope` is `in-diff` — the fourth guard is being added by this diff, so the pattern it completes is causally introduced by this change. `pre-existing` would be wrong here; the diff is responsible for pushing the pattern over the refactor threshold.
- The design_debt finding's `reachability` is `reachable` (schema v1.13) — the fragmented state machine is reached on any `restoreSession` invocation, which is a named entry point with concrete consumers. `hypothetical` would be wrong because the reviewer can point at the four consumers of `SessionManager` whose guard checks will fire; `requires-specific-config` would be wrong because no config gates the behavior. The decision tree's step 1 (concrete call path from an entry point) resolves here.
- The design_debt finding's `recommendation` names **writer-lift** (single state machine / single-writer lock / single state enum) as the preferred consolidation, not "add another guard" or "rename the flags".
- The design_debt finding's `lift_considered` object is populated. After v1.10.1, the following must hold for the guard-on-fourth-flag framing:
  - `type_lift.viable: true` with a rationale referencing a state enum / discriminated union
  - `writer_lift.viable: true` with a rationale referencing single-writer lock / state machine consolidation
  - `ordering_lift.viable: false` with a rationale referencing that ordering does not dissolve the cluster
  Under v1.10.0 (pre-fix) schema, the guard-recommendation rule is weaker; this fixture's assertion deliberately matches the fixed (v1.10.1+) behavior.
- The finding body names the three prior guards as evidence of the patch-chain pattern.

### Trace Log

- `trace_log.symbols_inspected` contains `SessionManager.restoreSession` (or the class `SessionManager`) with consumers traced
- `trace_log.mutated_records_inspected` contains the `SessionManager` record with siblings `restoring`, `sessionRestored`, `dirty`, `loading` enumerated
- `trace_log.ship_blocker_answer: "no"` — design debt does not block ship on its own
- `trace_log.findings_dropped_in_verification` is **present** (schema v1.8 unconditional requirement). Empty array `[]` is acceptable if every candidate finding survived the Claim verification pass unchanged; a populated entry is also acceptable if a candidate claim was narrowed or dropped during the pass. Absence of the field is a regression. Reason codes permitted under schema v1.12: `unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept | unverified-external-claim` — values outside this enum are schema-invalid.
- `trace_log.project_rules_loaded` is **present and non-empty** — contains an entry with `path: ".claude/rules/no-patches.md"` and a `bytes` value matching the file's size. This fixture ships the rule file specifically to exercise citation behavior (schema v1.9).
- `trace_log.external_claims_verified` is **absent** (removed in schema v2.0 — evidence lives in `findings[].evidence_sources`). Its presence indicates the reviewer emitted against a pre-v2.0 contract.
- `findings[].evidence_sources` is **absent or empty `[]`** on the design_debt finding — the guard-cluster pattern is argued from the codebase itself (four flags in `SessionManager`, the four prior defensive commits), not from external docs or runtime observation. A populated `evidence_sources` here is acceptable only if the reviewer legitimately cited an external source (e.g., a docs URL naming a state-machine pattern); a populated array for evidence that is actually in-repo is a schema-methodology inconsistency.
- `trace_log.rejections_loaded` is **absent** (schema v2.0 conditional — the field is omitted when no `rejections.json` exists; this fixture ships none). A present-but-empty array indicates a pre-v2.0 contract; a populated array indicates fabricated rejection entries, a grounding failure.
- `findings[].previously_rejected` is **absent** on every finding — no prior rejection hashes to match against, so the re-raise path cannot fire. A populated `previously_rejected` here would be a schema-methodology inconsistency (the field is only valid when a matching rejection exists in `trace_log.rejections_loaded`).
- The `scenarios_considered` list contains the single observability line `context: prior=absent rejections=absent rules=1` (schema v2.0 — replaces the separate `prior-review ingestion:` and `rejection memory:` lines; `rules=1` because this fixture ships `.claude/rules/no-patches.md`).

### Decision block (schema v1.11)

- Top-level `decision` is **present** on every run. Required fields: `action`, `patch_chain_detected`, `iteration_count`, `rationale`.
- `decision.iteration_count: 1` — this is a fresh session with no prior snapshot, so iteration count is 1.
- `decision.patch_chain_detected: false` — per v1.11 rules, session-scoped patch-chain detection requires a loaded prior review AND ≥1 `carries-over` finding. This fixture has neither (fresh run). `trace_log.patch_chain_risk.detected: true` (git-log signal) is a separate field and does fire here; the two fields measuring different signals is by design.
- `decision.action: iterate` — `stop-and-refactor` requires `patch_chain_detected: true AND iteration_count ≥ 2`, neither of which holds on this fresh run. Verdict `refactor-recommended` + action `iterate` is a legitimate disagreement: the author is told "start the refactor now, don't iterate" but the session-level auto-stop has not triggered because no prior session reviewed this target.
- `decision.rationale` is a non-empty sentence. Typical content: references the git-log patch-chain signal and notes this is iteration 1.
- `trace_log.prior_review_summary` is **absent** (no prior loaded).
- `findings[].prior_relation` is **absent** on every finding (no prior loaded).

### Rule citation

- The design_debt finding's `rule_refs` array is **present and non-empty**, containing at least one entry with `source: ".claude/rules/no-patches.md"`.
- The cited `quote` appears **verbatim** in `.claude/rules/no-patches.md` — a string-search for the quote in the rule file must succeed (modulo leading/trailing whitespace). Acceptable quotes include lines like "Every new guard on the read side is evidence that the write side has too many entry points." or "If two or more readers need to check the same invariant, collapse to a single writer that guarantees the invariant by construction." Paraphrased or composite quotes fail this assertion.
- The `rule` identifier is a short phrase drawn from the rule file's structure — `"Enforce at the writer, not downstream"` (the `##` heading) is the canonical choice.

## Must NOT contain

- `verdict: approve` — the diff has material design debt, not zero findings
- `verdict: block` — no correctness ship-blocker is present; inflating to block would miscategorize
- `verdict: needs-attention` — this is not a "fix in place and iterate" situation; the fixture exists to verify `refactor-recommended` is reachable
- Any finding that says "rename the flags" or "add a comment explaining the flags" — these are anti-pattern recommendations
- A guard recommendation (for the current diff's `loading` flag) with `lift_considered` showing all three lifts viable — per v1.10.1 rule, this would be schema-inconsistent
- An `approve` verdict with populated `patch_chain_risk` — verdict and patch-chain state must be self-consistent

## Notes

This fixture is the primary regression target for Phase 2.5 shipping (v1.8.1 + v1.9.0 + v1.10.0) and the v1.10.1 patch that follows. If this fixture ever returns `verdict: needs-attention` on future prompt edits, the refactor-recommended path has regressed.
