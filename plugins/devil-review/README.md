# devil-review

> *The devil is in the details.*

Adversarial code review plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Every diff has dark corners — the edge case nobody tested, the race condition that only fires under load, the invariant that quietly stopped being true three functions up the call chain. **devil-review** goes looking for them. It reviews your changes with skepticism, trying to **break confidence** in the change rather than validate it.

## Usage

```bash
# Auto-detect: reviews working tree if dirty, branch diff if clean
/devil-review

# Review working tree changes only
/devil-review --scope working-tree

# Review branch diff against main
/devil-review --scope branch

# Review against a specific base ref
/devil-review --base feature/auth

# Review a GitHub PR
/devil-review --pr 42

# Focus on a specific area
/devil-review PTY lifecycle cleanup

# Combine flags
/devil-review --scope branch --base develop concurrency handling
```

## What it does

1. **Resolves review target** — auto-detects working tree vs branch diff
2. **Collects context** — gathers diffs, status, commit history, untracked files
3. **Reads project rules** — checks CLAUDE.md architectural decisions, active task specs to avoid false positives
4. **Traces call chains** — for each changed function, reads callers and callees across files
5. **Adversarial review** — applies skeptical methodology focused on high-cost failures
6. **Reports findings** — severity-sorted findings with confidence scores, or a clean bill of health

## What it looks for

- Auth, permissions, and trust boundary violations
- Data loss, corruption, and irreversible state changes
- Race conditions, ordering assumptions, and re-entrancy
- Rollback safety, retry logic, and idempotency gaps
- Empty-state, null, timeout, and degraded dependency behavior
- Cross-platform assumptions (paths, shell semantics, OS APIs)
- Process lifecycle issues (leaks, orphans, PID reuse)
- Concurrency bugs (mutex ordering, file watcher races)

## What it does NOT do

- Style feedback, naming suggestions, or low-value cleanup
- Fix issues or modify code
- Report findings that are already addressed in the working tree
- Flag intentional architectural decisions documented in CLAUDE.md

## Output format

```
# Devil Review

Target: working tree diff
Scope: 4 files, 127 lines changed
Verdict: needs-attention

Unguarded concurrent write to shared config — data loss under parallel requests.

## Findings

### [critical] Write race in config save
- **File**: `src/config/manager.ts`
- **Lines**: L42-L58
- **Confidence**: 0.9

Two callers can read-modify-write the config file simultaneously.
The second write silently overwrites the first, losing its changes.

**Recommendation**: Add a file lock or serialize writes through a queue.
```

## License

MIT
