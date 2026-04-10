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

# Review branch diff against default base
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

## How it works

1. **Resolves target** — auto-detects working tree vs branch diff, or takes explicit scope
2. **Collects context** — gathers diffs, status, commit history, untracked files, PR metadata
3. **Loads methodology** — reads `methodology.md` for review philosophy and calibration rules
4. **Loads domain checklists** — classifies changed files and loads matching checklists from `domains/` (UI, mobile, desktop, backend API, library/SDK, data/persistence). Multiple domains load together when a diff spans them (e.g., React Native feature loads both UI and mobile; backend handler with SQL migration loads both API and data)
5. **Reads project rules** — checks CLAUDE.md and active specs to avoid false positives on intentional decisions
6. **Traces consumers** — for every changed symbol (function, component, type, schema, config key), reads the call sites
7. **Adversarial review** — applies skeptical methodology, focused on high-cost failures
8. **Answers ship-blocker question** — decides whether a single issue justifies blocking the PR
9. **Emits structured output** — markdown for humans + JSON fence for downstream tools

## Verdict semantics

- **`block`** — at least one critical or high finding that would make you refuse to merge
- **`needs-attention`** — material issues exist but none are ship-blocking; merge with follow-up
- **`approve`** — no material findings, the change looks safe to ship

The **ship-blocker question** — "Is there a single issue that would make me refuse to merge?" — is answered before any findings are listed. A yes drives the verdict to `block`.

## What it looks for

**Generic attack surface** (any project type):
- Auth, permissions, and trust boundary violations
- Data loss, corruption, and irreversible state changes
- Race conditions, ordering assumptions, re-entrancy
- Rollback safety, retry logic, idempotency gaps
- Empty-state, null, timeout, degraded dependency behavior
- Cross-platform assumptions (paths, shell semantics, OS APIs)
- Process lifecycle issues (leaks, orphans, PID reuse)
- Concurrency bugs (mutex ordering, file watcher races)

**Domain-specific checklists** — loaded automatically based on what files the diff touches. A single review can load several:

| Domain | Covers |
|---|---|
| `domains/ui.md` | Web UI / view layer — multi-instance mounting, sibling visibility leaks, focus management, stacking context, effect cleanup on hidden panes, reactivity pitfalls |
| `domains/mobile.md` | iOS, Android, React Native, Flutter — app lifecycle, permissions, offline/online transitions, battery, memory pressure, push notifications, OS version skew, accessibility |
| `domains/desktop.md` | Electron, Tauri, native — IPC security, multi-window coordination, auto-update safety, file watchers, packaging/signing, OS-specific quirks |
| `domains/api.md` | Backend APIs / servers — request validation, auth boundaries, response shape stability, idempotency, transactions, N+1 queries, rate limiting, observability |
| `domains/library.md` | SDKs and libraries — semver discipline, behavioral stability, dependency hygiene, runtime assumptions, tree-shakeability, cross-runtime compat |
| `domains/data.md` | Persistence and migrations — migration safety, NOT NULL additions, index changes, column renames, transaction scope, replication, RLS, caching |
| `domains/cli.md` | CLI tools — argument parsing, exit codes, stdio discipline, TTY detection, signal handling, subprocess management, path and environment hygiene |
| `domains/crypto.md` | Security-critical code — key handling, nonce/IV discipline, algorithm choice, constant-time comparisons, signature verification, TLS, session and token handling |

## What it does NOT do

- Style feedback, naming suggestions, low-value cleanup
- Fix issues or modify code
- Report findings already addressed in the working tree
- Flag intentional architectural decisions documented in CLAUDE.md
- Return `approve` to paper over tool failures — errors are reported explicitly

## Output format

Every review emits two parts: a markdown section and a JSON fence for downstream tools.

```
# Devil Review

Target: working tree diff
Scope: <N> files, <M> lines changed
Verdict: <block | needs-attention | approve>

<1-2 sentence ship/no-ship assessment>

## Trace Log

Ship-blocker question: <yes | no>
Reasoning: <one sentence>

Changed symbols inspected:
- `<symbol>` (<kind>) → consumers: <path/to/caller>:<line>, ...

Architectural decisions checked:
- <CLAUDE.md section ref, or "n/a">

Scenarios considered:
- <one-line adversarial scenario>
- ...

## Findings

### [severity] <short title>
- **File**: `<path/to/file>`
- **Lines**: L<start>-L<end>
- **Confidence**: <0.0-1.0>

<what can go wrong, why this code path is vulnerable, likely impact>

**Recommendation**: <concrete change to reduce risk>
```

Followed by a JSON fence carrying the same data in a structured form for downstream tools (see `skills/devil-review/output-schema.md` for the full contract).

## File layout

```
skills/devil-review/
├── SKILL.md           # orchestration entry point (arguments, diff collection, domain routing)
├── methodology.md     # review philosophy, severity, calibration, block test
├── output-schema.md   # markdown + JSON output format contract
└── domains/
    ├── ui.md          # web UI / view-layer checklist
    ├── mobile.md      # iOS, Android, React Native, Flutter checklist
    ├── desktop.md     # Electron, Tauri, native desktop checklist
    ├── api.md         # backend API / server checklist
    ├── library.md     # SDK / library / published package checklist
    ├── data.md        # persistence / migrations / schema checklist
    ├── cli.md         # CLI tool checklist
    └── crypto.md      # security-critical / cryptographic code checklist
```

New domain checklists can be added under `domains/` by extending the routing table in `SKILL.md` Step 5. Each checklist is loaded only when the diff touches matching files, so adding domains does not grow the base review cost — only the ceiling for cross-domain mega-diffs.

## License

MIT
