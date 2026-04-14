# devil-review — Phase 3 Plan

**Status:** Item 1 shipped 2026-04-14 (plugin v1.10.0). Items 2–5 still unstarted.
**Plugin version at time of writing:** v1.3.2 (initial spec); v1.10.0 (Item 1 shipping revision)
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

## Sequencing recommendation

Not a fixed order — pick based on observed need.

1. **Default starting point: Item 2 (README good/bad).** Lowest risk, highest onboarding value, unblocks nothing but helps everyone. Do this first unless a regression scare happens.
2. **If you edit any prompt file (SKILL.md / methodology.md / output-schema.md / any domain): Item 1 (fixtures).** The first prompt edit after real use is the moment fixtures become worth their cost.
3. **If Item 1 is done and output still feels shallow: Item 3 (agent test).** Uses fixtures from Item 1, so strictly downstream.
4. **Only on real demand: Item 4 (deferred domains).**
5. **Only at scale: Item 5 (dynamic discovery).**

**Do not batch.** Each item is independent and shippable alone. Batching increases risk and obscures which change caused what behavior shift.

---

## Success criteria (for when Phase 3 is "done")

Phase 3 is never strictly "done" — it's a menu, not a milestone. But we can call it materially complete when:

- [x] At least one fixture exists and has caught at least one regression in practice (Item 1) — shipped 2026-04-14 with 3 fixtures; the `01-guard-cluster-refactor` fixture deliberately asserts the v1.10.1-post-fix behavior so running it against v1.10.0 exposes the Finding 1 lift_considered schema inconsistency
- [ ] README has a worked good/bad example (Item 2)
- [ ] The `agent:` line in SKILL.md is either justified by a test or removed (Item 3)
- [ ] At least one deferred domain has been added OR explicitly declared not needed (Item 4)
- [ ] Dynamic discovery has been implemented OR explicitly declared premature at current scale (Item 5)

All five can remain open indefinitely without blocking any user-facing feature. That is the point of Phase 3.

---

## Revision log

- **2026-04-11** — Initial spec written. Plugin at v1.3.2. Phase 3 still unstarted.
- **2026-04-14** — Item 1 (fixtures regression harness) shipped. Trigger: Phase 2.5 shipping (v1.8.1 + v1.9.0 + v1.10.0) produced 3 `no-test` findings in self-review, moving fixtures from "optional menu item" to "blocker on next prompt edit". Shipped 3 fixtures (guard-cluster-refactor, clean-refactor, unsafe-migration) with expected-findings assertions; no last-snapshot.md yet (captured on first real run). Items 2–5 remain unstarted per "real demand only" policy.
