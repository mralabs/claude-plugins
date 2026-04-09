# devil-review

Adversarial code review plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

The devil is in the details. This plugin reviews your changes with skepticism — it tries to **break confidence** in the change, not validate it. Finds subtle bugs, race conditions, violated invariants, and unhandled failure paths that conventional reviews miss.

## Install

```bash
claude /plugin install mralabs/devil-review
```

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
Verdict: needs-attention

One critical race condition in board save path.

## Findings

### [critical] Title
- **File**: `path/to/file`
- **Lines**: L42-L58
- **Confidence**: 0.9

<description of what can go wrong and why>

**Recommendation**: <concrete fix>
```

## License

MIT
