# devil-review — Phase 3 Plan

**Status:** Item 1 shipped 2026-04-14 (v1.10.0). Items 6, 7, 8, 9 shipped 2026-04-15 (v1.12.0 / v1.13.0 / v1.14.0 / v1.15.0 + v1.15.1 patch). Items 12, 11, 10 shipped 2026-04-15 (v1.16.0 / v1.17.0 / v1.18.0) — saha-test-#3 menu complete. Item 10's UX relocated to a `--reject` inline flag in v1.19.0 (2026-04-15, same-day). Items 2, 3, 4, 5 remain unstarted (demand-gated per original policy). Item 14 (fixture 04 for chain-of-rejections override coverage) added 2026-04-15 post-v1.18.0 review — unstarted, trigger-gated. Items 15, 16, 17 added 2026-04-26 from saha test #4 (cross-model adversarial comparison: codex vs devil-review) — unstarted, ship as series 15 → 16 → 17.
**Plugin version at time of writing:** v1.3.2 (initial spec); v1.10.0 (Item 1 shipping); v1.11.0 (auto-detect prior-review); v1.12.0–v1.15.0 (saha-test-#2 shipping series 2026-04-15); v1.15.1 (patch correction); v1.16.0–v1.18.0 (saha-test-#3 shipping series 2026-04-15); v1.19.0 (UX relocation same-day); v1.19.1 (content-consolidation completion 2026-04-20); v1.19.2 (skill-quality patch 2026-07-17); v1.20.0 (rejection-memory hardening 2026-07-17); v1.21.0+ targets unstarted (saha-test-#4 series)
**Scope:** Everything deferred out of v1.3.x. Phase 1 (architecture) and Phase 2 (content) landed in v1.3.0; patches in v1.3.1/v1.3.2. Phase 3 is the "durability & maturation" bucket — optional, pickable à la carte after real usage feedback.

> **Guiding principle:** Don't design for hypothetical requirements. Every Phase 3 item is justified against an observed gap, not a theoretical one. Use the skill in real PRs first; let friction dictate priority.

---

## Item 1 — `fixtures/` regression harness ✅ SHIPPED 2026-04-14

**Shipping notes:** Landed in the `feat(devil-review): add fixtures regression harness` commit. Three fixtures created under `plugins/devil-review/fixtures/`:
- `01-guard-cluster-refactor/` — exercises Phase 2.5 features (lift hierarchy, patch-chain detection, `refactor-recommended` verdict, `finding_type: design_debt`, `lift_considered` schema)
- `02-clean-refactor/` — exercises the absence of findings; a symbol rename with all callers updated must return `verdict: approve` with empty `findings` and non-empty Trace Log
- `03-unsafe-migration/` — exercises `domains/data.md` + `verdict: block` path; NOT NULL column on large existing table without default

**Known gaps after shipping:**
- `last-snapshot.md` files are intentionally absent on initial fixture creation; the first real skill run captures them.
- No automated runner; the harness is manual per the plan's original decision.
- The `01-guard-cluster-refactor` fixture's expected-findings.md deliberately matches the v1.10.1 (post-fix) behavior for `lift_considered` semantics, not the v1.10.0 behavior. This fixture would fail against v1.10.0 output — which is the entire point of having fixtures. Running it against v1.10.0 surfaces the Finding 1 schema inconsistency concretely.

**Shipping trigger:** Phase 2.5 shipping landed v1.8.1 + v1.9.0 + v1.10.0 across three commits, and an adversarial self-review found 3 findings (all `no-test`). The fixture harness moved from "optional, pickable after real usage" to "blocker on the next prompt edit" because schema evolution without regression tests was visibly producing the same class of bugs repeatedly. This is the "real usage" signal the plan specified.

---

## Item 1 — Original spec (for reference)

**Goal:** Detect prompt-change regressions. When SKILL.md, methodology.md, output-schema.md, or any `domains/*.md` is edited, we want a disciplined way to answer "did this make the skill better, or did it silently break a known-good case?"

**Why it matters:** The skill *is* a prompt. A prompt change is a software change with no compiler, no type system, and no test suite. Right now any regression would be caught only by a user reporting bad output on a real PR. Fixtures give us a pre-commit sanity check.

**Non-goals:**
- Not a CI gate (no GitHub Action). Manual snapshot discipline only.
- Not a full eval suite. We're looking for "obvious regression", not "measuring model quality".
- Not an exhaustive corpus. 3–5 fixtures, hand-picked for diversity.

**Shape:**
```
plugins/devil-review/fixtures/
├── README.md                          # how to run, how to update snapshots
├── 01-ui-multi-instance/
│   ├── diff.patch                     # synthetic or real-anonymized diff
│   ├── context.md                     # minimal repo context the skill needs
│   ├── expected-findings.md           # loose must-contain assertions
│   └── last-snapshot.md               # last known-good output (gitignored? or tracked?)
├── 02-clean-refactor/
│   └── ...                            # expected: approve, empty findings, non-empty trace log
├── 03-unsafe-migration/
│   └── ...                            # expected: block, at least one critical finding
```

**Fixture selection criteria:**
1. **`01-ui-multi-instance`** — exercises `domains/ui.md` multi-instance / sibling visibility checklist. The original Phase 1/2 work was motivated by a UI bug of this shape, so it's the strongest anti-regression target.
2. **`02-clean-refactor`** — exercises the *absence* of findings. This is the hardest test: a skill that always finds something is a broken skill. Clean refactor must return `verdict: approve, findings: []` with a non-empty Trace Log. If this fixture ever fires findings, we have false-positive drift.
3. **`03-unsafe-migration`** — exercises `domains/data.md` + verdict escalation to `block`. Validates the `block` verdict path end-to-end.

**`expected-findings.md` format** (loose match, not diff):
```markdown
## Must contain
- verdict: block
- at least one finding with severity in {critical, high}
- finding references file: migrations/0042_...sql
- Trace Log includes architectural_decisions_checked entry

## Must NOT contain
- any finding with "consider adding a comment"
- any finding padding beyond the hard cap (≤5)
```

**Runner:** Manual. There is no harness executable.
1. `cd fixtures/01-ui-multi-instance/`
2. Feed `diff.patch` + `context.md` to the skill in a scratch checkout
3. Capture output to `last-snapshot.md`
4. Human eyeballs `expected-findings.md` assertions against `last-snapshot.md`
5. If intentional change: update snapshot + commit. If regression: fix skill, re-run.

**Estimated effort:** 1.5–2 hours. Fixture authoring is the bulk; each fixture needs a believable diff + just enough context.

**Dependency:** None. Can start anytime.

**Open question:** Should `last-snapshot.md` be tracked in git or gitignored? Tracked = diff reviewable, but creates commit churn every time the model's phrasing shifts. Gitignored = noise-free but loses history. **Lean tracked**, accept the churn, because snapshot diffs are the whole point of the regression signal.

---

## Item 2 — README good/bad output example

**Goal:** Onboarding. New users should see one concrete "this is what a good devil-review looks like" and one "this is what a bad one looks like" side-by-side, not just an abstract format template.

**Why it matters:** The current README shows the schema. It does not show a *reviewed artifact*. A new user has no intuition for what "finding bar" or "trace log discipline" actually produces. A worked example closes that gap in 5 minutes of reading.

**Shape:** Two new sections in `plugins/devil-review/README.md`:

### Good example
- Short synthetic diff (20–30 lines, self-contained, no external context needed)
- Full devil-review output:
  - Verdict: `needs-attention`
  - 1–2 findings, both high-signal, both grounded in the diff with line refs
  - Trace Log with 3–4 symbols inspected, 1 architectural decision checked, 2 scenarios considered
  - No padding, no hedging, no "consider adding…"

### Bad example (anti-pattern gallery)
- Same diff
- Broken output showing the anti-patterns the skill should *not* produce:
  - 5 findings, 3 of them cosmetic/padding
  - Empty Trace Log (`symbols_inspected: []`)
  - Hedging language ("might want to consider", "potentially", "could possibly")
  - Findings without file:line refs
  - Verdict says `approve` but findings list is non-empty (schema violation)
- Annotated: each anti-pattern gets a sidebar comment explaining *why* it's bad.

**Estimated effort:** 30–45 minutes. Writing a convincing bad example takes almost as long as writing a good one because each anti-pattern must map to a real rule in methodology.md.

**Dependency:** None. But ideally done *after* real usage, so the example reflects observed failure modes, not imagined ones.

**Risk:** Zero. Doc-only change.

---

## Item 3 — `agent: Explore` decision

**Goal:** Verify (or overturn) the choice of `agent: Explore` in SKILL.md.

**Background:** Explore is documented as "fast agent specialized for exploring codebases… quick/medium/very thorough". devil-review is a deep, slow, adversarial review. The semantic mismatch was flagged during Phase 1 but deferred because changing it requires empirical evidence, not reasoning.

**The question:** Is Explore the right substrate for adversarial review, or does it bias the skill toward breadth-first file-hopping when we want depth-first consequence-tracing?

**Hypotheses:**
- **H1:** Explore is fine. Its "very thorough" mode is what we want. No change.
- **H2:** Explore leaks breadth-first bias into review output — shallow findings, lots of file mentions, not enough consequence tracing. Switch to default / general-purpose.
- **H3:** The choice doesn't matter because `context: fork` dominates behavior. Remove `agent:` entirely.

**Test protocol:**
1. Pick one fixture from Item 1 (preferably `01-ui-multi-instance` — has depth).
2. Run the skill 3 times with each config: `agent: Explore`, no `agent:` line, `agent: general-purpose` (if available).
3. For each run, score on 4 axes (1–5):
   - Finding groundedness (file:line refs, quote from diff)
   - Consequence depth (downstream effects traced vs. just "this function looks wrong")
   - Trace Log richness (symbols_inspected × scenarios_considered)
   - False-positive rate (findings that don't survive scrutiny)
4. 9 runs total. Average scores per config. Pick the winner.

**Estimated effort:** 2 hours. Nine full skill runs + scoring.

**Dependency:** **Item 1 must be done first.** You can't run this test without fixtures.

**Defer trigger:** If Item 1 ships and the skill's real-usage output already feels deep enough, drop Item 3 entirely. "Works in practice" beats "proven in test".

---

## Item 4 — Deferred domains (demand-gated)

**Policy:** Do not add speculatively. Add only when the user is actively working in a project that would exercise the domain.

**Queue:**
- **`domains/iac.md`** — Terraform / Pulumi / Kubernetes / Helm. Checklist focus: state drift, blast radius of plan/apply, secret exposure in tfvars, module versioning, destroy ordering, provider upgrade gotchas.
- **`domains/graphql.md`** — N+1 / DataLoader misuse, query complexity / depth limits, schema evolution (breaking vs. non-breaking), nullable field semantics, resolver error propagation, federation gotchas.
- **`domains/nosql.md`** — eventual consistency boundaries, hot partitions, document shape evolution, missing indexes, scan-vs-query cost, TTL + GSI interactions, transaction scope limits.

**Each domain estimated at:** ~1 hour — skeleton follows `domains/ui.md` shape (Load when / anti-patterns / required checks / trace log hints).

**Trigger:** "I'm reviewing a [terraform|graphql|dynamo|etc.] PR and devil-review felt shallow on it." Until that sentence exists, domains stay in the queue.

---

## Item 5 — Dynamic domain discovery

**Goal:** Replace the hardcoded domain table in SKILL.md with a `Glob("domains/*.md")` + frontmatter-driven trigger system, so adding a domain requires zero SKILL.md edits.

**Proposed domain frontmatter:**
```yaml
---
name: ui
triggers:
  extensions: [.vue, .jsx, .tsx, .svelte]
  path_patterns: [components/**, views/**, pages/**]
  keywords: [component, render, mount]
load_priority: high
---
```

**SKILL.md change:** Step 3 becomes:
1. `Glob("skills/devil-review/domains/*.md")`
2. For each file, read frontmatter only (cheap — ~20 lines)
3. Match frontmatter triggers against changed files in the diff
4. For matched domains, read the full file

**Why defer:** With 8 domains, the hardcoded table in SKILL.md is fine. Dynamic discovery pays off at 15+ domains or when external contributors start adding domains and can't be trusted to keep the SKILL.md table in sync. We're at 8 and single-maintainer. Premature.

**Re-evaluate at:** 12 domains OR first external domain contribution, whichever comes first.

**Estimated effort:** 1.5 hours. Small, but needs careful testing — all 8 existing domains must keep loading correctly after the refactor.

**Risk:** Medium. Changes the load path for every domain. One bug = skill loads wrong domains.

---

## Item 6 — Structured prior-review attribution ✅ SHIPPED 2026-04-15 (v1.15.0 / schema v1.11)

**Shipping notes:** Landed as `feat(devil-review): v1.15.0 structured prior-review attribution (Item 6 expanded)`. Shipped the full expanded spec: per-finding `prior_relation`, `trace_log.prior_review_summary`, top-level `decision` block, severity dampening rule, chain-closing override clause (c) on verdict rule 3, and the distinction between session-scoped `decision.patch_chain_detected` and git-log-scoped `trace_log.patch_chain_risk.detected`. Fixtures 01/02/03 updated with decision block assertions covering ship/iterate/iterate cases and the legitimate verdict-vs-decision-action disagreement on fixture 01 (refactor-recommended + iterate at iteration 1).

**Original spec preserved below for reference.**

---


**Goal:** Turn the prose attribution that prior-review-overlap currently produces into a machine-readable shape, so downstream automation (commit bots, PR decorators, dashboards) can reason about "which findings resolved, which carried over, which are new drift" without parsing narrative text.

**Why it matters (observed, not speculative):** Saha testinde prior-review flag'iyle çalıştırılan bir review explicit olarak "prior findings resolved, new findings are introduced by the fix or already existed — not a patch-chain pattern" framing'i üretti ve verdict'i `refactor-recommended`'e eskalasyondan dampened. Attribution bu noktada en büyük değerdi — bulguyu körlemesine verdict'e çevirmek yerine "bunlar gerçekten yeni mi yoksa prior-işaret mi" diye gating. Ama bu bilgi şu anda **prose** olarak yaşıyor (`theme_assessment`, finding body annotation "This location also appeared in the prior review as finding #N"). Automation consumer onu parse edemez.

**Non-goals:**
- Otomatik resolution detection (LLM reviewer'ın görsel kararı yerine heuristic). Reviewer-gated kalacak.
- Prior-review dependency'yi zorunlu yapmak. Auto-detect miss durumunda alan omittable.
- Multi-round accumulation (chain_depth round counter). Single-step karşılaştırma korunacak — see methodology.md "Scope: single-step, single-session" rule.

**Shape (target v1.12.0 minor, schema v1.8):**

Finding-level, optional:
```json
{
  "severity": "medium",
  "finding_type": "design_debt",
  "prior_relation": {
    "category": "carries-over | resolved | new-drift-from-fix | pre-existing-orthogonal",
    "prior_finding_ref": "<prior finding title quoted verbatim, or null>"
  }
}
```

Top-level `trace_log`, optional (only when prior was loaded):
```json
"prior_review_summary": {
  "total_in_prior": 3,
  "resolved": 2,
  "still_open": 0,
  "new_drift_introduced": 1,
  "pre_existing_unrelated": 0
}
```

**Verdict derivation integration:** Extend rule 3 with a new clause (c) — "chain closing if `resolved` ≥ `still_open + new_drift_introduced`, do not escalate to `refactor-recommended` even if `design_debt_severity` is high". This operationalizes the dampening the reviewer performed manually in the saha test.

**Methodology addition:** new subsection under "Patch-chain detection" titled "Prior-relation classification" with the four categories decision tree:
- `carries-over` — same invariant violation present in both prior and current state (fix did not address, or addressed partially)
- `resolved` — prior finding's location is no longer a finding in current state (fix worked)
- `new-drift-from-fix` — finding at a location introduced or changed by the prior fixes (fix opened a new foot-gun)
- `pre-existing-orthogonal` — finding at a location the prior review did not reach AND the prior fix did not touch (existed in the code before the fix, reviewer just missed it then)

**Backward compatibility:**
- Fields are optional. v1.7 consumers parse v1.8 payloads without error.
- Absence of `prior_relation` on a finding = same as pre-v1.8 behavior (no attribution).
- `prior_review_summary` omitted when no prior was loaded (which is already the case for the fields that depend on it).

**Estimated effort:** 2–3 hours. Methodology subsection, schema fields, JSON rules, verdict derivation rule 3 update, README prose for new fields, semver rationale.

**Dependency:** None. Shippable alongside or after Item 2/3/4/5 independently.

**Trigger to activate:**
- First automation consumer appears (commit bot writing "resolves: prior#2", PR decorator showing resolution counts, dashboard aggregating across reviews)
- OR a concrete saha test where prose attribution was insufficient and the reviewer needed structured fields to reason
- OR user reports "I can't tell at a glance which findings are the real new bugs vs residual drift"

Until one of these fires, prose attribution is considered sufficient per the existing saha test ("mekanizma iş görüyor").

**Risk:** Low–medium. New emission burden on every finding when prior loaded (one more object per finding). LLM classification of the four categories is ambiguous in edge cases (e.g., "fix touched this line and a new issue appeared — is it `new-drift-from-fix` or `pre-existing-orthogonal` the fix didn't cause but highlighted?"). Decision tree above covers the common cases; edge cases fall back to `pre-existing-orthogonal` per the "when in doubt, drop severity" spirit.

### 2026-04-15 update — saha test #2 triggered + expanded Item 6

**Trigger fired.** Second real-usage saha test (two-round devil-review on the same project) produced concrete observations that activate Item 6's "user reports 'I can't tell at a glance which findings are the real new bugs vs residual drift'" trigger. Reviewer ran Round 2 after applying Round 1's fixes; Round 2 re-flagged a Round 1 finding at lower severity (`medium / design_debt`) without crediting the prior round. Prose attribution mechanism (v1.11.0) worked for the *review framing* but did not surface **which individual findings resurfaced**.

**Expansion 1 — severity dampening for re-surfaced findings (new rule in methodology):**

When `prior_relation.category == "carries-over"` on a finding:
- If prior severity was `high` or `critical` and current state still exhibits the same invariant violation → hold severity at prior level (do not silently demote).
- If the finding is a re-surface at equal-or-lower severity compared to prior → bar is raised: only emit if the reviewer can articulate *why* the prior fix did not address it. If the "why" is "fix was unrelated to this aspect", reclassify as `pre-existing-orthogonal` and drop severity one notch, not two.
- Net effect: resurfaced findings either get credit (same severity + carries-over tag, reviewer-visible) or get dropped. They do NOT get silently downgraded to noise.

**Expansion 2 — top-level machine-readable decision field (new schema addition):**

In addition to `verdict`, emit a top-level `decision` block:
```json
"decision": {
  "action": "iterate | stop-and-refactor | ship",
  "patch_chain_detected": true,
  "iteration_count": 2,
  "rationale": "<one-sentence why>"
}
```

Derivation rules:
- `patch_chain_detected: true` iff prior review was loaded AND ≥1 finding has `prior_relation.category == "carries-over"` AND the current diff touches the same files as the prior diff AND the new finding count is not materially lower than prior.
- `action: stop-and-refactor` iff `patch_chain_detected` AND `iteration_count ≥ 2`. Overrides `verdict` for automation purposes; `verdict` remains prose-facing, `decision.action` is script-facing.
- `action: ship` iff `verdict: approve` AND prior review shows `resolved ≥ still_open + new_drift_introduced` (chain closing).
- `action: iterate` otherwise.
- `iteration_count` derived from prior-review session metadata; defaults to 1 when no prior loaded.

**Why expand now, not later:** the field is the missing piece for CI gating and `/loop`-style auto-stop. Saha test reviewer explicitly called it out: "Script-okunabilir bir field gerek: decision: iterate | stop-and-refactor | ship, patch_chain_detected: true/false, iteration_count: N". Without it, patch-chain dampening stays prose-bound and automation remains impossible.

**Revised effort estimate:** 3–4 hours (was 2–3). Methodology additions, schema fields for both `prior_relation` and `decision`, verdict-derivation rule update, README prose, fixture regression (01-guard-cluster-refactor fixture needs `decision` assertions).

**Backward compatibility:** `decision` block is additive. Absence = pre-expansion behavior. Fixture snapshots must be re-captured; schema consumers parsing only `verdict` continue to work.

---

## Item 7 — Self-fact-check pass ✅ SHIPPED 2026-04-15 (v1.12.0 / schema v1.8)

**Shipping notes:** Landed as `feat(devil-review): v1.12.0 self-fact-check pass (Item 7)`. Added methodology section "Claim verification pass (pre-emit)" with four bug classes (asymmetry error, unsupported reachability, scope inflation, counterfactual leak) and four-step verification procedure. New required `trace_log.findings_dropped_in_verification` array with six-value reason enum. Pre-output checklist bullet + Final check "claim-verified" bullet added. Fixtures 01/02/03 updated to assert field presence.

**Original spec preserved below for reference.**

---



**Goal:** Before emitting findings, reviewer verifies each claim against the diff/code it references. Catch factual over-claims and unsupported reachability assertions in the reviewer's own output.

**Why it matters (observed, not speculative):** Saha test #2 produced two concrete factual errors in reviewer output:
1. "Only surfaces the proposal-delete error when both fail" — actually surfaces when either fails; asymmetry is only in the both-fail case. Partially wrong.
2. "Widened here because zero-source globs ... no-write/no-delete code path" — in reality cancel/retry paths all route to cleanup; widening was theoretical. Unsupported reachability claim.

These are credibility bugs. A reviewer that over-claims once loses authority for the entire review. Every other Phase 3 item is gated on this floor: no point shipping structured attribution if the attributed claims are factually wrong.

**Non-goals:**
- Not a formal verification system. Reviewer's best-effort re-check against visible code, not a proof.
- Not re-running the whole review. One additional pass over emitted findings only.

**Shape:** New methodology subsection titled "Claim verification pass (pre-emit)". Added to SKILL.md Step 6 (post-finding-generation, pre-emit):

For each candidate finding:
1. **Restate the load-bearing claim** in one sentence (e.g., "this path is unreachable when X", "this function overwrites Y when Z").
2. **Locate supporting evidence** in the diff or in the referenced code (file:line). Quote 1–3 lines.
3. **Check for falsifiers** — is there any visible branch, caller, or code path that contradicts the claim? If yes, either narrow the claim or drop the finding.
4. **Reachability claims** specifically: if the finding says "widened / narrowed / unreachable / only-fires-when", trace at least one concrete call path from an entry point to the claimed behavior. If no path can be stated, reclassify the finding from behavioral to structural (e.g., "this branch is hard to reason about" instead of "this branch is unreachable").

**Emit constraint:** findings that fail the verification pass are either narrowed, reclassified, or dropped. Dropped findings are noted in the trace log as `findings_dropped_in_verification: [{original_claim, reason}]` — visible evidence that the pass fired.

**Estimated effort:** 1.5–2 hours. Methodology subsection, SKILL.md step insertion, trace-log field addition, one fixture update (02-clean-refactor) to demonstrate the empty `findings_dropped_in_verification: []` case.

**Dependency:** None. Should ship *before* Item 6 expansion — structured attribution on unverified claims is worse than prose attribution on verified ones.

**Risk:** Low. Pure methodology addition. Risk is only that the LLM treats the pass as performative ("I verified") without actually doing it — mitigation is to require the quote-1-to-3-lines step as visible evidence in the trace log.

**Semver:** minor bump (new mandatory methodology pass + new trace-log field).

---

## Item 8 — Project-rule citation loader ✅ SHIPPED 2026-04-15 (v1.13.0 / schema v1.9)

**Shipping notes:** Landed as `feat(devil-review): v1.13.0 project-rule citation loader (Item 8)`. Added SKILL.md Step 5.2b "Project review rules" with 10-file / 30 KB caps and the four glob patterns. New required `trace_log.project_rules_loaded` (array of `{path, bytes}`) and optional `findings[].rule_refs` (array of `{source, rule, quote}`) with verbatim-quote anti-hallucination gate. Methodology section "Project-rule citation" articulates the cite-don't-drop distinction from pre-review context, the multi-rule cap of 3, and the interaction with Claim verification. Fixture 01 ships a synthetic `.claude/rules/no-patches.md` rule file to exercise citation end-to-end; fixtures 02/03 assert empty-list behavior.

**Original spec preserved below for reference.**

---



**Goal:** When the project contains explicit rule files (`.claude/rules/*.md`, `CLAUDE.md`, `code-review.md`, or similar), load them as part of review setup and tag each finding with the specific rule it cites.

**Why it matters (observed, not speculative):** Saha test #2 project had `.claude/rules/no-patches.md` and `code-review.md` present. Reviewer's output implicitly followed those rules (e.g., "writer-lift önerisi no-patches.md'ye bire bir oturdu") but did not explicitly cite them. Reviewer feedback: *"plugin bunları load edip her finding'i ilgili kuralla eşleştirmeli. Bu tek başına review'un mesaj gücünü ciddi artırır."*

A finding that says "this violates the project's no-patches rule at `.claude/rules/no-patches.md`" is materially more actionable than "this is a patch on a patch". The citation turns the reviewer from opinion-source to rule-enforcer.

**Non-goals:**
- Not a general-purpose linter. Rules are project-local prose, not enforceable patterns.
- Not automatic rule-matching by keyword. LLM-driven mapping, not regex.
- Not a replacement for the built-in `CLAUDE.md` already auto-loaded by Claude Code. This item adds discovery of *additional* project-local rule files the skill should consult during review.

**Shape:**

New SKILL.md step (early — right after reading diff, before generating findings):
1. `Glob` for project rule candidates:
   - `.claude/rules/*.md`
   - `code-review.md`, `CODE_REVIEW.md`, `REVIEW.md`
   - `docs/review-rules.md`, `docs/contributing.md`, `CONTRIBUTING.md`
   - Any file matching `**/rules/*.md` at repo root or one level deep
2. Read up to ~10 of the most relevant (by filename + size heuristic). Cap total loaded rule content at ~30KB to avoid context bloat.
3. For each file, extract short rule identifiers if present (e.g., heading names).
4. During finding generation, for each finding, attempt to cite applicable rule(s) from the loaded corpus.

New schema field on each finding (additive):
```json
"rule_refs": [
  {
    "source": ".claude/rules/no-patches.md",
    "rule": "Enforce at the writer, not downstream",
    "quote": "<1-2 line direct quote from the rule file>"
  }
]
```

Empty array when no applicable rule exists. Direct-quote requirement prevents the LLM from inventing rule text.

**Trace log addition:** `project_rules_loaded: [{path, bytes}]` — visible evidence of which rule files were consulted.

**Estimated effort:** 2–2.5 hours. Glob + load step, methodology subsection, schema field, one fixture update that includes a synthetic rule file to validate citation behavior.

**Dependency:** None strictly, but best shipped after Item 7 — citing rules you haven't verified your finding against is worse than no citation at all.

**Risk:** Medium. Context bloat if cap is wrong. LLM may invent rule quotes if quote requirement is soft — must be enforced as "findings with `rule_refs[].quote` not present verbatim in the cited file are schema-invalid".

**Semver:** minor bump (new loader + new schema field).

---

## Item 9 — Finding scope tag ✅ SHIPPED 2026-04-15 (v1.14.0 / schema v1.10)

**Shipping notes:** Landed as `feat(devil-review): v1.14.0 finding scope tag (Item 9)`. Added required `findings[].scope` enum (`in-diff | pre-existing | future-work`) with default-to-in-diff rule for pre-v1.10 payload replay. Methodology section "Scope classification" articulates the decision tree, hard-cap interaction, verdict filter, and future-work anti-pattern warning. Severity axis derivation + verdict derivation rules 1-3 updated to filter on `scope == "in-diff"`. Compatibility property extended to note default composes correctly with default-to-correctness. Fixtures 01/03 assert `scope: in-diff`.

**Original spec preserved below for reference.**

---



**Goal:** Classify each finding as `in-diff | pre-existing | future-work` so consumers can distinguish "fix this now" from "latent bug that existed before this PR" from "improvement for later".

**Why it matters (observed, not speculative):** Saha test #2 reviewer flagged a "latent pre-diff" issue (the delete_import_artifacts asymmetry) but the output did not structurally distinguish this from in-diff findings. The `code-review.md` rule in that project explicitly says "stay scoped to the diff". Without a scope tag, the reviewer is either rule-violating (by raising pre-diff issues) or under-informing (by dropping them silently). A scope tag resolves the tension: pre-diff findings are allowed but explicitly tagged so the author can choose.

**Non-goals:**
- Not a filter. Pre-diff findings are still emitted. The tag is metadata, not gating.
- Not a severity modifier. Severity stands on its own.

**Shape:**

New finding-level field:
```json
"scope": "in-diff | pre-existing | future-work"
```

Definitions:
- `in-diff` — the problem is in code added or modified by this diff. Default.
- `pre-existing` — the problem exists in the code the diff did not touch, but was discovered during review of this diff (e.g., a caller the reviewer inspected). Should be raised but clearly tagged.
- `future-work` — the finding is a design improvement, not a bug. Reviewer is suggesting a next-step, not blocking the current change.

**Methodology addition:** new subsection "Scope classification" — decision tree for the three categories, with emphasis that `in-diff` is default and reviewer must justify `pre-existing` or `future-work` in the finding body.

**Verdict interaction:** `pre-existing` and `future-work` findings do NOT count toward `verdict: block` or `refactor-recommended` escalation. Only `in-diff` findings drive verdict. This keeps the scope tag from becoming a severity back-door.

**Estimated effort:** 1–1.5 hours. Schema field, methodology subsection, verdict-rule update, fixture updates for all three fixtures (each gets at least one finding with an explicit scope tag).

**Dependency:** None. Shippable independently.

**Risk:** Low. Additive schema, clear decision tree. Main risk is reviewer over-using `future-work` as a way to avoid hard calls — mitigation is the methodology instruction "future-work requires a concrete next-step, not a vague 'consider'".

**Semver:** minor bump.

---

## Item 10 — User rejection memory ✅ SHIPPED 2026-04-15 (v1.18.0 / schema v1.14)

**Shipping notes:** Landed as `feat(devil-review): v1.18.0 user rejection memory (Item 10)`. Largest Phase 3 item to date — new sibling skill, new sidecar storage format, new Step 3b substep, new schema fields, new verdict override rule. New `/devil-reject <N> [rationale]` slash command records a rejection to `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` (sidecar with its own `schema_version: "1.0"`, independent of main payload schema). Hash normalization: trim + lowercase file/lines + collapse title whitespace + `:`-joined sha256 — cosmetic title edits hash the same, substantive changes re-fire. `/devil-review` Step 3b extended with "Rejection memory load (v1.14+)" substep: for each candidate finding, compute the same hash and suppress silently (default) or re-raise with `previously_rejected` annotation (exceptional — requires nameable new evidence in one sentence). New required `trace_log.rejections_loaded` (array of `{hash, rejected_at}`) and new optional `findings[].previously_rejected` (`{rejected_at, prior_rationale, new_evidence}`). New chain-of-rejections verdict override rule 0 (highest precedence): fires when ≥2 findings have `previously_rejected` populated, forcing `verdict: approve` + `decision.action: ship` with rationale naming the resurface count and the chain-of-rejections pattern — automation-facing dual of the v1.11 chain-closing override. Fixtures 01/02/03 assert `trace_log.rejections_loaded: []` and `scenarios_considered: rejection memory: absent`. Self-review dogfooded the diff: verified hash normalization synchronized across four surfaces, override precedence documented consistently, orthogonality-with-prior-review rule articulated. Compatibility property preserved: v1.13 payloads re-validated under v1.14 rules produce identical verdicts (override cannot fire on legacy payloads lacking `previously_rejected`, default-to-empty-when-absent on `rejections_loaded` preserves derivation).

**Original spec preserved below for reference.**

---


**Goal:** When a user decides a finding is not actionable and dismisses it, record that decision so subsequent runs suppress the repeat (unless new evidence surfaces). Today's plugin has no mechanism for "user has already told me this finding is not a concern" — Round 1 flags, user skips, Round 2 re-flags same location with same logic. The plugin's snapshot-based prior-review loop catches prior *reviewer* drops but not prior *user* dismissals.

**Why it matters (observed, not speculative):** Saha test #3 reviewer flagged this as the single biggest UX friction across two rounds on a real project. Specific example: Windows trailing-backslash finding — Round 1 flagged, user assessed as not-a-real-concern, skipped; Round 2 came back with identical logic and re-flagged. Combined with saha test #2's severity-dampening feature, the silent re-raise creates a patch-chain-of-rejected-findings pattern: the reviewer keeps surfacing the same dismissed claims round after round, and the user either re-dismisses each round (friction) or starts tuning the reviewer out (worse — loses signal).

**Non-goals:**
- Not a permanent blocklist. Rejections are session-and-target scoped (same discipline as prior-review snapshots). A new session on the same target starts fresh. Rationale: stale rejections from months ago should not mask findings that are now valid because surrounding code has changed.
- Not a global "mute this class of finding". Each rejection is tied to a specific file+line+title hash. Similar finding elsewhere re-fires.
- Not automatic. The user must explicitly reject — the plugin cannot infer "user skipped = rejection" from silence.

**Shape:**

1. **Rejection storage.** New file at `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json`:
   ```json
   [
     {
       "hash": "<sha256 of file:line:title-normalized>",
       "file": "<path>",
       "lines": "L<start>-L<end>",
       "title": "<finding title>",
       "rejected_at": "<ISO timestamp>",
       "rationale": "<user-provided one-sentence reason or null>"
     }
   ]
   ```

2. **Rejection mechanism.** A new slash invocation or skill argument: `/devil-review --reject <finding-index> [<rationale>]`. When invoked post-review, appends the indexed finding to rejections.json. Alternative: a separate short skill `/devil-reject <N> [<reason>]` that reads the latest snapshot's finding #N and writes the rejection entry. Choice of UX deferred to implementation; both work.

3. **Next-run suppression.** SKILL.md Step 3b extension: after loading the prior-review snapshot, also load rejections.json. Compute hash for each current candidate finding. If hash matches a rejection, either:
   - **Suppress silently** if no new evidence (default path)
   - **Re-raise with annotation** if new evidence exists — finding body leads with "Previously rejected on `<date>` with rationale `<text>`. New evidence: `<what changed>`." Severity and confidence carry from current analysis, not the prior rejection.

4. **Schema addition (minor, v1.16.0 / schema v1.12).** Optional finding field:
   ```json
   "previously_rejected": {
     "rejected_at": "<ISO>",
     "prior_rationale": "<text or null>",
     "new_evidence": "<sentence describing what is different this round>"
   }
   ```
   Present only when a rejected finding is being re-raised with justification. Absent on fresh findings and on suppressed (not re-raised) rejections.

5. **Verdict interaction (chain-of-rejections clause).** When `rejected_findings_resurfaced_count ≥ 2` (i.e., 2+ previously-rejected findings are re-raised this round), emit `decision.action: ship` AND `verdict: approve` with `rationale: "chain-of-rejections pattern — reviewer repeatedly surfacing user-dismissed findings; stop iterating, ship as-is"`. This is the automation-facing dual of Item 6's chain-closing override: that rule handled "fix worked"; this one handles "user and reviewer disagree about whether the finding is real".

6. **Trace log addition.** `trace_log.rejections_loaded: [{hash, rejected_at}]` — visible evidence that rejections were consulted. Empty array valid when no rejections.json exists for this session+target. Absence of the field (when rejections.json does exist) is a grounding failure.

**Estimated effort:** 4–5 hours. Largest Phase 3 item to date. New storage format, new slash command or skill argument, Step 3b extension, methodology section on rejection discipline, schema additions, fixture updates (at least one fixture should exercise rejection + suppression + re-raise with new evidence), README prose.

**Dependency:** None strictly. Item 11 (reachability) shipping first would sharpen the rejection mechanism because hypothetical/unreachable findings are the ones most likely to be dismissed — rejection memory works best when the plugin itself correctly classified the finding's reachability upstream.

**Risk:** Medium-high. New storage format (schema drift risk on rejections.json across future versions — needs its own small schema_version field). User-mechanism UX has to be usable — a clunky `/devil-review --reject` flow that nobody uses silently defeats the feature. Chain-of-rejections verdict clause has to be calibrated; a 2-rejection threshold is a starting value, may need revision after usage.

**Semver:** minor bump (new optional field + new trace-log field + verdict rule extension). The rejections.json file is a sidecar, not a schema change proper.

---

## Item 11 — Finding reachability classification ✅ SHIPPED 2026-04-15 (v1.17.0 / schema v1.13)

**Shipping notes:** Landed as `feat(devil-review): v1.17.0 finding reachability classification (Item 11)`. Required `findings[].reachability` enum added (`reachable | hypothetical | requires-specific-config`), with default-to-reachable backward-compat rule mirroring v1.10's default-to-in-diff. Verdict derivation rules extended so `correctness_severity`, `design_debt_severity`, and block/needs-attention/refactor-recommended rules now filter on `scope == "in-diff"` AND `reachability == "reachable"`. New methodology section "Reachability classification (mandatory per-finding)" with three-branch decision tree (concrete call path → reachable; specific config named → requires-specific-config; neither → hypothetical), bias-toward-hypothetical-when-uncertain rule, and explicit orthogonality-to-severity-and-confidence discipline. Claim verification pass step 4 (reachability claims) now resolves naturally via classification rather than drop. Fixtures 01/03 updated with reachability: reachable assertions and decision-tree rationale. Self-review caught a cross-section consistency bug (Scope section's Verdict interaction subsection stated scope-only filter while Severity axes described the complete three-way filter) — rolled into shipping commit. Compatibility property preserved: v1.12 payloads re-validated under v1.13 rules produce identical verdicts.

**Original spec preserved below for reference.**

---


**Goal:** Add a per-finding `reachability` classifier orthogonal to severity and confidence. A bug that fires under specific obscure config is different from a bug that fires on the main path, and today's schema has no way to distinguish them except by squeezing the distinction into the `confidence` score (imperfect — high-confidence hypothetical is still "maybe never hit" whereas low-confidence reachable is "probably hits when triggered"). Only reachable findings drive verdict escalation, same pattern as `scope` filter.

**Why it matters (observed, not speculative):** Saha test #3 reviewer explicitly called out the priority confusion: `confidence: 0.7` hypothetical finding (Windows trailing-backslash under specific config) vs `confidence: 0.85` reachable bug (async listener race on main flow) both presented as equal-weight findings in the output. Reader has to reverse-engineer which ones actually matter. The hypothetical finding's confidence score came from "reviewer is 0.7 sure this IS a bug in theory"; the reachable finding's confidence came from "reviewer is 0.85 sure this bug fires in practice". Different claims compressed into one dimension. Saha feedback: "readers of the trace log should see both".

**Non-goals:**
- Not a severity modifier. A reachable bug is not automatically more severe; it is just more urgent. Severity reflects impact when the bug fires; reachability reflects likelihood of firing.
- Not a replacement for `confidence`. Confidence is the reviewer's epistemic uncertainty about whether the finding is right; reachability is a structural property of the code path. A reachable finding can still have low confidence (reviewer is not sure); a hypothetical finding can still have high confidence (reviewer is sure this WOULD be a bug if reached).

**Shape:**

1. **New required finding field** (schema v1.12):
   ```json
   "reachability": "reachable | hypothetical | requires-specific-config"
   ```

   Definitions:
   - `reachable` — the bug fires under normal usage on at least one code path the reviewer can name. Include a concrete path in the finding body ("triggered by user clicking X", "fires on any PTY spawn", "any API request with empty body").
   - `hypothetical` — the bug would fire if the conditions held, but the reviewer cannot currently name a code path that produces those conditions. Often precondition-dependent, often from reasoning-from-types rather than reasoning-from-paths.
   - `requires-specific-config` — the bug fires only under a specific configuration, environment, or feature flag the reviewer has observed or can document. Stronger than hypothetical (the config exists) but weaker than reachable (the config is not on the main path).

2. **Default-to-reachable rule** for backward compat. Pre-v1.12 payloads replayed under v1.12 rules treat absence as `reachable` — the existing verdict escalation behavior is preserved (everything drove verdict pre-v1.12 regardless of reachability; this preserves the same outcome).

3. **Verdict filter extension.** Only `reachable` findings drive verdict escalation:
   - `correctness_severity` derived from correctness findings with `scope: in-diff` AND `reachability: reachable`
   - `design_debt_severity` same filter
   - `block` rule requires reachable correctness critical/high
   - `needs-attention` requires reachable material finding
   
   `hypothetical` and `requires-specific-config` findings emit transparently but do not escalate. Pattern identical to `scope` filter from v1.14.0.

4. **Markdown template addition.** Per-finding line:
   ```
   - **Reachability**: <reachable | hypothetical | requires-specific-config>
   ```

5. **Methodology addition.** New "Reachability classification" subsection in Calibration rules. Decision tree:
   - Can you name a concrete call path from a user action, cron, boot, API route, or event to the claimed bug? → `reachable`
   - Can you name the specific config/flag/environment that would make the bug reachable? → `requires-specific-config` (name it in body)
   - Neither of above — bug is inferred from types, schemas, or general reasoning without a traced path? → `hypothetical`
   
   Bias toward `hypothetical` when uncertain; promote to `requires-specific-config` only when the specific thing is named.

**Estimated effort:** 1.5–2 hours. Schema field, methodology subsection, verdict-rule update (extend the scope filter to also filter on reachability), markdown template update, fixture updates (fixtures 01/03 assert `reachability: reachable` on their findings).

**Dependency:** None. Shippable independently. Best shipped before Item 10 because rejection memory works better when reachability is correctly classified upstream — hypothetical findings are the most common rejection target, and a user seeing a hypothetical finding tagged as such may not need to reject it at all (it is self-flagged as low-priority).

**Risk:** Low. Additive schema + additive verdict filter. Main risk is reviewer over-classifying as `reachable` to drive verdict up (the in-diff-overreach pattern from Item 9, applied to reachability). Mitigation: the decision tree requires naming a concrete call path for `reachable` — no path = not reachable.

**Semver:** minor bump.

---

## Item 12 — Evidence gate for cross-boundary external claims ✅ SHIPPED 2026-04-15 (v1.16.0 / schema v1.12)

**Shipping notes:** Landed as `feat(devil-review): v1.16.0 evidence gate for external claims (Item 12)`. Methodology "Claim verification pass (pre-emit)" extended from four steps to five — step 5 requires citing a specific source (docs URL, source file:line, runtime observation, or spec identifier) for any load-bearing claim about external-system behavior. New optional `findings[].evidence_sources` (array of `{claim, source_type, source, verified_at}`) and required `trace_log.external_claims_verified` (integer ≥0, counts verification actions not finding entries). Reason enum for `findings_dropped_in_verification` extended with `unverified-external-claim` (seventh value). Three-option fallback for findings without gatherable evidence: gather-and-populate / drop-severity-and-tag-unverified / drop-entirely. Fixtures 01/02/03 updated with external-claim assertions; all three expect `external_claims_verified: 0` since their findings ground in in-repo structure or cross-vendor SQL consensus rather than version/platform-dependent external behavior. Compatibility property preserved — v1.11 payloads re-validated under v1.12 rules produce identical verdicts (evidence gate is grounding/observability, not verdict input).

**Original spec preserved below for reference.**

---


**Goal:** Extend the v1.12.0 Claim verification pass with a specific clause for claims about **external behavior** — third-party library semantics, standard library behavior, OS/runtime specifics, protocol details. Today's claim verification catches over-claims about the diff and surrounding read code, but treats "Rust PathBuf strips trailing separators" or "MSVCRT parses argv with ... semantics" as free assertions as long as they sound plausible. These claims can be verified with a single documentation query or a short runtime observation — the reviewer currently doesn't ask.

**Why it matters (observed, not speculative):** Saha test #3 flagged this concretely: "PathBuf's trailing separator strip behavior could be verified in Rust stdlib docs with one query — reviewer didn't ask." And "MSVCRT argv parse quirks could be checked against published docs — reviewer asserted behavior without source." These unverified external claims drive findings that may be entirely wrong, and the Claim verification pass doesn't currently catch them because the "evidence in diff/code" step applies only to local code, not to external library behavior.

**Non-goals:**
- Not a full dependency audit. Reviewer is not expected to read the full source of every imported library.
- Not a blocker on findings that cite well-established, universally-known behavior (e.g., "JSON does not allow trailing commas"). Only claims whose specific form is version/platform-dependent need evidence.

**Shape:**

1. **Methodology extension.** Add a subsection to "Claim verification pass (pre-emit)" titled "Cross-boundary external claims":
   
   When a load-bearing claim references behavior of external systems — third-party libraries (including stdlib), OS runtimes, protocols, file formats, shell semantics — the four-step verification gains a mandatory fifth step:
   
   5. **Evidence-cite external claims.** Name the source: a docs URL (via WebFetch), a source-code file:line (via clone + read), a runtime observation (via Bash command + result), or a published specification. The `evidence_source` must be specific enough for a consumer to verify independently. Generic "stdlib says so" or "docs mention this" without a pointer does not qualify.
   
   Findings whose load-bearing claim depends on an external assertion without `evidence_source` must either: (a) gather evidence before emit, or (b) drop severity and confidence by one level each and tag the claim as `evidence: unverified` in the finding body, or (c) drop the finding entirely. The third option is preferred when the reviewer cannot reasonably gather evidence (e.g., proprietary binary, no docs available, no runtime access).

2. **New optional finding schema field** (v1.12):
   ```json
   "evidence_sources": [
     {
       "claim": "<one-sentence claim about external behavior>",
       "source_type": "docs-url | source-file | runtime-observation | specification",
       "source": "<URL, file:line, command+output, or spec identifier>",
       "verified_at": "<ISO timestamp of verification>"
     }
   ]
   ```
   Empty array when no external claims in the finding. Populated when external claims exist and were verified. Absent findings interpret as "no external claims" under the default-to-empty rule.

3. **Unverified tag.** When external claim is load-bearing AND evidence could not be gathered AND reviewer elects option (b) above, add to finding body: `evidence: unverified — <brief reason evidence was not gathered>`. This is prose, not a schema field. Consumers that care can grep for the string.

4. **Trace log field.** `trace_log.external_claims_verified: <integer>` — count of external claims the reviewer verified in this review. 0 is valid (no external claims). Purely observability; lets consumers see "did this review actually do research or not".

**Estimated effort:** 1.5–2 hours. Methodology extension, schema field, trace log field, fixture updates (at least one fixture with an external claim and its evidence, to validate the pattern).

**Dependency:** None. Shippable independently. Would compound with Item 7 (claim verification) which is already shipped.

**Risk:** Low. Pure methodology + additive schema. Main risk: reviewer performs "evidence gathering" performatively (fetches a URL but doesn't actually validate the claim against its content) — similar concern to Item 7's original "performative verification" risk. Mitigation: `evidence_source` must be specific (docs URL, not just "the docs"); methodology instruction that reviewer must quote the relevant passage in the finding body when it's a docs URL.

**Semver:** minor bump.

---

## Item 14 — Fixture 04 exercising chain-of-rejections override (rule 0)

**Goal:** Add a fourth fixture under `plugins/devil-review/fixtures/04-chain-of-rejections/` that exercises the v1.14 chain-of-rejections verdict override (rule 0). The fixture pre-seeds `rejections.json` with ≥2 rejection hashes matching findings the reviewer would produce on the fixture diff, and asserts the override fires — `verdict: approve`, `decision.action: ship`, `decision.rationale` names the resurface count and the chain-of-rejections pattern.

**Why it matters (observed, not speculative):** Post-ship adversarial review of the v1.18.0 shipping (and carried through v1.19.0's UX relocation) surfaced that fixtures 01, 02, 03 all have `resurface_count = 0`. The override-0 path is structurally untested by the regression harness: a regression that (a) mis-applied the `≥2` threshold (fires at `≥1` or `≥3`), (b) forgot to force `verdict: approve` or `decision.action: ship`, or (c) evaluated rules 1-4 before the override would pass fixtures 01/02/03 undetected. Same gap pattern as the scope-filter-only fixture coverage (fixtures don't exercise `pre-existing` or `future-work`) and the reachability-filter-only coverage (fixtures don't exercise `hypothetical` or `requires-specific-config`), but more urgent because override 0 is the newest rule and has not been exercised in real usage yet.

**Non-goals:**
- Not a calibration exercise for the `≥2` threshold. Calibration comes from real `/devil-review --reject` saha usage; the fixture locks in whatever threshold is current.
- Not a test of the reviewer's suppress-vs-re-raise judgment (that's reviewer-gated per methodology; fixture exercises the structural override once rejections ARE re-raised).
- Not a replacement for the existing 3 fixtures — all four coexist.

**Shape:**

New fixture directory `plugins/devil-review/fixtures/04-chain-of-rejections/`:

- `diff.patch` — synthetic diff (small, self-contained) that produces at least 2 findings whose normalized `file:lines:title` hashes can be computed deterministically from a seeded rejection file.
- `context.md` — minimal repo context.
- `rejections.json` — pre-seeded sidecar with `schema_version: "1.0"` and 2+ rejection entries whose hashes correspond to findings the diff is expected to produce. The hashes need to be computed from actual expected titles — either by running the skill once, capturing the emitted titles, and seeding from that, or by using very short deterministic synthetic titles whose hash can be pre-computed.
- `expected-findings.md` — assertions:
  - `verdict: approve` (override forces this)
  - `decision.action: ship` (override forces this)
  - `decision.rationale` contains the literal phrase "chain-of-rejections" AND names the resurface count
  - `≥ 2` findings have `previously_rejected` populated with matching `rejected_at` and `new_evidence`
  - `trace_log.rejections_loaded` is non-empty with entries matching the seeded rejections
  - `scenarios_considered` contains `rejection memory: loaded`
  - Rule 1 (block), rule 2 (needs-attention), rule 3 (refactor-recommended) do NOT fire regardless of what other in-diff + reachable findings the diff would produce
- `last-snapshot.md` — captured after first real run (same convention as existing fixtures).

**Estimated effort:** 30-60 minutes once a real `/devil-review --reject` saha test provides seed snapshot data. Without saha data, 1-1.5 hours crafting from scratch with synthetic hashes — and higher risk of locking in incorrect behavior because the fixture tests "what the code does today" rather than "what the code should do after real calibration".

**Dependency:** Ideally a real `/devil-review --reject` saha test that produces ≥2 re-raised findings. The test provides both (a) the seed data for the fixture and (b) calibration signal for whether the `≥2` threshold is correct. Writing the fixture before saha calibration risks locking in a threshold or rationale format that real usage says should change.

**Trigger to activate:**
- First real-world `/devil-review --reject` saha test that produces ≥2 re-raised findings in a session — use the saha snapshot as fixture seed and the calibration observation as the basis for `expected-findings.md` assertions
- OR a reported regression suspicion on rule 0 (threshold change, forced-verdict logic, precedence) — fixture becomes immediate priority to lock behavior
- OR any modification to rule 0 in methodology or output-schema — the fixture lands alongside the modification, not as a follow-up

Until one of these fires, the override-0 coverage gap is a known accepted gap per the tracked-items revision log entry in v1.18.0's shipping record.

**Risk:** Low for the fixture itself once saha data exists. Medium if written from scratch pre-calibration — could lock in wrong `expected-findings.md` assertions. Mitigation: explicitly wait for saha data before writing; the gap is documented and tracked.

**Semver:** No version bump for adding a fixture (patch at most). Fixture changes don't propagate to user-visible plugin behavior.

---

## Item 15 — Severity floor for user-irrecoverable findings

**Goal:** Establish a methodology rule that any finding whose user-impact requires out-of-band recovery (restart app, restart OS, reinstall, manually clear cache/data, factory reset) hits a `high` minimum severity floor. Severity dampening rules (carries-over, prior-relation) cannot demote below the floor. The floor closes a calibration drift gap where the LLM reviewer can talk itself into "edge case" framing on bugs whose user-recovery cost makes them structurally above the noise threshold.

**Why it matters (observed, not speculative):** Saha test #4 (cross-model adversarial comparison: codex vs devil-review on the same diff in another project, devil-review running v1.19.1) produced a concrete calibration gap. devil-review correctly identified a permission-cache bug whose user impact was "can't recover until app restart" — verbatim from the finding text — but routed it to `considered_not_promoted` rather than promoting to `findings`. Codex (different model family, fresh perspective) flagged the same bug as no-ship. The promotion path filtered out a finding whose user-recovery cost was structurally above the noise threshold. User feedback verbatim: "Severity miscalibration — gördü ama indirdi ... Bu keşif hatası değil, kalibrasyon hatası — gerçek user impact'i (kullanıcı OS Settings'ten permission açar → restart'a kadar bildirim yok) doğru tartmadı." Without a severity floor tied to recovery cost, the LLM reviewer's calibration drifts on exactly the class of bug that should never ship.

**Non-goals:**
- Not an automated impact classifier — the floor is a methodology rule the reviewer applies during severity calibration, not a separate field on findings.
- Not a replacement for the ship-blocker question — the floor sets a *minimum* severity; the reviewer still answers ship-blocker honestly.
- Not a generalized calibration override — narrowly scoped to recovery-cost signals (restart/reinstall/data-loss-to-recover).

**Shape (target v1.20.0 minor, schema v1.15):**

Methodology addition under "Severity calibration" → new subsection "Severity floor for user-irrecoverable findings":

A finding hits a `high` minimum severity floor when the user impact requires:
- Restarting the application (force-quit + relaunch)
- Restarting the OS / device
- Reinstalling the app
- Manually clearing app data, cache, or config files
- Factory reset / fresh install

The floor applies regardless of frequency (even if the bug fires once per session, recovery cost makes it high+) and cannot be demoted by severity dampening (`carries-over` rule cannot push below the floor). When the floor applies, the finding body must include the recovery cost explicitly: e.g., "Recovery cost: user must restart app to recover (no in-process recovery path)." Body prose only — the floor is a calibration rule, not a structured tag.

Schema-side, one new audit integer: `trace_log.severity_floor_applications` (≥0) counting how many findings the floor was applied to in this review. Same enforcement pattern as `external_claims_verified` and `rejections_loaded` — required field, `0` is valid when no findings hit the floor.

**Verdict derivation integration:** No new rule. Existing rule 1 (`block`) already requires severity ≥ high; any finding hitting the floor automatically becomes a candidate for `block` if it's also in-diff + reachable + ship_blocker_answer=yes. The floor's value is forcing severity assignment to be honest, not adding a new path.

**Backward compatibility:** Severity is already an enum; raising a floor adds no new values. v1.14 consumers parse v1.15 payloads without error. Replay property: a v1.14-era review where the reviewer had honestly assigned `high` to a permission-cache bug produces identical verdict under v1.15. The change only affects reviews where the v1.14 reviewer would have assigned `medium` and the v1.15 reviewer corrects to `high` — i.e., the calibration drift the floor is designed to prevent.

**Estimated effort:** 1.5–2 hours. Methodology subsection (most of the work), schema field, README prose, fixture audit (likely no current fixture trips the floor; 03-unsafe-migration is closest but is already a `block` on data-loss).

**Dependency:** None for shipping itself. **Hard ordering requirement for Item 16** (cap-bypass): without the floor pushing findings up to `high`, Item 16's `must_promote` pool stays empty in practice and the schema change is dead weight. Ship 15 first.

**Trigger to activate:** ✅ Triggered 2026-04-26 by saha test #4 — concrete observation of devil-review demoting a "user must restart" bug below promotion threshold while codex flagged it no-ship. Ship as part of saha-test-#4 series (Item 15 → 16 → 17).

**Risk:** Medium. Recovery-cost classification is qualitative — "data corruption requires re-import" might or might not count depending on whether re-import is in-app vs out-of-band. Mitigation: the methodology lists 5 explicit triggers (restart-app/restart-OS/reinstall/clear-data/factory-reset); reviewer applies the floor only when one of these is concretely named in the finding's recovery-cost line. Edge cases drop to standard severity calibration. The floor is a *minimum*, not a *cap* — reviewer can always go higher when impact is critical.

---

## Item 16 — Two-channel emit (must-promote channel for cap-bypassing high-severity findings)

**Goal:** Add a separate top-level `must_promote` array that holds high-or-critical-severity in-diff+reachable findings. Entries in `must_promote` do NOT count against the hard cap (3 / 5 / 3-per-group per `methodology.md:289` + `:405`). The cap remains in force for low/medium findings — its load-bearing purpose (preventing noise from drowning a single high finding) is preserved — but the cap can no longer silently bury high+ findings into `considered_not_promoted` simply because the group has more than 3.

**Why it matters (observed, not speculative):** Saha test #4 surfaced a concrete cap-overflow case. The split-review group cap of 3 is structural per `methodology.md:289` ("3 under 500 lines / 5 under 1500 / 3 per split group") and `methodology.md:405` ("Split reviews: maximum 3 findings per group"). When 4+ high-severity findings exist in a group, the cap forces one or more into `considered_not_promoted` regardless of severity ordering. User feedback verbatim: "Devil kendi prompt'unda findings sayısını grup başına 3'le sınırlandırıyor. Yani 5 gerçek high-priority bulgu olsa bile en fazla 3'ü yüzeye çıkar. Permission cache muhtemelen bu cap yüzünden z-index collision'a yenildi. Yapısal bir handicap — daha derin sorunları kasıtlı olarak gizleyebilir." The cap exists for noise control over low/medium findings; applying it uniformly to high+ findings is overshoot.

**Non-goals:**
- Not removing the cap. Cap remains for `low`/`medium` findings — that's its load-bearing purpose.
- Not a verdict override mechanism. `must_promote` findings flow through standard verdict rules (1-4); they just bypass the cap.
- Not retroactive — does not change how `considered_not_promoted` is populated for legacy payloads.

**Shape (target v1.21.0 minor, schema v1.16):**

Top-level new optional array, identical finding shape to standard `findings`:
```json
"must_promote": [
  { "title": "...", "severity": "high | critical", "scope": "in-diff", "reachability": "reachable", "finding_type": "...", "file": "...", "lines": "...", "body": "..." }
]
```

Methodology addition under "Calibration rules" → new subsection "Two-channel emit (cap-bypass for high-severity in-diff findings)":

After the Claim verification pass (steps 1-5) and before the hard cap is applied, partition surviving findings into two pools:
- **`must_promote` pool**: any finding with `severity ∈ {high, critical}` AND `scope == "in-diff"` AND `reachability == "reachable"`.
- **`findings` pool**: everything else (low/medium of any scope, plus high+/critical that are `pre-existing`/`future-work` or `hypothetical`/`requires-specific-config`).

Apply the hard cap (3 / 5 / 3-per-group) **only to the `findings` pool**. The `must_promote` pool has no cap — every qualifying finding emits.

`considered_not_promoted` continues to receive cap-overflow from the `findings` pool only. There is no `must_promote` overflow.

**Verdict derivation integration:** Verdict rules 0-4 must be amended to evaluate over `must_promote ∪ findings` rather than just `findings`. Concretely:
- Rule 0 (chain-of-rejections override): unaffected — operates on resurface_count, pool-independent.
- Rule 1 (`block`): reads from union. A `must_promote` finding with `finding_type ∈ {correctness, absent}` AND `ship_blocker_answer == "yes"` triggers `block` exactly as a `findings`-pool finding would.
- Rule 2 (`needs-attention`): reads from union for "any in-diff + reachable finding of material severity".
- Rule 3 (`refactor-recommended`): reads from union for the design_debt count and the patch-chain signal interaction.
- Rule 4 (`approve`): requires both pools empty (or only non-driving findings — pre-existing/future-work or hypothetical/requires-specific-config).

**Markdown rendering:** New section "Must promote (cap-bypass)" rendered before the standard "Findings" section, only when `must_promote` is non-empty. Format identical to standard finding format. Counts roll into the trace log header line: `Findings: N must-promote + M capped + K considered-not-promoted`.

**Backward compatibility:** Field is optional; v1.15 consumers parse v1.16 payloads without error. Replay property: legacy reviews with no `must_promote` field treat it as `[]`, all findings flow through the standard cap path, verdict calculation is unchanged. The new pool only changes outcomes when the v1.16 reviewer actively classifies findings into it. A v1.15 review whose author would have hit the cap with 4 high-severity findings still emits the same `considered_not_promoted` array under v1.15 rules; v1.16 changes that pattern by routing 1+ of those into `must_promote`.

**Estimated effort:** 3–4 hours. Methodology partition rule, schema additions (top-level array), verdict rule amendments (touches all five rules), markdown rendering, fixture audit (no current fixture has 4+ high-severity findings; fixture 04 may exercise it after Item 14 ships).

**Dependency:** **Item 15 ships first.** The `must_promote` pool is meaningfully populated only when Item 15's severity floor is actively pushing findings up to `high`. Without Item 15, `must_promote` stays empty in practice and the schema change is dead weight.

**Trigger to activate:** ✅ Triggered 2026-04-26 by saha test #4 — concrete cap-overflow observed in split-review-group context where high-severity bugs were demoted to `considered_not_promoted` against severity ordering.

**Risk:** Medium. The pool partition is mechanical, but the verdict rule changes touch every rule (0-4). Mitigation: the partition rule is exactly mechanical (`severity ∈ {high, critical}` AND scope filter AND reachability filter); replay property is preserved by the empty-default; existing fixtures regression-test the union semantics. Cross-section consistency check needed (same class as v1.17.0 self-review's Scope-vs-Severity-axes drift): every section that mentions "the findings array" must be checked for whether it should now read "findings ∪ must_promote".

---

## Item 17 — Upstream event-source trace for event-driven findings

**Goal:** Extend Claim verification pass with a new step (step 6) that requires the reviewer to trace the event source upstream when a finding's load-bearing claim involves a watched event, IPC message, websocket message, file watcher event, or any other event-driven trigger. Without the upstream trace, the reviewer treats the event as a constant when it's actually variable — finding bodies say "when X event arrives, Y happens" without verifying whether X actually arrives in the conditions claimed.

**Why it matters (observed, not speculative):** Saha test #4 produced a concrete depth gap. Codex (cross-model comparison) traced upstream into `src-tauri/src/application/status_service.rs` to verify what event source `agent_status_watch` actually emitted under various conditions, including transient cases. devil-review stayed in the frontend slice and treated the event as a given. User feedback verbatim: "Codex'in log'unda src-tauri/src/application/status_service.rs'i birden fazla sed call ile okuduğunu görüyorum (satır 60-67). Yukarıdan agent_status_watch event source'una kadar gitti. Devil muhtemelen frontend diff'inde kaldı. Backend bağlantısını okumamak, 'neden bu event geliyor, hangi koşulda transient olabilir' sorusunu cevaplayamamak demek." This is a methodology gap, not a model gap — devil-review did not have a step that said "if your finding involves an event handler, trace the source". The result is finding bodies that assert event semantics without verifying them.

**Non-goals:**
- Not a generic "explore upstream from every finding" rule — that would explode review scope. Triggered only when the finding's load-bearing claim involves an event/subscription/message.
- Not a replacement for the diff-only scope rule — `scope: in-diff` findings remain in-diff. The upstream trace is for *understanding* the finding correctly, not for raising additional findings outside the diff (those would be `scope: pre-existing`).
- Not an evidence-gate extension — Item 12's evidence gate (step 5) covers external library/runtime claims; Item 17 (step 6) covers internal event sources within the same codebase.

**Shape (target v1.22.0 minor, schema v1.17):**

Methodology addition under "Claim verification pass" → new step 6 (after the existing 5 steps from Item 12):

**Step 6 — Event-source upstream trace.** When a finding's load-bearing claim involves a watched event, IPC message, websocket message, file watcher event, or other event-driven trigger:
1. Identify the event identifier (channel name, event type, message kind) from the consumer code.
2. Search the codebase for the emitter (`grep`/`Glob` for the identifier).
3. Read the emitter to verify under what conditions the event fires — including transient/error/edge cases.
4. If the emitter behavior contradicts the finding's assumption (e.g., "this event fires on error" → emitter shows it fires on success too), revise or drop the finding.
5. If the emitter cannot be located within the codebase (event comes from a runtime, OS, or external service), drop to step 5 (Item 12's evidence gate) — cite runtime documentation or drop the finding.

Schema-side, one new audit integer: `trace_log.event_sources_traced` (≥0) counting how many event sources were traced. Same enforcement pattern as `external_claims_verified` — required field, `0` is valid when no findings involved events.

The Claim verification pass title and any cross-references update from "five steps" (current, post-v1.16.0) to "six steps".

**Verdict derivation integration:** None. The trace is part of pre-cap calibration, not verdict derivation.

**Backward compatibility:** New trace_log integer is required (same enforcement pattern as `external_claims_verified`). Default-to-zero on absent for legacy payloads. Replay property: pre-v1.17 payloads have no event-source-trace expectation, so verdict is unchanged. Post-v1.17 reviews emit `event_sources_traced: 0` honestly when no findings involved events, satisfying the requirement without forcing trace work that has no subject.

**Estimated effort:** 2 hours. Methodology section (step 6 prose), schema field, README, fixture audit (fixture 01-guard-cluster-refactor may have an event-driven finding worth exercising; fixtures 02 and 03 likely do not).

**Dependency:** **Item 16 ships first.** Item 17's value compounds with two-channel emit because the upstream trace may push findings up the severity scale (revealing the event fires more often than thought) which then needs Item 16's cap-bypass channel to surface them at full count. Item 17 could ship in parallel with 16 in principle, but serial keeps regression-bisection clean per "Do not batch".

**Trigger to activate:** ✅ Triggered 2026-04-26 by saha test #4 — concrete depth gap observed where the reviewer stayed in the diff slice and missed the event-source semantics that codex traced upstream.

**Risk:** Low–medium. The trace is bounded (consumer → emitter, not arbitrary upstream walking). Edge case: when the emitter is dynamically constructed (event name from a config, runtime registration), the trace may be inconclusive — methodology must accept "emitter not statically locatable, dropping to step 5 evidence-gate semantics" as a valid resolution.

---

## Sequencing recommendation

Not a fixed order — pick based on observed need.

**Post saha-test #2 recommended sequence (2026-04-15):**

1. **Ship Item 7 (self-fact-check pass) first.** Credibility floor. Every other item compounds on top of a reviewer that doesn't over-claim. Prompt-only, no schema change, low risk.
2. **Then Item 8 (project-rule citation loader).** Highest visible message-power gain per saha feedback. Additive schema. Best if Item 7 shipped first so cited rules attach to verified claims.
3. **Then Item 9 (scope tag).** Small additive schema, resolves the "stay in diff vs raise latent bug" tension.
4. **Then Item 6 expanded (structured attribution + severity dampening + decision field).** Largest schema footprint. Items 7–9 may reveal edge cases that sharpen Item 6's shape; shipping it last minimizes rework.

**Remaining original items (unchanged priority):**

5. **Item 2 (README good/bad).** Lowest risk, onboarding value. Do whenever; good for a "palate cleanser" between larger shippings.
6. **Item 3 (agent test).** Uses fixtures from Item 1. Only if output still feels shallow after Items 6–9 ship.
7. **Item 4 (deferred domains).** Only on real demand.
8. **Item 5 (dynamic discovery).** Only at scale (12+ domains or external contributor).

**Post saha-test #3 recommended sequence (2026-04-15, extends the saha-test-#2 sequence above):**

9. **Ship Item 12 (evidence gate for external claims) next.** Smallest schema footprint (one optional finding field + one trace_log integer), pure methodology extension to Item 7's Claim verification pass. Compounds on Item 7's credibility floor — an evidence-gated external claim is a verified external claim. Low risk.
10. **Then Item 11 (reachability classification).** New required field on findings, verdict rule filter extension (mirroring Item 9's scope filter). Medium-size shipping. Best before Item 10 because rejection memory works better when the plugin correctly flags hypothetical findings as hypothetical — hypothetical-tagged findings are the most common rejection target and being self-flagged reduces the rejection pressure.
11. **Then Item 10 (user rejection memory).** Largest Phase 3 item to date — new sidecar storage format, new UX for rejection, Step 3b extension, schema additions, chain-of-rejections verdict clause. Shipping last minimizes rework because Item 11's reachability classifier and Item 12's evidence gate both reduce the finding surface that would otherwise pressure users toward rejection in the first place.

**Post saha-test #4 recommended sequence (2026-04-26, extends the saha-test-#3 sequence above):**

12. **Ship Item 15 (severity floor for user-irrecoverable findings) next.** Smallest schema footprint (one trace_log integer), pure methodology calibration rule. **Hard ordering requirement** (not just preference): without the floor pushing findings up to `high`, Item 16's `must_promote` pool stays empty in practice and the schema change is dead weight. Low risk — methodology rule with no verdict-rule changes; existing rule 1 (`block`) already does the right thing once severity is honestly assigned.
13. **Then Item 16 (two-channel emit / `must_promote` channel).** Schema-touching minor (new top-level array, verdict rule amendments to all five rules). Bypasses the hard cap for high+critical in-diff+reachable findings. Best after Item 15 because the floor is what makes the bypass actively trigger; before Item 15, `must_promote` stays empty and the schema additions are unexercised dead weight.
14. **Then Item 17 (upstream event-source trace).** Methodology extension to Item 7's claim verification pass (now six steps after Item 12 took it from four to five). Best after Items 15+16 because the upstream trace may surface high-severity findings that then need the floor (15) and the cap-bypass (16) to land correctly in the output.

Sequencing rationale: smallest-footprint-first, with each item compounding on the previous. Reverse direction from saha-test-#3 (which was largest-last because of risk); saha-test-#4 is smallest-first because of the dependency chain. Items 15 → 16 form a tight pair (15 enables 16); Item 17 is loosely coupled and could ship in parallel with 16, but serial keeps regression-bisection clean per "Do not batch".

**Do not batch.** Each item is independent and shippable alone. Batching increases risk and obscures which change caused what behavior shift. This is especially true for Items 6–12 and 15–17 which each touch schema — batching makes regression bisection across fixtures harder.

---

## Success criteria (for when Phase 3 is "done")

Phase 3 is never strictly "done" — it's a menu, not a milestone. But we can call it materially complete when:

- [x] At least one fixture exists and has caught at least one regression in practice (Item 1) — shipped 2026-04-14 with 3 fixtures; the `01-guard-cluster-refactor` fixture deliberately asserts the v1.10.1-post-fix behavior so running it against v1.10.0 exposes the Finding 1 lift_considered schema inconsistency
- [ ] README has a worked good/bad example (Item 2)
- [ ] The `agent:` line in SKILL.md is either justified by a test or removed (Item 3)
- [ ] At least one deferred domain has been added OR explicitly declared not needed (Item 4)
- [ ] Dynamic discovery has been implemented OR explicitly declared premature at current scale (Item 5)
- [x] Structured prior-review attribution shipped (Item 6 expanded) — v1.15.0 on 2026-04-15, schema v1.11 with `prior_relation`, `prior_review_summary`, `decision` block, severity dampening, chain-closing clause (c)
- [x] Self-fact-check pass shipped (Item 7) — v1.12.0 on 2026-04-15, schema v1.8 with `findings_dropped_in_verification` + methodology "Claim verification pass" section
- [x] Project-rule citation loader shipped (Item 8) — v1.13.0 on 2026-04-15, schema v1.9 with `project_rules_loaded` + `rule_refs` with verbatim-quote gate
- [x] Finding scope tag shipped (Item 9) — v1.14.0 on 2026-04-15, schema v1.10 with `findings[].scope` + verdict filter
- [x] User rejection memory shipped (Item 10) — v1.18.0 on 2026-04-15, schema v1.14 with `findings[].previously_rejected` + `trace_log.rejections_loaded` + chain-of-rejections verdict override (rule 0) + sidecar storage at `.claude/devil-review/<session>/rejections.json` (sidecar schema v1.0). UX relocated from a sibling `/devil-reject` skill to a `--reject <CSV>` inline flag on `/devil-review` in v1.19.0 (same-day); schema and sidecar format unchanged across the two versions
- [x] Finding reachability classification shipped (Item 11) — v1.17.0 on 2026-04-15, schema v1.13 with required `findings[].reachability` enum + default-to-reachable backward-compat + verdict filter mirroring v1.10's scope filter
- [x] Evidence gate for external claims shipped (Item 12) — v1.16.0 on 2026-04-15, schema v1.12 with `findings[].evidence_sources` + `trace_log.external_claims_verified` + `unverified-external-claim` reason code; methodology Claim verification pass extended from four to five steps
- [ ] Fixture 04 exercising chain-of-rejections override (Item 14) shipped OR saha evidence shows override 0 does not fire in practice (gap remains acceptable)
- [ ] Severity floor for user-irrecoverable findings shipped (Item 15)
- [ ] Two-channel emit / `must_promote` channel shipped (Item 16)
- [ ] Upstream event-source trace shipped (Item 17)

All sixteen remain open indefinitely without blocking any user-facing feature. Items 1, 6, 7, 8, 9, 10, 11, 12 are shipped. Item 14 is spec'd but unstarted (trigger-gated on saha data). Items 15, 16, 17 are spec'd from saha test #4 (2026-04-26) — unstarted, ship as series 15 → 16 → 17. Items 2, 3, 4, 5 remain demand-gated.

---

## Revision log

- **2026-04-11** — Initial spec written. Plugin at v1.3.2. Phase 3 still unstarted.
- **2026-04-14** — Item 1 (fixtures regression harness) shipped. Trigger: Phase 2.5 shipping (v1.8.1 + v1.9.0 + v1.10.0) produced 3 `no-test` findings in self-review, moving fixtures from "optional menu item" to "blocker on next prompt edit". Shipped 3 fixtures (guard-cluster-refactor, clean-refactor, unsafe-migration) with expected-findings assertions; no last-snapshot.md yet (captured on first real run). Items 2–5 remain unstarted per "real demand only" policy.
- **2026-04-14 (same-day)** — Item 6 (structured prior-review attribution) added to the menu. Trigger: first saha test of `--prior-review` flag (pre-v1.11.0 auto-detect) in a real review produced explicit attribution language ("prior findings resolved, new findings introduced by fix, not a patch-chain pattern") and dampened an otherwise likely `refactor-recommended` verdict to `needs-attention`. Reviewer identified the mechanism as the single most valuable part of the patch-chain detection feature, but noted the attribution is emitted as prose (in `theme_assessment` and finding body annotations) rather than structured fields. Item 6 spec captures the fields and verdict-derivation integration for when automation consumers arrive or prose attribution proves insufficient. Unstarted; gated on observable demand.
- **2026-04-15** — Saha test #2 (two-round devil-review on a real project) produced seven concrete observations. Three of them (finding-diff across rounds, severity recalibration on re-surfaced findings, structured `decision` field for CI/`/loop` gating) triggered Item 6's original triggers and expanded its spec: added severity dampening rule for `carries-over` findings, added top-level `decision` block with `action | patch_chain_detected | iteration_count | rationale`. Four new items added to the menu — Item 7 (self-fact-check pass, closing two observed factual errors in reviewer output), Item 8 (project-rule citation loader, making implicit rule-following explicit), Item 9 (finding scope tag, resolving in-diff vs pre-existing tension). Sequencing revised: Items 7 → 8 → 9 → 6-expanded, because credibility floor (7) and verified-claim citations (8) compound on each other, and Item 6's larger schema footprint benefits from edge cases surfaced by 7–9. Plugin at v1.11.0; no version bump this revision (doc-only).
- **2026-04-15 (same-day, shipping series)** — Items 7, 8, 9, 6-expanded all shipped in sequence per the planned order: v1.12.0 (Item 7, schema v1.8), v1.13.0 (Item 8, schema v1.9), v1.14.0 (Item 9, schema v1.10), v1.15.0 (Item 6 expanded, schema v1.11). Four schema bumps across four commits, each with per-commit self-review rolled in; fixtures 01/02/03 updated at every bump. Compatibility property preserved: v1.7 consumers parse v1.11 payloads, and v1.7-era verdict calculations replay identically under v1.11 rules because the four additive defaults (correctness on finding_type absent, in-diff on scope absent, synth-decision on decision absent, none on severity axes absent) compose correctly. The saha-test-#2 shipping series is the largest single-session Phase 3 advance to date — Items 2, 3, 4, 5 remain unstarted per "real demand only" policy. Next saha test after this series is the re-validation trigger for Item 3 (agent: Explore decision).
- **2026-04-15 (same-day, v1.15.1 patch)** — v1.15.1 shipped as a patch correction after applying devil-review's own methodology (dogfooding) to the six shipping commits of the saha-test-#2 series. Two concrete schema-methodology inconsistencies surfaced: (a) `findings[].prior_relation.category` enum allowed `resolved` at finding-level despite methodology forbidding it; narrowed to three values. (b) Legacy-payload `decision` synthesis used a binary approve-vs-iterate rule that produced verdict/action contradictions on `refactor-recommended` payloads; replaced with a full verdict→action map. Schema version stayed at 1.11 (no field shape changes). Adversarial self-review validated the methodology — plugin applied to its own output caught real bugs, confirming the shipping-series discipline works end-to-end.
- **2026-04-15 (same-day, saha test #3)** — Saha test #3 (two-round devil-review on another project, running v1.15.1) produced four validations (confirming findings_dropped_in_verification, lift_considered + no-patches.md mapping, severity+confidence+scope scoring, and finding a real bug all work as designed) and four concrete gaps mapping to three new items. Three items added to the menu: **Item 10** (user rejection memory — storage + mechanism for persisting user's dismissal decisions across rounds, including a chain-of-rejections verdict clause), **Item 11** (finding reachability classification — per-finding `reachable | hypothetical | requires-specific-config` orthogonal to severity/confidence, with verdict filter paralleling the v1.14.0 scope filter), **Item 12** (evidence gate for cross-boundary external claims — extension to Item 7's Claim verification pass requiring `evidence_source` for third-party/stdlib/OS behavior claims, else drop or tag unverified). A fourth observation (verdict/ship-blocker semantics for low-severity-only reviews) is resolved transitively by Item 11's reachability filter — no standalone item needed. A surfacing observation (prior_review_summary counts not prominent enough in markdown) is a minor polish deferred. Sequencing recommendation: Item 12 → Item 11 → Item 10 (smallest schema footprint first, largest last, with each item's output reducing the need for the next). Unstarted; no version bump this revision (doc-only).
- **2026-04-15 (same-day, saha-test-#3 series start)** — Item 12 (evidence gate for cross-boundary external claims) shipped as v1.16.0 / schema v1.12. First item from the saha-test-#3 menu landed. The Claim verification pass grew from four steps to five — step 5 requires citing a specific source for any load-bearing claim about external-system behavior (third-party libraries including stdlib, OS runtimes, protocols, file formats, shell semantics, hardware). Three-option discipline for findings without gatherable evidence: gather-and-populate / drop-severity-and-tag / drop-entirely. New optional `findings[].evidence_sources` and required `trace_log.external_claims_verified` integer; `unverified-external-claim` added to the drop-reason enum. Shipped per sequencing recommendation: Item 12 first because it is the smallest-footprint extension of the v1.12.0 credibility floor (Item 7). Items 11 (reachability) and 10 (rejection memory) remain in the saha-test-#3 menu; Item 11 next per sequencing (shipping before Item 10 reduces rejection pressure by self-flagging hypothetical findings upstream).
- **2026-04-15 (same-day, saha-test-#3 series continues)** — Item 11 (finding reachability classification) shipped as v1.17.0 / schema v1.13. Required `findings[].reachability` enum added (`reachable | hypothetical | requires-specific-config`), default-to-reachable backward-compat rule, verdict filter extended to `scope == "in-diff"` AND `reachability == "reachable"`. Pattern identical to Item 9's scope filter from v1.10 — same default-to-X replay preservation, same hard-cap interaction, same anti-pattern mitigation. Saha test #3 friction resolved: the priority confusion between a `confidence: 0.7` hypothetical Windows-specific finding and a `confidence: 0.85` reachable main-flow bug — reachability is a structural property of the code path, confidence is epistemic uncertainty about the claim, and the two should not collapse into one axis. Self-review caught a cross-section consistency bug during dogfooding (Scope section's Verdict interaction stated scope-only filter while Severity axes described the full three-way filter) — rolled into the shipping commit per self-review discipline. Only Item 10 (user rejection memory) remains in the saha-test-#3 menu.
- **2026-04-15 (same-day, saha-test-#3 series complete)** — Item 10 (user rejection memory) shipped as v1.18.0 / schema v1.14. Largest Phase 3 item to date: new sibling `/devil-reject` skill (`plugins/devil-review/skills/devil-reject/`), new session-scoped sidecar `.claude/devil-review/<session>/rejections.json` (with its own sidecar schema_version "1.0" independent of the main payload schema), new Step 3b "Rejection memory load" substep in `/devil-review`, new required `trace_log.rejections_loaded`, new optional `findings[].previously_rejected`, and new chain-of-rejections verdict override (rule 0, highest precedence). The override is the automation-facing dual of v1.11's chain-closing override: chain-closing said "fixes are working, don't escalate to refactor"; chain-of-rejections says "user and reviewer disagree, stop iterating". The ≥2 resurface threshold is an uncalibrated starting value per the discipline used in v1.10 patch-chain and v1.11 chain-closing thresholds. Pre-ship self-review caught zero text-drift inconsistencies after the "four rules → five rules" rename and hash-normalization synchronization check across four surfaces. A post-ship adversarial review of the full saha-test-#3 shipping series (including this commit) surfaced two low-severity design_debt items tracked for v1.18.x — sidecar `schema_version` written but not validated by readers, and fixtures 01/02/03 do not exercise the chain-of-rejections override (rule 0) because all three fixtures have resurface_count=0. Pre-ship self-review caught text-level drift; post-ship review caught design-pattern gaps — different scopes, both worth noting for the shipping-series record. The saha-test-#3 menu is now complete (Items 12 → 11 → 10 shipped in sequence); Items 1, 6, 7, 8, 9, 10, 11, 12 are shipped total across the full Phase 3 run so far, with Items 2, 3, 4, 5 remaining demand-gated per original policy.
- **2026-04-15 (same-day, v1.19.0 UX relocation)** — v1.19.0 replaced the `/devil-reject` sibling skill (shipped in v1.18.0) with a `--reject <CSV>` inline flag on `/devil-review`. User-surfaced UX friction: the two-skill approach (review → see findings → invoke separate skill → re-review) required two command invocations when the common workflow wanted one. The inline flag collapses this to a single call — `/devil-review --reject 2,5` records rejections against the most recent prior snapshot and runs a fresh review in one step. Schema unchanged at 1.14, sidecar `rejections.json` format unchanged (still schema_version "1.0"), verdict override rule 0 unchanged, and `findings[].previously_rejected` + `trace_log.rejections_loaded` semantics unchanged. What changed: the skill directory `plugins/devil-review/skills/devil-reject/` was deleted (147 lines gone); Step 1 of `/devil-review` SKILL.md gained `--reject` argument parsing; Step 3b's "Rejection memory load" was restructured into 7 explicit substeps with substep 1 now the authoritative hash-normalization spec (moved from the deleted /devil-reject Step 4) and substep 2 the `--reject` flag application; three new error codes added for --reject error handling (reject_without_prior, reject_index_out_of_range, rejections_file_malformed). Minor bump (not major) per CLAUDE.md semver — no output schema change, no verdict semantic change, just slash-command surface rearrangement. User explicitly accepted the breakage for any intermediate `/devil-reject` invocations ("backward yapmaya gerek yok"); in practice the v1.18.0 skill existed for minutes in this session and had no deployed users. The two v1.18.x tracked items (sidecar schema_version validation gap, override-0 fixture coverage gap) are now tracked for v1.19.x — the relocation did not address either of them, and they remain patch-worthy independently of the UX change.
- **2026-04-15 (same-day, post-v1.19.0 planning)** — post-ship review's two tracked follow-up items formalized with distinct homes based on scope. (a) **Sidecar schema_version validation** (~5 lines, zero-risk until sidecar evolves): recorded as an inline TODO comment in `SKILL.md` Step 3b substep 3 rather than a full plan item. Full Item spec would be overkill for a 5-line fix tied to a deterministic trigger (next sidecar v1.1 field addition); the TODO sits next to the code that needs the fix and fires naturally when a future maintainer touches those paths. Item number intentionally skipped (the plan jumps from Item 12 to Item 14). (b) **Fixture 04 exercising chain-of-rejections override (Item 14)** added as a formal plan item with goal, shape, trigger, and risk. Full item spec is warranted because the work is non-trivial (30-60 min post-calibration, longer pre-calibration), the trigger is softer (saha data required to avoid premature lock-in), and the risk of writing pre-calibration is real (locks in current behavior rather than correct behavior). Trigger: first real `/devil-review --reject` saha test with ≥2 re-raised findings, OR regression suspicion on rule 0, OR any modification to rule 0 semantics. Until one of these fires, the override-0 coverage gap is accepted per tracking discipline. No version bump this revision (doc-only); plan doc convention.
- **2026-04-26 (saha test #4)** — Saha test #4 (cross-model adversarial comparison: codex adversarial review vs devil-review on the same diff in another project, devil-review running v1.19.1) produced concrete calibration and depth gaps mapping to three new items. Plugin user ran both reviewers and reported five distinct gaps. The three structural correctness gaps that became items: (a) **Severity miscalibration** — devil-review correctly identified a permission-cache bug ("can't recover until app restart" — verbatim) but routed it to `considered_not_promoted` rather than promoting; codex (different model family) flagged the same bug as no-ship. The promotion path filtered out a finding whose user-recovery-cost made it structurally above the noise threshold. → **Item 15** (severity floor for user-irrecoverable findings: restart-app/restart-OS/reinstall/clear-data/factory-reset triggers force `high` minimum severity, dampening cannot demote below). (b) **Cap-overflow on high-severity findings** — split-review group cap of 3 (`methodology.md:289` + `:405`) silently buried 4th+ high-severity findings into `considered_not_promoted` regardless of severity ordering; the cap exists for noise control over low/medium findings, but applying it uniformly to high+ findings is overshoot. → **Item 16** (two-channel emit with `must_promote` array bypassing the cap for high+critical in-diff+reachable findings; verdict rules 0-4 amended to read from `must_promote ∪ findings`). (c) **Frontend-slice-only review** — devil-review stayed in the diff slice and missed event-source semantics that codex traced upstream into a backend file. Methodology had no step requiring upstream trace for event-driven findings. → **Item 17** (upstream event-source trace as Claim verification pass step 6, paralleling Item 12's step 5 evidence gate but for internal events rather than external runtimes). Two non-Item observations resolved without new spec: (d) **"iterate" verdict feels soft compared to "no-ship"** — saha feedback noted devil's `verdict: needs-attention` + `decision.action: iterate` reads as "fix and continue" while codex's "no-ship" framing was clearer stop signal. Post-analysis showed this collapses to (a): once the permission-cache bug is correctly promoted to `findings` with severity ≥ high (Item 15's floor), verdict rule 1 produces `verdict: block` which IS the existing no-ship signal. The action label "iterate" describes the developer workflow ("fix this then come back"), not the ship gate. No new item needed; if post-shipping saha test still shows the verdict's no-ship-ness is not visually prominent in markdown, surface as a future polish item then. (e) **Same-model-family blindspot** — both impl and review use Claude; patterns Claude considers acceptable (e.g., `finally { known = true }`) pass through. Plugin code cannot fix this; documentation update only — README "Limitations" or "Complementary tooling" section to note "pair with cross-model adversarial review (e.g., codex plugin in this same marketplace) for severity calibration triangulation". Ships as patch alongside or after the 15-16-17 series. Sequencing recommendation: Item 15 → 16 → 17, smallest-footprint-first, with hard ordering between 15 and 16 (15 enables 16's `must_promote` pool to be non-empty in practice). Reverse direction from saha-test-#3's largest-last sequencing because the dependency chain runs the other way here. Unstarted; no version bump this revision (doc-only).
- **2026-07-17 (skill-quality review → v1.19.2 patch)** — An external skill-quality review (plugin-dev skill-reviewer + plugin-validator agents run over the whole marketplace) surfaced one confirmed defect and several polish items; the patch-level subset shipped same-day as v1.19.2. (a) **`allowed-tools` gap (confirmed critical):** Step 3b requires `sha256sum`/`shasum -a 256` for rejection hashing and `date -u` for `rejected_at` timestamps, but `allowed-tools` only allowed `Bash(git:*)`/`Bash(gh:*)` — every `--reject` run or review with a `rejections.json` present triggered a permission prompt. Fixed by adding `Bash(sha256sum:*)`, `Bash(shasum:*)`, `Bash(date:*)`. (b) **Inline TODO relocated here:** the sidecar `schema_version` validation TODO (placed inline in SKILL.md Step 3b substep 3 per the 2026-04-15 post-v1.19.0 planning entry) was flagged as per-run prompt bloat that outweighs its proximity benefit; removed from SKILL.md and now tracked here instead. The rule stands unchanged: both Step 3b substep 2 (writer) and substep 3 (reader) check `schema_version` *presence* but not that its *value* equals `"1.0"`; add `if schema_version != "1.0"` → error in both paths **in the same commit as the next sidecar format evolution** (e.g., a `suppress_until` field or hash-normalization change), not as a standalone patch. (c) Description rewritten from pure slogan to scope+slogan; Step 5 heading renamed to "Load context and run mandatory traces" to match its content (substeps 4–9 are active trace work, not loading); methodology.md "Patch-chain detection" bold run-in promoted to a `###` heading so SKILL.md's "Patch-chain detection section" references resolve to a real heading; `license: MIT` added to plugin.json. Shipped as an immediate same-day follow-up refactor commit (separate from this patch per no-batch): extracting Step 3b's ~115-line rejection-memory mechanics to a `rejection-memory.md` sibling and relocating substeps 4–6 documentation to the emit phase — a `refactor(devil-review)` with no behavior change, sequenced before the saha-test-#4 series.
- **2026-07-17 (post-ship adversarial review → v1.20.0 rejection-memory hardening)** — A same-day adversarial review of the plugin itself (user-requested "is it fit for purpose" pass over SKILL.md + methodology.md + output-schema.md + rejection-memory.md) surfaced six findings; five content-level findings plus one tracked TODO shipped as v1.20.0, the strategic sixth activated the content-consolidation plan's F/G trigger (recorded in that plan's revision log). Findings and dispositions: (1) **Chain-of-rejections override logically inverted** — suppressed rejections never counted toward the ≥2 resurface threshold, so the override fired only when the reviewer re-raised with concrete new evidence, i.e. it structurally punished exactly the rule-following behavior and could force `approve`/`ship` over a ship-blocker-class re-raise. Fixed with the severity carve-out: override does not fire when any re-raised finding is reachable + in-diff + correctness + high/critical. (2) **Rejection hash brittle to line drift** — the `file:lines:title` hash re-fired rejected findings whenever intermediate fixes shifted line numbers, defeating the round-N+1 scenario the feature was built for (the saha-test-#3 Windows-backslash friction would have recurred after any edit above the finding). Fixed by narrowing the hash to `file:title`; `lines` stays in the entry as audit metadata; loaders recompute hashes from stored fields so old entries keep matching. Sidecar `schema_version` bumped `"1.0"` → `"1.1"` with reader-side value validation — this resolves the v1.19.2 entry's tracked TODO (b) exactly per its trigger ("in the same commit as the next sidecar format evolution (e.g., ... hash-normalization change)"). (3) **WebFetch referenced but not allowed** — methodology's Claim-verification step 5 and output-schema's `external_claims_verified` rule both instruct docs-URL evidence gathering via `WebFetch`, but `allowed-tools` omitted it, silently disabling evidence option (a) in the fork context; the v1.19.2 allowed-tools fix had covered only the hashing/timestamp binaries. Fixed by adding `WebFetch` to `allowed-tools`. (4) **`--reject` target ambiguity** — SKILL.md Step 1 said indices bind to "the most recent prior snapshot" while `rejection-memory.md` substep 2 resolves the snapshot from the *current review target's* slug; the two specs diverged when the session's latest snapshot belonged to a different target. Fixed by aligning SKILL.md, methodology.md, and README wording to the target-scoped behavior (substep 2 was already correct). (5) **Version-label ambiguity** — section headers used bare "(v1.14+)" (schema versions) while calibration notes used bare "v1.18.x" (plugin versions); section headers and parenthetical rule/feature labels across the four core files now carry an explicit `schema` or `plugin` prefix (payload-context references like "v1.5 payloads", which are unambiguously schema, left as-is). (6) **Core-load concern (strategic, not shipped as content)** — measured 197 KB (~50k tokens) loaded per invocation across the four core files before domains/rules/diff; flagged as the top fit-for-purpose risk (schema compliance crowding out code analysis). Disposition: activated Phase F + Phase G triggers in `content-consolidation-plan.md` with sequencing **F → G before the saha-test-#4 series (Items 15 → 16 → 17)** — Items 15–17 add fields and rules, and adding them onto an uncompressed base compounds the load problem. Semver: minor (v1.20.0) — rule 0 gains a condition and the sidecar format evolves; schema stays 1.14 with an amendment note in `schema-history.md` per the v1.15.1 correction precedent. Fixtures 01–03 unaffected (all exercise empty rejection state).
