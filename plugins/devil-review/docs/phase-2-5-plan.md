# devil-review — Phase 2.5 Plan

**Status:** Specced 2026-04-14
**Plugin version at time of writing:** v1.8.0
**Scope:** Methodology/output expansion bundle sitting between Phase 2 (content) and Phase 3 (durability). Driven by real-usage feedback: iterating devil-review N+1 times on the same diff starts producing findings that are artifacts of prior rounds' guards, not organic defects. Phase 2.5 is the fix.

> **Guiding principle:** The underlying proposal had 7 items with overlap. Applied the plugin's own lift hierarchy to the proposal itself — collapsed to 3 coherent shippable changes. Each is independent and shippable alone; batching is discouraged (same rule as Phase 3).

---

## Problem statement

Devil-review is stateless between rounds. When the same diff is reviewed 2–3 times in a row (user iterates on fixes, re-invokes the skill), findings drift from "organic bugs" to "artifacts of guards added in prior rounds". The skill has no mechanism to:

1. Recognize a guard cluster as design debt vs. individual correctness bugs.
2. Distinguish "code works but is accumulating debt" from "ship-blocker correctness issue".
3. Prefer structural fixes (type/writer/ordering lift) over additive guards when recommending.
4. Detect patch-chain patterns in git history that suggest iteration has hit diminishing returns.

Result: user runs 3 rounds when 1 round + structural refactor recommendation would have sufficed.

The fix is content (methodology + schema), not infrastructure — Phase 2.5, not Phase 3.

---

## Sequencing (ship incrementally, one commit per version)

Three coherent changes, each independently shippable. Do not batch. Each lands in its own commit with its own self-review pass per CLAUDE.md discipline.

### v1.8.1 (patch) — Lift hierarchy on defensive recommendations

**Scope:** Prompt-only change. No schema bump, no new fields.

**Change to `methodology.md`:** Add a new subsection under "Calibration rules" (after the existing "Prefer state machine integration over additive guards" block, before "Generalization test"). Title: **"Lift hierarchy for defensive recommendations"**.

Content (approximate):

> When your recommendation is "add a check" or "add a guard", evaluate four alternatives in order and prefer the earliest that is viable:
>
> 1. **Type lift** — encode the invariant in the type system (newtype, discriminated union, narrower type, non-nullable field). The compiler enforces it; no runtime cost; cannot be bypassed.
> 2. **Writer lift** — collapse to a single writer that guarantees the invariant by construction. Multiple writers maintaining the same invariant is a duplication smell.
> 3. **Ordering lift** — fix the bootstrap/lifecycle sequence so the invariant holds by construction. Guards that check "is X initialized" often mean X is constructed in the wrong order.
> 4. **Guard** — runtime check, last resort. Legitimate only at system boundaries (user input, external API, untrusted data) or when 1–3 are genuinely infeasible.
>
> If you recommend a guard, document in the finding body why lifts 1–3 were rejected. "The codebase already uses guards here" is not a rejection — it is a symptom of skipped lifts in prior rounds. Name the specific constraint that blocks each lift.
>
> **Interaction with state machine integration.** This rule is strictly narrower than "Prefer state machine integration over additive guards". Both point toward consolidation, but the lift hierarchy specifies *how* to consolidate and *when runtime guards are acceptable*. When both rules apply, apply state machine integration first (is the condition co-varying or cross-cutting?), then the lift hierarchy (if cross-cutting, what's the earliest viable lift?).

**Change to `output-schema.md`:** No schema version bump. Add one sentence to the `Recommendation` field guidance in Part 1 (Markdown section): "If the recommendation is a runtime guard, the body must name why type/writer/ordering lifts were rejected." This is prose guidance, not a schema field.

**Why patch not minor:** Pure content addition that refines existing recommendation discipline. No new schema fields, no new trace_log entries, no new required behaviors beyond what "Prefer state machine integration" already asks. Downstream consumers see no structural change.

**Self-review pass:**
- Generalization test: does this rule apply beyond the specific patch-chain scenario? Yes — it applies to every defensive recommendation, even first-round ones.
- Mutation fanout: does adding a new rule affect existing rule interactions? Yes — explicit interaction note added for state machine integration overlap.
- Over-correction check: does the rule wrongly suppress legitimate guards? Yes, it could — mitigated by explicit "legitimate at system boundaries" carve-out.

**Estimated effort:** 20 minutes. Single methodology.md edit + two manifest bumps + README footer sync.

---

### v1.9.0 (minor) — Extended verdict, severity axes, and finding taxonomy

**Scope:** Schema bump to v1.6. One extended enum value on `verdict`, new optional top-level severity axes, new required nested `findings[].finding_type`. All additions are either optional at top level or nested inside existing arrays — a strict v1.5 consumer that ignores unknown keys reads v1.6 payloads without error.

**Schema additions (output-schema.md v1.6):**

`verdict` enum — extend, do not replace:
- Current: `"block" | "needs-attention" | "approve"`
- Extended: `"block" | "needs-attention" | "refactor-recommended" | "approve"`
- `refactor-recommended` is new. Meaning: "the code in this diff is correct enough to ship, but structural debt is high enough that iterating further will make it worse — step back and restructure instead of adding another guard."
- Existing three values keep their exact prior semantics. Any review that would have emitted `needs-attention` or `approve` under v1.5 rules continues to emit the same value under v1.6 rules unless the new `design_debt` axis specifically fires.

Top-level (`trace_log` sibling), both **optional**:
- `correctness_severity`: `"critical" | "high" | "medium" | "low" | "none"` — worst correctness finding severity. Omitted when all findings are non-correctness or when findings array is empty.
- `design_debt_severity`: `"critical" | "high" | "medium" | "low" | "none"` — worst design-debt finding severity. Same enum as `correctness_severity` and `findings[].severity`. Omitted when no design_debt findings exist.
- **Enum alignment (Finding 3 fix):** both axes reuse the existing `findings[].severity` vocabulary verbatim. There is no separate design-debt severity vocabulary. The business rule "design debt never blocks ship on its own" is enforced in the **verdict derivation** below, not by amputating the enum.

Finding-level (required, but nested additive per v1.4 precedent):
- `finding_type`: `"correctness" | "design_debt" | "best_practice_violation" | "architectural_smell"` — required on every finding emitted by v1.6. For backward compatibility, consumers reading payloads without this field (e.g., replaying a v1.5 snapshot) must treat the absence as `"correctness"`. This default matches historical behavior: before v1.6, all findings were implicitly correctness bugs.
  - `correctness` — the code produces wrong output under realistic conditions (existing definition).
  - `design_debt` — the code works but its structure will cause future correctness issues or blocks refactoring.
  - `best_practice_violation` — a project-convention or domain-convention deviation that is not a correctness bug today but increases surprise cost. Fed by domain checklists.
  - `architectural_smell` — the code violates an architectural decision (CLAUDE.md or spec) but is currently correct.

Considered-not-promoted enrichment (both **optional**):
- `considered_not_promoted[].design_alternative_considered`: optional string — "this could be resolved by lifting invariant X to writer Y" etc. Gives reviewers a channel for "I saw it, it's not a bug today, it's debt".
- `considered_not_promoted[].tracked_as_debt`: optional boolean — true when the observation represents debt worth tracking even though it doesn't rise to a finding. No consumer required today; metadata for future tooling.

Lift-considered on findings (**optional**, populated when the recommendation is a guard):
- `findings[].lift_considered`: optional object.
  - `type_lift`: `{ viable: boolean, rationale: string }`
  - `writer_lift`: `{ viable: boolean, rationale: string }`
  - `ordering_lift`: `{ viable: boolean, rationale: string }`
  - Structure forces the reviewer to commit per-lift rather than hand-waving "lifts don't apply".

**Methodology additions (methodology.md):**

New subsection under "Calibration rules" titled **"Severity axes and finding taxonomy"**:

- Explains correctness vs design_debt axis split. Both axes use the same severity enum; the difference is in `finding_type`, not in the severity vocabulary.
- Specifies: how to classify a finding into one of the four `finding_type` values. Decision tree:
  - "Does the code produce wrong output today under a realistic scenario?" → `correctness`.
  - "Does the code violate a CLAUDE.md architectural decision or spec?" → `architectural_smell`.
  - "Does the code violate a domain checklist's best-practice item without being a correctness bug?" → `best_practice_violation`.
  - "Is the code correct today but its structure is accumulating risk (guard cluster, multiple writers of same invariant, state fragmentation)?" → `design_debt`.
- Specifies: how `correctness_severity` and `design_debt_severity` are derived — take the max severity among findings of that `finding_type`. Omit the field when no finding of that type exists.

**Verdict derivation — extended, not redefined:**

The existing rule stays. New rule applies only when the new `refactor-recommended` value is a candidate. Strict precedence, evaluated top to bottom:

1. **`block`** — at least one finding with `finding_type == "correctness"` AND severity `critical` or `high`, AND `ship_blocker_answer == "yes"`. (Unchanged from v1.5: a v1.5 payload with a critical/high finding and no `finding_type` field defaults to `correctness`, so the rule produces identical verdicts for v1.5-era inputs.)
2. **`needs-attention`** — at least one finding of any type with material severity, AND rule 1 does not apply. (Unchanged.)
3. **`refactor-recommended`** — **new**. All of: (a) rule 1 does not apply, (b) `design_debt_severity` is `high` OR `critical`, (c) either a patch-chain signal fires (see v1.10.0) OR the `design_debt` findings outnumber the `correctness` findings in this review. Meaning: there may be correctness issues, but fixing them in place will not address the real problem; the structural debt is the real blocker to further iteration.
4. **`approve`** — no findings, or rule 1–3 do not apply. (Unchanged.)

**Compatibility property:** any v1.5-era review re-run under v1.6 rules produces the same verdict, because v1.5 payloads had no `finding_type` field (default `correctness`), no `design_debt_severity` (default none), and no patch-chain signals (v1.10 feature). Rules 1, 2, and 4 reduce exactly to the v1.5 rules in this case. Rule 3 is unreachable without v1.6 inputs. This is what keeps v1.9.0 a genuine minor bump.

**Verdict consistency rule update (inside output-schema.md JSON rules):**

- `block` → requires at least one finding with `finding_type == "correctness"` (or absent, treated as correctness) AND severity critical/high, AND `ship_blocker_answer == "yes"`. (Narrowed from "any finding" to "correctness finding", but the default-to-correctness rule keeps v1.5 payloads compliant.)
- `refactor-recommended` → requires rule 3 above to be satisfied. `ship_blocker_answer` is `"no"` (not a ship-blocker by correctness, the whole point of the new verdict).
- `approve` → still requires zero findings.
- `needs-attention` → everything else with material findings and `ship_blocker_answer == "no"`.

**Self-review pass:**
- Schema mutation fanout: do v1.5 consumers break on v1.6 payloads? No new *required top-level* fields. New verdict enum value `refactor-recommended` — strict v1.5 consumers that validate the verdict enum will reject it, which is the expected behavior for an enum extension and is signaled by `schema_version: "1.6"`. All other additions are either optional at top level or nested inside existing arrays (same shape as v1.4's nested extensions).
- Generalization test: does the extended verdict describe any real bug class, or just patch-chain artifacts? It describes any "correct but fragile" code — wider than the motivating case.
- Over-correction check: does `design_debt` become a dumping ground? Risk mitigated by the decision tree — classification must answer "does it produce wrong output today" as the first gate.
- Writer-lift self-check: do `verdict` and any new field carry overlapping signal? No — `verdict` is the single exit signal, severity axes are information-carrying inputs to the verdict derivation, `finding_type` classifies individual findings. One writer per concept.

**Estimated effort:** 2 hours. Schema edit, methodology edit, README sync, self-review pass, decide whether existing v1.5 fixtures need migration (none exist — Phase 3 Item 1 not started — so no migration burden).

**Risk:** Low-medium. The new verdict value is the only hard compatibility break, and it is the core of the feature. Severity axes are optional; `finding_type` is nested-additive with a documented default that makes old payloads re-validate.

---

### v1.10.0 (minor) — Patch-chain detection and prior-review context

**Scope:** Read git log during Step 3 to detect patch-chain patterns. Accept optional prior-review output in SKILL.md arguments. Emit a new `trace_log.patch_chain_risk` structure.

**SKILL.md additions:**

Extend Step 1 argument parsing:
- New optional flag: `--prior-review <file-path>` — path to a previous devil-review markdown output for the same diff. When present, plugin reads it before review and uses it to inform patch-chain detection and `considered_not_promoted` continuity.

Extend Step 3 (Collect review context) with a new sub-step **3b — Patch-chain scan** (runs after mode-specific diff collection, before Step 4 large-diff guard):

```
git log -<N> --oneline -- <changed-files>
```

Where `<N>` is 5 for working-tree/branch mode, 10 for PR mode (PRs accumulate more commits).

Scan the resulting commit messages for patch-chain signals:
- Messages prefixed `fix:`, `guard:`, `prevent:`, `patch:`, `workaround:` (configurable, document the list in methodology).
- Same file appearing in ≥3 of last `N` commits.
- Cluster signal: ≥50% of the last 4 commits match any signal above on the same file set.

If cluster signal triggers, populate `trace_log.patch_chain_risk` in the output.

**Methodology additions (methodology.md):**

New subsection **"Patch-chain detection"** under "Calibration rules":

- Explains the signal: recent commits dominated by defensive prefixes on the same files indicate iteration has hit diminishing returns.
- Rule: when patch-chain is detected, it becomes an input to **verdict derivation rule 3 (`refactor-recommended`)** from v1.9.0. Specifically, it satisfies clause (c) "patch-chain signal fires" without needing the "design_debt findings outnumber correctness findings" alternative. Recording the patch-chain trace is mandatory in this case.
- False-positive guard: legitimate hotfix-heavy files (e.g., a known-flaky integration test file) can trigger this signal without being a design-debt problem. Reviewer must check: "do the prior fixes address different root causes, or are they variations on the same theme?" Same-theme = patch chain. Different roots = coincidence. The reviewer's theme-vs-root assessment gates the signal — a coincidence match does not fire `patch_chain_risk.detected: true`.
- **Threshold rationale (deferred from self-review).** The specific thresholds (`N` commits scanned, `≥50%` cluster ratio, 4-commit window) are not derived from data — no corpus of past reviews exists to calibrate against. They are starting values chosen to be strict enough to avoid firing on typical 1–2 hotfix sequences but permissive enough to fire on a genuine 3-round iteration. The first round of real usage after shipping is the calibration signal; if the false-positive rate is visible and persistent, revise the thresholds in a v1.10.x patch bump and document the empirical basis in the revision log. Hardcoding arbitrary starting values and iterating on them is preferable to blocking the whole feature on a calibration corpus that does not exist.

**Schema additions (output-schema.md v1.7):**

New `trace_log.patch_chain_risk` object, conditionally required (only present when signal triggers):

```json
{
  "detected": true,
  "chain_depth": 3,
  "signals": ["fix-prefix-cluster", "same-file-hotspot"],
  "prior_commits": ["abc123 fix: restore race", "def456 fix: dead UUID"],
  "recommendation": "Current findings may be artifacts of prior patches — prefer refactor over guard #N+1.",
  "prior_review_file": "<path or null>"
}
```

When `--prior-review` is supplied:
- Parse the prior review's `findings[]` and `trace_log.considered_not_promoted[]`.
- For each current finding, check if the same location/symbol appeared in the prior review. If yes, annotate the current finding body: "This location also appeared in the prior review as finding #N." (Not a new schema field — body-only annotation.)
- If ≥50% of current findings reference locations from the prior review, set `patch_chain_risk.signals` to include `"prior-review-overlap"`.

**Prior-review input format:** accept the markdown-with-JSON-fence output format the plugin already emits. No new format.

**Self-review pass:**
- Generalization test: does patch-chain detection help beyond the motivating case? Yes — any multi-round review workflow benefits.
- Mutation fanout: do the new fields interact with v1.9 fields? `patch_chain_risk` feeds verdict derivation rule 3 (`refactor-recommended`) from v1.9.0, so v1.9 must ship before v1.10. Sequencing is already correct.
- Over-correction check: does the signal fire too often? Mitigated by the "same theme vs different roots" guard and explicit reviewer-gated promotion — the signal is input to judgment, not automatic enforcement.
- Runtime contract verification: `--prior-review <file-path>` — is the file content validated? It's markdown emitted by the plugin itself; treat it as trusted-but-verified, but explicitly guard against non-devil-review markdown (schema_version presence check in the JSON fence).

**Estimated effort:** 3 hours. SKILL.md extension, methodology addition, schema bump, prior-review parser, self-review pass.

**Risk:** Low-medium. Git log scanning is cheap and local. Prior-review parsing is opt-in (`--prior-review` flag).

---

## Deferred — not in Phase 2.5

These were in the original 7-item proposal but dropped during collapse:

- **Guard cluster AST detection** — promised "language-agnostic" but requires real AST parsing per language. Would be a separate infrastructure phase. The LLM-based diff reading in devil-review already catches guard clusters qualitatively; deterministic detection is not worth the parser infrastructure until someone demands it.
- **Meta-round awareness as a separate mechanism** — absorbed into `--prior-review` in v1.10.0. No separate "round counter" infrastructure.
- **Pinia/Tauri/Vue domain-specific rules** — does not belong in a project-agnostic plugin. The `best_practice_violation` finding_type from v1.9.0 provides the taxonomy slot; specific rules live in user-project CLAUDE.md files, not plugin domains.

---

## Success criteria

Phase 2.5 is complete when:

- [ ] v1.8.1 ships: methodology contains the lift hierarchy, and a review of a guard-heavy diff produces recommendations that name lift alternatives (observable behavior change).
- [ ] v1.9.0 ships: output includes the extended `verdict` enum (with `refactor-recommended`), optional `correctness_severity` and `design_debt_severity` (shared enum with `findings[].severity`), and required `findings[].finding_type`. A review of a "correct but fragile" diff returns `verdict: refactor-recommended` without blocking ship. A v1.5-era payload re-run under v1.6 rules produces an identical verdict (compatibility property).
- [ ] v1.10.0 ships: git log scan runs on every review, and a multi-round iteration with `--prior-review` populates `patch_chain_risk` correctly. Signal fires on a test scenario with 3+ fix-prefixed commits on the same file; does not fire on a clean refactor.
- [ ] README reflects all three changes (same-commit-as-release convention from CLAUDE.md).

All three versions can be released over multiple days/weeks — no batching, each is useful on its own.

---

## Revision log

- **2026-04-14** — Initial spec written. Plugin at v1.8.0. Motivated by user feedback that 3-round iteration produced guard-cluster artifacts instead of organic findings. Collapsed a 7-item proposal to 3 shippable versions using the plugin's own lift hierarchy (writer lift on shared "prior state" concern, type lift on verdict taxonomy).

- **2026-04-14 (same-day revision)** — Applied devil-review v1.8.0 methodology to the plan itself per CLAUDE.md self-review discipline. Three blocking findings rolled in:

  1. **Semver misclassification (Finding 1 of self-review).** v1.9.0 as originally specced added four new **required top-level fields** plus a redefined `block` verdict semantic. Per CLAUDE.md semver rules, "verdict semantics redefined" and required top-level additions are major-bump triggers. Revised: new severity axes are now **optional** at top level; `finding_type` is required but **nested** inside the findings array (same shape as v1.4's additive nested extension); `block` semantic is preserved unchanged for v1.5-era payloads via a default-to-correctness rule for missing `finding_type`. v1.9.0 is now a genuine minor bump.

  2. **Writer-lift violation (Finding 2 of self-review).** The original plan introduced `primary_recommendation: "ship" | "iterate" | "refactor"` alongside the existing `verdict` enum, carrying overlapping exit-signal semantics with `verdict`. This violated the **writer lift** discipline the same plan was introducing in v1.8.1 — two writers of the same signal. Revised: `primary_recommendation` dropped entirely. `verdict` enum extended with a fourth value `refactor-recommended`. One exit signal, one writer.

  3. **Type inconsistency (Finding 3 of self-review).** The original plan gave `design_debt_severity` a different enum (`"none" | "low" | "medium" | "high"`, no `critical`) from the existing `findings[].severity` vocabulary. Two severity vocabularies for the same concept. Revised: single shared enum `"critical" | "high" | "medium" | "low" | "none"`. The business rule "design debt never blocks ship on its own" is now enforced in verdict derivation rule 3, not by amputating the enum.

  Deferred items from the self-review's `considered_not_promoted`:

  - Patch-chain threshold rationale was missing in the v1.10.0 spec. Addressed inline in v1.10.0 under **Threshold rationale (deferred from self-review)** — thresholds are acknowledged as uncalibrated starting values, to be revised in a v1.10.x patch bump after real usage.
  - `prior-review-overlap` signal (theme vs location) flagged but resolved by Finding 2's verdict consolidation — the overlap signal now feeds derivation rule 3 clause (c) rather than its own verdict axis.

  This revision follows CLAUDE.md's rule: "self-review findings rolled into the same commit must be called out in a dedicated section so the rationale for each fix is auditable." This section is that dedicated call-out.
