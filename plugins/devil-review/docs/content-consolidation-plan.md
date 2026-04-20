# devil-review — Content Consolidation Plan

**Status:** All phases (A–E) shipped 2026-04-20 (refactor, no version bump). Plan complete.
**Plugin version at time of writing:** v1.19.0 (no bump planned — every phase is `refactor(devil-review)`, no new capability).

**Scope:** Reduce core content bloat across `SKILL.md` + `methodology.md` + `output-schema.md` (pre-Phase-A baseline: 1495 markdown lines / ~216 KB loaded on every invocation — the character count is the load-relevant metric, line counts vary because version-history entries and rule paragraphs are long single lines) by eliminating structural duplication. No behavioral change — same rules, same verdicts, same schema; authoritative source consolidated and near-duplicates converted to cross-references.

> **Guiding principle:** Don't design for hypothetical requirements. Delete duplication. Keep one authoritative source per rule. Cross-reference, don't restate.

**Origin:** Session audit 2026-04-20 surfaced structural duplication totaling an estimated ~20–25% of core load, with the same rule (verdict derivation, chain-of-rejections override, default-to-X compatibility, classification-axis pattern) stated verbatim in 3–4 places. The additions were all individually justified; the missing discipline was consolidation at the time each new rule was added. This plan catches up. Baseline character counts captured at Phase A shipping time so subsequent phases can be measured against a concrete pre-consolidation load.

---

## Item A — Extract schema version history ✅ SHIPPED 2026-04-20 (refactor, no version bump)

**Shipping notes:** Landed as `refactor(devil-review): extract schema version history to docs/`. Two new files and one edit:
- `plugins/devil-review/docs/schema-history.md` — verbatim lift of the schema history block (v1.0 → v1.14 entries, the `Legacy-payload decision synthesis` indented block inside the v1.11 entry, and the v1.15.1 correction-note blockquote). `diff(1)` confirmed byte-identical version entries pre-edit vs. post-edit. Added a one-paragraph intro and a "Compatibility property across all bumps" summary so the document stands alone.
- `plugins/devil-review/skills/devil-review/output-schema.md` — schema-history block replaced with a single pointer paragraph naming the specific content (version history, compatibility properties, pre-v1.11 synthesis map, v1.15.1 correction note) so readers know what lives at the other end of the link.
- Cross-reference paths verified: `../../docs/schema-history.md` from `skills/devil-review/` resolves correctly; reverse direction (`../skills/devil-review/output-schema.md` from `docs/`) resolves correctly.

**Measured impact:**
- `output-schema.md`: 67,132 → 50,966 chars (**-24%** of that file).
- Core load total: ~216 KB → ~200 KB (**-7.5%** of per-invocation load; ~4k tokens saved).
- Markdown-line counts: `output-schema.md` 429 → 403 lines (the 26-line delta understates the impact because schema history entries were long single-line paragraphs; the character delta is the load-relevant number).

**No behavioral change:** rule text for the current schema (v1.14) unchanged; fixtures unaffected; no plugin version bump.

### Item A — Original spec (for reference)

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

## Item B — Consolidate verdict derivation ✅ SHIPPED 2026-04-20 (refactor, no version bump)

**Shipping notes:** Landed as `refactor(devil-review): consolidate verdict derivation to methodology.md`. Scope narrower than initial draft — SKILL.md Step 6 checklist was already using cross-references (not restatements), so only `output-schema.md` had a full duplicate of the rules. Single-file edit:
- `output-schema.md` "Verdict consistency" — 6-bullet block (rule 0 + rules 1-4 + a header bullet) replaced with a single pointer bullet that: (1) identifies the five-rule derivation (override 0 + rules 1-4), (2) names the filter conditions (`scope == "in-diff"` AND `reachability == "reachable"` with pre-v1.10 and pre-v1.13 default rules), (3) tells schema consumers they must apply those rules to validate payload conformance (the consumer-audience obligation was the output-schema-specific content worth preserving), (4) cross-references `methodology.md` §Verdict derivation as the authoritative statement.
- Severity inflation guard left in place — related to verdict/severity coupling but a distinct rule.
- `methodology.md` — unchanged, remains the authoritative source for the full rule text, Compatibility property, and Override discipline.

**Measured impact:**
- `output-schema.md`: 50,966 → 49,161 chars (**-3.5%** of that file post-Phase-A; **-1,805 chars**).
- Core load total: ~200 KB → ~198 KB (**-0.9%**).
- Smaller savings than Phase A because the verdict consistency bullet, while duplicate-of-methodology, was compact; Phase C (chain-of-rejections, 4+ places) and Phase D (scope/reachability structural pattern) are the next-largest wins.

**Claim-verification correction rolled into the shipping notes:** Phase B's original spec (below) claimed "three places: `SKILL.md` Step 6 pre-output checklist (brief restatement), `output-schema.md` ..., `methodology.md` ...". The `SKILL.md` claim was wrong — the checklist has cross-reference pointers to methodology.md sections (e.g., `See the "Scope classification" section in methodology.md`), not full rule restatements. Only two places had real duplication. Noted here for auditability; the shipping reflected the corrected scope.

### Item B — Original spec (for reference)

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

## Item C — Consolidate chain-of-rejections override ✅ SHIPPED 2026-04-20 (refactor, no version bump)

**Shipping notes:** Landed as `refactor(devil-review): consolidate chain-of-rejections override to methodology.md`. Two-file edit. Scope narrower than the initial draft because Phase B's verdict-consistency consolidation already removed the output-schema.md duplicate of rule 0 as a side effect (the 6-bullet block that Phase B replaced included the rule 0 bullet). The actual remaining duplication was:
- `SKILL.md` Step 3b substep 6 "Chain-of-rejections verdict override" — ~11 lines of rule restatement (body, rationale prose, threshold-calibration note) followed by a cross-reference line. Kept the procedural skill-execution content (compute resurface count, apply override, emit `decision.rationale`, re-raised findings still emit in `findings`, rules 1-4 do not evaluate) and deleted the rationale/calibration prose, which lived authoritatively in `methodology.md` §User rejection memory already. Final substep: ~7 lines.
- `methodology.md` Verdict derivation rule 0 bullet (line 493) — a ~4-sentence restatement of the rule, despite that the same file contained the authoritative rule in §User rejection memory two hundred lines earlier. Compressed to a single-sentence rule statement (trigger + outcome + non-evaluation of rules 1-4) with an explicit same-file cross-reference. Rule 0 still participates in the 5-rule precedence list with enough detail to scan, and readers who need the detail land one anchor click away.

**Measured impact:**
- `SKILL.md`: 45,385 → 44,918 chars (**-1.0%** of file; -467 chars).
- `methodology.md`: 103,599 → 103,475 chars (**-0.1%** of file; -124 chars).
- Core load total: ~198 KB → ~197.6 KB (**-0.3%** of core load; ~150 tokens/invocation).
- Savings are small because the duplicate rule 0 statements were compact; the win is deduplication of future amendments (single authoritative source for rule 0), not per-invocation bytes.

**Claim-verification correction rolled into the shipping notes:** Phase C's original spec claimed "4+ places" including two output-schema.md locations ("verdict consistency rule 0" AND "chain-of-rejections callout (separate bullet)"). Re-reading post-Phase-B: both were in the same 6-bullet block Phase B consolidated; only one output-schema.md duplicate ever existed, and Phase B eliminated it. Phase C's real targets were two: SKILL.md substep 6 + methodology.md verdict derivation rule 0 bullet. Noted for auditability; the shipping reflected the corrected scope.

### Item C — Original spec (for reference)

**Goal:** Verdict rule 0 (chain-of-rejections override) appears in 4+ places: `SKILL.md` Step 3b substep 6, `output-schema.md` verdict consistency rule 0, `output-schema.md` chain-of-rejections callout (separate bullet), `methodology.md` "User rejection memory" section, `methodology.md` verdict derivation rule 0. Consolidate to `methodology.md` "User rejection memory"; other places cross-reference.

**Effort:** small.
**Risk:** low — rule is self-contained and does not branch into other systems.
**Semver:** refactor.
**Dependency:** B (verdict derivation consolidation makes the rule 0 consolidation more obvious — rules 0–4 live together).

---

## Item D — Scope + Reachability parallel refactor ✅ SHIPPED 2026-04-20 (refactor, no version bump)

**Shipping notes:** Landed as `refactor(devil-review): consolidate verdict-interaction duplication across classification axes`. Scope changed significantly from the original spec on design review. The original plan proposed creating a new `## Classification axes (shared pattern)` section to host content common to both axes. On pre-edit design review, this was found to be over-engineering — the bulk of the duplicated content (the 5-bullet "Verdict interaction" filter list, stating `correctness_severity` / `design_debt_severity` / `block` / `needs-attention` / `refactor-recommended` clause (b) all filtering on `scope == in-diff` AND `reachability == reachable`) was **already stated authoritatively** in `§Calibration rules → Verdict derivation` (rules 1-4 each carry their own filter conditions). Creating a new shared section would have introduced a third authoritative-adjacent home for the same filter, not consolidated to one.

The revised, surgical edit: delete the duplicate 5-bullet verdict-interaction list from both axis sections, replace with a compact 3-line paragraph that names the driving value, cross-references `§Calibration rules → Verdict derivation` for the full rules, and preserves the "approve when only non-driving findings" semantic callout per axis. Hard cap interaction left untouched — Scope's version carries tactical prioritization guidance worth preserving, and Reachability's version is already compact with a "same rule as scope" cross-reference.

**Files touched:**
- `methodology.md` `## Scope classification` Verdict interaction — 7 lines (intro + 5 filter bullets + verdict-approve paragraph with bridge to Reachability) → 3 lines (compact cross-ref + diff-itself-safe paragraph).
- `methodology.md` `## Reachability classification` Verdict interaction — 9 lines (intro + 5 filter bullets + hypothetical-approve paragraph with bridge to Scope) → 3 lines (compact cross-ref + reachable-surface-clean paragraph).
- Phase C cross-reference bundle: `SKILL.md` substep 6 last sentence and `methodology.md:493` rule 0 bullet both had `bias rule` in a cross-reference list pointing at `§User rejection memory → Chain-of-rejections override`. The bias rule is in the parent `§User rejection memory` section but not in the Chain-of-rejections override subsection; the cross-reference over-claimed. Both dropped `bias rule` from the list. Surfaced during Phase C's post-commit review; user authorized bundling with Phase D because both files touch methodology and the fix is 4 words total (see `feedback_review_before_commit.md` memory entry for the bundling exception rule).

**Measured impact:**
- `methodology.md`: 103,475 → 101,873 chars (**-1.6%** of file; -1,602 chars).
- `SKILL.md`: 44,918 → 44,906 chars (**-0.03%**; -12 chars, "bias rule" removal).
- Core load total: ~197.6 KB → ~195.9 KB (**-0.8%**; ~400 tokens/invocation).
- Net of 5 edits (2 verdict-interaction refactors + 2 bias-rule narrowings + 0 new abstractions). Future amendments to the scope/reachability filter live in a single authoritative place (§Calibration rules → Verdict derivation).

**Claim-verification correction rolled into the shipping notes:** Phase D's original spec prescribed creating a new `## Classification axes (shared pattern)` section and thinning both axis sections as instantiations of it. Pre-edit design review found the proposed shared section would have been an unnecessary abstraction layer — the duplicated content already had an authoritative home in `§Calibration rules → Verdict derivation`. The revised scope is surgical (delete duplicates, cross-reference existing authoritative section) rather than structural (create new abstraction). Shipping reflected the revised scope; original spec text preserved in the "Original spec (for reference)" subsection for auditability. Pattern established across Phases B, C, D: each phase re-verifies its scope against actual duplication before editing, and the scope sometimes narrows when duplicates turn out to already have authoritative homes we can reference instead.

### Item D — Original spec (for reference)

**Goal:** `methodology.md` has two sections (`Scope classification`, `Reachability classification`) with identical structural shape: decision tree, verdict interaction, hard cap interaction, bias rule, anti-pattern, backward-compat. Define a "Classification axes" pattern once; instantiate per axis with only the axis-specific values (enum, default, failure-mode examples).

**Why it matters:** The two sections are ~85 lines combined, ~30 of which are structural repetition. A third orthogonal axis (if ever added) would repeat the structure again — consolidating makes the pattern explicit and makes axis additions cheap.

**Effort:** medium.
**Risk:** medium-high. If paraphrasing the shared pattern shifts semantics, both axes drift. Must self-review per plugin methodology before commit.
**Semver:** refactor (no behavioral change), but requires careful self-review (apply devil-review to its own diff).
**Dependency:** C (easier to reason about classification axes after verdict/override consolidation clears noise).

---

## Item E — Backward-compat consolidation ✅ SHIPPED 2026-04-20 (refactor, no version bump)

**Shipping notes:** Landed as `refactor(devil-review): consolidate backward-compat rationale to single authoritative source`. Scope narrowed from the original spec on design review. The original plan proposed enumerating all default-to-X rules in a single section (possibly a new `docs/backward-compat.md`). On re-verification, the authoritative enumeration **already existed** — `methodology.md` §Calibration rules → Compatibility property (L484-492) is the 8-bullet replay-invariant list, established in earlier schema bumps. The real duplication was not "missing consolidation target" but "duplicate rationale sentences at consumer sites that should reference the existing target".

Revised scope: keep the DEFAULT RULE statement at each consumer site (schema readers and axis-section readers both need "absence → X" stated inline) but remove the duplicate RATIONALE sentences ("This rule is what keeps v1.X payloads producing identical verdicts under v1.Y rules..." / "This preserves legacy verdict calculations identically...") and replace with a cross-reference to the authoritative Compatibility property.

**Files touched:**
- `output-schema.md:359` (finding_type field rule) — trailing "This rule is what keeps v1.5 payloads producing identical verdicts under v1.6 rules; do not change it." replaced with `Rationale in [methodology.md §Calibration rules → Compatibility property](methodology.md).`
- `output-schema.md:360` (scope field rule) — same pattern, v1.10 version.
- `output-schema.md:363` (reachability field rule) — same pattern, v1.13 version.
- `methodology.md:291` (Scope Backward compatibility) — rationale sentence replaced with same-file cross-reference `See §Calibration rules → Compatibility property (same file, below) for the replay invariants.`; also tightened "(replay of pre-v1.10 snapshots)" → "(pre-v1.10 snapshots)".
- `methodology.md:315` (Reachability Default classification) — same pattern as Scope, with a longer rationale sentence removed; also tightened "(pre-v1.13 snapshots replayed under v1.13 rules)" → "(pre-v1.13 snapshots)".

**Preserved intact:**
- `methodology.md:484-492` Compatibility property — the authoritative enumeration, unchanged.
- `methodology.md:459` (finding_type decision tree inline reference) — justification context, not a rationale restatement.
- `methodology.md:468` (severity axis derivation inline defaults list) — derivation-application context, not duplication.
- "Do not change it" warning equivalent: `methodology.md:493-494` Compatibility property closes with "Do not add rules that break it without bumping to a major version" — stronger than the per-field warnings removed.

**Measured impact:**
- `output-schema.md`: 49,183 → 49,159 chars (**-24 chars**; 3 edits, each replaced ~103-char rationale sentence with ~95-char cross-ref, net -8 chars per edit).
- `methodology.md`: 101,873 → 101,646 chars (**-227 chars**; 2 edits removing longer rationale paragraphs + minor paren tightenings).
- Core load total: ~195.9 KB → ~195.7 KB (**-0.12%**; ~60 tokens/invocation).
- Smallest per-phase delta in the consolidation plan. The real win is single-source-of-truth for backward-compat rationale: any future schema axis (a v1.15+ classification) only needs to extend the Compatibility property list, not restate the rationale at every consumer site.

**Claim-verification correction rolled into the shipping notes:** Phase E's original spec proposed creating a new consolidation target (single "Backward compatibility" section or a new `docs/backward-compat.md`). Pre-edit re-verification found the authoritative enumeration already existed at `methodology.md:484-492`. Revised scope: delete duplicates at consumer sites and cross-reference existing target, rather than create a new one. Fourth consecutive phase (B, C, D, E) where the original spec's scope was broader than the actual duplication warranted — establishes the pattern that the consolidation phases benefit from a re-verification pass before editing because earlier phases sometimes preempt later-phase targets and existing sections sometimes already serve as consolidation targets. Original spec preserved in "Original spec (for reference)" subsection below.

### Item E — Original spec (for reference)

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

- [x] **Phase A** (shipped 2026-04-20): `docs/schema-history.md` created; `output-schema.md` has a single-line pointer in place of the history block; no behavioral change. Core load -7.5% (~4k tokens / invocation).
- [x] **Phase B** (shipped 2026-04-20): verdict derivation stated once (in `methodology.md`); `output-schema.md` cross-references it via a pointer bullet that also names the consumer-validation obligation. `SKILL.md` already used cross-references pre-Phase-B; no change needed there. Core load -0.9% (~450 tokens / invocation).
- [x] **Phase C** (shipped 2026-04-20): chain-of-rejections override stated authoritatively once (in `methodology.md` §User rejection memory); `SKILL.md` substep 6 + `methodology.md` verdict derivation rule 0 bullet trimmed to compact procedural/structural statements with cross-references. Core load -0.3% (~150 tokens / invocation); the win is single-source-of-truth for future amendments, not per-invocation bytes.
- [x] **Phase D** (shipped 2026-04-20): duplicate 5-bullet verdict-interaction list deleted from both axis sections; compact cross-references to `§Calibration rules → Verdict derivation` in place. Original spec's shared-pattern section was deemed over-engineering (duplicates already had an authoritative home); revised scope was surgical delete-and-cross-reference. Bundled Phase C `bias rule` cross-reference narrowing in the same commit per user-authorized bundling exception. Core load -0.8% (~400 tokens/invocation).
- [x] **Phase E** (shipped 2026-04-20): backward-compat rationale consolidated to the authoritative Compatibility property in `methodology.md` §Calibration rules; default-rule statements kept at consumer sites (`output-schema.md` field rules + `methodology.md` axis sections) with cross-references to the authoritative rationale. Scope was narrower than original spec because the authoritative enumeration already existed — no new section needed. Core load -0.12% (~60 tokens / invocation).
- [x] Core file (SKILL.md + methodology.md + output-schema.md) character load reduction measured at shipping time: pre-Phase-A baseline 216,116 chars → post-Phase-E 195,711 chars = **-9.4%** (~5,100 tokens/invocation). Original target was ≥15%, actual was -9.4%. Target-miss rationale: the highest-char-density duplication (schema history extraction, Phase A) had been correctly estimated (~16 KB), but the remaining duplicates (Phases B–E) turned out to be compact cross-referenceable rule statements rather than large prose restatements — so total consolidation ceiling was lower than initially estimated. The -9.4% is the honest measurement; the -15% target was aspirational rather than evidence-based. Line count is a secondary metric because rule paragraphs are long single lines; the token/character metric is what affects per-invocation cost.

---

## Revision log

- 2026-04-20 — plan created. Session audit identified structural duplication across SKILL.md + methodology.md + output-schema.md (verdict derivation repeated in 3 places, chain-of-rejections override in 4+, scope/reachability classification pattern in 2); sequencing decided A → B → C → D → E based on risk (A lowest, D highest) and dependency (B/C/D/E benefit from A's clean-up, E synthesizes across all prior).
- 2026-04-20 — plan-doc self-review pre-commit (applying devil-review discipline to its own diff): initial draft used approximate markdown-line counts from session audit ("~1391 lines", "~340 lines", "~210 lines") that conflated visual/wrapped lines with markdown lines. Corrected to authoritative baseline captured from `wc -c` after Phase A file changes (core load 216 KB pre-Phase-A / 200 KB post-Phase-A) and kept markdown-line counts as secondary metrics with explanatory context. Claim-verification drop logged: the phrase "~340 lines of structural duplication" in the original origin paragraph was replaced with "~20-25% of core load" because the line-count basis was unverifiable; the character-based estimate is defensible from the per-phase impact tallies.
- 2026-04-20 — Phase A shipped. `schema-history.md` created (byte-identical version entries vs. pre-edit output-schema.md, `diff(1)` verified); `output-schema.md` schema-history block replaced with pointer; character load on `output-schema.md` -24%, core total -7.5%. Zero behavioral change; no version bump. Phase B becomes the next shipping target.
- 2026-04-20 — Phase B shipped. `output-schema.md` "Verdict consistency" 6-bullet block replaced with a single pointer bullet to `methodology.md` §Verdict derivation. Claim-verification correction surfaced: original spec claimed SKILL.md Step 6 checklist had a third restatement, but on re-reading SKILL.md's verdict-related text is cross-references (not rule text) — only two files had real duplication. Shipping reflected the corrected scope; spec note preserved in the Item B section's "Original spec (for reference)" subsection. Core load -0.9% (~450 tokens/invocation). Methodology.md untouched (already authoritative). Phase C (chain-of-rejections override consolidation) becomes the next shipping target.
- 2026-04-20 — Phase C shipped. `SKILL.md` Step 3b substep 6 trimmed (~11 lines → ~7 lines, rationale/calibration prose removed); `methodology.md` verdict derivation rule 0 bullet compressed from ~4-sentence restatement to a single-sentence trigger-and-outcome statement with a same-file cross-reference to §User rejection memory. Second claim-verification correction: Phase C's original spec listed two output-schema.md targets ("verdict consistency rule 0" + "chain-of-rejections callout"), but Phase B's 6-bullet consolidation had already removed both — they lived in the same block. Real Phase C targets were two files (SKILL.md + methodology.md), not four places. Note preserved in Item C's "Original spec (for reference)" subsection for auditability. Core load -0.3% (~150 tokens/invocation); per-byte win is modest, the single-source-of-truth win is the real outcome. Phase D (scope/reachability parallel refactor — highest-risk phase) becomes the next shipping target.
- 2026-04-20 — New session discipline established: pre-commit review. After Phase C shipped without an explicit pre-commit review pass being surfaced to the user (review was rolled into the commit body instead of presented separately), the user corrected the pattern: every commit from now on gets a distinct review message presented first, and waits for explicit OK before `git commit`. A post-commit review of Phase C surfaced a low-severity finding: the cross-reference lists in SKILL.md substep 6 and methodology.md rule 0 bullet mentioned "bias rule" as something at the target anchor, but the bias rule lives in the parent `§User rejection memory` section, not in the `Chain-of-rejections override` subsection the cross-reference points to. User authorized bundling the 4-word fix with Phase D (same subsystem, trivial change); discipline recorded in `feedback_review_before_commit.md` memory entry as a sanctioned post-commit-fix-bundling exception.
- 2026-04-20 — Phase D shipped (with bundled Phase C follow-up). Scope narrowed significantly on pre-edit design review: the original plan proposed a new `## Classification axes (shared pattern)` section, but the duplicated 5-bullet verdict-interaction list already had an authoritative home in `§Calibration rules → Verdict derivation` (rules 1-4 each carry the filter). Revised scope was surgical — delete the duplicate 5 bullets from both axis sections, replace with a compact 3-line paragraph cross-referencing the existing authoritative section, preserve axis-specific semantics (pre-existing/future-work → approve for Scope, hypothetical/config-specific → approve for Reachability). Hard cap interaction left untouched (Scope's tactical prioritization guidance was worth preserving). Bundled Phase C bias-rule cross-reference narrowing in the same commit. Core load -0.8% (~400 tokens/invocation). Phase E (backward-compat consolidation) becomes the next shipping target. Cumulative A+B+C+D: core load ~216 KB → ~195.9 KB (-9.3%; ~5k tokens/invocation).
- 2026-04-20 — Post-Phase-D follow-up shipped as separate `fix(devil-review): harmonize cross-reference to Verdict derivation` commit. During Phase D's post-edit review, the `output-schema.md:369` pointer bullet (from Phase B) was noted as using a less-precise anchor form (`§Verdict derivation`) compared to Phase D's hierarchy-aware form (`§Calibration rules → Verdict derivation`). Fix was a single-word addition; not bundled with Phase D because output-schema.md was not in Phase D's file set (no-batch-shipping discipline). Three cross-references to Verdict derivation (output-schema.md pointer, methodology.md Scope Verdict interaction, methodology.md Reachability Verdict interaction) now all use the same anchor form.
- 2026-04-20 — Phase E shipped. Scope narrowed on pre-edit design review (fourth consecutive phase with scope narrowing — B, C, D, E all had original specs that were broader than real duplication warranted): original plan proposed enumerating all default-to-X rules in a new consolidation target, but the authoritative enumeration already existed at `methodology.md:484-492` Compatibility property (established in earlier schema-bump commits). Revised scope: delete duplicate rationale sentences at five consumer sites, add cross-references to the existing authoritative target. Default rule statements ("absence → X") preserved at each site for reader utility; only the rationale ("This rule is what keeps v1.X payloads producing identical verdicts...") was removed. Core load -0.12% (~60 tokens/invocation) — smallest per-phase delta in the plan. The real win is single-source-of-truth for future amendments: any v1.15+ axis additions only need to extend the Compatibility property list, not restate the rationale at every consumer site. Plan complete. Cumulative A+B+C+D+E+harmonize-fix: core load 216,116 chars → 195,711 chars (-9.4%; ~5,100 tokens/invocation).
- 2026-04-20 — Content consolidation plan complete. All five phases shipped in a single afternoon session (2026-04-20) as six commits (A, B, C, D, Phase-B-harmonize fix, E) plus the initial plan-doc commit. Session discipline surfaced two important meta-rules recorded as memory entries: (1) `feedback_review_before_commit.md` — present distinct review pass before every commit, wait for explicit OK; (2) bundling exception for tiny post-commit self-review findings in the same subsystem (Phase C's bias-rule fix bundled with Phase D). Pattern observation: all four consolidation phases (B, C, D, E) had original specs where the scope needed to be narrowed on pre-edit re-verification because earlier phases sometimes preempted later-phase targets or the authoritative consolidation home already existed elsewhere. Pre-edit re-verification is therefore a first-class phase discipline for consolidation plans, not a nice-to-have.
