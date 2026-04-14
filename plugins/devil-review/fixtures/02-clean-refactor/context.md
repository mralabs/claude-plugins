# Fixture 02 — Clean refactor

## Scenario

A straightforward symbol rename. `formatDate` is renamed to `formatDateISO` to disambiguate from a newly-added `formatDateRelative` (not in this diff, elsewhere in the project). All call sites of the renamed function are updated in the same diff. Behavior is identical.

This fixture tests the **absence** of findings. A skill that always finds something is a broken skill — a clean rename should return `verdict: approve` with `findings: []`.

## Repo context the skill needs

- **Framework:** TypeScript, Node.js. Generic utility module.
- **All callers updated:** `src/user.ts` and `src/order.ts` both import the renamed symbol. No other file imports `formatDate` from `./utils`. Verify with a scratch-repo grep.
- **No test file regressions:** tests in `src/__tests__/utils.test.ts` (if present in the scratch setup) import from `./utils` — update them in the diff if they reference `formatDate` by name.
- **No CLAUDE.md architectural decision** about naming conventions that this rename violates.
- **No active spec** for the rename.

## Commit history

Recent commits on `src/utils.ts`, `src/user.ts`, `src/order.ts` are unrelated business-feature commits — no defensive prefixes (`fix:`, `guard:`, `prevent:`, etc.). The patch-chain detector should not fire.

Example commits to inject into the scratch checkout:

```
aaa1111 feat(order): add discount calculation
bbb2222 chore(user): extract user type alias
ccc3333 feat(utils): add parseDate helper
```

## Domain classification expected

- Loaded: none (generic utility module, no domain match)
- `classification_notes` should explain: no domain match on `.ts` files that are neither UI (no templates), nor library (not published), nor any other domain surface.

## Focus text

Run `/devil-review` without a focus argument.
