# devil-review — Content Consolidation Plan

**Status:** Phase A unstarted. Phases B–E unstarted.
**Plugin version at time of writing:** v1.19.0 (no bump planned — every phase is `refactor(devil-review)`, no new capability).

**Scope:** Reduce core content bloat across `SKILL.md` + `methodology.md` + `output-schema.md` (pre-Phase-A baseline: 1495 markdown lines / ~216 KB loaded on every invocation — the character count is the load-relevant metric, line counts vary because version-history entries and rule paragraphs are long single lines) by eliminating structural duplication. No behavioral change — same rules, same verdicts, same schema; authoritative source consolidated and near-duplicates converted to cross-references.

> **Guiding principle:** Don't design for hypothetical requirements. Delete duplication. Keep one authoritative source per rule. Cross-reference, don't restate.

**Origin:** Session audit 2026-04-20 surfaced structural duplication totaling an estimated ~20–25% of core load, with the same rule (verdict derivation, chain-of-rejections override, default-to-X compatibility, classification-axis pattern) stated verbatim in 3–4 places. The additions were all individually justified; the missing discipline was consolidation at the time each new rule was added. This plan catches up. Baseline character counts captured at Phase A shipping time so subsequent phases can be measured against a concrete pre-consolidation load.

---

## Item A — Extract schema version history

**Goal:** Move `output-schema.md` schema history section (25 markdown lines / ~16 KB — the entries are long single-line paragraphs, so markdown-line count understates the content weight; ~16 KB ≈ ~4k tokens of per-invocation load, v1.0 → v1.14 entries plus the embedded `Legacy-payload decision synthesis` block and the v1.15.1 correction note) to a new `docs/schema-history.md`. Replace in-file with a single pointer line to the new document.

**Why it matters:** Schema history is read on every `/devil-review` invocation but is only consulted by consumers replaying legacy payloads — the common path does not need it. Moving it out keeps the current schema document focused on what's current.

**Shape:**
- `plugins/devil-review/docs/schema-history.md` (new) — verbatim lift of the current schema history block plus a one-paragraph intro explaining the document's purpose and its relationship to `output-schema.md`.
- `plugins/devil-review/skills/devil-review/output-schema.md` — schema history block replaced with: `**Current schema version: \`1.14\`.** Full version history, compatibility properties, and legacy-payload handling rules: [\`../../docs/schema-history.md\`](../../docs/schema-history.md).`

**Effort:** small. Pure lift-and-shift; no rule rewrites.
**Risk:** low. No semantic change. Cross-reference target exists before the pointer is emitted (create history file first, then edit output-schema.md).
**Semver:** refactor — no plugin version bump.
**Dependency:** none.

---

## Item B — Consolidate verdict derivation

**Goal:** The same 5-rule verdict derivation (override 0 + rules 1–4) appears in three places: `SKILL.md` Step 6 pre-output checklist (brief restatement), `output-schema.md` "Verdict consistency" rules (~25 lines), `methodology.md` "Verdict derivation" section (~25 lines). Pick `methodology.md` as authoritative; the other two become one-line cross-references.

**Why it matters:** Three wordings of the same rule means any future amendment has three places to update. In practice that means amendments drift — the schema v1.15.1 correction already landed in two places and left one stale text pocket (caught by this audit).

**Shape:**
- `methodology.md` "Verdict derivation" — unchanged, remains authoritative.
- `output-schema.md` "Verdict consistency" — replaced with: `**Verdict derivation rules** live in [\`methodology.md\` §Verdict derivation](methodology.md). This document only restates the five-value enum and the required pairing with \`decision.action\`.`
- `SKILL.md` Step 6 pre-output checklist — verdict-derivation bullet converted to a cross-reference to the methodology section; the checklist keeps the "verify this is emitted" responsibility, not the rule text.

**Effort:** medium. Requires careful cross-reference wording so readers on any path still reach the authoritative rule.
**Risk:** medium. If the cross-reference is too terse, readers may miss that the full rule lives in `methodology.md`.
**Semver:** refactor.
**Dependency:** A (history moved out first keeps `output-schema.md` focused so the verdict-consistency edit is cleaner).

---

## Item C — Consolidate chain-of-rejections override

**Goal:** Verdict rule 0 (chain-of-rejections override) appears in 4+ places: `SKILL.md` Step 3b substep 6, `output-schema.md` verdict consistency rule 0, `output-schema.md` chain-of-rejections callout (separate bullet), `methodology.md` "User rejection memory" section, `methodology.md` verdict derivation rule 0. Consolidate to `methodology.md` "User rejection memory"; other places cross-reference.

**Effort:** small.
**Risk:** low — rule is self-contained and does not branch into other systems.
**Semver:** refactor.
**Dependency:** B (verdict derivation consolidation makes the rule 0 consolidation more obvious — rules 0–4 live together).

---

## Item D — Scope + Reachability parallel refactor

**Goal:** `methodology.md` has two sections (`Scope classification`, `Reachability classification`) with identical structural shape: decision tree, verdict interaction, hard cap interaction, bias rule, anti-pattern, backward-compat. Define a "Classification axes" pattern once; instantiate per axis with only the axis-specific values (enum, default, failure-mode examples).

**Why it matters:** The two sections are ~85 lines combined, ~30 of which are structural repetition. A third orthogonal axis (if ever added) would repeat the structure again — consolidating makes the pattern explicit and makes axis additions cheap.

**Effort:** medium.
**Risk:** medium-high. If paraphrasing the shared pattern shifts semantics, both axes drift. Must self-review per plugin methodology before commit.
**Semver:** refactor (no behavioral change), but requires careful self-review (apply devil-review to its own diff).
**Dependency:** C (easier to reason about classification axes after verdict/override consolidation clears noise).

---

## Item E — Backward-compat consolidation

**Goal:** "default-to-correctness", "default-to-in-diff", "default-to-reachable" compatibility rules appear scattered through `output-schema.md` field rules and `methodology.md` verdict-derivation compatibility property. Single "Backward compatibility" section in `output-schema.md` (or a new short `docs/backward-compat.md` if the section grows) enumerates all default-to-X rules; other places cross-reference.

**Effort:** small.
**Risk:** low.
**Semver:** refactor.
**Dependency:** A, B, C, D (last to land — compat rules are derived from the consolidated rules and it's easier to enumerate once the rules are deduplicated).

---

## Sequencing

A → B → C → D → E.

Rationale:
- **A first** because it is risk-free and captures the biggest win (~200 lines, ~%15 of core load) with zero semantic concern. Unblocks the remaining phases by making `output-schema.md` more navigable.
- **B before C** because chain-of-rejections (C) is one of the verdict derivation rules (rule 0) — consolidating verdict derivation (B) first puts rule 0 in context.
- **D after C** because scope/reachability classifications interact with verdict derivation; cleaning verdict first makes the classification pattern clearer.
- **E last** because it synthesizes across A–D; listing all `default-to-X` rules makes more sense after their home sections are consolidated.

**No batch shipping.** Each item ships as its own commit with its own self-review. See `.claude/rules/no-batch-shipping.md`.

---

## Success criteria

- [ ] **Phase A**: `docs/schema-history.md` created; `output-schema.md` has a single-line pointer in place of the history block; no behavioral change.
- [ ] **Phase B**: verdict derivation stated once (in `methodology.md`); `SKILL.md` + `output-schema.md` cross-reference it.
- [ ] **Phase C**: chain-of-rejections override stated once (in `methodology.md`); other mentions cross-reference.
- [ ] **Phase D**: classification axes pattern defined once; scope and reachability sections are thin instantiations.
- [ ] **Phase E**: backward-compat default-to-X rules enumerated in one section.
- [ ] Core file (SKILL.md + methodology.md + output-schema.md) character load reduced by ≥15% from pre-Phase-A baseline (~216 KB → ≤ ~184 KB). Line count is a secondary metric because rule paragraphs are long single lines; the token/character metric is what affects per-invocation cost.

---

## Revision log

- 2026-04-20 — plan created. Session audit identified structural duplication across SKILL.md + methodology.md + output-schema.md (verdict derivation repeated in 3 places, chain-of-rejections override in 4+, scope/reachability classification pattern in 2); sequencing decided A → B → C → D → E based on risk (A lowest, D highest) and dependency (B/C/D/E benefit from A's clean-up, E synthesizes across all prior).
- 2026-04-20 — plan-doc self-review pre-commit (applying devil-review discipline to its own diff): initial draft used approximate markdown-line counts from session audit ("~1391 lines", "~340 lines", "~210 lines") that conflated visual/wrapped lines with markdown lines. Corrected to authoritative baseline captured from `wc -c` after Phase A file changes (core load 216 KB pre-Phase-A / 200 KB post-Phase-A) and kept markdown-line counts as secondary metrics with explanatory context. Claim-verification drop logged: the phrase "~340 lines of structural duplication" in the original origin paragraph was replaced with "~20-25% of core load" because the line-count basis was unverifiable; the character-based estimate is defensible from the per-phase impact tallies.
