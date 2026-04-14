# Fixture 01 — Guard cluster refactor

## Scenario

`src/session.ts` holds a `SessionManager` that gates concurrent session-restore operations using per-instance boolean flags. Over time, three flags have accumulated (`restoring`, `sessionRestored`, `dirty`). The current diff adds a fourth (`loading`) to patch a newly-observed concurrent-load race.

This is a textbook patch-chain: each prior round of review added another guard instead of consolidating the state machine. The correct response is no longer "add another guard" — it is "collapse the four flags into a single state enum or use a single-writer lock".

## Repo context the skill needs

- **Framework:** TypeScript, Node.js. No UI layer. This is a backend/library module.
- **No CLAUDE.md architectural decisions** about session state; the flag-based approach was never ratified, it accumulated.
- **No active spec** with acceptance criteria for this diff.
- **Test file:** `src/__tests__/session.test.ts` exists but only covers the happy-path restore (no concurrent-load assertion, no state-machine assertion on the flag combination).

## Commit history on `src/session.ts` (inject before running)

When setting up the scratch checkout, create commits with these messages on the file — the patch-chain detector reads them:

```
abc1234 fix: prevent double-restore race
def5678 guard: sessionRestored early-return
ghi9012 patch: dirty flag checked on re-entry
jkl3456 fix: loading flag for concurrent-load race (this PR — apply as working-tree diff)
```

The first three commits are historical; the fourth is the change being reviewed (applied as `diff.patch` on the working tree, not committed).

## Domain classification expected

- Loaded: none (TypeScript backend module that does not match any current `domains/*.md`)
- Or: `library.md` if the scratch project's package.json declares it as a published package. The fixture's assertions work under either classification.

## Focus text

Run `/devil-review` without a focus argument. The fixture should exercise the natural flow — patch-chain detection, lift hierarchy, design_debt classification — without being biased by a focus hint.
