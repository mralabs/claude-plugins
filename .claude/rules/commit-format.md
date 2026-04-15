# Commit format

- `feat(<plugin>): v<X.Y.Z> <tagline>` — minor or major bump introducing new capability
- `fix(<plugin>): v<X.Y.Z> <tagline>` — patch bump for clarifications and corrections
- `fix(<plugin>): sync manifest <old> -> <new>` — manifest-only fix when versions drifted from actual state
- `chore(<plugin>|repo): <...>` — tooling, hooks, CI; no version bump
- `refactor(<plugin>|repo): <...>` — structural changes without semantic version impact
- `docs(<plugin>|repo): <...>` — docs-only commits that are not part of a release

Commit body explains the **reasoning**, not just the what. Self-review findings rolled into the same commit must appear under a "Self-review fixes rolled into this commit:" section so the rationale for each fix is auditable.

Authoritative source: `CLAUDE.md` — "Commit message format".
