# devil-review fixtures — regression harness

Manual snapshot discipline. No CI gate, no automated runner.

## Purpose

The skill is a prompt. A prompt change is a software change with no compiler, no type system, and no test suite. This directory exists so prompt regressions are visible before they reach a real PR.

Each fixture is a scenario the skill should handle in a specific, known-good way. When a methodology or schema rule changes, the reviewer re-runs the fixtures and compares the output to the last known-good snapshot. The point is *not* to measure model quality — it is to catch the obvious regression where a prompt edit silently breaks a case that used to work.

## Layout

Each fixture is a self-contained directory with four files:

| File | Purpose |
|---|---|
| `diff.patch` | Synthetic or real-anonymized unified diff that the skill will review. Hand-authored to be minimal and focused. |
| `context.md` | Repo context the skill needs but that is not part of the diff — framework, recent commit history, architectural notes. Read by the human who sets up the scratch checkout, not the skill directly. |
| `expected-findings.md` | Loose must-contain assertions. Human-readable, verified by a human after each run. Not a diff-match. |
| `last-snapshot.md` | The last known-good full skill output (markdown + JSON fence) for this fixture. Tracked in git. Missing on initial fixture creation until the first real run captures output. |

## Running a fixture manually

1. `cd plugins/devil-review/fixtures/<fixture-name>/`
2. Set up a scratch git checkout that reproduces the fixture scenario:
   - Apply `diff.patch` to the scratch repo (or stage it as a working-tree change).
   - Ensure the files named in `context.md` exist with the content described (inline any commit history that the fixture depends on).
3. Invoke `/devil-review` from inside the scratch checkout. Capture the entire markdown + JSON output.
4. Write the output to a local file. Diff it against `last-snapshot.md`:
   ```
   diff <captured-output> last-snapshot.md
   ```
5. Verify the captured output satisfies every assertion in `expected-findings.md`. Human reads the bullets and checks each against the new output.
6. Classify the diff outcome:
   - **No diff, all assertions pass** → the prompt edit did not regress this fixture.
   - **Diff present, but all assertions still pass** → the phrasing changed but the substance held. Update `last-snapshot.md` to the new output and commit ("expected snapshot update").
   - **Diff present AND some assertion now fails** → real regression. Fix the prompt, re-run, snapshot.
   - **No diff, but an assertion now fails** → the fixture's expected behavior changed deliberately. Update `expected-findings.md` first, then re-run and snapshot.

## When to run fixtures

**Trigger:** a commit edits any of the following files. Run the affected fixtures before the commit lands (or at minimum before the containing shipping series is pushed).

- `plugins/devil-review/skills/devil-review/SKILL.md`
- `plugins/devil-review/skills/devil-review/methodology.md`
- `plugins/devil-review/skills/devil-review/output-schema.md`
- `plugins/devil-review/skills/devil-review/domains/*.md`

**Do NOT run for:** manifest-only edits (`plugin.json`, `marketplace.json`), README changes, plan-doc edits under `docs/`, or changes to the fixtures themselves. These do not touch the prompt surface and cannot regress skill behavior.

**Narrow edits:** when the edit is narrow (e.g., a single-domain change in `domains/api.md`), you may run only the fixtures exercising that surface. When in doubt, run all three — the manual cost is ~5 minutes each and the saving of a missed regression is much higher.

**First-run capture:** if `last-snapshot.md` is absent for a fixture you are running, capture the plugin's full output into that file on the first successful run and commit it alongside the triggering edit. Subsequent runs diff against the snapshot.

**Failure handling:** if a fixture fails assertions, do not update `last-snapshot.md`. Either fix the skill (intentional regression exposed) or fix the fixture (expected behavior genuinely shifted). The snapshot is only updated after a clean pass, never to paper over a failure.

## Fixture catalog

- `01-guard-cluster-refactor/` — exercises Phase 2.5 rules (lift hierarchy, patch-chain detection, `refactor-recommended` verdict, `lift_considered` schema, `finding_type: design_debt`). A session-state module with three accumulated boolean-guard flags adds a fourth. Expected: patch-chain signal fires, verdict `refactor-recommended`, design_debt finding with a writer-lift recommendation and all-three-lifts evaluated.
- `02-clean-refactor/` — exercises the *absence* of findings. A function rename with all call sites updated should return verdict `approve` with a non-empty Trace Log. If this fixture ever fires findings, we have false-positive drift.
- `03-unsafe-migration/` — exercises `domains/data.md` + verdict escalation to `block`. A `NOT NULL` column addition on a large existing table without a default value is a ship-blocker. Verifies domain loading, block verdict path, and `finding_type: correctness` classification.

## When to add a new fixture

When a real review surfaces a class of bug not covered by the existing catalog, **and** the fix would benefit from a regression assertion. Prefer adding one fixture that exercises several axes over three fixtures that each exercise one axis.

## When NOT to add a new fixture

- Per-rule fixtures. The catalog stays small and hand-picked.
- Fixtures for rules that are unlikely to regress (e.g., the ship-blocker question's text).
- Fixtures that test the model's phrasing rather than the skill's behavior. Phrasing shifts; methodology rules are supposed to be stable.

## Known gap — there is no automated runner

Running fixtures is a manual discipline. The alternative — an automated harness that invokes the skill in a subprocess and diffs outputs — was considered and rejected for the initial implementation because the cost of building it exceeds the regression budget at the current fixture count. Revisit when the fixture count crosses ~8 or when a real regression ships because a fixture was not re-run.

## Relationship to CI

None. CI does not run these fixtures. The version-drift pre-commit hook is the only automated check in this repo.
