# devil-review — Design Rationale

Why the rules are the way they are. Extracted verbatim from the runtime skill files (v2 restructure, Item 3, 2026-07-17) so that per-invocation load carries rules, not history. Each section names the rule's runtime home; the text below is the rationale that used to sit next to it.

Nothing here is normative. If a statement below ever contradicts a rule in `skills/devil-review/*.md`, the rule file wins.

## Scope classification

**Rule location**: `skills/devil-review/output-schema.md` §Scope classification.

### Why the field exists

**Why this field exists.** A finding that says "the diff is broken" and a finding that says "this unrelated code has been broken for months" are different signals for the author. Mixing them is the classic "reviewer overreach" antipattern: the PR author opens the review expecting "did I do this right" and gets "and also please fix these three unrelated things". Without a scope tag, the reviewer is either (a) rule-violating by raising pre-diff issues at all, or (b) under-informing by dropping them silently. Scope tagging resolves the tension: pre-existing findings are allowed but explicitly labeled, so the author can triage them separately from the ship decision.

## Reachability classification

**Rule location**: `skills/devil-review/output-schema.md` §Reachability classification.

### Why the field exists

**Why this field exists.** `confidence` is the reviewer's epistemic uncertainty about whether the finding is *correct*. `reachability` is a structural property of the code path. A reachable finding can have low confidence (reviewer is not sure their reading of the code is right); a hypothetical finding can have high confidence (reviewer is sure this WOULD be a bug if reached — they just cannot name a reaching path). Conflating the two loses information: a reader cannot distinguish "high-confidence bug that fires hourly" from "high-confidence theoretical bug that has never fired and may never fire". Saha test #3 surfaced the concrete confusion — a `confidence: 0.7` hypothetical Windows-specific trailing-backslash finding read as equal-weight with a `confidence: 0.85` async listener race on the main user flow, because confidence alone collapsed two orthogonal dimensions.

## User rejection memory

**Rule location**: `skills/devil-review/output-schema.md` §User rejection memory.

### Observed origin

**Why this exists (observed).** Saha test #3 surfaced the following friction pattern on a real project: Round 1 of `/devil-review` flagged a Windows trailing-backslash edge case; the user assessed it as not-a-real-concern and skipped it; Round 2 re-flagged the same location with identical logic. The reviewer had no memory of the prior dismissal and re-raised the same claim. Combined with the severity-dampening rule from saha test #2, the silent re-raise creates a "patch-chain of rejected findings" — the reviewer persistently surfaces the same dismissed claims, and the user either re-dismisses each round (friction) or tunes the reviewer out entirely (worse — real signal gets lost in noise).

Rejection memory closes the loop: the reviewer consults the file, matches candidate findings against rejection hashes, and either suppresses silently or re-raises with justification.

## Chain-of-rejections override

**Rule location**: `skills/devil-review/output-schema.md` §Chain-of-rejections override.

### Rationale

When that evidence establishes a ship-blocker-class reachable correctness bug, forcing `approve`/`ship` would turn the user's earlier dismissal against the current evidence: the rejection was made without the facts now on the table. Without the carve-out, the override structurally punished exactly the reviewer behavior the re-raise bar demands (suppressed rejections never count toward the resurface threshold — only evidence-backed re-raises do). With it, the override fires only on persistent disagreement about *materiality* — sub-high, non-correctness, non-in-diff, or non-reachable re-raises — which is precisely the friction pattern it exists to stop.

### Rationale

**Rationale.** Round N+1 of a review that keeps surfacing the same dismissed findings is not producing signal — it is producing friction. The user either ignores the output (worst case, loses real future signals), re-invokes `--reject` on every round (friction), or disengages from the plugin (plugin loses a user). The override is the plugin saying "I keep bringing these up and you keep saying they do not matter; I accept your judgment and stop." This is the opposite of the patch-chain override from v1.11, which said "stop iterating because fixes are not working" — here we stop iterating because fixes are not needed.

## Patch-chain detection

**Rule location**: `skills/devil-review/output-schema.md` §Patch-chain detection.

### Failure-mode narrative

(Schema v1.7 / plugin v1.10.0.) This rule operationalizes a specific failure mode of iterative review: when the same diff is reviewed N+1 times, findings drift from "organic bugs the diff introduced" to "artifacts of guards the *prior* rounds introduced". Each new round of review sees the guards added by the previous round and raises a finding about the edge case those guards did not cover — and then the next round adds another guard and the cycle continues. The correct next step after round 2 or 3 is not another guard; it is a structural refactor that collapses the guard cluster into a single invariant enforced by type, writer, or ordering (see the Lift hierarchy in `methodology.md`).

### What auto-detection adds

**What prior-review auto-detection adds.** Every run auto-writes its output (Step 8) to a session-scoped, target-scoped path. Every subsequent run on the same target in the same session auto-reads that snapshot (Step 3b, no flag required) and uses it for the `prior-review-overlap` signal. This gives direct evidence that the review is iterating on the same diff. The signal fires even when the git log alone is ambiguous (e.g., prior rounds' changes were amended into a single commit, so `fix:` prefixes never accumulated). Prior-review overlap is a stronger signal than git log prefixes because it shows the *reviewer* has been circling the same surface, not just that git history has. When both signals fire, the case for refactor is overwhelming. Session scoping prevents stale snapshots from prior Claude Code sessions from contaminating today's review.

## Verdict rule 3 clause (c)

**Rule location**: `skills/devil-review/output-schema.md` §Verdict rule 3 clause (c).

### Saha-test-#2 origin

This operationalizes the dampening the reviewer performed manually in saha test #2, where Round 2 correctly concluded "prior findings resolved, new findings introduced by fix or pre-existing — not a patch chain" and dampened away from `refactor-recommended`.

## Severity floor for user-irrecoverable findings

**Rule location**: `skills/devil-review/methodology.md` §Calibration rules → Severity floor for user-irrecoverable findings.

### Saha-test-#4 origin

Saha test #4 (cross-model adversarial comparison, 2026-04-26): devil-review correctly identified a permission-cache bug whose user impact was "can't recover until app restart" — verbatim from the finding text — but routed it to `considered_not_promoted` rather than promoting to `findings`. Codex (different model family, fresh perspective) flagged the same bug as no-ship. The promotion path filtered out a finding whose user-recovery cost was structurally above the noise threshold. Without a severity floor tied to recovery cost, the reviewer's calibration drifts on exactly the class of bug that should never ship. Full spec: `phase-3-plan.md` Item 15 (folded into v2.0.0; the spec's `severity_floor_applications` counter field was dropped per the schema-diet discipline — the `Recovery cost:` body line is the audit artifact).

## Event-source upstream trace

**Rule location**: `skills/devil-review/methodology.md` §Claim verification pass → step 6.

### Saha-test-#4 origin

Saha test #4: codex traced upstream into the backend (`status_service.rs`) to verify what the watched event source actually emitted under various conditions, including transient cases; devil-review stayed in the frontend diff slice and treated the event as a given. This was a methodology gap, not a model gap — no step said "if your finding involves an event handler, trace the source", so finding bodies asserted event semantics without verifying them. Full spec: `phase-3-plan.md` Item 17 (folded into v2.0.0; the spec's `event_sources_traced` counter field was dropped per the schema-diet discipline — the traced-emitter `producer:` body note is the audit artifact).
