# devil-review — Phase 3 Plan

**Status:** Item 1 shipped 2026-04-14 (plugin v1.10.0). Item 6 triggered + expanded 2026-04-15 (second saha test). Items 2–5 and Items 7–9 still unstarted.
**Plugin version at time of writing:** v1.3.2 (initial spec); v1.10.0 (Item 1 shipping revision); v1.11.0 (auto-detect prior-review); 2026-04-15 revision captures saha test #2 feedback
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

## Item 6 — Structured prior-review attribution

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

## Item 7 — Self-fact-check pass

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

## Item 8 — Project-rule citation loader

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

## Item 9 — Finding scope tag

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

**Do not batch.** Each item is independent and shippable alone. Batching increases risk and obscures which change caused what behavior shift. This is especially true for Items 6–9 which each touch schema — batching makes regression bisection across fixtures harder.

---

## Success criteria (for when Phase 3 is "done")

Phase 3 is never strictly "done" — it's a menu, not a milestone. But we can call it materially complete when:

- [x] At least one fixture exists and has caught at least one regression in practice (Item 1) — shipped 2026-04-14 with 3 fixtures; the `01-guard-cluster-refactor` fixture deliberately asserts the v1.10.1-post-fix behavior so running it against v1.10.0 exposes the Finding 1 lift_considered schema inconsistency
- [ ] README has a worked good/bad example (Item 2)
- [ ] The `agent:` line in SKILL.md is either justified by a test or removed (Item 3)
- [ ] At least one deferred domain has been added OR explicitly declared not needed (Item 4)
- [ ] Dynamic discovery has been implemented OR explicitly declared premature at current scale (Item 5)
- [ ] Structured prior-review attribution shipped (Item 6 expanded) OR a saha test explicitly shows prose attribution remains sufficient — as of 2026-04-15, saha test #2 triggered expansion; now gated on shipping, not on demand signal
- [ ] Self-fact-check pass shipped (Item 7) OR saha evidence shows reviewer claims are grounded without it
- [ ] Project-rule citation loader shipped (Item 8) OR saha evidence shows implicit rule-following is sufficient without explicit citation
- [ ] Finding scope tag shipped (Item 9) OR saha evidence shows in-diff/pre-existing distinction does not matter in practice

All nine can remain open indefinitely without blocking any user-facing feature. That is the point of Phase 3.

---

## Revision log

- **2026-04-11** — Initial spec written. Plugin at v1.3.2. Phase 3 still unstarted.
- **2026-04-14** — Item 1 (fixtures regression harness) shipped. Trigger: Phase 2.5 shipping (v1.8.1 + v1.9.0 + v1.10.0) produced 3 `no-test` findings in self-review, moving fixtures from "optional menu item" to "blocker on next prompt edit". Shipped 3 fixtures (guard-cluster-refactor, clean-refactor, unsafe-migration) with expected-findings assertions; no last-snapshot.md yet (captured on first real run). Items 2–5 remain unstarted per "real demand only" policy.
- **2026-04-14 (same-day)** — Item 6 (structured prior-review attribution) added to the menu. Trigger: first saha test of `--prior-review` flag (pre-v1.11.0 auto-detect) in a real review produced explicit attribution language ("prior findings resolved, new findings introduced by fix, not a patch-chain pattern") and dampened an otherwise likely `refactor-recommended` verdict to `needs-attention`. Reviewer identified the mechanism as the single most valuable part of the patch-chain detection feature, but noted the attribution is emitted as prose (in `theme_assessment` and finding body annotations) rather than structured fields. Item 6 spec captures the fields and verdict-derivation integration for when automation consumers arrive or prose attribution proves insufficient. Unstarted; gated on observable demand.
- **2026-04-15** — Saha test #2 (two-round devil-review on a real project) produced seven concrete observations. Three of them (finding-diff across rounds, severity recalibration on re-surfaced findings, structured `decision` field for CI/`/loop` gating) triggered Item 6's original triggers and expanded its spec: added severity dampening rule for `carries-over` findings, added top-level `decision` block with `action | patch_chain_detected | iteration_count | rationale`. Four new items added to the menu — Item 7 (self-fact-check pass, closing two observed factual errors in reviewer output), Item 8 (project-rule citation loader, making implicit rule-following explicit), Item 9 (finding scope tag, resolving in-diff vs pre-existing tension). Sequencing revised: Items 7 → 8 → 9 → 6-expanded, because credibility floor (7) and verified-claim citations (8) compound on each other, and Item 6's larger schema footprint benefits from edge cases surfaced by 7–9. Plugin at v1.11.0; no version bump this revision (doc-only).
