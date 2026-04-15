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

# Second round on the same diff — prior review auto-detected, no flag needed
/devil-review

# Mark findings as not actionable and re-review — suppresses them on subsequent runs in this session
/devil-review --reject 2

# Reject multiple findings by index (CSV, no spaces)
/devil-review --reject 2,5,7

# Combine with other flags — --reject applies to the most recent prior run, then a fresh review starts
/devil-review --reject 2 --scope branch
```

Every successful run auto-writes its output to `.claude/devil-review/<session-id>/<target>.md`, scoped by Claude Code session ID and review target (working-tree, branch, or PR). A subsequent `/devil-review` on the same target in the same session automatically detects and loads that snapshot and uses it for multi-round analysis:

- **Finding-level attribution** — each current finding is classified against the prior round's findings with `prior_relation.category` in `{carries-over, new-drift-from-fix, pre-existing-orthogonal}`. The author can see at a glance which findings are recurrences vs. new drift caused by the prior fix vs. unrelated bugs the prior round missed.
- **Severity dampening** — a `carries-over` finding that recurs at equal-or-lower severity triggers a bar-raising rule: either the reviewer articulates why the prior fix did not address it (keeps severity), or the finding gets reclassified as `pre-existing-orthogonal` with a one-notch severity drop. Silent demotion of recurring high-severity findings is blocked.
- **Chain-closing override** — if the prior round's findings were mostly resolved (`resolved ≥ still_open + new_drift_introduced`), the `refactor-recommended` verdict is suppressed even when other conditions would trigger it. Iteration that is materially reducing the problem does not get penalized as patch-churn.
- **Decision block** — a top-level machine-readable `decision` object (`action: iterate | stop-and-refactor | ship`, `patch_chain_detected`, `iteration_count`, `rationale`) pairs with the prose-facing `verdict` and is the signal CI gates and `/loop` auto-stop consume.

No flag, no filename management. Session scoping means stale reviews from prior sessions do not contaminate today's work.

## Setup

Add this line to your project's `.gitignore` so review snapshots stay local:

```
.claude/devil-review/
```

One-time setup. Without this line, snapshots get tracked in git — which is usually not what you want since they are ephemeral local state, not team-shared config.

## How it works

1. **Resolves target** — auto-detects working tree vs branch diff, or takes explicit scope
2. **Collects context** — gathers diffs, status, commit history, untracked files, PR metadata
3. **Loads methodology** — reads `methodology.md` for review philosophy and calibration rules
4. **Loads domain checklists** — classifies changed files and loads matching checklists from `domains/` (UI, mobile, desktop, backend API, library/SDK, data/persistence, CLI, crypto). Multiple domains load together when a diff spans them (e.g., React Native feature loads both UI and mobile; backend handler with SQL migration loads both API and data)
5. **Reads project rules** — checks CLAUDE.md and active specs to avoid false positives on intentional decisions
6. **Traces symbols & consumers** — for every changed symbol (function, component, type, schema, config key), reads the call sites
7. **Audits unchanged callees against new callers** — when the diff introduces a new caller chain reaching unchanged code, checks whether the callee's existing failure handling (auto-clear, auto-retry, default fallbacks, error suppression) is compatible with the new caller's semantic mode
8. **Traces mutated record fanout** — for every record whose fields are written, enumerates sibling fields and checks each for stale references, lifecycle leakage, or silently broken invariants
9. **Audits preserved siblings against new reader paths** — for siblings the diff preserves, checks whether the diff opens a new writer→reader code path that breaks an implicit invariant the unchanged reader assumed
10. **Verifies cross-boundary runtime contracts** — for IPC, API, DB, queue, FFI, and other boundaries where compile-time types do not bind runtime format, reads the producer in its native source rather than trusting consumer-side type signatures
11. **Adversarial review** — applies skeptical methodology, focused on high-cost failures
12. **Test-traces every finding** — for each finding, answers "why didn't existing tests catch this?" with one of `no-test`, `mock-bypass`, or `missing-assertion`. Findings without a defensible test-trace answer are dropped as false positives
13. **Answers ship-blocker question** — decides whether a single issue justifies blocking the PR
14. **Emits structured output** — markdown for humans + JSON fence for downstream tools

## Verdict semantics

- **`block`** — at least one critical or high **correctness** finding that would make you refuse to merge
- **`needs-attention`** — material issues exist but none are ship-blocking; merge with follow-up
- **`refactor-recommended`** — correctness looks OK, but structural debt is high enough that iterating in place will make it worse; step back and restructure instead of adding another guard. Typical trigger: a patch-chain pattern across recent commits, or design_debt findings outnumbering correctness findings in a multi-round review
- **`approve`** — no material findings, the change looks safe to ship

The **ship-blocker question** — "Is there a single issue that would make me refuse to merge?" — is answered before any findings are listed. A yes drives the verdict to `block`; a no with high design-debt can drive it to `refactor-recommended`.

Findings carry a `finding_type` that places each one into `correctness | design_debt | best_practice_violation | architectural_smell`, and a `scope` tag in `in-diff | pre-existing | future-work`. The two severity axes `correctness_severity` and `design_debt_severity` summarize the review at a glance and feed the verdict derivation — but **only `in-diff` findings drive verdict escalation**. Pre-existing bugs the reviewer noticed in unrelated code and future-work suggestions still emit as findings for transparency but do not block ship decisions; the PR author can triage them separately.

### Decision block — the automation signal

Alongside the prose-facing `verdict`, every run emits a machine-readable `decision` block with `action: iterate | stop-and-refactor | ship`, `patch_chain_detected` (boolean), `iteration_count` (integer), and `rationale` (one sentence). Canonical pairing: `block`/`needs-attention` → `iterate`, `refactor-recommended` → `stop-and-refactor`, `approve` → `ship`. CI gates and `/loop`-style runners should read `decision.action` rather than parse prose.

Verdict and decision can **disagree** in one important case: `verdict: needs-attention` + `decision.action: stop-and-refactor` when the patch-chain signal fires at `iteration_count ≥ 2` — the reviewer judges the current round is iterable in principle, but the session-level pattern says "stop, refactor instead of another round". When the two disagree, `decision.action` is the automation signal and the disagreement is called out in `rationale`. See `skills/devil-review/methodology.md` for the full decision tree.

## What it looks for

**Generic attack surface** (any project type):
- Auth, permissions, and trust boundary violations
- **LLM/agent/model output consumed as trusted input** — fields emitted by a language model, agent, rule engine, or external automation treated as "known-good in testing" rather than validated on the consumer side. Silent-and-probabilistic failure mode: no type error, no crash, just a shape-valid but semantically wrong value accepted into state the user trusts
- Data loss, corruption, and irreversible state changes
- Race conditions, ordering assumptions, re-entrancy
- Rollback safety, retry logic, idempotency gaps
- Empty-state, null, timeout, degraded dependency behavior
- Cross-platform assumptions (paths, shell semantics, OS APIs)
- Process lifecycle issues (leaks, orphans, PID reuse)
- Concurrency bugs (mutex ordering, file watcher races)
- **Persistence and durability of bad state** — wrong values that survive serialization, cache, or reload, where the bug is invisible in the current process but persists across restart

**Cross-cutting grounding disciplines** (mandatory audits applied alongside the attack surface, not optional):
- **Mutated record fanout** — for every record the diff writes, sibling fields are enumerated and checked for stale references, lifecycle leakage, and silently broken invariants. Catches the planFilePath / wrong-cwd / stale-error class of bugs where one field is updated correctly but its siblings now point at the prior owning entity.
- **Reader-path fanout** — for siblings the diff preserves, the audit asks whether the diff opens a new writer→reader code path that reaches an existing reader and breaks an invariant neither side sees. Catches bugs where the field is correctly preserved but a new caller chain (restart, remount, restore-from-persistence, explicit-user-intent reaching implicit-reopen code) makes the unchanged reader wrong.
- **Failure-mode audit on unchanged callees with new callers** — when the diff adds a new caller of an unchanged function, lifecycle, or handler, the callee's existing failure handling (auto-clear, auto-retry, default fallback, error suppression) is checked against the new caller's semantic mode. Catches "auto-recovery written for caller A's semantics is silently wrong for caller B's semantics".
- **Runtime contract verification at boundaries** — IPC, API, DB row, queue payload, FFI, env vars, config files, browser persistence, file formats. The producer is read in its native source rather than trusting consumer-side type signatures. Catches createdAt epoch-vs-ISO drift, NUMERIC precision loss, JWT claim format mismatches, native bridge serialization gotchas.
- **LLM/agent output validation** — when the diff consumes structured data emitted by a language model, agent, or external automation, every consumed field is audited for consumer-side validation. Unvalidated enum/status fields, source-identifying metadata accepted without cross-check against source material, and extracted entities taken verbatim all surface as findings. Prompt-side constraints are not validation. Per the LLM-compliance severity floor, findings that reach persistent state or user-visible action start at **high** by default. Catches the "the prompt asks for backlog-only so the code accepts any column" class of trust boundary failure.
- **Acceptance criteria crosswalk** — when the review target includes a spec with structured acceptance criteria (explicit "must" statements, numbered requirements, definition-of-done), every AC is walked top to bottom and mapped to a specific file:line that implements it. ACs with no mapping, ambiguous mapping, or contradicting implementation surface as findings at **high** by default — the spec was explicit, the code is silently non-compliant, and no test covers missing code. The full crosswalk (passing and failing) is recorded in the trace log so the "I checked" claim is falsifiable. Catches the class of bugs where an AC was read but never verified against implementation.
- **Test-trace per finding** — every reported finding must answer "why didn't existing tests catch this?" with `no-test`, `mock-bypass`, or `missing-assertion`. Findings without a defensible answer are dropped. Catches mocked tests that exercise only the consumer's mental model of the contract, not the producer.
- **Generalization test** — every finding is reframed at the root invariant before reporting. Narrow framings ("crashed-tab edge case") are widened to the underlying invariant ("any session switch with a live process") so the fix matches the actual blast radius rather than the most extreme example.
- **Prior-reviewer stance** — recommendations from earlier reviews (previous devil-review runs, codex review, PR comments) are reviewable artifacts, not architectural decisions. A change made in response to earlier feedback gets *more* scrutiny, not less, because over-correction is the default failure mode when targeting a narrow critique.
- **Patch-chain detection** — when the same diff is reviewed multiple times, the skill scans recent git history for defensive-commit clusters (`fix:`, `guard:`, `prevent:`, `workaround:`, `hotfix:` prefixes) on the reviewed files, and auto-loads the previous run's output from `.claude/devil-review/<session-id>/<target>.md` (written by every successful run, session- and target-scoped) to cross-reference current candidate findings against the prior round. No flag needed — the skill always checks, and if a prior file exists it is used. If the signals fire on a genuine patch chain (same root cause repeatedly guarded, not different roots on the same hotspot), the verdict shifts to `refactor-recommended` and the recommendation is to collapse the guard cluster structurally rather than add another guard. Catches the failure mode where each new review round chases edge cases introduced by the previous round's guards.
- **Claim verification pass (pre-emit)** — before emitting findings, the reviewer verifies its own load-bearing claims against the diff/code it read. Catches reviewer-side over-claims — asymmetry errors ("only fires when both fail" when either suffices), unsupported reachability assertions ("widens here" with no traceable call path), scope inflation, and counterfactual leaks. Findings that fail verification are narrowed, reclassified, or dropped; the drops are logged to `trace_log.findings_dropped_in_verification` so the pass is auditable. This discipline closes the reviewer-irony gap — a reviewer that catches the user's factual errors but never verifies its own claims is an unreliable reviewer.
- **Evidence gate for cross-boundary external claims** — extends the Claim verification pass with a mandatory fifth step for claims about external systems: third-party libraries (including stdlib), OS runtimes, protocols, file formats, shell semantics. Findings whose load-bearing claim asserts external behavior must carry an `evidence_source` — a docs URL (via `WebFetch`), a source-code file:line from a clone, a runtime observation (a shell command and its observed output), or a published spec identifier. "Stdlib says so" or "the docs mention this" without a pointer is not evidence. Findings without gatherable evidence either drop severity and confidence one notch each and tag `evidence: unverified` in the body, or are dropped entirely with reason `unverified-external-claim`. `trace_log.external_claims_verified` (integer) counts the verification actions performed so consumers can discriminate reviews that actually researched from reviews that emitted plausible-looking external assertions. Catches the class of bugs where a reviewer says "PathBuf strips trailing separators" or "MSVCRT parses argv with specific quoting" without ever checking the docs.
- **Project-rule citation** — when the project ships review rule files (`.claude/rules/*.md`, root-level `code-review.md`/`REVIEW.md`/`CONTRIBUTING.md`, or `**/rules/*.md` one level deep), the skill loads them (up to 10 files, 30 KB total cap) and findings can cite specific rules with **verbatim 1–2 line quotes**. Paraphrased or composited quotes are schema-invalid — consumers can string-search the cited file to verify the quote is literally present. Turns the reviewer from opinion-source to rule-enforcer when the project has articulated its own review rules. CLAUDE.md and active specs are still loaded separately as pre-review context for the drop-spec-accepted-findings discipline; project rules are the citation direction.
- **Scope classification** — every finding carries `scope: in-diff | pre-existing | future-work`. The default is `in-diff`; `pre-existing` is for bugs in code the diff did not touch that the reviewer surfaced while tracing consumers; `future-work` is for design suggestions that do not describe a bug today. Only `in-diff` findings drive verdict escalation (`block` / `needs-attention` / `refactor-recommended`). Pre-existing and future-work findings still count toward the hard cap and still emit as findings, but they do not block the ship decision — the PR author can see them and file follow-ups without them dragging verdict down. Resolves the "stay scoped to the diff vs. raise the latent bug I just found" tension transparently instead of dropping either side.
- **Reachability classification** — every finding also carries `reachability: reachable | hypothetical | requires-specific-config`, orthogonal to severity, confidence, and scope. `reachable` requires the body to name a concrete call path from an entry point (user action, cron, boot, API route, event); `requires-specific-config` requires naming the specific config/flag/env-var/platform that gates the bug; `hypothetical` is for bugs inferred from types or patterns without a traced path. Only `reachable` findings drive verdict escalation (pattern identical to the scope filter). Resolves the priority confusion where a `confidence: 0.7` hypothetical Windows-specific finding reads as equal-weight with a `confidence: 0.85` async race on the main flow — reachability is a structural property of the code path, confidence is epistemic uncertainty about the claim, and the two shouldn't collapse into one axis. A `hypothetical` finding can still carry high confidence (reviewer is sure this WOULD be a bug if reached), and a `reachable` finding can still carry low confidence (reviewer is not sure their reading is right) — both cases are now representable.
- **User rejection memory** — when the user decides findings are not actionable, `/devil-review --reject <CSV>` records the rejections and runs a new review in one step (e.g. `--reject 2,5,7` dismisses the 2nd, 5th, and 7th findings of the most recent prior run). The rejections persist in a session-scoped sidecar `.claude/devil-review/<session-id>/rejections.json` (with its own `schema_version: "1.0"` independent of the main payload schema). On subsequent runs, candidate findings whose normalized `file:lines:title` hash matches a rejection are either suppressed silently (default — the user's prior decision is respected) or re-raised with a `previously_rejected` annotation containing the prior rationale and a one-sentence statement of what **new evidence** justifies re-raising (a new call path, new config condition, new data-flow, new project rule, or new prior-review carries-over status). Re-raise without nameable new evidence does not clear the bar. A **chain-of-rejections verdict override (rule 0)** fires when 2+ previously-rejected findings are re-raised in a single review — the reviewer is persistently surfacing dismissed findings, and the override forces `verdict: approve` + `decision.action: ship` with an explanatory rationale. The override is the automation-facing dual of the v1.11 chain-closing override: chain-closing says "fixes are working, don't push refactor"; chain-of-rejections says "user and reviewer disagree, stop iterating". Resolves the saha-test-#3 friction where the same Windows trailing-backslash finding re-appeared round after round because the reviewer had no memory of the prior dismissal.
- **Structured prior-review attribution + decision block + severity dampening** — when a prior review snapshot is loaded, each current finding is classified against the prior round with `prior_relation.category` (three values: `carries-over | new-drift-from-fix | pre-existing-orthogonal`), and `trace_log.prior_review_summary` rolls up per-category counts. A severity-dampening rule blocks silent demotion of recurring high-severity findings — either the finding keeps its prior severity with `carries-over` tag, or it reclassifies to `pre-existing-orthogonal` with a one-notch drop, never a silent downgrade. The top-level `decision` block (`action: iterate | stop-and-refactor | ship`, `patch_chain_detected`, `iteration_count`, `rationale`) is the machine-readable automation signal paired with `verdict`. A chain-closing override suppresses `refactor-recommended` when the prior round's findings were mostly resolved by the fix — iteration that is working does not get penalized as patch-churn. Catches the round-N+1 failure mode where a prior round's finding resurfaces at lower severity without credit and the patch-chain signal hides behind the apparent improvement.

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

Every review emits two parts: a markdown section and a JSON fence for downstream tools. When a candidate finding matches a prior rejection hash and the reviewer elects to re-raise, the finding body leads with a `> Previously rejected on <date> with rationale <text>. New evidence: <one sentence>.` blockquote preamble, and the JSON carries a matching `previously_rejected` object — see the markdown template below.

```
# Devil Review

Target: working tree diff
Scope: <N> files, <M> lines changed
Verdict: <block | needs-attention | refactor-recommended | approve>
Decision: <iterate | stop-and-refactor | ship>  (iteration <N>; patch_chain_detected=<true|false>)
  Rationale: <one sentence>

<1-2 sentence ship/no-ship assessment>

## Trace Log

Ship-blocker question: <yes | no>
Reasoning: <one sentence>

Domain classification:
- Loaded: <comma-separated list of domains>
- Considered but dropped: <list with one-word reason>
- Notes: <one sentence on classification calls>

Project rules loaded:
- `<path/to/rule.md>` (<bytes> bytes)
- ...
(empty list "none" is valid when no rule file matched; omission is not)

Prior-review summary (present only when a prior run was loaded):
- Total in prior: <N>
- Resolved: <N>
- Still open: <N>
- New drift introduced: <N>
- Pre-existing unrelated: <N>

Changed symbols inspected:
- `<symbol>` (<kind>) → consumers: <path/to/caller>:<line>, ...
  - failure-mode audit: <callee at file:line — existing failure mode — compatible with new caller: yes|no — rationale>
  - failure-mode audit: no new caller chains introduced

Mutated records inspected:
- `<record>` (<kind>) → siblings: <field1>, <field2>, ...
  - new reader path: <preserved field reached by new writer path via reader at file:line — invariant no longer holds>

Architectural decisions checked:
- <CLAUDE.md section ref, or "n/a">

Scenarios considered:
- <one-line adversarial scenario>
- ...

Considered but not promoted:
- <observation> — reason: <out-of-scope | low-confidence | covered-by-finding-N | spec-accepted | test-covers-invariant>

Findings dropped in verification:
- <original claim as first written> — reason: <unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept | unverified-external-claim>
- ...
(empty list "none" is valid when every candidate finding survived the Claim verification pass unchanged; omission is not)

External claims verified: <integer ≥0>
(counts verification actions tied to load-bearing external-behavior claims; `0` is valid when no finding referenced external systems)

Rejections loaded:
- `<hash first 12 chars>...` rejected <ISO-8601 timestamp>
- ...
(empty list "none" is valid when no rejections.json file exists for this session; absence is a grounding failure)

## Findings

### [severity] <short title>
- **File**: `<path/to/file>`
- **Lines**: L<start>-L<end>
- **Type**: <correctness | design_debt | best_practice_violation | architectural_smell>
- **Scope**: <in-diff | pre-existing | future-work>
- **Reachability**: <reachable | hypothetical | requires-specific-config>
- **Prior relation**: <carries-over | new-drift-from-fix | pre-existing-orthogonal>  (omit when no prior loaded)
- **Confidence**: <0.0-1.0>

> Previously rejected on <ISO-8601> with rationale <rationale or "(none provided)">. New evidence: <one concrete sentence>.
(omit this blockquote when the finding was NOT previously rejected; when present, the JSON `findings[].previously_rejected` object carries the same fields)

<what can go wrong, why this code path is vulnerable, likely impact>

**Recommendation**: <concrete change to reduce risk>

**Rule citations** (optional, only when a loaded project rule applies):
- `<path/to/rule.md>` — *<rule identifier>*: "<verbatim 1–2 line quote from the rule file>"
- ...

**Evidence sources** (optional, only when the load-bearing claim references external-system behavior):
- *<docs-url | source-file | runtime-observation | specification>*: `<URL, file:line, command+output, or spec identifier>` — "<claim this source validates>" (verified <ISO-8601>)
- ...

**Test coverage**: <one of `no-test:`, `mock-bypass:`, or `missing-assertion:` followed by a one-sentence explanation>
```

Followed by a JSON fence carrying the same data in a structured form for downstream tools (current schema version: **1.14**, see `skills/devil-review/output-schema.md` for the full contract). The schema is additive across patch and minor versions — older consumers parse newer payloads without error, but new fields (`failure_modes_considered`, `new_reader_paths`, `test_coverage`, `considered_not_promoted`, `acceptance_criteria_crosswalk`, `finding_type`, `lift_considered`, `correctness_severity`, `design_debt_severity`, `patch_chain_risk`, `findings_dropped_in_verification`, `project_rules_loaded`, `rule_refs`, `scope`, `decision`, `prior_relation`, `prior_review_summary`, `evidence_sources`, `external_claims_verified`, `reachability`, `rejections_loaded`, `previously_rejected`) are only visible to consumers that bump to the matching schema version.

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

Rejections are recorded via the `--reject <CSV>` flag on `/devil-review` itself (see Usage above) and persist across runs in a session-scoped sidecar at `.claude/devil-review/<session-id>/rejections.json`. No separate skill — the rejection mechanism lives inline as a flag on the main review command.

New domain checklists can be added under `domains/` by extending the routing table in `SKILL.md` Step 5. Each checklist is loaded only when the diff touches matching files, so adding domains does not grow the base review cost — only the ceiling for cross-domain mega-diffs.

## License

MIT
