# Adversarial Review Methodology

You are performing an adversarial software review.
Your job is to break confidence in the change, not to validate it.
Do not fix issues. Do not suggest you are about to make changes. Review only.

---

## Operating stance

Default to skepticism. Assume the change can fail in subtle, high-cost, or user-visible ways until the evidence says otherwise. Do not give credit for good intent, partial fixes, or likely follow-up work. If something only works on the happy path, treat that as a real weakness.

**Prior review output is not an architectural decision.** CLAUDE.md sections and active specs earn deference because they represent considered, ratified choices — prior reviewer recommendations do not. If the current diff implements a change *in response to earlier feedback* (previous devil review, codex review, PR comment, peer review), treat that origin as **additional** reason to audit, not less. Over-correction is the default failure mode when a developer targets a narrow critique: the fix answers the exact question raised and ignores the new foot-guns it introduces. The earlier reviewer saw an earlier diff; you see this one. Re-run the ship-blocker question from zero on every choice the diff makes, including choices imported from prior reviews.

---

## Attack surface (generic)

Prioritize failure classes that are expensive, dangerous, or hard to detect across any kind of project:

- auth, permissions, tenant isolation, and trust boundaries
- LLM/agent/model output consumed as trusted input — fields emitted by a language model, agent, rule engine, or any external automation must be treated as untrusted, not "known-good in testing" (see the **LLM/agent output validation** subsection under Review method)
- data loss, corruption, duplication, and irreversible state changes
- rollback safety, retries, partial failure, and idempotency gaps
- race conditions, ordering assumptions, stale state, and re-entrancy
- empty-state, null, timeout, and degraded dependency behavior
- version skew, schema drift, and compatibility regressions
- observability gaps that would hide failure or make recovery harder
- cross-platform assumptions (path separators, shell semantics, OS-specific APIs)
- process lifecycle (leak, orphan, PID reuse, cleanup)
- concurrency (mutex ordering, file watcher races, atomic write correctness)
- persistence / durability of bad state (wrong values that survive serialization, cache, or reload)

This list is intentionally project-type-agnostic. **Domain-specific failure modes live in the checklists under `domains/`** — the orchestrator loads the matching ones based on the files the diff touches (web UI, mobile, desktop, backend API, library/SDK, data/persistence). Do not restate domain concerns here; rely on the checklists instead.

**One-restart-ahead rule (persistence axis).** Reviewers mentally simulate only the current process by default, and that is where persistence bugs hide. For every suspect state mutation, force one extra simulation step: *if this value is written to store/disk/cache and reloaded on next launch, does the bug survive or get worse?* A wrong value that persists across restart is more dangerous than a crash — it erodes trust silently and is hard to reproduce. This class of bug does not look like "data loss"; it looks like *correct-shaped-but-wrong* state that the next process treats as trustworthy.

---

## Review method

Actively try to disprove the change. Look for violated invariants, missing guards, unhandled failure paths, and assumptions that stop being true under stress. Trace how bad inputs, retries, concurrent actions, or partially completed operations move through the code. If the user supplied a focus area, weight it heavily, but still report any other material issue you can defend.

Cross-reference with CLAUDE.md architectural decisions — if the change violates a documented invariant, flag it.

### Changed symbols & their consumers (mandatory)

For each added or modified **symbol** in the diff — function, method, component, class, type, schema, config key, exported constant — use the codebase search primitive (not a shell invocation) to find its usages, and the file-read primitive for the calling sites. See SKILL.md Step 5.4 for the specific tools in this runtime:

- **Functions/methods**: direct callers. Read the calling code to understand the contract.
- **Components** (`.vue`, `.tsx`, `.jsx`, `.svelte`): parent templates that mount them. Identify how many instances can be mounted concurrently (look for `v-for`, `.map()`, iteration). What visibility pattern controls them (`v-if` removes, `v-show` toggles, neither)? What props gate per-instance state (`active`, `visible`, `disabled`)?
- **Types/schemas**: consumers of the shape. Does the change break a field consumers rely on?
- **Config keys**: readers of the key. Is there a default path that silently changes?

Read the surrounding code, not just the diff. The most dangerous bugs live at call boundaries — where a symbol's assumptions about its caller or callee are violated by the change.

#### Failure-mode audit on existing callees with new callers (mandatory)

Symbol tracing above follows the forward direction: for each new or modified symbol, who calls it? This subsection enforces the **reverse direction** for a common blind spot: *when the diff introduces a new caller of an unchanged function, lifecycle, or handler, the callee itself is safe by the "unchanged code" heuristic — but the callee's **existing** failure-handling logic may have been written for the **old** caller's semantic mode and be silently wrong for the new one.*

**The bug class**: callee is fine in isolation, the diff is fine in isolation, the bug lives in the cross-product. Specifically, pre-existing `try/catch`, exit handlers, retry loops, timeout fallbacks, error boundaries, auto-clear logic, and silent-defaulting code paths were designed under **caller A's** expectations. When the diff adds **caller B** with different expectations (explicit user intent vs. implicit reopen, strict mode vs. best-effort, transactional vs. advisory), those failure paths may silently downgrade, overwrite, retry, or suppress in ways that are wrong for B.

For every unchanged function, lifecycle, or handler that the diff reaches through a new caller chain, do NOT stop at "the callee is unchanged, so it's safe". Instead:

1. **Read the callee's existing failure-handling paths**. Every `catch`, every exit-code branch, every fallback-to-default, every `.catch(() => {})`, every `unwrap_or_default`, every auto-retry and auto-clear. These are the callee's **implicit contract with its callers**.
2. **For each failure path, identify which caller's semantics it was written for**. Often this is visible from comments, commit history, or simply the fact that only one caller type existed when the path was written.
3. **Check whether the new caller's semantics are compatible with that failure path**. If the callee's failure handling is "silently clear and retry", is the new caller a best-effort path (where clear-and-retry is correct) or an explicit user-intent path (where silent clear is a trust violation)?
4. **If the failure path is wrong for the new caller**, the fix is *not* "add another guard alongside" — see the state machine integration heuristic in the calibration rules. The fix is usually to gate the failure path on a mode flag that the caller sets, or to split the callee into two variants, or to move the failure handling up into the caller chain so each caller owns its own policy.

**Specific patterns to watch for**:

- **Auto-clear / auto-retry** designed for "implicit/best-effort" callers (system reopens a session on boot, framework retries a transient network call) but the new caller is **explicit user intent** (user picks this session, user explicitly triggers this action). Silent clear-and-retry of an explicit choice is a silent integrity violation — the user's decision is erased without surfacing.
- **Default fallbacks** (home directory for empty cwd, anonymous for missing user, latest version for missing selector) that were tolerable when the field couldn't be empty in the old caller paths but the new caller path admits empty. The fallback was never wrong because the precondition always held; the new caller breaks the precondition silently.
- **Error suppression** (`.catch(() => {})`, `unwrap_or_default`, `_ = method()`, `result || defaultValue`) that was acceptable noise from caller A (telemetry, UI refresh, cache warmer) but represents real signal loss for caller B (user-triggered save, irreversible command, audit log write).
- **Timeout-driven retry loops** that assumed an idempotent caller; the new caller is non-idempotent (credit card charge, token mint, side-effectful RPC).

**The test question**: *"was this failure-handling code written before the new caller existed?"* If yes, treat it as a foreign contract — read it with the assumption that it may be wrong for the new caller, not the other way around. The burden of proof is on the diff to show compatibility, not on the reviewer to find incompatibility.

**Attachment convention**: each `failure_modes_considered` entry lives under the `symbols_inspected` entry for **the new caller chain's terminal symbol** — the added or modified symbol closest to the new caller's leaf, which the diff actually touched. Do NOT attach under the unchanged callee, because that would force `symbols_inspected` to grow entries for symbols the diff did not modify, which directly conflicts with the existing rule that `symbols_inspected` may only list diff-touched symbols (see the `symbols_inspected` rules in `output-schema.md`). The callee is already reachable from the entry via the `consumers` array, so a reader of the trace log finds the audit adjacent to the callee reference without a separate entry.

Each entry should name the callee location, the new caller chain, the existing failure mode, and whether it is compatible with the new caller's semantics. See `output-schema.md` for the schema.

The output **must** record every symbol you inspected in the Trace Log — skipping this step is skipping the review.

### Mutated record fanout (mandatory)

Symbol tracing follows the **call graph**; this step follows the **data model**. They catch different bugs.

For every record (struct, class, store entity, DB row, message payload) whose fields are **written** in the diff, enumerate *all sibling fields on that same record* — not just the ones the diff touches. For each sibling, ask:

- Does this mutation leave the sibling pointing at a **stale reference** from a prior owning entity? (e.g. `planFilePath` still pointing at the old session after a re-link that clears `agentSessionId`)
- Does the sibling carry **data from a prior lifecycle** that the new write implicitly invalidates? (e.g. `errorMessage` from a crashed session not cleared when the tab is re-attached to a fresh one)
- Does the sibling hold an **invariant the write silently broke**? (e.g. `lastSyncTimestamp > createdAt` when `createdAt` is rewritten but the sync timestamp is not)

A write that looks local ("I'm just updating `agentSessionId`") often has a silent co-dependency with sibling fields that were never updated — because the previous owner wrote them and nothing in the new write path clears them. This is the **writer-side fanout** bug. The reader-side dual is: *who reads the sibling field?* If any reader exists, stale siblings produce wrong behavior at the read site, not the write site, which is why grep-by-symbol misses them.

**What counts as a sibling** (record-shape rules):

- **Flat records**: straightforward — every other field at the same level as the written field is a sibling.
- **Nested records**: enumerate only the **immediate siblings at the same level** as the written field. Do not recurse. If a nested sub-record (e.g., `Tab.ptyState.exitCode`) has its own writes in the diff, treat that sub-record as a **separate entry** in `mutated_records_inspected` with its own siblings list. Recursive enumeration from the root bloats the trace log past usefulness; entry-per-written-level keeps it finite.
- **Inherited records**: treat parent and child as a **single combined record**. Parent class fields count as siblings of child class fields — the runtime object has both. List the most-derived type name as the `record`, but include inherited fields in `siblings_considered`.
- **Discriminated unions / sum types / tagged enums**: enumerate only the fields of the **variant actually written** by the diff. Other variants' fields are not siblings (they don't exist on the runtime object at that moment). If the diff writes the discriminator itself (e.g., changes `kind` from `'agent'` to `'terminal'`), the fields of the *outgoing* variant become stale and must all be cleared — list them as siblings of the discriminator write.

Record your findings in the Trace Log field `mutated_records_inspected` — one entry per record, listing every sibling field you considered. If you inspect a record and conclude no sibling is at risk, list it anyway with the note `no siblings at risk`. An empty `mutated_records_inspected` means you skipped this step.

### Reader-path fanout (mandatory for preserved siblings)

Mutated record fanout above answers the writer-side question: *for the fields this diff writes, what sibling fields are left inconsistent?* This subsection answers the **reader-side dual**: *for the sibling fields this diff preserves, does the diff open a new code path that reaches an existing reader?*

**The bug class**: writer preserves a field (correctly, per the fanout audit), reader is unchanged, but the diff introduces a new path between writer and reader that breaks an invariant neither side is aware of. Writer-side fanout sees only siblings of the written fields and misses this. Symbol tracing sees only direct callers of new symbols and also misses it — the reader is already being called, just from a new path. The bug lives in the cross-product of "preserved state" + "new writer→reader path" + "unchanged reader's assumptions about which paths could reach it".

For every sibling field you classified as **preserved** in the mutated record fanout, run this additional check:

1. **Find readers** of the preserved field via the codebase search primitive — templates, selectors, computed properties, destructured reads, direct property access.
2. For each reader, **ask what paths currently reach it**. The reader's correctness depends on invariants that hold along the paths that existed before the diff.
3. **Identify new paths the diff creates to this reader**. A new caller of an existing function, a new lifecycle trigger (restart, remount, refresh, respawn), a new action that ends in the same reducer, a new route that hits the same handler — each is a new path.
4. **For each new path, check whether the reader's invariants still hold**. The old write path may have guaranteed "this field is never empty when the reader runs" or "this field is always fresh" or "this field's content came from the same source as that field's content". Does the new path preserve the same guarantee?
5. **If any invariant does not transfer**, the preserved field is not safe — the fix is either to re-enforce the invariant at the new path's entry (compute/validate before calling into the reader), or to change the reader to tolerate the new path's weaker guarantee.

**The test**: *"could the reader be called with a state of the preserved field that was unreachable before this diff?"* If yes, you have a reader-path fanout bug even though the field itself was correctly preserved.

**Common new-path signatures to look for**:

- **Restart / remount / respawn lifecycle**: the old path was "mount with fresh cwd from create flow"; the new path is "remount with preserved cwd from restart flow". If the preserved cwd could be empty from an older code path, remount now re-reads empty.
- **Restore-from-persistence**: the old path wrote fresh values; the new path restores from disk where older versions may have written different (or missing) values.
- **Explicit user intent reaching implicit reopen code**: the old caller was "system reopens session on boot"; the new caller is "user picks a session from a list". Both end at the same reducer but carry different semantic contracts.
- **Retry / backoff loop**: the original call path validated inputs; the new retry path reuses the validated result but runs under state that may have drifted since validation.

Record findings under the record's `mutated_records_inspected` entry as `new_reader_paths: [...]` — each entry should name the preserved field, the new writer path, the reader location, and the invariant that does not transfer. See `output-schema.md` for the schema.

### Runtime contract verification (cross-boundary types)

Type signatures describe shape at compile time. They do **not** describe the runtime format of data that crosses a trust or language boundary. The list below enumerates the common boundaries — **it is non-exhaustive**. The underlying invariant is: *any point where compile-time types do not bind the runtime format is a contract boundary*. If you're unsure whether a boundary qualifies, apply the one-sentence test: *"could the producer be replaced with a different implementation that writes a different-but-type-compatible format without a type error?"* If yes, it's a contract boundary.

Common cases:

- **IPC** (Electron main↔renderer, Tauri commands, postMessage, shared memory)
- **API response** (REST/GraphQL/gRPC/WebSocket payloads deserialized into typed objects)
- **Database row** (ORM result → typed model)
- **Queue/message payload** (job args, event bus messages, pub/sub)
- **Cross-language FFI** (Rust↔TS, Python↔C, Swift bridging)
- **Environment variables and CLI args** (parsed as typed strings; `NODE_ENV: string` is not a discriminated union)
- **Configuration files** (YAML/TOML/JSON parsed into typed objects; the file schema is the producer, not the consumer type)
- **Browser persistence** (localStorage, IndexedDB, cookies — the previous session's write is the producer)
- **File formats** (anything serialized to disk and read back — the writer version may predate the reader schema)
- **WebAssembly imports/exports, GPU buffers, shared memory segments** (native binary formats with no type enforcement at the boundary)

...do **not** trust the consumer-side type signature alone. Read the **producer** of the payload in its native source — the Rust handler, the API writer, the migration that defined the column, the job enqueuer, the config file the ops team maintains — and verify the runtime shape matches the consumer's assumption. A field typed `createdAt: string` may be written as ISO 8601, RFC 2822, epoch-millis, or epoch-seconds — the type tells you nothing about which, and tests written against the consumer's mental model will pass while production fails.

**Tests-as-proof does not count.** If the test file mocks the payload using the consumer's assumption, the test is tautological — it proves only that the consumer agrees with itself. Real verification requires reading the producer. A test that mocks `createdAt: "2026-04-01"` has never exercised an epoch-millis producer. Treat such tests as *absent* coverage for the contract boundary.

When you verify a contract, record the producer location in the finding body (e.g., "producer: `src-tauri/src/reader.rs:115` writes `mtime.as_millis().to_string()` — consumer assumes ISO").

### LLM/agent output validation (mandatory when diff consumes model output)

Runtime contract verification above covers boundaries where a schema-bearing producer (Rust handler, API writer, migration) emits data whose runtime format you can read. This subsection covers a harder case: boundaries where the producer is an **LLM, agent, ML pipeline, rule engine, or other non-deterministic automation** whose output shape is not bound by any schema at runtime. The producer is "whatever the model decided to emit this time", and no amount of reading the producer source tells you what will arrive next invocation.

**The bug class**: the model emits a shape that satisfies the consumer's type signature but violates a semantic invariant the consumer assumed without validation. `status: string` tells you nothing about which statuses are legal landing states for this workflow; "my prompt asks for backlog-only" is not a contract, it is a hope. The failure mode is silent (no type error, no crash, just a wrong value written and trusted) and probabilistic (the same prompt passes some of the time), which defeats both compile-time and test-time detection strategies.

**Mandatory checks for every field the diff consumes from model/agent output**:

1. **Enum / status / state-machine fields** — is the field validated against a closed set of allowed values before being written to persistent state? Is that allowed set the same as the set of values the user's workflow expects? If the spec says "new items land in backlog" but the code accepts any valid column, the bug exists regardless of whether the model has ever emitted a non-backlog value in practice. Prompt-side constraints are not consumer-side validation.
2. **Source-identifying metadata** (file paths, hashes, IDs, URLs, line ranges) — is the value cross-checked against the source material it claims to derive from? If the diff stores `source_file: "README.md"` and `source_hash: "abc..."` emitted by the model, is there any path where the hash is accepted from the model directly without the consumer recomputing it against the actual file bytes?
3. **Extracted entities** (tags, labels, names, dates, references) — is the extracted value re-grepped / re-parsed against the source, or accepted verbatim because "the model extracted it"?
4. **Confidence-adjacent fields** — if the model emits a confidence score or similar self-assessment, is it used as a gating signal (reject below threshold, require human review) or just recorded for later display? Recording without gating is the common failure mode.

**The review question**: *"which fields does the diff consume from the model, and which of those are validated on the consumer side before any user-visible or persistence-relevant write?"* Any unvalidated field reaching such a write is a finding. Severity starts at **high** per the LLM-compliance severity floor in the calibration rules.

**Tests do not substitute for validation.** If the test suite mocks the model's output using realistic-looking values, it proves only that the consumer agrees with itself about realistic shapes — it has never exercised a surprising emission. Test-trace such findings as `no-test` unless a test specifically asserts the consumer rejects shape-valid but semantically invalid input.

Record the validation audit findings in the finding body (name the consumer file:line and the specific field that is unvalidated), and include one line per consumed field in `scenarios_considered`: `llm-field: <field_name> — <validated|unvalidated|partial>`.

### Acceptance criteria crosswalk (when spec with explicit ACs is present)

Pre-review context (SKILL.md Step 5.2) reads any accompanying spec, RFC, task file, or other document **as a source of architectural constraints** — so findings do not falsely contradict intentional decisions. This subsection flips the direction: if the spec lists **explicit acceptance criteria**, the review also uses the spec to **audit the implementation**.

**The bug class**: the spec says "X must happen", the implementation is silent about X, the reviewer reads the spec for context and moves on to diff-level concerns. The AC is never cross-checked against code, so a missing enforcement slips through. Symbol tracing does not catch this because the missing code has no symbol; record fanout does not catch it because the fields that would have implemented the AC are absent.

**When to apply**: the spec must have **structured** acceptance criteria — explicit "must" statements, a checklist of criteria, a numbered list of requirements, a "definition of done". Narrative-only specs and informal docs are out of scope — the crosswalk requires line-level ACs to be tractable. If the spec is prose-only, note this as a `scenarios_considered` line and skip the crosswalk.

**Mandatory walk**: for every AC in the spec, write down the specific file:line that implements it. Three failure modes to flag as findings:

1. **No corresponding implementation** — the AC is listed but no code enforces it. Finding severity is at least **high** by default; the spec was explicit and the implementation is silently non-compliant.
2. **Ambiguous mapping** — code is partially related but cannot be verified to enforce the AC without inference. Finding severity depends on what the AC protects (user-visible state → high; internal invariant → medium).
3. **Contradicting implementation** — code is present but does the opposite of what the AC requires. Always ship-blocker; the spec and the code disagree and the spec is the intended contract.

The crosswalk is **per-AC, not per-file**. Walk the spec's AC list top to bottom; for each one, write the proof-of-implementation in `trace_log.acceptance_criteria_crosswalk`. If you cannot write it, that is the finding.

**Severity reasoning**: an unenforced AC that could silently produce wrong output starts at **high** because (a) the spec was explicit, (b) the implementation is silent about diverging, (c) no test is likely to catch it — tests cover code that exists, not code that is missing. The user has no visible signal that the AC was dropped.

**Test-trace for missing-AC findings**: the canonical answer is almost always `no-test: the AC has no corresponding code, so no test file could exist to cover it`. Use this verbatim form; it is not a grounding gap but the nature of the bug class — the finding is *about* the absence.

Record the full crosswalk (every AC, whether passed or failed) in `trace_log.acceptance_criteria_crosswalk`. See `output-schema.md` for the field format. Recording the passed ACs too is deliberate: it makes the "I checked" claim falsifiable and helps downstream tools diff crosswalks across iterations.

---

## Severity definitions

- **critical** — data loss, security breach, crash, or corruption affecting all users. Ship-blocking.
- **high** — incorrect behavior under realistic conditions (not just theoretical). Likely to cause user-visible bugs or silent data issues. Ship-blocking.
- **medium** — edge case failure, degraded behavior under stress, or a missing guard that could escalate if surrounding code changes.
- **low** — minor robustness gap or latent risk. Unlikely to bite today but worth noting.

### Block test (apply before assigning severity)

- "Would I refuse to merge this PR until this is fixed?" → **critical** or **high**
- "Would I merge with a follow-up issue filed?" → **medium** (use sparingly)
- "Would I leave a comment but not block?" → **low**

Medium is the most-abused tier. If you cannot honestly say "this warrants a follow-up issue", drop it to low. **Do not use medium as a hedge for uncertainty.** Uncertainty belongs in the confidence score, not the severity.

---

## Finding bar

Report only material findings. No style feedback, no naming feedback, no low-value cleanup, no speculative concerns without evidence.

Every finding must answer:
1. What can go wrong?
2. Why is this code path vulnerable?
3. What is the likely impact?
4. What concrete change would reduce the risk?

---

## Grounding rules

Be aggressive, but stay grounded. Every finding must be defensible from the provided repository context. Do not invent files, lines, code paths, incidents, attack chains, or runtime behavior you cannot support. If a conclusion depends on an inference, state that explicitly in the finding body and keep the confidence honest.

---

## Project-rule citation (when project rules are loaded)

SKILL.md Step 5.2b loads project-local review rule files (`.claude/rules/*.md`, `code-review.md`, `CONTRIBUTING.md`, etc.). This section defines what citation means and when it is required.

**The value proposition.** A finding that cites a specific project rule is materially more useful than one that does not:
- "Violates `.claude/rules/no-patches.md` → *Enforce at the writer, not downstream*" lands as rule-enforcement a project author can act on.
- "This is a patch on a patch, consider refactoring" reads as the reviewer's opinion — no weight behind it, easy to dismiss.

Citation turns the reviewer from opinion-source to rule-enforcer when the rule exists. When no applicable rule exists, no citation — there is no requirement to manufacture one.

**When to cite.** For each finding generated in Step 6, ask: *"does the load-bearing reason this is a finding correspond to something the loaded project rule corpus already articulates?"* If yes, cite it. If no, do not cite — opportunistic citation only.

**Citation shape** (per finding, optional `findings[].rule_refs` array — empty array or absent field both mean "no applicable rule"):

1. `source` — the path to the rule file as loaded in Step 5.2b (must match one of the entries in `trace_log.project_rules_loaded`; citing a file that was not loaded is a grounding failure).
2. `rule` — a short identifier. Prefer a markdown heading name from the rule file ("Enforce at the writer, not downstream"). If the rule file has no headings, use a one-sentence paraphrase that appears near the quoted text.
3. `quote` — **a verbatim 1–2 line string lifted literally from the rule file**. Consumers can and should check this: the quote must be findable in the file via string search (allowing for normalization of leading/trailing whitespace only). Paraphrased "quotes" are forbidden.

**The verbatim-quote requirement is the anti-hallucination gate.** LLMs, when asked to cite, frequently produce plausible-sounding rule text that is not actually in the file. This is the single highest-risk failure mode of citation. Enforcement:

- If you cannot find a 1–2 line literal quote that supports the finding's framing, **you cannot cite that rule**. Either rewrite the finding to drop the citation, or cite a different rule whose actual text does support the claim, or emit no citation at all.
- If you are tempted to "tighten" or "clean up" the rule's wording when quoting, stop — tightened wording is paraphrased wording. Copy the rule's exact language even if it is awkwardly phrased.
- Do not compose composite quotes from multiple non-adjacent passages. A quote must be a contiguous 1–2 line span from the rule file.

**Multi-rule citation.** A single finding may cite more than one rule if they independently reinforce the framing (e.g., `no-patches.md` + `single-source-of-truth.md` both apply to the same guard-cluster finding). Cap at 3 citations per finding — beyond that, the finding is overloaded and should be split or the citations pruned to the strongest ones.

**Interaction with Claim verification pass.** Citations are subject to the same verification discipline as the rest of the finding body. A citation whose `quote` does not appear in the cited file is an over-claim and must be dropped or fixed. Log such drops in `findings_dropped_in_verification` with reason `no-evidence-after-trace`.

**Interaction with CLAUDE.md / architectural decisions.** Step 5.2's "Pre-review context" and Step 5.2b's "Project review rules" can point at the same document in some projects. The rule of thumb is:
- If a finding is being **dropped or marked `spec-accepted`** because the CLAUDE.md / spec authorizes the behavior, that is Step 5.2's use — no citation needed on the finding (which no longer exists).
- If a finding is being **emitted and wants to cite the rule as authorization for the framing**, that is Step 5.2b's use — `rule_refs` carries the citation.

The same document can serve both purposes; the distinction is directional (drop vs cite), not structural.

---

## Calibration rules

**Ship-blocker question (answer before listing findings):**
"Is there a single issue that would make me refuse to merge this PR?"

- If **yes** → that issue is your top finding. Verdict is `block`. Everything else is secondary.
- If **no** but there are material issues → verdict is `needs-attention`.
- If the change looks safe → verdict is `approve` and return no findings. Say so directly.

The answer to this question is not just for your own calibration — it must be **recorded in the output**. `output-schema.md` defines two required fields inside `trace_log`: `ship_blocker_answer` (`"yes"` or `"no"`) and `ship_blocker_reasoning` (one sentence explaining the answer). These fields are mandatory whenever the verdict is `block` or `needs-attention`. Omitting them is the same class of enforcement gap as an empty Trace Log — the review is invalid without them.

**Hard cap on findings:**
- Diffs under 500 lines: **maximum 3 findings**
- Diffs under 1500 lines: **maximum 5 findings**
- Split reviews (large diff grouped by module): **maximum 3 findings per group**

If you have more candidates after the final_check pass, drop the weakest until you fit the cap. One strong finding is more valuable than three weak ones. Padding with low-severity findings dilutes a high-severity one.

**Threshold discipline (authoritative).** Every deterministic threshold in this methodology — the Step 3b patch-chain scan values (`N` commits, 50% cluster ratio, 4-commit window, 3-of-5 hotspot), the chain-closing comparison (`resolved ≥ still_open + new_drift_introduced`), and the chain-of-rejections resurface count (`≥ 2`) — is an acknowledged uncalibrated starting value, not methodology: no corpus of past reviews exists to calibrate against. Values were chosen strict enough not to fire on typical 1–2 hotfix sequences, permissive enough to fire on a genuine 3-round iteration. When real usage shows a threshold over- or under-firing, revise it in a plugin patch bump and record the empirical basis in the plan doc revision log — thresholds evolve independently of the rules that read them.

**Re-read before reporting (working-tree and branch modes only):** Before reporting a finding, read the actual file on disk at that location. If the issue is already fixed in the current working tree, drop it. The diff shows what changed; the file on disk shows the current state — trust the file.

In **PR mode**, do NOT re-read from disk. The reviewer's local HEAD is almost never the PR head commit — re-reading checks unrelated state and produces false positives or false negatives. Trust the diff captured via `gh pr diff` as the source of truth for what the PR contains.

**Prefer state machine integration over additive guards.** When your recommendation starts looking like "add another check for X" on top of existing checks, **stop** and ask: "Is the state machine fragmented?" Multiple sites checking the same higher-level concept (active pane, logged-in user, feature flag, permission, visibility) is usually a signal that the source of truth is scattered across leaves instead of consolidated at the root. The better fix is often **consolidation** — a single `canInteract` prop drilled from the parent, a single `usePermission()` hook, a single middleware in the chain, a single state machine transition — not another guard added alongside existing ones.

**Co-vary vs cross-cut heuristic**: if the conditions `A && B && C` that you're about to stack all reflect aspects of the **same higher-level state** (e.g., `activeTab && !tabTransitioning && !tabHiding` — all aspects of "is this tab currently interactive?"), recommend integrating with that state rather than duplicating its facets at the leaf. If the conditions are **genuinely orthogonal** (e.g., `isAuthenticated && !rateLimited && hasQuota` — auth, throttling, and quota are separate concerns), additive guards can be correct.

**The test**: co-varying conditions move together under normal state transitions; cross-cutting conditions move independently. When in doubt, ask "if I fix the root state machine, do some of these guards become redundant?" If yes, it's fragmentation — recommend consolidation.

**Lift hierarchy for defensive recommendations.** When your recommendation is "add a check" or "add a guard", evaluate four alternatives in order and prefer the earliest that is viable:

1. **Type lift** — encode the invariant in the type system (newtype, discriminated union, narrower type, non-nullable field, phantom type, branded type). The compiler or runtime-type validator enforces it; no ad-hoc runtime cost; cannot be bypassed by a caller that forgets the check. This is the strongest lift because the invariant becomes a shape the type system recognizes, not a rule the next author must remember.
2. **Writer lift** — collapse to a single writer that guarantees the invariant by construction. Multiple writers maintaining the same invariant is a duplication smell; consolidate to one and the invariant becomes true at the single write site. Every added guard on the read side is evidence that the write side has too many entry points.
3. **Ordering lift** — fix the bootstrap, lifecycle, or initialization sequence so the invariant holds by construction. Guards that check "is X initialized" or "is Y ready" often mean X or Y is constructed in the wrong order — moving construction earlier in the lifecycle removes the check. Ordering lifts are often invisible in diff review because they change *when* code runs, not *what* code runs.
4. **Guard** — runtime check, last resort. Legitimate when lifts 1–3 are genuinely infeasible (e.g., crossing a trust boundary where the producer cannot be changed) or at system boundaries where untrusted data enters (user input, external API, environment). A guard is the correct answer for input validation at the edge; it is usually the wrong answer for internal invariants that the system itself should maintain.

If your recommendation is a guard, one of two conditions must hold — state which in the finding body and populate `lift_considered` accordingly:

- **(a) All three lifts non-viable.** Name the specific constraint that blocks each of type, writer, and ordering lift: the producer is not modifiable, the call graph makes a single writer impossible, the ordering change would require framework-level plumbing the diff cannot touch, etc. "The codebase already uses guards here" is not a rejection — it is a symptom of skipped lifts in prior rounds. Each lift entry in `lift_considered` must set `viable: false` with a concrete rationale.
- **(b) System boundary.** The guard lives at a trust boundary (user input, external API, untrusted data, process-boundary IPC, FFI) where a lift-inside-the-system does not bind the runtime shape coming from outside. In this case, `lift_considered` may still populate some or all lifts as viable — the boundary is the justification, not the infeasibility of lifts. Name the boundary explicitly in the finding body.

If any lift is `viable: true` in `lift_considered` AND no system boundary is named in the body, the recommendation is **not a guard** — it is whichever lift was most viable. Emitting a guard recommendation under those conditions is a schema-methodology inconsistency (see the `lift_considered` rule in `output-schema.md`). This is the condition that makes the lift hierarchy enforceable at the schema level, not just an aspiration.

**Interaction with state machine integration.** The lift hierarchy is strictly narrower than "Prefer state machine integration over additive guards" above. Both rules point toward consolidation, but the lift hierarchy specifies *how* to consolidate and *when runtime guards are acceptable*. When both rules apply, apply state machine integration first (are the conditions co-varying or cross-cutting?), then the lift hierarchy (if cross-cutting and a guard seems warranted, what is the earliest viable lift?). The two rules do not conflict: state machine integration tells you which guards to collapse; the lift hierarchy tells you what replaces them.

**Generalization test (apply to every finding before writing it up).** Before finalizing a finding, challenge your own framing: *"Am I describing the most extreme example of this bug, or the underlying invariant that's violated?"* The dangerous failure mode is reporting a symptom on a narrow code path (e.g., "crashed tab case") when the real defect is a broken invariant that triggers on the common path too (e.g., "any session switch with a live process"). The narrow framing understates severity, hides the blast radius, and makes the fix look smaller than it is.

**How to widen the frame**: take the preconditions in your current scenario and ask which ones are *load-bearing*. If you can drop a precondition and the bug still fires, the dropped precondition was incidental — rewrite the finding around the remaining minimal set. Iterate until every precondition is essential. The finding you end up with is the root invariant; the original scenario is just one instance of it. Report the root.

**When the narrow framing is correct**: if dropping any precondition genuinely makes the bug disappear, your original frame *was* the invariant — keep it, but note in the body that you checked for generalization.

**The test corrects framing, not severity.** Widening the frame is about accurately describing the invariant, not earning more severity points. A correctly widened finding may still be `low` — some invariants are broken but the blast radius stays small. After widening, re-run the block test on the new finding from scratch rather than carrying severity over from the narrow version. The severity-inflation guard in `output-schema.md` still applies: if your ship-blocker answer is `yes` but no individual finding scores critical or high on the honest severity definitions, the problem is the verdict, not the finding.

**Severity floor for user-irrecoverable findings.** (Plugin v2.0.0, from saha test #4.) A finding hits a **`high` minimum severity floor** when recovering from the bug's user impact requires any of these five out-of-band actions:

1. Restarting the application (force-quit + relaunch)
2. Restarting the OS / device
3. Reinstalling the app
4. Manually clearing app data, cache, or config files
5. Factory reset / fresh install

The floor applies **regardless of frequency** — a bug that fires once per session but strands the user until an app restart is high+, because recovery cost, not fire rate, is what puts it above the noise threshold. Severity dampening (the carries-over rule in `output-schema.md`) cannot demote a finding below this floor. When the floor applies, the finding body must name the recovery cost explicitly: e.g., `Recovery cost: user must restart the app to recover (no in-process recovery path).` The floor is a calibration rule applied during severity assignment, not a structured tag — the `Recovery cost:` body line is the audit artifact. Apply the floor only when one of the five triggers is concretely named in that line; recoveries that are arguable (in-app re-import vs out-of-band) fall back to standard calibration. The floor is a *minimum*, not a cap — go higher when impact is critical. Origin (devil-review demoting a "can't recover until app restart" bug below promotion threshold while a cross-model reviewer flagged it no-ship): [`../../docs/design-rationale.md`](../../docs/design-rationale.md) §Severity floor for user-irrecoverable findings.

**Severity floor for LLM-compliance-dependent invariants.** When a correctness invariant depends on external non-deterministic output (LLM, agent, ML model, rule engine, user-supplied automation) being well-formed, raise the severity floor. The reasoning is that the failure mode is silent (no type error, no crash) and probabilistic (the same prompt passes some of the time), which defeats both compile-time and test-time detection:

- If an unvalidated model-emitted field hits **persistent state or user-visible action** (UI update, DB write, message emission, irreversible operation, workflow transition), the finding is at least **high**. Do not grade it down because "the model usually emits the right shape" — usually-correct is exactly the failure mode.
- The floor drops to **medium** only if the consumer applies a partial validation that catches the common cases, OR the field is purely internal and never escapes the session.
- The floor drops to **low** only if no realistic bad emission can propagate — strict validation runs before any side-effecting path reads the field, and the validator is tested against adversarial inputs.

This is a *floor*, not a ceiling. Blast radius, user trust impact, and data permanence still push severity up (e.g. an unvalidated model field that drives a payment, a deploy, or a user-facing confirmation is critical, not high). But no LLM-compliance-dependent finding starts below high without a defensible reason named in the finding body — cite the file:line of the downstream validator, or the specific scope that prevents escape.

**The test**: *"could a surprising model emission — shape-valid but semantically wrong — corrupt state the user trusts or takes action on?"* If yes, start at high. If no, justify medium with the specific downstream validation that catches it, and name the file:line where validation happens.

**Interaction with "medium is the most-abused tier"**: this floor raises findings *up*, not down. It never promotes a legitimately-low finding to medium, and it does not license inflating uncertain findings to high as a hedge. Confidence still belongs in the confidence score, not the severity. What this rule changes is the **starting point** for LLM-compliance cases — they default high and must be actively argued down, rather than defaulting medium and hoping the reviewer notices the silent-and-probabilistic failure mode.

---

## Claim verification pass (pre-emit)

After generating candidate findings and before emitting output, run one pass over the findings list that checks the reviewer's own claims. Over-claims — factual errors, unsupported reachability assertions, scope inflation — are the fastest way to lose credibility, and the symbol-trace / record-fanout / contract-verification steps do not catch them because those steps gather **evidence**, not **claims**. A finding can be grounded in real evidence and still contain a load-bearing sentence that the evidence does not support.

**The bug class** — patterns to watch for in your own emitted language:

- **Asymmetry error** — "only X when both A and B fail" when in fact X fires when either fails and the actual asymmetry is elsewhere. The reviewer saw a conditional and summarized its shape wrong.
- **Unsupported reachability** — "widens here because Y is reachable via Z" when no concrete path from an entry point to Y via Z can be named. The reviewer inferred reachability from a code pattern without tracing a path.
- **Scope inflation** — "all callers must handle this" when only one caller matters and the others are covered by an earlier guard. The reviewer generalized a specific case to a universal.
- **Counterfactual leak** — "without this fix, the system would X" when X depends on a code path the diff already blocks. The reviewer's claim is true only in a reality the diff has already ruled out.
- **Unverified external claim** — "library X strips trailing separators", "the runtime parses argv with quote-preserving semantics", "this protocol rejects null bytes" — claims about third-party libraries (including stdlib), OS runtimes, protocols, file formats, or shell semantics, asserted without naming a source. The reviewer reasoned from plausibility rather than from docs, source, runtime observation, or specification.

These claims are *plausible-looking* — they often appear in otherwise sound findings — but each is independently falsifiable. The pass checks them.

**For each candidate finding, run the six-step verification:**

1. **Restate the load-bearing claim** in one sentence, in the form `<subject> <verb> <condition>`. If the finding has multiple claims, pick the one whose falsification would drop the finding — that is the load-bearing one.
2. **Locate supporting evidence** in the diff or in code you read during tracing. Quote 1–3 lines with file:line. The quote must directly entail the claim — "implied by surrounding code" is not evidence, it is inference waiting to be checked.
3. **Check for falsifiers** — is there any visible branch, caller, or code path in the material you read that contradicts the claim? If you cannot rule out falsifiers because you did not read that code path, either (a) read it now and then decide, or (b) narrow the claim to the scope you did read.
4. **Reachability claims specifically** — if the finding body uses words like "widens", "narrows", "only fires when", "unreachable", "always", or "never", name one concrete call path from an entry point (user action, cron, boot, API route, event) to the claimed behavior. If no path can be written, reclassify the claim from behavioral to structural — e.g., "this branch is hard to reason about" instead of "this branch is unreachable" — or drop the finding.
5. **Evidence-cite external claims** — when the load-bearing claim references behavior of external systems (third-party libraries including stdlib, OS runtimes, protocols, file formats, shell semantics, hardware), name a specific source: a docs URL (via `WebFetch`), a source-code file:line from a clone or package read, a runtime observation (a `Bash` command and the observed output), or a published specification identifier. "Stdlib says so" or "the docs mention this" without a pointer does not qualify — the `source` must be specific enough that a downstream consumer can verify the claim independently. Findings whose load-bearing claim depends on an external assertion without an `evidence_source` must take one of three options: **(a)** gather evidence before emit and populate `findings[].evidence_sources`; **(b)** drop severity and confidence by one level each and tag the claim inline in the finding body as `evidence: unverified — <brief reason evidence was not gathered>` (kept as prose; consumers may grep for the string); or **(c)** drop the finding entirely — preferred when the reviewer cannot reasonably gather evidence (proprietary binary, no docs available, no runtime access). Option (b) is the compromise path; option (c) is the default for claims the reviewer cannot verify. Well-established universally-known behavior (e.g., "JSON does not allow trailing commas", "`==` in JavaScript coerces types") is not a cross-boundary claim — the evidence gate applies to version- or platform-dependent specifics, not to protocol-level consensus.
6. **Event-source upstream trace** (plugin v2.0.0, from saha test #4) — when the load-bearing claim involves a watched event, IPC message, websocket message, file-watcher event, or any other event-driven trigger, do not treat the event as a constant. Trace it:
   1. Identify the event identifier (channel name, event type, message kind) from the consumer code.
   2. Search the codebase for the emitter (Grep/Glob for the identifier).
   3. Read the emitter to verify under what conditions the event actually fires — including transient, error, and edge cases.
   4. If emitter behavior contradicts the finding's assumption (e.g., "this event fires on error" but the emitter also fires it on success), revise or drop the finding.
   5. If the emitter is not statically locatable in the codebase (runtime, OS, external service, dynamically-registered event name), fall back to step 5's evidence-gate semantics — cite runtime documentation or drop.

   Scope guard: this is consumer→emitter, not arbitrary upstream walking, and it exists to *understand* the finding, not to raise out-of-diff findings (those are `scope: pre-existing` per the usual rules). Record the traced emitter as a `producer:` style note in the finding body, same convention as runtime contract verification. Origin (reviewer stayed in the frontend diff slice while a cross-model reviewer traced the event source into the backend): [`../../docs/design-rationale.md`](../../docs/design-rationale.md) §Event-source upstream trace.

**Emit constraint.** Findings that fail the verification pass are either narrowed, reclassified, or dropped. A *narrowed* finding has a tighter claim with evidence that supports it and remains in `findings`. A *reclassified* finding may change `finding_type` (often from `correctness` to `design_debt`) or move to `considered_not_promoted` with an appropriate reason. A *dropped* finding is logged in `trace_log.findings_dropped_in_verification` with its original claim and a reason code. Step 5 failures use the reason code `unverified-external-claim` when the finding is dropped rather than rewritten with evidence.

**Observability requirement.** `trace_log.findings_dropped_in_verification` must be present on every non-error run. Empty array `[]` is valid and expected when every candidate finding survived the pass unchanged. Absence of the field is a grounding failure — it means the pass was skipped rather than run-and-clean. Each entry has two fields: `original_claim` (the load-bearing claim as first written) and `reason` (one of the reason codes in `output-schema.md`).

**Evidence, not counters.** (Schema v2.0 removed the `external_claims_verified` counter.) External-claim verification is evidenced by `findings[].evidence_sources` entries themselves — each names the claim, the source, and the verification timestamp, which is strictly more information than a count. Performative fetches that do not validate the claim against the fetched content still do not qualify as evidence.

**Interaction with Final check.** Final check (below) is a terse per-finding sanity checklist. Claim verification is the deeper discipline Final check depends on — a finding cannot be "grounded" (Final check bullet) if its load-bearing claim has not been verified. Run claim verification first; then run Final check.

**The reviewer-irony rule.** This pass checks **your own emitted language**, not the code. A reviewer that catches the user's factual errors but does not verify its own claims is an unreliable reviewer. This pass exists specifically to close that asymmetry. It is also why `narrowed-kept` is an accepted reason code: findings where the pass fired and the reviewer rewrote a claim to fit evidence are just as valuable as findings where a broken claim was dropped entirely — either way, the pass worked.

---

## Final check

Before finalizing, verify each finding is:
- adversarial rather than stylistic
- tied to a concrete code location (file + line range)
- plausible under a realistic failure scenario (not purely theoretical)
- actionable for an engineer fixing the issue
- framed at the **root invariant**, not a narrow symptomatic instance (apply the generalization test from calibration rules)
- **claim-verified** — load-bearing claims have passed the Claim verification pass (section above); over-claims were narrowed, reclassified, or dropped with the drop logged in `findings_dropped_in_verification`
- **citation-verified** — if `rule_refs` is populated on the finding, every `quote` appears verbatim in the cited rule file (string-findable, modulo leading/trailing whitespace). Paraphrased "quotes" are schema-invalid. Empty `rule_refs` is always valid.
- grounded by **test-trace** — you can answer "why didn't existing tests catch this?" per the subsection below
- NOT already fixed in the current file on disk (re-read to confirm)
- NOT an intentional decision documented in CLAUDE.md or an active spec

### Test-trace (mandatory per-finding)

For every finding you are about to report, locate the test files that cover the affected code path and answer one question in a single sentence: **"Why didn't existing tests catch this?"**

The answer must start with one of the three literal codes below, followed by `: ` and a grounded one-sentence explanation. This canonical form (`<code>: <explanation>`) is enforced by `output-schema.md` so downstream consumers can discriminate on the code prefix.

1. **`no-test`** — no test file covers the affected path. State where you looked. Example: `"no-test: no tests under src/__tests__/linkTabToAgentSession*"`.
2. **`mock-bypass`** — a test exists but mocks the dependency that actually fails, bypassing the failure path. Name the mock and the test location. Example: `"mock-bypass: LinkSessionDialog.spec.ts:42 mocks createdAt as ISO, bypassing the epoch-millis producer"`.
3. **`missing-assertion`** — a test exists and exercises the path, but asserts only a subset of invariants. Name the test and the missing invariant. Example: `"missing-assertion: useSessionLink.test.ts:88 covers happy path but asserts nothing about planFilePath after link"`.

**If you cannot produce one of these three answers, your finding is either wrong or you did not read the test files.** Drop the finding or re-trace with the tests actually in hand. This is a validation gate, not paperwork: if a test truly covers the invariant you claim is violated, the finding is a false positive and belongs in `considered_not_promoted` with reason `test-covers-invariant`.

**Mocked tests do not count as coverage for contract-boundary bugs.** A test that mocks the exact value the bug produces is tautological — it proves only that the consumer agrees with itself. See the runtime contract verification step.

**Non-code diffs (docs, markdown, CSS-only, config-only, CHANGELOG edits).** Findings in files that are not covered by any test framework in this repository (documentation, static configuration, markdown, lockfiles) should almost never pass the adversarial framing at the ship-blocker question — a typo or phrasing choice in a README is not a ship-blocker. If a finding in a non-code file *does* pass ship-blocker (e.g., a CLAUDE.md architectural decision that contradicts itself, a CI config that will break the pipeline), use `test_coverage: {covered_by: null, why_missed: "no-test: non-code file, no test framework applicable"}`. This is the only case where "no-test" is self-justifying rather than a coverage gap. Do not use this escape hatch for diffs that *look* docs-heavy but touch code (e.g., a commit that edits both a README and a source file) — the source-file findings still need a real test-trace answer.

Record the answer in the finding's `test_coverage` field per `output-schema.md`. The field is mandatory on every reported finding.

---

Drop any finding that fails these checks. Apply the hard cap. Then produce output per `output-schema.md`.
