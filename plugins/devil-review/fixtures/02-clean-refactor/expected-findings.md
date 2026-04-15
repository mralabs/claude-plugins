# Fixture 02 — Expected findings

Loose must-contain / must-NOT-contain assertions. This fixture tests the *absence* of findings.

## Must contain

### Verdict and axes

- `verdict: approve` — no material issues, clean rename with all callers updated.
- `findings: []` — empty findings array.
- `correctness_severity: none` or field absent.
- `design_debt_severity: none` or field absent.

### Trace Log

- `trace_log.ship_blocker_answer` is either omitted (allowed for `approve`) or emits `"no"` with matching reasoning.
- `trace_log.symbols_inspected` is **non-empty** — `formatDate` (deleted), `formatDateISO` (added), and at least one consumer must be traced. Empty `symbols_inspected` on a non-trivial diff is a grounding failure even when the finding count is zero.
- `trace_log.symbols_inspected` contains at least one entry with the `(deleted)` suffix on the name — deletions count as changes per output-schema rules.
- `trace_log.classification_notes` is a non-empty sentence.
- `trace_log.domains_loaded: []` or the single matched domain, with classification_notes explaining why.
- `trace_log.mutated_records_inspected` may be empty (no record writes in a rename), with `"no record writes in diff"` recorded as a scenario line.
- `trace_log.findings_dropped_in_verification` is **present and empty** (`[]`). On a clean-refactor fixture no candidate findings exist in the first place, so the Claim verification pass has nothing to drop or narrow — but the field must still be emitted to prove the pass was run (per schema v1.8). Absence of the field is a regression signal.
- `trace_log.project_rules_loaded` is **present**. Empty array `[]` is expected (no rule files in this fixture's scratch setup), but the field itself must be emitted to prove Step 5.2b ran (per schema v1.9). Absence of the field is a regression signal.

### Patch-chain

- `trace_log.patch_chain_risk` is either absent or emits `detected: false` with `signals_fired: []`. No defensive prefix in the commit history should fire the scan.

## Must NOT contain

- Any finding. Period.
- `verdict: block`, `verdict: needs-attention`, or `verdict: refactor-recommended`.
- Low-severity cosmetic findings ("consider adding a JSDoc comment", "the new name could be shorter") — these are the padding failure mode.
- `patch_chain_risk.detected: true` — the fixture's commit history has no defensive prefixes.
- Hedged findings ("might want to consider", "potentially worth", "could possibly") — hedging is the language of a reviewer who cannot defend the finding on its merits.

## Notes

If this fixture ever returns a non-empty `findings` array, the skill has false-positive drift. Common regression causes:
- A new methodology rule that fires on stylistic grounds rather than correctness grounds.
- Loss of the "finding bar" discipline from methodology — cosmetic findings becoming acceptable.
- Domain checklists that overreach into rename scenarios.

This fixture is deliberately trivial. If it ever produces findings, the skill is broken regardless of how plausible those findings sound on their face.
