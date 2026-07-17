# Output Schema

Return your review in **two parts**: a human-readable markdown section, followed by a machine-readable JSON fence. Both sections must be present on every non-error run. Downstream tools consume the JSON; the markdown is for the reviewer reading the result.

## Pre-emit checklist

This file loads at SKILL.md Step 7 — after the hunt. Complete these before writing output (the hunt-side checklist in SKILL.md Step 6 must already be done):

- classify every finding on the axes — `finding_type`, `scope`, `reachability` — per their decision trees, and apply the LLM-compliance severity floor where it applies; when a prior review is loaded, add `prior_relation` on every finding, populate `trace_log.prior_review_summary`, and apply severity dampening to `carries-over` findings
- populate the conditional trace_log blocks whose triggers fired: `patch_chain_risk` with a non-empty `theme_assessment` whenever any Step 3b signal fired (regardless of the final `detected` value), `acceptance_criteria_crosswalk` when a spec with structured ACs loaded
- populate `lift_considered` on every finding whose recommendation is a runtime guard, OR name the system boundary in the finding body
- run rejection memory **Phase B** per §User rejection memory → Phase B execution spec (this file, below; per-candidate hash match; suppress-silently vs re-raise-with-`previously_rejected`; chain-of-rejections override with the severity carve-out)
- derive `verdict` (rules 0–4) and the `decision` block per §Severity axes and verdict derivation and §Decision derivation (this file, below)
- emit the observability `scenarios_considered` lines: `prior-review ingestion: <status>` and `rejection memory: <status>` on every non-error run, plus one `llm-field: <name> — <status>` line per consumed model-output field when the diff consumes model output
- **backstop**: verify every required field in the JSON rules below is present — a new required field added in a future schema version is caught by this bullet without a per-field checklist entry

---

## Emit-time rules

The sections below were relocated from `methodology.md` (v2 restructure, Item 1) — they classify findings that already exist and derive the verdict; they are not needed during the hunt.

## Scope classification (mandatory per-finding)

Every finding carries a `scope` tag that says where the problem lives relative to the diff being reviewed. Three values:

- **`in-diff`** — the problem is in code added, modified, or deleted by this diff. This is the default and covers the large majority of findings. A regression introduced by the diff, a new unchecked input, a newly-introduced race, a newly-broken invariant — all `in-diff`.
- **`pre-existing`** — the problem exists in code the diff did not touch, but the reviewer discovered it while tracing callers/readers/consumers for the diff. The code was already broken before this PR. Still worth raising (the reviewer's eyes landed on it), but structurally separate from the change under review.
- **`future-work`** — a design improvement the reviewer is flagging as worth doing later. The code works today; the observation is about what would make the next change easier, or what would harden an area that has only been lucky so far. Not a bug, a suggestion.

**Why this field exists.** A finding that says "the diff is broken" and a finding that says "this unrelated code has been broken for months" are different signals for the author. Mixing them is the classic "reviewer overreach" antipattern: the PR author opens the review expecting "did I do this right" and gets "and also please fix these three unrelated things". Without a scope tag, the reviewer is either (a) rule-violating by raising pre-diff issues at all, or (b) under-informing by dropping them silently. Scope tagging resolves the tension: pre-existing findings are allowed but explicitly labeled, so the author can triage them separately from the ship decision.

**Classification decision tree (first matching rule wins):**

1. Does the finding point at a line that appears in the diff's `+` lines (added) or context-overlap with `-` lines (modified context)? → `in-diff`.
2. Is the finding a structural observation about something the diff *introduced* (a new pattern, a new invariant that is now at risk, a new call chain) even if you cite a line outside the diff's `+` markers? → `in-diff`. The diff is causally responsible for the risk even if the physical line is elsewhere.
3. Is the finding a concrete bug or correctness issue in code the diff did not cause, did not modify, and does not depend on? → `pre-existing`.
4. Is the finding a suggestion for a future improvement that does not describe a bug that exists today? → `future-work`.

**Default classification.** `in-diff` is the default. If you cannot clearly justify `pre-existing` or `future-work`, the classification is `in-diff`. Use the body of the finding to name why it is `pre-existing` ("discovered while tracing consumers of `X`") or `future-work` ("not a bug today; becomes one when feature Y lands") when you assign those values.

**Verdict interaction.** Only `scope: in-diff` findings drive verdict escalation. The full verdict rules — rules 0–4 filtered on `scope == "in-diff"` AND `reachability == "reachable"` — live in §Severity axes and verdict derivation (this file, below). A review with only `pre-existing` or `future-work` findings lands at `verdict: approve` because the diff itself is safe to ship; the scope-tagged findings surface unrelated issues transparently without dragging the verdict down.

**Hard cap interaction.** All three scopes count toward the findings hard cap (3 under 500 lines / 5 under 1500 / 3 per split group). Without this rule, a reviewer could pad with `pre-existing` findings to drown out a single `in-diff` finding. The cap forces prioritization across scopes: if you have room for 3 findings and one is a critical in-diff bug, the other two slots should usually go to the next two highest-priority in-diff findings, not to pre-existing observations — unless a pre-existing finding is itself severe enough to warrant the slot.

**Backward compatibility.** Findings without a `scope` field (pre-v1.10 snapshots) are treated as `in-diff` by default. See §Severity axes and verdict derivation → Compatibility property (this file, below) for the replay invariants.

**Anti-pattern to avoid.** Using `future-work` as a way to avoid hard calls. "The diff has a subtle correctness issue but I'm marking it `future-work` so the review approves" is a calibration failure — if the diff is broken today, the scope is `in-diff`, severity is real, and the verdict is `block` or `needs-attention`. `future-work` requires a **concrete next-step that the diff does not need**, not a vague "consider improving this later".

---

## Reachability classification (mandatory per-finding)

Every finding carries a `reachability` tag orthogonal to `severity`, `confidence`, and `scope`. It answers the question "how likely is this bug to fire in practice?" — a dimension that is structurally separate from "how bad is it when it fires" (`severity`) and from "how sure is the reviewer the bug exists at all" (`confidence`). Three values:

- **`reachable`** — the bug fires under normal usage on at least one code path the reviewer can name. The finding body must include a concrete path: "triggered by user clicking X", "fires on any PTY spawn", "any API request with empty body", "cron tick at :00". A reachable finding is a bug that will hit a user without any unusual conditions.
- **`hypothetical`** — the bug would fire *if* the preconditions held, but the reviewer cannot currently name a code path that produces those conditions. Often derived from reasoning-from-types ("the type allows null so a null would crash") or reasoning-from-patterns ("this looks like a TOCTOU, but I cannot point at a caller that races") rather than reasoning-from-paths. Real enough to surface, not real enough to claim it fires.
- **`requires-specific-config`** — the bug fires only under a specific configuration, environment, feature flag, or platform the reviewer has observed or can document. Stronger than `hypothetical` (the config exists and is named in the body) but weaker than `reachable` (the config is not on the main path). Examples: "only when `FEATURE_X` env var is set", "only on Windows under MSVCRT argv parsing", "only when the user has opted into experimental API v2".

**Why this field exists.** `confidence` is the reviewer's epistemic uncertainty about whether the finding is *correct*. `reachability` is a structural property of the code path. A reachable finding can have low confidence (reviewer is not sure their reading of the code is right); a hypothetical finding can have high confidence (reviewer is sure this WOULD be a bug if reached — they just cannot name a reaching path). Conflating the two loses information: a reader cannot distinguish "high-confidence bug that fires hourly" from "high-confidence theoretical bug that has never fired and may never fire". Saha test #3 surfaced the concrete confusion — a `confidence: 0.7` hypothetical Windows-specific trailing-backslash finding read as equal-weight with a `confidence: 0.85` async listener race on the main user flow, because confidence alone collapsed two orthogonal dimensions.

**Classification decision tree (first matching rule wins):**

1. Can you name a concrete call path from an entry point (user action, cron, boot, API route, event handler, deploy hook) to the claimed bug behavior? → `reachable`. Record the path in the finding body.
2. Can you name the specific config, environment variable, feature flag, platform, or opt-in state that would make the bug reachable? → `requires-specific-config`. Name the specific thing in the body.
3. Neither of the above — the bug is inferred from types, schemas, or general code-shape reasoning without a traced path or named config? → `hypothetical`.

**Bias rule.** When uncertain, classify as `hypothetical` rather than `reachable`. Promoting to `requires-specific-config` requires naming the specific config in the body; promoting to `reachable` requires naming a concrete path. "It probably fires somewhere" does not clear the bar for either — it is the canonical `hypothetical` finding.

**Default classification.** `reachable` is the default for payloads that lack the field (pre-v1.13 snapshots). See §Severity axes and verdict derivation → Compatibility property (this file, below) for the replay invariants.

**Verdict interaction.** Only `reachability: reachable` findings drive verdict escalation. The full verdict rules — rules 0–4 filtered on `scope == "in-diff"` AND `reachability == "reachable"` — live in §Severity axes and verdict derivation (this file, below). A review whose only findings are `hypothetical` or `requires-specific-config` lands at `verdict: approve` because the reachable failure surface is clean; the non-driving findings emit transparently for the author to consider.

**Hard cap interaction.** All three reachability levels count toward the hard cap (same rule as scope). A reviewer cannot pad with hypothetical findings to drown out a reachable one — the cap forces prioritization, and when it fires the weakest findings drop regardless of reachability level.

**Interaction with severity.** Reachability is *not* a severity modifier. A reachable bug is not automatically more severe than a hypothetical one; it is just more urgent. Severity reflects impact when the bug fires; reachability reflects likelihood of firing. Do not silently drop severity on hypothetical findings — the `hypothetical` tag itself is the calibration signal, and the verdict filter already prevents it from escalating inappropriately. Silent severity demotion on hypothetical findings is the exact failure mode the tag exists to prevent.

**Interaction with Claim verification pass.** The pass's step 4 (reachability claims specifically) now has a natural resolution: if step 4 cannot name a concrete call path, the finding is not dropped — it is classified as `hypothetical` or `requires-specific-config`. Drop is reserved for findings where even the hypothetical framing does not hold (no plausible precondition under which the bug would fire). This is a refinement, not a reversal, of step 4: the pre-v1.13 "reclassify or drop" guidance now has three paths instead of two, and the reclassify path is the common one.

**Anti-pattern to avoid.** Over-classifying as `reachable` to drive verdict up. This is the in-diff-overreach pattern from Item 9 applied to reachability: a reviewer tempted to escalate a weak finding can label it `reachable` with a vague "fires when someone calls this code" rather than `hypothetical`. Mitigation is the decision tree: step 1 requires naming a *concrete* call path from an entry point, not just "it is called from somewhere". If you cannot name the entry point, the classification is not `reachable`.

---

## User rejection memory (schema v1.14+)

A rejection is a user's explicit judgment that a prior finding is not actionable — it does not describe a real bug in their system, or the bug does not matter for their use case. Rejections are recorded via the `--reject <CSV>` inline flag on `/devil-review` (e.g. `/devil-review --reject 2,5` rejects the 2nd and 5th findings of the prior run **on the same review target** in the current session — the snapshot resolved by the SKILL.md Step 8 target slug, the same one Step 3b auto-detects — then runs a new review). The sidecar file lives at `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` with its own `schema_version` (currently `"1.1"`) independent of the main payload schema. The reviewer must consult this file on every run to avoid silently re-raising findings the user has already dismissed.

**Why this exists (observed).** Saha test #3 surfaced the following friction pattern on a real project: Round 1 of `/devil-review` flagged a Windows trailing-backslash edge case; the user assessed it as not-a-real-concern and skipped it; Round 2 re-flagged the same location with identical logic. The reviewer had no memory of the prior dismissal and re-raised the same claim. Combined with the severity-dampening rule from saha test #2, the silent re-raise creates a "patch-chain of rejected findings" — the reviewer persistently surfaces the same dismissed claims, and the user either re-dismisses each round (friction) or tunes the reviewer out entirely (worse — real signal gets lost in noise).

Rejection memory closes the loop: the reviewer consults the file, matches candidate findings against rejection hashes, and either suppresses silently or re-raises with justification.

**Scope of rejection memory.**

- **Session and target scoped.** Rejections live under `${CLAUDE_SESSION_ID}` — a new session starts fresh. Rationale: stale rejections from weeks ago should not mask findings that are now valid because surrounding code has changed. If long-term rejection memory becomes a need, that is a future feature; current scope matches the prior-review snapshot discipline.
- **Hash-keyed, not class-keyed.** Each rejection is a sha256 over a normalized `file:title` pair. A similar finding at a different file or with a substantively different title re-fires; a finding whose **line range drifted** between rounds does NOT re-fire (plugin v1.20.0 correction — the original `file:lines:title` hash re-fired the very finding the rejection was meant to suppress whenever intermediate fixes shifted line numbers). The hash normalization is specified authoritatively in `rejection-memory.md` substep 1 — trim + lowercase `file` + collapse `title` whitespace + `:`-joined + sha256; `lines` is recorded in the entry for audit but excluded from identity. Title case is preserved (proper-noun changes re-fire). The same normalization applies both when recording rejections via `--reject` and when matching candidate findings during review.
- **Target-agnostic within a session.** A rejection recorded after a working-tree review also applies when the same hash surfaces in a later branch-mode or PR-mode review within the session. The hash is the identity, not the review mode.
- **Explicit.** The reviewer cannot infer "user skipped this finding = rejection" from silence. A rejection exists only when the user explicitly passes `--reject <CSV>` on a `/devil-review` invocation. Absence of rejection is not consent.
- **No per-finding rationale in the inline flag.** `--reject 2,5` records both with `rationale: null`. Users who want rationales attached can edit `rejections.json` directly after recording. The flag syntax is kept simple because rationales attach to individual findings (different reasons for 2 vs 5) and CSV-with-rationales becomes awkward quickly. Manual edit is visible, auditable, and rare enough that adding a CLI syntax is not worth the surface-area cost.

**The suppress-vs-re-raise decision (reviewer-gated).**

When a candidate finding matches a rejection hash, the reviewer chooses between two paths:

- **Suppress silently** is the default. When the current analysis has produced no materially new evidence for the finding, drop it from `findings`. Do not log the suppressed finding in `findings_dropped_in_verification` (that field is for Claim-verification drops, a different category). Instead, add a `scenarios_considered` line `rejection suppressed: <hash first 12 chars> — <file>:<lines>` so the suppression is visible. The user sees that the reviewer respected their prior decision.
- **Re-raise with annotation** is exceptional. Re-raise when the current analysis has surfaced new evidence the prior rejection did not consider. Valid categories of new evidence:
  1. A new call path from an entry point to the claimed bug that was not traced in the prior round (often the case after Reachability step 1 newly traces a path — the finding may have been hypothetical last time and is now reachable).
  2. A new config, feature flag, or platform condition that changes the bug's reachability classification.
  3. A new sibling field or data-flow that makes the invariant more load-bearing than the prior round showed.
  4. A project-rule citation now applies (a rule file was added since the prior rejection).
  5. A new prior-review snapshot shows the bug now `carries-over` in a way that was not present before.

  When re-raising, populate `findings[].previously_rejected` with `{rejected_at, prior_rationale, new_evidence}`. `new_evidence` must be **one concrete sentence** describing the nameable difference — padding with "additional analysis surfaced" does not clear the bar. The finding body must **lead** with:

  > Previously rejected on `<rejected_at>` with rationale `<prior_rationale or "(none provided)">`. New evidence: `<new_evidence>`.

  Followed by the usual finding content. Severity and confidence carry from the current analysis; the rejection did not set severity, and the reviewer's current read may be higher or lower than the prior.

**Bias rule.** When uncertain whether new evidence rises to the re-raise bar, suppress. Rejection memory exists to respect the user's prior decision; silently re-raising on speculative "more thinking" defeats the purpose. Re-raise requires a nameable difference, not a vibe.

**Chain-of-rejections override (verdict rule 0 — highest precedence).**

When the count of findings emitted with `previously_rejected` populated (the *resurface count*) reaches **≥ 2** in a single review, the reviewer is persistently surfacing user-dismissed findings across a session. This is the automation-facing dual of the v1.11 chain-closing override: that rule handled "prior fixes worked, don't escalate to refactor"; this rule handles "user and reviewer disagree about whether these findings are real, stop iterating".

The override:
- `verdict: approve` regardless of standard rule derivation.
- `decision.action: ship` regardless of derivation.
- `decision.rationale: "chain-of-rejections pattern — <N> previously-rejected findings re-raised; stop iterating, ship as-is"` (or equivalent wording naming the resurface count).
- Re-raised findings still emit in `findings` for transparency — the override flips verdict/action, not the findings list.
- `decision.patch_chain_detected` is independent of this override and follows the v1.11 rule (based on `carries-over` findings plus file overlap with prior diff).

**Severity carve-out (plugin v1.20.0).** The override does NOT fire when any re-raised finding is simultaneously `finding_type: correctness`, severity `high` or `critical`, `scope: in-diff`, and `reachability: reachable`. Re-raise already requires concrete new evidence — a nameable new call path, config, or data-flow the prior rejection never considered. When that evidence establishes a ship-blocker-class reachable correctness bug, forcing `approve`/`ship` would turn the user's earlier dismissal against the current evidence: the rejection was made without the facts now on the table. Without the carve-out, the override structurally punished exactly the reviewer behavior the re-raise bar demands (suppressed rejections never count toward the resurface threshold — only evidence-backed re-raises do). With it, the override fires only on persistent disagreement about *materiality* — sub-high, non-correctness, non-in-diff, or non-reachable re-raises — which is precisely the friction pattern it exists to stop. When the carve-out blocks the override, rules 1-4 evaluate normally and re-raised findings count like any other finding.

This rule fires **before** verdict rules 1-4 in the standard precedence. When it fires, the other rules do not evaluate.

**Rationale.** Round N+1 of a review that keeps surfacing the same dismissed findings is not producing signal — it is producing friction. The user either ignores the output (worst case, loses real future signals), re-invokes `--reject` on every round (friction), or disengages from the plugin (plugin loses a user). The override is the plugin saying "I keep bringing these up and you keep saying they do not matter; I accept your judgment and stop." This is the opposite of the patch-chain override from v1.11, which said "stop iterating because fixes are not working" — here we stop iterating because fixes are not needed.

**Calibration note.** The `≥ 2` resurface threshold is an uncalibrated starting value per `methodology.md` §Calibration rules → Threshold discipline. The severity carve-out above is NOT a tunable threshold — it is part of the rule itself.

**Anti-pattern to avoid.** Using `--reject` as an ack-dismiss workflow for every mid-severity finding, then letting the reviewer silently accept everything forward. If you find yourself rejecting multiple findings per review as a matter of course, you are calibrating the plugin away from the defects it is meant to catch — that is a usage signal that either (a) the plugin's severity bar is misaligned for your project (a fix to make), or (b) your project has a real false-positive problem in this area (a calibration issue to surface). Rejection is for specific findings you have triaged, not a wholesale preference toggle.

**Interaction with prior-review snapshot + carries-over tagging.** Rejections and prior-review-carries-over are **orthogonal mechanisms**:
- A finding can be both `carries-over` (matches a prior review's finding) and match a rejection hash. When both: the rejection takes precedence — suppress-silently or re-raise-with-new-evidence per the rule above. If re-raised, the finding still gets `prior_relation.category: carries-over` alongside `previously_rejected` populated.
- Silent suppression does NOT count as a `resolved` prior finding. The rejection is a user judgment, not a reviewer judgment that the bug is gone. `prior_review_summary.resolved` counts only findings the reviewer judged no-longer-present in current state.
- Suppressed rejections do not appear in `findings` and therefore do not count toward the resurface count. Only **re-raised** rejections count toward the chain-of-rejections threshold — suppressing a rejection is respecting the user, not surfacing a finding, so it cannot contribute to a chain the user is fighting against.

### Phase B — Match & emit (execution spec, relocated from rejection-memory.md)

#### Substep 4 — Per-candidate-finding suppression check

For each candidate finding produced by the review (after Claim verification, before emit), compute the normalized sha256 hash per `rejection-memory.md` substep 1 over the candidate's `file` and `title`. Compare against the loaded (recomputed) rejection hashes.

#### Substep 5 — Suppression vs. re-raise

When a candidate finding's hash matches a rejection entry, the reviewer must decide between two paths — **this is a reviewer-gated judgment, not an automatic rule**:

- **Suppress silently (default).** When the current analysis produces no materially new evidence for the finding, drop it from `findings` without emitting `previously_rejected`. Do NOT log the suppressed finding in `findings_dropped_in_verification` (that field is for Claim-verification drops, not user-rejection drops). Instead, add a `scenarios_considered` line: `rejection suppressed: <hash first 12 chars> — <file>:<lines>`. This is the visibility signal that a rejection fired.
- **Re-raise with annotation (exceptional).** When the current analysis has produced **new evidence** the prior rejection did not consider — a new call path, a new config, a new sibling field that changes the picture, a new data-flow the reviewer just traced — the finding is re-raised. Populate `findings[].previously_rejected` on the re-raised finding with `{rejected_at, prior_rationale, new_evidence}` where `new_evidence` is a one-sentence description of **what is concretely different this round**. The finding body must lead with "Previously rejected on `<rejected_at>` with rationale `<prior_rationale or "(none provided)">`. New evidence: `<new_evidence>`." followed by the usual finding content. Severity and confidence are carried from the current analysis, NOT from the prior rejection — the rejection did not set severity, and the reviewer's current read of severity may be higher or lower than any prior assessment.

If the reviewer cannot articulate concrete new evidence in one sentence, the path is **suppress silently**. Padding with "additional analysis revealed" does not clear the re-raise bar. This is the calibration signal: re-raise requires a nameable difference.

#### Substep 6 — Chain-of-rejections verdict override

Compute the *resurface count*: number of findings emitted with `previously_rejected` populated on the current run. When the resurface count reaches **≥ 2** AND the severity carve-out does not apply, apply the override per §User rejection memory → Chain-of-rejections override (this file, above):

- **Severity carve-out check first (plugin v1.20.0):** the override does NOT fire when any re-raised finding is simultaneously `finding_type: correctness`, severity `high` or `critical`, `scope: in-diff`, and `reachability: reachable`. In that case rules 1-4 evaluate normally and re-raised findings count like any other finding. Rationale: see the authoritative section.
- `verdict: approve` and `decision.action: ship` — regardless of rules 1-4.
- `decision.rationale` names the resurface count and the chain-of-rejections pattern (exact text format specified in the override rule above).
- Re-raised findings still emit in `findings` — the override flips verdict/action, not the findings list.

Rules 1-4 do not evaluate when this override fires. Rationale, carve-out rationale, and threshold-calibration note: see the authoritative section.

## Severity axes and verdict derivation

**Severity axes and finding taxonomy.** (Schema v1.6 / plugin v1.9.0.) Findings now split across two axes: **correctness severity** and **design-debt severity**. Every finding carries a `finding_type` that places it into one of four categories; the two axis severities are derived as the max severity among findings of the relevant category. This separation exists so that "the code works but its structure is accumulating future-correctness risk" can be surfaced without being confused with "the code is wrong today" — two different signals that call for two different next-steps from the user.

**Finding type classification — decision tree (first matching rule wins):**

1. *"Does the code produce wrong output today under a realistic scenario I can name?"* → `correctness`. This is the existing review behavior — when in doubt, this is the category to pick. The default-to-correctness rule in the JSON rules below (v1.5 payloads replayed through v1.6 tooling) is what makes the v1.6 verdict rules produce identical results on pre-v1.6 inputs.
2. *"Does the code violate a CLAUDE.md architectural decision, active spec, or ratified design note?"* → `architectural_smell`. The code may be functionally correct; the violation is against the project's intentional choices. Findings in this category often need to be dropped via the `spec-accepted` path if the code's divergence is itself the intentional decision — check before reporting.
3. *"Does the code violate a domain checklist's best-practice item — e.g., a Pinia persistence boundary violation, a Tauri command ordering convention, a React hooks-of-hooks pattern — without being a correctness bug today?"* → `best_practice_violation`. These findings are fed by `domains/*.md` checklists, not by the generic attack surface. Severity tends to cap at `medium` unless the best-practice violation is an attack-surface enabler.
4. *"Is the code correct today but its structure is accumulating risk (guard cluster, multiple writers of same invariant, state fragmentation, patch-chain pattern, skipped lift per the Lift hierarchy in `methodology.md`)?"* → `design_debt`. This is the new category v1.6 introduces. The test question is "will this structure make the next bug in this area harder to fix, or make the next review harder to reason about?" If yes, design debt.

A single finding has exactly one `finding_type`. Findings that straddle categories should be split into separate findings, or classified into the category that matches the most severe consequence. Do not emit `null` or invent categories outside the four-value enum.

**Severity axis derivation:**

- `correctness_severity` = max severity among findings with `finding_type == "correctness"` **AND** `scope == "in-diff"` **AND** `reachability == "reachable"` (including the default cases — `finding_type` absent on replayed v1.5 payloads defaults to `correctness`, `scope` absent on pre-v1.10 payloads defaults to `in-diff`, `reachability` absent on pre-v1.13 payloads defaults to `reachable`). If no such findings exist, emit `"none"` or omit the field — both are valid per the schema.
- `design_debt_severity` = max severity among findings with `finding_type == "design_debt"` **AND** `scope == "in-diff"` **AND** `reachability == "reachable"`. Same emit-or-omit rule.
- `architectural_smell` and `best_practice_violation` findings do not roll up to a dedicated axis today. They still carry `findings[].severity` and still count toward the hard cap, but they do not drive the verdict derivation directly. If real usage surfaces a need for a dedicated axis for either category, add one in a future bump — do not retrofit the existing axes.
- **Scope filter rationale.** `pre-existing` and `future-work` findings are allowed to be reported but do not drive verdict escalation — per the "Scope classification" section above. A review whose only findings are pre-existing bugs in unrelated code lands at `verdict: approve` because the *diff itself* is safe to ship; the pre-existing issues are surfaced transparently so the author can file follow-ups without mixing them into the ship decision.
- **Reachability filter rationale.** `hypothetical` and `requires-specific-config` findings are allowed to be reported but do not drive verdict escalation — per the "Reachability classification" section above. A review whose only findings are hypothetical or config-specific lands at `verdict: approve` because the *reachable* failure surface is clean. The pattern is identical to the scope filter: transparency to the author, no silent drop-through to the verdict.

**Verdict derivation — five rules, strict precedence, evaluated top to bottom:**

Rule 0 is an override that fires before rules 1-4 and bypasses the standard filter. Rules 1-4 filter on `scope == "in-diff"` AND `reachability == "reachable"` (the defaults when `scope` is absent on pre-v1.10 payloads and `reachability` is absent on pre-v1.13 payloads). `pre-existing`/`future-work` and `hypothetical`/`requires-specific-config` findings are emitted for transparency but do not drive verdict — see the "Scope classification" and "Reachability classification" sections for the rationale.

0. **Chain-of-rejections override (schema v1.14+)** — at resurface count ≥ 2 (findings with `previously_rejected` populated), AND no re-raised finding clearing the severity carve-out (reachable in-diff correctness at high/critical — plugin v1.20.0), force `verdict: approve` and `decision.action: ship`; rules 1-4 do not evaluate. Full rule, carve-out rationale, calibration note, and `decision.rationale` text format: §User rejection memory → Chain-of-rejections override (same file, above).
1. **`block`** — override 0 does not fire, at least one finding with `finding_type == "correctness"` (or absent, treated as correctness) AND `scope == "in-diff"` (or absent, treated as in-diff) AND `reachability == "reachable"` (or absent, treated as reachable) AND severity `critical` or `high`, AND `ship_blocker_answer == "yes"`. Identical to the v1.5 rule on pre-v1.10 payloads and to the v1.12 rule on pre-v1.13 payloads; legacy payloads flow through unchanged because all three defaults (correctness + in-diff + reachable) preserve the original filter.
2. **`needs-attention`** — override 0 does not fire, rule 1 does not apply, at least one `in-diff` + `reachable` finding of material severity exists, `ship_blocker_answer == "no"`. The reviewer judges the issues are real but fixable in place — keep iterating.
3. **`refactor-recommended`** — override 0 does not fire, rule 1 does not apply, AND `design_debt_severity` (computed from `in-diff` + `reachable` findings only) is `high` or `critical`, AND either (a) a patch-chain signal fires (plugin v1.10.0 feature) OR (b) the count of `in-diff` + `reachable` `design_debt` findings is strictly greater than the count of `in-diff` + `reachable` `correctness` findings in this review, AND (c) the chain is NOT closing — `prior_review_summary` is absent OR `resolved < still_open + new_drift_introduced` (schema v1.11 feature — see "Verdict rule 3 clause (c) — chain-closing override" in the Patch-chain detection section). Clause (c) prevents `refactor-recommended` from firing when iteration is actually making things better. Semantic: *"there may be correctness issues, but fixing them in place will not address the real problem; step back and restructure."* `ship_blocker_answer == "no"` — by definition this is not a correctness ship-blocker.
4. **`approve`** — zero findings, or all findings are `pre-existing`/`future-work` or `hypothetical`/`requires-specific-config`, or none of override 0 / rule 1 / rule 2 / rule 3 apply. A review with only non-verdict-driving findings lands here: the diff ships, orthogonal issues are surfaced for the author to triage separately.

**Compatibility property.** Any v1.5-era payload re-run under v1.6+ rules produces the same verdict, and any v1.9-era payload re-run under v1.10 rules produces the same verdict:

- v1.5 findings have no `finding_type` → default-to-correctness → rule 1 behaves as the v1.5 `block` rule.
- v1.5 payloads have no `design_debt_severity` → absent treated as `"none"` → rule 3 clause (a) and (b) both unreachable without v1.6 inputs → rule 3 never fires.
- v1.9-and-earlier findings have no `scope` → default-to-in-diff → the scope filter is a no-op on legacy payloads, preserving verdict calculation identically. A v1.9 review that would have emitted `block` still emits `block` under v1.10 rules.
- v1.10-and-earlier payloads have no `prior_review_summary` → clause (c) of rule 3 evaluates `prior_review_summary` as absent → "chain is closing" condition is false → clause (c) does not block a `refactor-recommended` that was already going to fire. Legacy payloads that previously emitted `refactor-recommended` continue to emit it.
- v1.12-and-earlier findings have no `reachability` → default-to-reachable → the reachability filter is a no-op on legacy payloads, preserving verdict calculation identically. A v1.12 review that would have emitted `block` still emits `block` under v1.13 rules; the new filter only changes outcomes when reviewers actively classify a finding as `hypothetical` or `requires-specific-config`, which legacy payloads never do.
- v1.13-and-earlier payloads have no `findings[].previously_rejected` → resurface count is 0 on replay → override 0 never fires → rules 1-4 evaluate exactly as before. The new override only changes outcomes when the current run genuinely re-raises ≥2 rejections, which requires the v1.18.0 plugin to have loaded a `rejections.json` file and chosen to re-raise entries from it. Legacy payloads cannot satisfy these preconditions.
- Rules 2 and 4 reduce exactly to the v1.5 `needs-attention` and `approve` rules respectively.

This property is what keeps every minor bump a genuine minor bump per the repo's semver discipline, not a major one. Do not add rules that break it without bumping to a major version.

**Override discipline.** The verdict derivation is a guideline. When you believe the rules produce the wrong verdict for a specific review (e.g., a single high-severity correctness finding is actually a test-only artifact that doesn't reach production, or a patch-chain signal fires on legitimate unrelated hotfixes), override it — but name the override reason in `trace_log.ship_blocker_reasoning` or add a scenario line explaining the deviation. Do not override silently; an override without a call-out looks to downstream consumers like a bug.

### Patch-chain detection

(Schema v1.7 / plugin v1.10.0.) This rule operationalizes a specific failure mode of iterative review: when the same diff is reviewed N+1 times, findings drift from "organic bugs the diff introduced" to "artifacts of guards the *prior* rounds introduced". Each new round of review sees the guards added by the previous round and raises a finding about the edge case those guards did not cover — and then the next round adds another guard and the cycle continues. The correct next step after round 2 or 3 is not another guard; it is a structural refactor that collapses the guard cluster into a single invariant enforced by type, writer, or ordering (see the Lift hierarchy in `methodology.md`).

The detection is deterministic (git log scan, prior-review overlap check — all in SKILL.md Step 3b), but the **interpretation is reviewer-gated**. A file that legitimately receives three independent hotfixes for three unrelated bugs will trip the same deterministic signals as a genuine patch chain, and for that file `refactor-recommended` would be wrong. The theme-vs-root guard in SKILL.md Step 3b is the gate: *"do the prior defensive commits address the same root cause, or different root causes on the same file set?"*

- **Same root** → real patch chain. Emit `patch_chain_risk.detected: true`. Satisfies clause (a) of verdict derivation rule 3 (`refactor-recommended`). Prefer refactor over further guard iteration even if current findings are only medium severity.
- **Different roots** → coincidence cluster. Emit `patch_chain_risk.detected: false` with a theme_assessment explaining why. Do not let the signal drive the verdict.

**How this interacts with the lift hierarchy.** The lift hierarchy (`methodology.md` §Calibration rules) governs *individual recommendations*: when recommending a guard, evaluate type / writer / ordering lifts first. Patch-chain detection governs *the overall verdict*: when multiple rounds of guard recommendations have already landed in the codebase, the correct response is structural refactor even if the current round's individual findings all pass the lift-hierarchy check in isolation. The two rules reinforce each other — the lift hierarchy tries to prevent the patch chain from forming in the first place; patch-chain detection flags it once it has formed across rounds.

**What prior-review auto-detection adds.** Every run auto-writes its output (Step 8) to a session-scoped, target-scoped path. Every subsequent run on the same target in the same session auto-reads that snapshot (Step 3b, no flag required) and uses it for the `prior-review-overlap` signal. This gives direct evidence that the review is iterating on the same diff. The signal fires even when the git log alone is ambiguous (e.g., prior rounds' changes were amended into a single commit, so `fix:` prefixes never accumulated). Prior-review overlap is a stronger signal than git log prefixes because it shows the *reviewer* has been circling the same surface, not just that git history has. When both signals fire, the case for refactor is overwhelming. Session scoping prevents stale snapshots from prior Claude Code sessions from contaminating today's review.

**Scope: single-step, single-session.** Each run reads only the immediately prior run's snapshot — Step 8 overwrites the session-and-target-scoped file on every run. Longer chains are caught round-by-round because `prior-review-overlap` fires on each iteration; the refactor decision depends on "I keep flagging the same locations," not on a cumulative round counter. A new Claude Code session ID starts with a clean slate, so multi-day snapshots cannot falsely fire on today's unrelated work — and git log signals (fix-prefix cluster, same-file hotspot) remain session-independent, compensating for the lost cross-session overlap signal when the patch chain spans sessions.

**Prior-review is review context, not review truth.** The earlier reviewer saw an earlier diff; you see this one. The prior review's findings are *evidence that this surface has been scrutinized before*, not architectural decisions. Re-check each prior finding against the current state — some may have been correctly fixed, some may have been patched-over, some may still be present in modified form. The one thing you cannot do is defer to the prior review's severity or verdict on any given item; per the "Prior review output is not an architectural decision" rule in `methodology.md`'s operating stance, the current review rebuilds its own severity assignments from zero.

### Prior-relation classification (when prior review is loaded)

When Step 3b loads a prior-review snapshot, each current finding is classified against the prior review's findings. This makes the attribution machine-readable instead of prose-buried in `theme_assessment`. Emit per-finding `prior_relation.category` on every current finding, with **three** permitted values (first matching rule wins):

1. **`carries-over`** — the same invariant violation is present in both the prior state and the current state. The prior fix either did not address this finding or addressed it only partially. The file:line may have shifted (code moved, got renamed, got refactored around) but the underlying invariant being violated is the same.
2. **`new-drift-from-fix`** — the finding is at a location the prior fix **introduced or changed**. The previous round's fix was correct for what it addressed, but opened a new foot-gun elsewhere. This is the highest-signal category — it tells the author "your previous fix made the system worse in a new way" and is the most common source of genuine patch-chain dynamics.
3. **`pre-existing-orthogonal`** — the finding is at a location the prior review did not reach AND the prior fix did not touch. The bug existed in the code before the prior fix, but the prior reviewer just missed it. Not a patch-chain signal; different scrutiny surface.

**`resolved` is NOT a finding-level category.** A prior finding whose bug is no longer present in the current state is, by definition, not a current finding — it belongs in `trace_log.prior_review_summary.resolved` as a **count**, not in `findings[].prior_relation.category` as an emitted value. Schema v1.11 initially allowed `resolved` at finding-level; the plugin v1.15.1 correction narrows this to the three values above. Emission of `category: resolved` on a finding is a schema-methodology inconsistency downstream consumers are entitled to reject.

**When to classify.** For every current finding, when a prior review was loaded. When no prior review was loaded (fresh first run, or auto-detect returned `absent`), omit `prior_relation` entirely on all findings — there is no prior to relate to.

**Edge cases.** When a finding is genuinely ambiguous between `new-drift-from-fix` and `pre-existing-orthogonal` (e.g., the fix touched this file and a new issue appeared, but the issue logic predates the fix), default to `pre-existing-orthogonal`. This is the "when in doubt, drop severity" spirit — `new-drift-from-fix` is the more accusatory classification and should require concrete evidence that the prior fix caused the drift.

### Severity dampening for carries-over findings

When a finding's `prior_relation.category == "carries-over"`, apply the dampening rule before finalizing severity:

- **Hold at prior level** if the prior finding was at `high` or `critical` severity AND the current state still exhibits the same invariant violation. Do NOT silently demote a recurring high-severity finding to `medium` or `low` just because this is round N+1 — that pattern is what the saha test #2 caught, and it hides the real patch-chain dynamic behind noise.
- **Raise the bar** if the finding is a re-surface at equal-or-lower severity than the prior. Emit only if you can articulate in the finding body *why the prior fix did not address it*. If the answer is "the prior fix was unrelated to this aspect of the invariant", reclassify the finding from `carries-over` to `pre-existing-orthogonal` and drop severity one notch (not two) — the finding is real but is not evidence of a patch chain.
- **Do not silently downgrade.** A resurfaced finding either gets credit (same severity + `carries-over` tag, reviewer-visible) or gets reclassified/dropped with justification. Lower-severity re-flagging without credit is the saha-test-#2 antipattern this rule closes.

**Reviewer-irony interaction.** Severity dampening cannot raise severity above what the current state independently justifies — it only blocks silent demotion. If the current state's severity is genuinely lower than the prior (e.g., the fix addressed 80% of the blast radius and the remaining 20% is materially smaller), dampening may not apply — state this explicitly in the finding body and let severity reflect reality. The rule is "don't hide recurrence behind severity drift", not "never let severity drop".

### Decision derivation (top-level `decision` block)

In addition to `verdict`, every non-error emission carries a machine-readable `decision` block for downstream automation (CI gates, `/loop` auto-stop, PR decorators). This turns "is this review a signal to stop iterating and refactor" into a script-readable field, independent of the prose-facing `verdict`.

Structure:
```json
"decision": {
  "action": "iterate | stop-and-refactor | ship",
  "patch_chain_detected": <boolean>,
  "iteration_count": <integer>,
  "rationale": "<one-sentence why this action>"
}
```

**Field derivation:**

1. **`patch_chain_detected: true`** iff all four hold:
   - A prior review was loaded (Step 3b returned `loaded` status); AND
   - ≥1 current finding has `prior_relation.category == "carries-over"`; AND
   - The current diff touches at least one file that also appeared in the prior diff (files in common, not a disjoint set); AND
   - The current `in-diff` finding count is not materially lower than the prior (< 50% reduction is "not materially lower"). A diff that went from 4 findings to 1 is *closing the chain*; from 4 to 3 is *churning the chain*.
   
   Otherwise `patch_chain_detected: false`.

   **Distinction from `trace_log.patch_chain_risk.detected`.** These two fields measure *different things*:
   - `trace_log.patch_chain_risk.detected` (schema v1.7+) is the **git-log signal**, reviewer-gated by the theme-vs-root guard. It aggregates over commit history and can fire on the first-ever session reviewing a file with a long defensive-prefix history.
   - `decision.patch_chain_detected` (schema v1.11+) is the **session signal**, requiring a prior review snapshot and at least one `carries-over` finding. It cannot fire on a fresh session regardless of git history.
   
   Both signals can be present, absent, or one-but-not-the-other. Example: fresh first-run on a file with three historical `fix:` commits will emit `patch_chain_risk.detected: true` but `decision.patch_chain_detected: false`. This is correct — the git history flags the anti-pattern for the author; the session signal would only fire once the reviewer itself has started circling.

2. **`iteration_count`** = the count of times this session has reviewed this target. Derived from prior-review session metadata when available; defaults to `1` on a fresh run with no prior. If the prior review snapshot itself carried an `iteration_count`, increment that value by 1; otherwise if a prior exists but had no `iteration_count`, set to `2` (one past run + this run).

3. **`action`**:
   - `stop-and-refactor` iff `patch_chain_detected == true` AND `iteration_count ≥ 2`. The signal is strong enough that continuing to iterate is worse than stepping back. This is the machine-readable form of `verdict: refactor-recommended` — but note that `action` can fire `stop-and-refactor` even when `verdict` is `needs-attention`, if the patch-chain signal is loud enough.
   - `ship` iff `verdict == "approve"` AND (no prior loaded OR `prior_review_summary.resolved ≥ prior_review_summary.still_open + prior_review_summary.new_drift_introduced`). Chain-closing condition: the fix actually reduced the problem more than it introduced. Pure first-run approvals also ship.
   - `iterate` otherwise. Default action — there are findings to address but no structural step-back signal.

4. **`rationale`** — one sentence explaining why this action was chosen. For `stop-and-refactor`, name the patch-chain evidence. For `ship`, name the chain-closing evidence or the zero-findings state. For `iterate`, name the top outstanding in-diff finding.

**Interaction with `verdict`.** `verdict` stays prose-facing and uses the four-value enum (`block | needs-attention | refactor-recommended | approve`). `decision.action` is its three-value downstream companion. Consumers that already handle `verdict` continue to work; `decision` is additive for consumers that want automation hooks. In the common case the two agree:

- `verdict: block` + `action: iterate` (fix the blocker, come back)
- `verdict: needs-attention` + `action: iterate`
- `verdict: refactor-recommended` + `action: stop-and-refactor`
- `verdict: approve` + `action: ship`

Edge cases exist (e.g., `verdict: needs-attention` but `patch_chain_detected: true` at iteration 2 → `action: stop-and-refactor` even though verdict is "keep iterating"). When `verdict` and `action` disagree, `action` is the automation signal; reviewers reading the prose should treat the disagreement as a deliberate call-out that manual judgment matters here.

### Verdict rule 3 clause (c) — chain-closing override

Add a chain-closing condition to the `refactor-recommended` verdict rule (schema v1.11): *Do NOT escalate to `refactor-recommended` — even when `design_debt_severity` is high/critical and patch-chain signals fire — when `prior_review_summary.resolved ≥ prior_review_summary.still_open + prior_review_summary.new_drift_introduced`.* The chain is closing: the fix resolved more prior findings than it left open or introduced. Escalating to `refactor-recommended` at that point would be noise; the structural-refactor recommendation fires when iteration is making things worse, not when iteration is making things better.

Emit `verdict: needs-attention` (if any in-diff finding remains) or `approve` (if none) in the chain-closing case, and name the chain-closing evidence in `trace_log.ship_blocker_reasoning` or in `decision.rationale`. This operationalizes the dampening the reviewer performed manually in saha test #2, where Round 2 correctly concluded "prior findings resolved, new findings introduced by fix or pre-existing — not a patch chain" and dampened away from `refactor-recommended`.

**Threshold rationale**: see `methodology.md` §Calibration rules → Threshold discipline — the thresholds here are acknowledged uncalibrated starting values, revisable in a plugin patch bump on real-usage evidence.

---

## Part 1 — Markdown section

```
# Devil Review

Target: <"working tree diff" | "branch diff against <ref>" | "PR #<n>">
Scope: <N files, M lines changed>  [or: "split review (N files across G groups)"]
Focus: <user's focus text, if provided>
Verdict: <block | needs-attention | refactor-recommended | approve>
Decision: <iterate | stop-and-refactor | ship>  (iteration <N>; patch_chain_detected=<true|false>)
  Rationale: <one sentence>

<1-2 sentence ship/no-ship assessment — terse, not neutral>

## Trace Log

Ship-blocker question: <yes | no>
Reasoning: <one sentence — why yes or why no>

Domain classification:
- Loaded: <comma-separated list of domains, or "none (generic attack surface only)">
- Considered but dropped: <comma-separated list with one-word reason, or "none">
- Notes: <one sentence on any ambiguous classification calls>

Project rules loaded:
- `<path/to/rule.md>` (<bytes> bytes)
- ...
(empty list "none" is valid when no rule file matched the Step 5.2b globs; omission is not)

Prior-review summary (present only when Step 3b loaded a prior):
- Total in prior: <N>
- Resolved: <N>
- Still open: <N>
- New drift introduced: <N>
- Pre-existing unrelated: <N>

Changed symbols inspected:
- `<symbol>` (<kind: function|component|type|schema|config>) → consumers: <file:line>, <file:line>
  - failure-mode audit: <`<callee>` at <file:line> — <existing failure mode> — compatible with <new caller>: yes|no — <rationale>>
  - failure-mode audit: <...>
- `<symbol>` → consumers: <file:line>
  - failure-mode audit: no new caller chains introduced
- ...

Mutated records inspected:
- `<record>` (<kind: struct|store-entity|db-row|ipc-payload|api-payload|queue-message>) → siblings: <field1>, <field2>, <field3>
  - new reader path: <preserved field `<name>` reached by new writer path `<A → B → C>` via reader at <file:line> — invariant `<X>` no longer holds>
  - new reader path: <...>
- `<record>` → siblings: <field1>, <field2> — note: no siblings at risk
- ...

Architectural decisions checked:
- <CLAUDE.md section, spec path, or "n/a">

Scenarios considered:
- <one-line adversarial scenario — what you mentally rendered>
- <another scenario>
- ...

Considered but not promoted:
- <observation> — reason: <out-of-scope | low-confidence | covered-by-finding-<N> | spec-accepted | test-covers-invariant>
- ...

Findings dropped in verification:
- <original claim as first written> — reason: <unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept | unverified-external-claim>
- ...
(empty list `none` is valid when every candidate finding survived the Claim verification pass unchanged — omission is not; per methodology.md)

External claims verified: <integer ≥0>
(counts verification actions — `0` is valid when no finding referenced external-system behavior; absence is a grounding failure)

Rejections loaded:
- `<hash first 12 chars>...` rejected <ISO-8601 timestamp>
- ...
(empty list `none` is valid when no `rejections.json` file exists for the session; absence of the field is a grounding failure — schema v1.14)

## Findings

### [severity] Title
- **File**: `path/to/file`
- **Lines**: L<start>-L<end>
- **Type**: <correctness | design_debt | best_practice_violation | architectural_smell>
- **Scope**: <in-diff | pre-existing | future-work>
- **Reachability**: <reachable | hypothetical | requires-specific-config>
- **Prior relation**: <carries-over | new-drift-from-fix | pre-existing-orthogonal>  (omit when no prior loaded; `resolved` is trace_log-only, not a finding-level value)
- **Confidence**: <0.0 to 1.0>

> Previously rejected on <ISO-8601> with rationale <rationale or "(none provided)">. New evidence: <one concrete sentence>.
(omit this blockquote preamble when the finding was NOT previously rejected — schema v1.14; when present, the JSON `findings[].previously_rejected` object must also be populated with matching fields)

<body — what can go wrong, why this code path is vulnerable, likely impact>

**Recommendation**: <concrete change to reduce risk>

**Rule citations** (optional, only when a loaded project rule applies):
- `<path/to/rule.md>` — *<rule identifier>*: "<verbatim 1–2 line quote from the rule file>"
- ...

**Evidence sources** (optional, only when the finding's load-bearing claim references external-system behavior):
- *<source_type>*: `<URL, file:line, command+output, or spec identifier>` — "<one-sentence claim the source validates>" (verified <ISO-8601 timestamp>)
- ...
(omit when no external claims; use body prose `evidence: unverified — <reason>` for option-(b) unverified tags per methodology)

**Test coverage**: <one of the three canonical forms>
- `no-test: <one-sentence explanation — where you looked>`
- `mock-bypass: <one-sentence explanation — which mock, which test file:line>`
- `missing-assertion: <one-sentence explanation — which test file:line, which invariant is missing>`

---

(repeat per finding, sorted by severity: critical > high > medium > low)

If no material findings: "No material findings. The change looks safe to ship."

## Next Steps
- <actionable next step>
- ...
```

### Recommendation field guidance

- **When the recommendation is a runtime guard, the body must name why type, writer, and ordering lifts were rejected** — per the **Lift hierarchy for defensive recommendations** rule in `methodology.md`. "The codebase already uses guards here" is not a rejection; name the specific constraint blocking each lift (producer not modifiable, call graph makes a single writer impossible, ordering change would require framework-level plumbing the diff cannot touch, etc.). This is prose discipline on the existing `recommendation` field, not a new schema field — downstream consumers see the same shape, just a more structured body when a guard is recommended.

### Trace Log rules (non-negotiable)

- **Ship-blocker question must be answered** whenever verdict is `block` or `needs-attention`. Both `ship_blocker_answer` and `ship_blocker_reasoning` (in the JSON) / both lines (in the markdown) are mandatory. An `approve` verdict may omit the ship-blocker lines — but if you include them, they must read `no`.
- **`domains_loaded` must be populated** on every non-error run. Empty array `[]` is valid only when no domain matched; in that case, add `"generic attack surface only — no domain matched"` as a scenario line. The value reflects what the orchestrator (SKILL.md Step 5) told you to load — not what you *wished* had loaded.
- **`domains_considered_dropped` must list any domain you weighed and rejected**, with a one-word reason (`not-matched`, `overlap`, `not-applicable`). If every candidate domain was loaded, leave the list empty `[]`. Drop-reasoning is auditable: the point is transparency, not padding.
- **`classification_notes` must always be a non-empty sentence.** Even for trivial calls, write one sentence explaining how classification was decided ("all files under `routes/` and `controllers/` — straightforward api.md load" is fine). `null` and empty string are invalid. The field exists to force you to *think* about classification, not to skip it.
- **`symbols_inspected` cannot be empty** on any review that produced findings. If you report a finding, you must have inspected at least one symbol's consumers to ground it.
- **`symbols_inspected` may be empty only** when the diff is pure additions with no touched pre-existing symbols (net-new isolated file) — and in that case, add `no pre-existing consumers — net-new code` as a scenario line.
- **`symbols_inspected[].failure_modes_considered` captures the callee failure-mode audit** from the "Failure-mode audit on existing callees with new callers" section in `methodology.md`. Populate it when the diff introduces a new caller chain that reaches an unchanged function, lifecycle, or handler whose existing failure-handling paths (auto-clear, auto-retry, default fallback, error suppression, timeout-driven retry) were written under the old caller's semantic assumptions. Each entry records the callee location, the new caller chain, the existing failure mode, and whether it is compatible with the new caller's semantics. **Attachment rule**: each entry attaches to the `symbols_inspected` entry for **the new caller chain's terminal symbol** — the added or modified symbol closest to the new caller's leaf. Do not attach under the unchanged callee; that would require adding `symbols_inspected` entries for symbols the diff did not touch, which violates the `symbols_inspected` non-emptiness rule ("may be empty only when the diff is pure additions with no touched pre-existing symbols"). Empty array `[]` is valid when the symbol has no new caller chains introduced by the diff — in that case, add a note to the symbol entry or a scenario line saying so. Skipping this nested field when new caller chains exist is the same class of grounding failure as an empty `symbols_inspected`.
- **`mutated_records_inspected` is required on every review that writes to a record.** Record tracing follows the data model, not the call graph — it catches stale-sibling-field bugs that symbol tracing misses. See the "Mutated record fanout" section in `methodology.md`. Each entry lists the record and every sibling field you considered, even those you concluded were safe (mark them `no siblings at risk`). Empty array `[]` is valid only when the diff contains no record writes at all — rare, and in that case add `no record writes in diff` as a scenario line.
- **`mutated_records_inspected[].new_reader_paths` captures the reader-path fanout audit** from the "Reader-path fanout" section in `methodology.md`. Populate it for each sibling field the diff preserves (does not write) when the diff also introduces a new writer→reader code path that reaches an existing reader of that field. Each entry records the preserved field, the new writer path, the reader location, and the invariant that no longer holds along the new path. Empty array `[]` is valid when no preserved siblings are reached by new writer paths. Do not confuse "field not written by the diff" with "field not at risk" — the reader-path fanout rule exists precisely because preserved fields can be reached through newly-introduced paths that break their implicit invariants.
- **Deletions count as changes.** If the diff removes a symbol, trace its former callers and list them in `symbols_inspected` with a `(deleted)` suffix on the symbol name.
- **One line per symbol, one line per scenario.** Do not prose-explain; the JSON block carries structured data for chain-consumers.
- If a domain checklist was loaded (e.g., `domains/ui.md`), list the domain under "Scenarios considered" as `domain: <name>` alongside concrete scenarios.
- **`considered_not_promoted` captures observations you noticed but decided not to report.** Use it when you see something during the trace — a smell, a secondary symptom, a speculative risk — that did not clear the finding bar. Each entry is one line with a reason from the fixed set: `out-of-scope`, `low-confidence`, `covered-by-finding-<N>` (where `<N>` is the 1-based index of the covering finding in the `findings` array — e.g. `covered-by-finding-2`), `spec-accepted`, or `test-covers-invariant` (a test you would expect to miss the bug actually asserts the invariant — finding is a false positive, record which test). The field is optional: empty list `[]` is valid, and you should not pad it to look thorough. Its purpose is the opposite — it exists so the reviewer can see *what you thought about and dropped*, so those observations are not silently lost and can be promoted manually if the user disagrees with your triage. If you used it to drop an observation because it was "just a symptom", check that the underlying invariant did not also escape your main findings list — see the generalization test in `methodology.md`.
- **`test_coverage` is required on every reported finding.** It carries the answer to "why didn't existing tests catch this?" per the test-trace rule in `methodology.md`. The field has two keys: `covered_by` (test file:line or `null`) and `why_missed`. `why_missed` must always follow the canonical form `<code>: <one-sentence explanation>` where `<code>` is exactly one of the three literals `no-test`, `mock-bypass`, or `missing-assertion`, followed by a colon, a space, and a one-sentence explanation grounded in a file/line. Examples: `"no-test: no tests under src/__tests__/linkTabToAgentSession*"`, `"mock-bypass: LinkSessionDialog.spec.ts:42 mocks createdAt as ISO, bypassing the epoch-millis producer"`, `"missing-assertion: useSessionLink.test.ts:88 covers happy path but asserts nothing about planFilePath"`. Free-form sentences without a leading code are invalid — the code prefix exists so downstream consumers can discriminate. If you cannot fill this field honestly, the finding is invalid — either re-read the tests or drop it to `considered_not_promoted` with reason `test-covers-invariant`. This is a grounding gate, not a documentation nicety.

---

## Part 2 — JSON fence

Emit immediately after the markdown section, in a fenced code block tagged `json`.

**Current schema version: `1.14`.** The version-by-version history (v1.0 → v1.14), compatibility properties across bumps, and legacy-payload handling rules (including the pre-v1.11 `decision`-block synthesis map and the plugin v1.15.1 enum-narrowing correction note) live in [`../../docs/schema-history.md`](../../docs/schema-history.md). This document describes only the current schema.

```json
{
  "schema_version": "1.14",
  "verdict": "block | needs-attention | refactor-recommended | approve",
  "decision": {
    "action": "iterate | stop-and-refactor | ship",
    "patch_chain_detected": false,
    "iteration_count": 1,
    "rationale": "<one-sentence why this action was chosen>"
  },
  "target": {
    "mode": "working-tree | branch | pr",
    "base_ref": "<ref or null>",
    "pr_number": "<number or null>"
  },
  "scope": {
    "files": 0,
    "lines_changed": 0,
    "split_groups": 0
  },
  "focus": "<user focus text or null>",
  "summary": "<1-2 sentence ship/no-ship assessment>",
  "correctness_severity": "critical | high | medium | low | none",
  "design_debt_severity": "critical | high | medium | low | none",
  "trace_log": {
    "ship_blocker_answer": "yes | no",
    "ship_blocker_reasoning": "<one sentence — why yes or why no>",
    "domains_loaded": ["<domain name>", "..."],
    "domains_considered_dropped": [
      { "domain": "<name>", "reason": "<one-word: not-matched | overlap | not-applicable>" }
    ],
    "classification_notes": "<one non-empty sentence explaining how domain classification was decided for this diff>",
    "symbols_inspected": [
      {
        "symbol": "<name>",
        "kind": "function | component | type | schema | config",
        "consumers": ["<path/to/caller>:<line>", "..."],
        "failure_modes_considered": [
          {
            "callee": "<callee symbol or lifecycle name>",
            "callee_file": "<path/to/callee>:<line-range>",
            "new_caller": "<new caller chain, e.g. 'applyResume → restartTab'>",
            "existing_failure_mode": "<one-sentence description of the callee's existing failure-handling path>",
            "compatible_with_new_caller": true,
            "rationale": "<one-sentence reason the existing failure mode is or is not compatible with the new caller's semantics>"
          }
        ]
      }
    ],
    "mutated_records_inspected": [
      {
        "record": "<name of struct, store entity, row, or payload>",
        "kind": "struct | store-entity | db-row | ipc-payload | api-payload | queue-message",
        "siblings_considered": ["<field1>", "<field2>", "..."],
        "new_reader_paths": [
          {
            "preserved_field": "<sibling field name>",
            "new_writer_path": "<new caller chain that now reaches this field's reader, e.g. 'applyResume → restartTab → TerminalPane.connectPty'>",
            "existing_reader": "<path/to/reader>:<line> — <one-sentence description of what the reader does with the field>",
            "invariant_broken": "<one-sentence description of the invariant that held along old paths but not the new one>"
          }
        ],
        "note": "<optional — e.g. 'no siblings at risk' or 'planFilePath stale after link'>"
      }
    ],
    "architectural_decisions_checked": ["<CLAUDE.md section ref>", "..."],
    "scenarios_considered": [
      "<one-line adversarial scenario>",
      "..."
    ],
    "considered_not_promoted": [
      {
        "observation": "<one-line description of what you noticed>",
        "reason": "out-of-scope | low-confidence | covered-by-finding-<N> | spec-accepted | test-covers-invariant",
        "design_alternative_considered": "<optional — one sentence naming the lift or structural change that would resolve the observation if it ever became a bug>",
        "tracked_as_debt": false
      }
    ],
    "acceptance_criteria_crosswalk": [
      {
        "ac": "<the acceptance criterion text, quoted verbatim from the spec>",
        "spec_location": "<path/to/spec:line or section heading>",
        "status": "implemented | ambiguous | missing | contradicted",
        "implementation": "<path/to/impl:line-range, or null if status is missing>",
        "notes": "<optional one-sentence rationale, especially for ambiguous or contradicted>"
      }
    ],
    "patch_chain_risk": {
      "detected": false,
      "signals_fired": ["fix-prefix-cluster | same-file-hotspot | prior-review-overlap", "..."],
      "chain_depth": 0,
      "prior_commits": ["<short-sha> <subject>", "..."],
      "prior_review_file": "<path or null>",
      "theme_assessment": "<one-sentence answer to: do prior defensive commits address the same root cause, or different roots on the same file set?>",
      "recommendation": "<one-sentence note on what the signal means for this review — e.g. 'prefer refactor over another guard iteration' or 'coincidence cluster on a legitimate hotfix-heavy file, not a patch chain'>"
    },
    "findings_dropped_in_verification": [
      {
        "original_claim": "<one sentence — the load-bearing claim as first written, before verification>",
        "reason": "unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept | unverified-external-claim"
      }
    ],
    "external_claims_verified": 0,
    "project_rules_loaded": [
      {
        "path": "<path/to/rule/file.md — must match a Step 5.2b glob result>",
        "bytes": 0
      }
    ],
    "prior_review_summary": {
      "total_in_prior": 0,
      "resolved": 0,
      "still_open": 0,
      "new_drift_introduced": 0,
      "pre_existing_unrelated": 0
    },
    "rejections_loaded": [
      {
        "hash": "<64-character lowercase sha256 hex — matches entries in .claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json>",
        "rejected_at": "<ISO-8601 timestamp from the rejection entry>"
      }
    ]
  },
  "findings": [
    {
      "severity": "critical | high | medium | low",
      "finding_type": "correctness | design_debt | best_practice_violation | architectural_smell",
      "scope": "in-diff | pre-existing | future-work",
      "reachability": "reachable | hypothetical | requires-specific-config",
      "title": "<short finding title>",
      "file": "<path/to/file>",
      "lines": "L<start>-L<end>",
      "confidence": 0.0,
      "what_can_go_wrong": "...",
      "why_vulnerable": "...",
      "impact": "...",
      "recommendation": "...",
      "lift_considered": {
        "type_lift": { "viable": false, "rationale": "<one-sentence constraint that blocks or enables this lift>" },
        "writer_lift": { "viable": false, "rationale": "<...>" },
        "ordering_lift": { "viable": true, "rationale": "<...>" }
      },
      "rule_refs": [
        {
          "source": "<path/to/project/rule/file.md — must match a path in trace_log.project_rules_loaded>",
          "rule": "<short identifier: heading name, numbered rule, or one-sentence paraphrase>",
          "quote": "<1–2 line string lifted verbatim from the rule file — consumers may string-search to verify>"
        }
      ],
      "prior_relation": {
        "category": "carries-over | new-drift-from-fix | pre-existing-orthogonal",
        "prior_finding_ref": "<prior finding title quoted verbatim, or null>"
      },
      "evidence_sources": [
        {
          "claim": "<one-sentence claim about external behavior>",
          "source_type": "docs-url | source-file | runtime-observation | specification",
          "source": "<URL, file:line, command+observed-output, or spec identifier — specific enough for independent verification>",
          "verified_at": "<ISO-8601 timestamp of verification>"
        }
      ],
      "previously_rejected": {
        "rejected_at": "<ISO-8601 timestamp from the matching rejection entry>",
        "prior_rationale": "<rejection rationale text from the rejection entry, or null if the rejection carried no rationale>",
        "new_evidence": "<one concrete sentence describing what is different this round that justifies re-raising — no padding, must be nameable>"
      },
      "test_coverage": {
        "covered_by": "<path/to/test:line or null>",
        "why_missed": "<code>: <one-sentence explanation>"
      }
    }
  ]
}
```

### JSON rules

- **`verdict`** is an enum: exactly one of `block`, `needs-attention`, `refactor-recommended`, `approve`. No other values. The fourth value `refactor-recommended` was added in schema v1.6 — it means "not a ship-blocker by correctness, but structural debt is high enough that iterating in place will make it worse; step back and restructure".
- **`decision`** is **unconditionally required** on every non-error run (schema v1.11+). Machine-readable automation signal that pairs with prose-facing `verdict`. Four fields:
  - `action` (enum, required): exactly one of `iterate | stop-and-refactor | ship`. Derivation rules live in §Decision derivation (this file, above).
  - `patch_chain_detected` (boolean, required): `true` iff all four hold — prior review loaded, ≥1 current finding has `prior_relation.category == "carries-over"`, current diff and prior diff share ≥1 file, and the current in-diff finding count is not materially lower than prior (< 50% reduction is "not materially lower").
  - `iteration_count` (integer, required, ≥1): count of times this session has reviewed this target. Defaults to `1` on a fresh run with no prior. When a prior snapshot exists and carries an `iteration_count`, increment by 1; otherwise set to `2` if prior exists without the field.
  - `rationale` (string, required): one sentence explaining why this action was chosen. Must be non-empty.
  Verdict ↔ decision.action agreement: typically `block`/`needs-attention` → `iterate`, `refactor-recommended` → `stop-and-refactor`, `approve` → `ship`. Disagreements are allowed and are the automation signal — e.g., `verdict: needs-attention` + `decision.action: stop-and-refactor` when `patch_chain_detected: true` at `iteration_count ≥ 2`. When they disagree, `decision.action` is the CI/automation signal and the disagreement should be called out in `rationale`.
- **`findings[].prior_relation`** is **conditionally required**: required on every finding when a prior review was loaded (Step 3b status `loaded`), omitted entirely on all findings when no prior was loaded (status `absent` or any `rejected-*` value). Two fields: `category` (enum, required — **three values**: `carries-over | new-drift-from-fix | pre-existing-orthogonal`) and `prior_finding_ref` (string or null, optional — the prior finding's title quoted verbatim, or null when no specific prior finding is referenced). Classification rules live in §Prior-relation classification (this file, above). Silent omission when a prior was loaded is a grounding failure — the attribution must be visible per finding. **`resolved` is not a permitted value here** (plugin v1.15.1 correction); the `resolved` concept lives only in `trace_log.prior_review_summary.resolved` as a count of prior findings no longer present. A finding emitted with `category: resolved` is schema-methodology invalid and downstream consumers are entitled to reject it.
- **`trace_log.prior_review_summary`** is **conditionally required**: required when a prior review was loaded, omitted entirely when no prior was loaded. Five integer fields, all required and ≥0: `total_in_prior` (count of findings in the prior review), `resolved` (count of prior findings that are no longer present in current state), `still_open` (count of prior findings that remain as `carries-over` in current findings), `new_drift_introduced` (count of current findings with `prior_relation.category == "new-drift-from-fix"`), `pre_existing_unrelated` (count with `pre-existing-orthogonal`). Verdict rule 3 clause (c) reads `resolved ≥ still_open + new_drift_introduced` from this field to determine chain-closing override — when the chain is closing, `refactor-recommended` is suppressed.
- **`trace_log.ship_blocker_answer`** is required when `verdict` is `block`, `needs-attention`, or `refactor-recommended`. Value is `"yes"` only when `verdict == "block"`; otherwise `"no"`. May be omitted when `verdict` is `approve`.
- **`trace_log.ship_blocker_reasoning`** is required alongside `ship_blocker_answer`. One sentence.
- **`trace_log.domains_loaded`** is required on every non-error run. Empty array `[]` is valid only if no domain matched — in that case, add a scenario noting "generic attack surface only".
- **`trace_log.domains_considered_dropped`** is required on every non-error run. Empty array `[]` is valid if no candidate domain was dropped. Every dropped entry needs `{domain, reason}` where reason is one of `not-matched`, `overlap`, `not-applicable`.
- **`trace_log.classification_notes`** is **unconditionally required** on every non-error run. A single non-empty sentence explaining how classification was decided — even trivial cases ("all files under `src/components/*.vue` — straightforward ui.md load" is fine). `null` and empty strings are invalid. The field forces deliberate thought about routing; it is not an optional "notes" slot.
- **`trace_log.symbols_inspected`** cannot be empty if `findings` is non-empty. If it is, you are reporting findings without grounding — drop them or redo the trace.
- **`trace_log.considered_not_promoted`** is optional — empty array `[]` is valid and preferred over padding. Each entry requires both `observation` (one sentence) and `reason`. `reason` must be one of the literal strings `out-of-scope`, `low-confidence`, `spec-accepted`, `test-covers-invariant`, or the pattern `covered-by-finding-<N>` where `<N>` is the 1-based index of the covering finding in the `findings` array (e.g. `covered-by-finding-1` for the first finding). If the covering finding is dropped or reordered later, update the index. Do not use this field to smuggle in extra findings — if an observation deserves action, promote it to `findings` and let it earn its slot under the hard cap. Use `test-covers-invariant` when you traced a candidate bug to an existing test that actually asserts the invariant you thought was violated — record the test location in the observation for auditability.
- **`trace_log.mutated_records_inspected`** is required on every review where the diff writes to at least one record. Each entry requires `record`, `kind`, `siblings_considered` (list every sibling field on the record, even ones you concluded were safe), and optionally `note`. Empty array `[]` is valid only if the diff contains zero record writes — in that case add `no record writes in diff` as a scenario line. Skipping this field when writes exist is the same class of grounding failure as an empty `symbols_inspected`: you skipped the data-model fanout trace.
- **`findings[].test_coverage`** is required on every finding. Both `covered_by` (test file path with line, or `null`) and `why_missed` (enum: `no-test`, `mock-bypass`, `missing-assertion`, plus a one-sentence explanation) must be present. If you cannot produce a test-trace answer from one of these three categories, the finding is invalid — either re-read the tests or drop it. See the test-trace rule in `methodology.md`. This field cannot be `null` and cannot be omitted: a finding without it indicates the reviewer skipped the validation gate and the finding cannot be trusted.
- **`trace_log.acceptance_criteria_crosswalk`** is conditionally required. When the pre-review context step loads a spec with **structured acceptance criteria** (explicit "must" statements, numbered requirements, bulleted ACs, definition-of-done checklist), the crosswalk must be populated with one entry per AC — including ACs that pass. Empty array `[]` is valid only when no spec loaded OR the loaded spec has no structured ACs (prose-only narrative RFCs qualify for the empty-list exemption). In the empty-list case, `classification_notes` or a scenario line must explain why: e.g. `"no spec loaded for this diff"` or `"spec loaded but no structured ACs — crosswalk skipped"`. Each entry requires `ac` (the AC text quoted verbatim), `spec_location` (file:line or section heading), `status` (one of `implemented`, `ambiguous`, `missing`, `contradicted`), and `implementation` (file:line-range for `implemented` / `ambiguous` / `contradicted`; `null` for `missing`). `notes` is optional but recommended for non-`implemented` statuses. See the "Acceptance criteria crosswalk" section in `methodology.md`. Skipping this field when a spec with ACs is present is the same class of grounding failure as an empty `symbols_inspected` — the audit did not happen.
- **`trace_log.project_rules_loaded`** is **unconditionally required** on every non-error run. Records which project-local review rule files SKILL.md Step 5.2b discovered and loaded. Each entry has two required fields: `path` (repo-relative path to the rule file) and `bytes` (size of the loaded content — after truncation if the 30 KB cap fired). Empty array `[]` is valid and expected when no rule candidate matched the Step 5.2b globs in the current project. Absence of the field is a grounding failure because it means the load step was skipped rather than run-and-empty. At most 10 entries per the Step 5.2b cap; when the skill truncated to stay under the 30 KB budget, the truncated file still appears in this array with its post-truncation byte count.
- **`findings[].rule_refs`** is optional. Populate it when a finding corresponds to a rule articulated in one of the loaded project rule files (`trace_log.project_rules_loaded`). Each entry has three required fields: `source` (must match one of the paths in `trace_log.project_rules_loaded` — citing an unloaded file is a grounding failure), `rule` (short identifier — heading name from the rule file, numbered rule, or a one-sentence paraphrase appearing adjacent to the quote), and `quote` (a **verbatim 1–2 line string lifted literally from the rule file**; downstream consumers may and should string-search the cited file to verify). Paraphrased quotes, composite quotes assembled from non-adjacent passages, or "cleaned up" rule text are schema-invalid — consumers are entitled to reject findings whose quote strings do not appear in the cited file. Cap at 3 citations per finding; beyond that, split the finding or prune to the strongest rules. Empty array `[]` or omitting the field both mean "no applicable rule" — citation is opportunistic, not mandatory. See the "Project-rule citation" section in `methodology.md`.
- **`trace_log.findings_dropped_in_verification`** is **unconditionally required** on every non-error run. It records the output of the Claim verification pass (see `methodology.md` section "Claim verification pass (pre-emit)"). Empty array `[]` is valid and expected when every candidate finding survived the pass unchanged — absence of the field is a grounding failure because it means the pass was skipped rather than run-and-clean. Each entry has two required fields: `original_claim` (one sentence, the load-bearing claim as first written before the pass fired) and `reason` (enum, schema v1.12: `unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept | unverified-external-claim`). Use `narrowed-kept` when the pass fired and the finding was rewritten with a tighter claim rather than dropped — the finding still appears in `findings` with its narrower version, and the original wider claim is logged here for auditability. Use `no-evidence-after-trace` when the pass could not locate supporting evidence for the claim even after re-reading the code paths the claim referenced. Use `unverified-external-claim` (added in v1.12) when the finding's load-bearing claim depended on external-system behavior that the reviewer could not verify via docs, source, runtime, or specification, and the reviewer elected option (c) from the methodology rule (drop rather than tag as unverified or gather evidence). Do not use this field to silently smuggle in observations that were never candidate findings — it is a record of the pass's *drops and narrowings*, not a general-purpose scratchpad.
- **`findings[].evidence_sources`** is optional (schema v1.12). Populate it when the finding's load-bearing claim references external-system behavior (third-party libraries including stdlib, OS runtimes, protocols, file formats, shell semantics, hardware) and the reviewer gathered evidence per step 5 of the Claim verification pass. Each entry has four required fields: `claim` (one sentence restating the external-behavior assertion), `source_type` (enum: `docs-url | source-file | runtime-observation | specification`), `source` (URL for `docs-url`, `path/to/file:line` for `source-file`, command and observed output for `runtime-observation`, spec identifier like `RFC 7231 §6.5.1` for `specification` — must be specific enough for independent verification), and `verified_at` (ISO-8601 timestamp of the verification action). Empty array `[]` or omitting the field both mean "no external claims in this finding"; both are valid. When the finding's body contains the literal string `evidence: unverified — <reason>`, the reviewer elected option (b) from the methodology rule — severity and confidence already dropped one notch each, and this array may remain empty for that specific claim. Paraphrased or imagined evidence sources are schema-invalid — downstream consumers may and should attempt to resolve the `source` to confirm it exists. For `runtime-observation`, the observed output must be reproducible (the same command on comparable hardware/OS produces the same output); non-deterministic observations must be reclassified as `specification` or dropped. Cap at 5 entries per finding; beyond that, split the finding or collapse claims that share a source.
- **`trace_log.external_claims_verified`** is **unconditionally required** (schema v1.12, integer ≥0). Counts **verification actions** the reviewer performed, not finding entries and not `evidence_sources[]` entries. A single `WebFetch` that validates three separate claims counts once; two independent verifications in one finding (say, a docs fetch AND a runtime observation, each for a different claim) count twice. `0` is valid and expected when no finding referenced external-system behavior. Absence of the field is a grounding failure because it means the evidence gate was skipped rather than run-with-no-external-claims. Performative fetches that did not validate the claim against fetched content do not count — this is the same discipline as the quote-verbatim rule on `rule_refs`. The integer is observability, not gating; verdict derivation does not read it.
- **`trace_log.patch_chain_risk`** is conditionally required. When SKILL.md Step 3b scans the git log and **any** of the three signals fires (`fix-prefix-cluster`, `same-file-hotspot`, `prior-review-overlap`), the field must be present and must carry a one-sentence `theme_assessment` regardless of whether `detected` ends up `true` or `false`. When no signal fires, the field may be omitted entirely. When the field is present: `detected` (boolean) records whether the reviewer's theme-vs-root judgment confirms the patch chain; `signals_fired` (array) lists which signals triggered the scan; `chain_depth` (integer) is the count of defensive commits in the window that match the prefix filter (0 if only the prior-review-overlap signal fired); `prior_commits` (array of one-line strings `"<sha> <subject>"`) records the evidence — omit or empty-array if the prior-review-overlap signal fired alone; `prior_review_file` is the resolved auto-detect path `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md` when Step 3b successfully loaded a snapshot, else `null` (file absent or rejected); `theme_assessment` is the mandatory one-sentence answer to the theme-vs-root gate; `recommendation` is a one-sentence note on what the signal means for this review. See §Patch-chain detection (this file, above) and the data-collection rules in SKILL.md Step 3b. Emitting `detected: true` without a `theme_assessment` is the same class of grounding failure as an empty `symbols_inspected` — the reviewer skipped the gate. The `refactor-recommended` verdict rule 3 clause (a) reads `detected == true` from this field; clause (b) is independent of this field and remains reachable in v1.6 payloads.
- **`findings` length must respect the hard cap** from `methodology.md` (3 under 500 lines, 5 under 1500, 3 per split group).
- **`confidence`** is 0.0–1.0. Use it for your own uncertainty — do not soften severity to compensate for low confidence.
- **`findings[].finding_type`** is required on every finding emitted by schema v1.6 or later. Values: `correctness | design_debt | best_practice_violation | architectural_smell`. Classification rules live in §Severity axes and verdict derivation (this file, above). **Default-to-correctness rule (backward compatibility):** consumers reading payloads without this field — typically v1.5-era snapshots replayed through v1.6 tooling — must treat absence as `"correctness"`. Rationale in the Compatibility property under §Severity axes and verdict derivation (this file, above).
- **`findings[].scope`** is required on every finding emitted by schema v1.10 or later. Values: `in-diff | pre-existing | future-work`. Classification rules live in §Scope classification (this file, above). **Default-to-in-diff rule (backward compatibility):** consumers reading payloads without this field — typically pre-v1.10 snapshots replayed through v1.10 tooling — must treat absence as `"in-diff"`. Rationale in the Compatibility property under §Severity axes and verdict derivation (this file, above). Only findings with `scope == "in-diff"` (or default) drive verdict escalation — `pre-existing` and `future-work` findings are surfaced for transparency but do not contribute to `correctness_severity`, `design_debt_severity`, or the `block`/`needs-attention`/`refactor-recommended` rules. All three scopes count toward the hard cap on findings.
- **`trace_log.rejections_loaded`** is **unconditionally required** (schema v1.14). Records which rejection entries the skill loaded from `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` during rejection memory Phase A (`rejection-memory.md`, run at Step 3b). Each entry has two required fields: `hash` (64-character lowercase sha256 hex string, computed per the normalization rule in `rejection-memory.md` substep 1 — trim + lowercase `file` + collapse `title` whitespace + `:`-joined over the `file:title` pair; line ranges are deliberately excluded from identity since plugin v1.20.0, because line drift between rounds must not re-fire a rejected finding) and `rejected_at` (ISO-8601 timestamp, preserved verbatim from the rejection entry). The emitted hash is **recomputed at load time** from each entry's stored `file` and `title` — the sidecar's stored `hash` field is audit metadata, which is what keeps `"1.0"`-era sidecar entries (recorded under the old line-bearing normalization) matching under the current rule. Empty array `[]` is valid and expected when the `rejections.json` file does not exist for the session or when the file exists with `rejections: []`. Absence of the field is a grounding failure because it means the rejection-memory load step was skipped. When the load attempt fails due to malformed JSON or missing `schema_version` in the sidecar file, emit `trace_log.rejections_loaded: []` and also emit the `scenarios_considered` line `rejection memory: rejected-malformed-json` — the empty array plus the status line together record that the load was attempted and rejected. The `rejections.json` sidecar has its own `schema_version` field (currently `"1.1"`; readers accept `"1.0"` and `"1.1"` and treat any other value as malformed) managed independently of the main payload schema; sidecar schema drift does not require a main-schema bump.
- **`findings[].previously_rejected`** is optional (schema v1.14). Populate only on findings that were re-raised despite matching a rejection hash in `trace_log.rejections_loaded`. Three required fields: `rejected_at` (ISO-8601 timestamp copied verbatim from the matching rejection entry), `prior_rationale` (the rejection rationale string from the rejection entry, or `null` when the rejection was recorded without a rationale), `new_evidence` (a **single concrete sentence** describing what concrete difference in the current analysis justifies re-raising — a new call path, a new config condition, a new sibling field, a new project rule, a new prior-review carries-over status). `new_evidence` must be specific enough that a downstream reader can understand why the finding came back; generic "additional analysis surfaced" or "reviewer reconsidered" does not qualify and a finding emitted with such `new_evidence` is subject to rejection by consumers as schema-methodology inconsistent. When a finding has `previously_rejected` populated, the finding body must lead with the literal prose preamble: `Previously rejected on <rejected_at> with rationale <prior_rationale or "(none provided)">. New evidence: <new_evidence>.` followed by the usual finding content. Suppressed rejections (candidate finding matched a rejection hash and was silently dropped per the default path) do NOT populate this field — they do not appear in `findings` at all. The field's presence is the re-raise signal; its absence is the default path. See §User rejection memory (this file, above) for the suppress-vs-re-raise decision rule.
- **`findings[].reachability`** is required on every finding emitted by schema v1.13 or later. Values: `reachable | hypothetical | requires-specific-config`. Classification rules live in §Reachability classification (this file, above). **Default-to-reachable rule (backward compatibility):** consumers reading payloads without this field — typically pre-v1.13 snapshots replayed through v1.13 tooling — must treat absence as `"reachable"`. Rationale in the Compatibility property under §Severity axes and verdict derivation (this file, above). Only findings with `reachability == "reachable"` (or default) drive verdict escalation — `hypothetical` and `requires-specific-config` findings are surfaced for transparency but do not contribute to `correctness_severity`, `design_debt_severity`, or the `block`/`needs-attention`/`refactor-recommended` rules. All three reachability levels count toward the hard cap on findings. Reachability is **orthogonal** to `severity` and `confidence`: a `reachable` finding can have low `confidence` (reviewer is not sure their reading is right), and a `hypothetical` finding can have high `confidence` (reviewer is sure this WOULD be a bug if reached but cannot name a reaching path). The body must record supporting evidence: `reachable` findings name a concrete call path from an entry point; `requires-specific-config` findings name the specific config, flag, environment variable, or platform; `hypothetical` findings need no additional body requirement but the classification itself signals the reviewer could neither trace a path nor name a config.
- **`correctness_severity`** is an optional top-level enum (`critical | high | medium | low | none`). Derived as the max severity among findings with `finding_type == "correctness"` (including findings where `finding_type` is absent and defaults to correctness). Omit the field entirely when no correctness findings exist, or emit `"none"` — both are valid. Consumers should treat absence as `"none"`.
- **`design_debt_severity`** is an optional top-level enum with the same values. Derived as the max severity among findings with `finding_type == "design_debt"`. Same emit-or-omit rule. `architectural_smell` and `best_practice_violation` findings do not contribute to either axis — they have their own `findings[].severity` but do not roll up today.
- **`findings[].lift_considered`** is optional. Populate it when the recommendation is a runtime guard (per the Lift hierarchy rule in `methodology.md`). Each of `type_lift`, `writer_lift`, `ordering_lift` carries `{ viable: boolean, rationale: string }` where `rationale` is a one-sentence explanation of the constraint that either blocks or enables that lift. For a guard recommendation to be justified, either (a) **all three** of `type_lift`, `writer_lift`, `ordering_lift` must be `viable: false` with a specific constraint named per lift, OR (b) the finding body must name a **system boundary** (user input, external API, untrusted data, trust boundary where the producer cannot be changed) as the reason a lift is not the right primitive. If any of the three lifts is `viable: true` and no system boundary is named in the body, the recommendation should be that viable lift, not a guard — emitting a guard recommendation under these conditions is a schema-methodology inconsistency that downstream consumers are entitled to reject. If the recommendation is not a guard (e.g., recommending a lift directly, recommending a test, recommending removing code), the field may be omitted.
- **`considered_not_promoted[].design_alternative_considered`** is optional — a one-sentence description of the lift or structural change that would resolve the observation if it ever escalated to a bug. Use it when you see a latent issue that is not a bug today but has an obvious structural fix; leaves a breadcrumb for the next reviewer.
- **`considered_not_promoted[].tracked_as_debt`** is optional boolean. Set to `true` when the observation represents design debt worth tracking even though it doesn't rise to a finding. No consumer required today; metadata for future tooling.
- **Verdict consistency.** The five-rule verdict derivation (override 0 + rules 1-4, filtered on `scope == "in-diff"` AND `reachability == "reachable"` with default-to-in-diff applied to pre-v1.10 payloads and default-to-reachable applied to pre-v1.13 payloads) is stated authoritatively in §Severity axes and verdict derivation (this file, above) — including the per-rule bullets for `block` / `needs-attention` / `refactor-recommended` / `approve`, the Compatibility property across schema versions, and the Override discipline rule for manual deviations. Consumers validating payload conformance must apply those rules: a `verdict` that disagrees with the rules applied to the current `findings` is a schema-methodology inconsistency and downstream consumers are entitled to reject the payload. Rule 0 (chain-of-rejections override) bypasses rules 1-4 when the resurface count reaches ≥ 2 and no re-raised finding clears the severity carve-out (reachable in-diff correctness at high/critical, plugin v1.20.0) — see §User rejection memory (this file, above).
- **Severity inflation guard**: if you answered the ship-blocker question `yes` but no individual **correctness** finding scores critical or high, your severity assignment is wrong — re-evaluate the severity of the blocking finding before inflating it to match the verdict. A design_debt finding with severity critical does not justify `ship_blocker_answer == "yes"`; it justifies `verdict: refactor-recommended` with `ship_blocker_answer == "no"`. The block test should agree with severity naturally; if it doesn't, either the finding is not actually a correctness ship-blocker or the finding is miscategorized.

---

## Error output

If the skill cannot run (e.g., not a git repo, `gh` missing in PR mode, empty diff), emit:

```
# Devil Review

Target: <attempted target>
Verdict: <n/a>

<one-sentence explanation of why review cannot proceed>
```

Followed by:

```json
{
  "schema_version": "1.14",
  "verdict": null,
  "error": "<error code: not_a_repo | gh_missing | empty_diff | shallow_clone_no_base | reject_without_prior | reject_index_out_of_range | rejections_file_malformed | other>",
  "message": "<human-readable explanation>"
}
```

Do not fabricate a review. Do not return an `approve` verdict to paper over a tool failure.
