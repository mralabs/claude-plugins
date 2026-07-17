# devil-review — v2.0 Restructure Plan (hunt/emit split)

**Status:** Unstarted. Plan created 2026-07-17 from the post-ship adversarial review of the plugin itself (see `phase-3-plan.md` revision log, same date) and the token-load discussion that followed. Supersedes `content-consolidation-plan.md` Phase G as a standalone item (see Item 4 below); Phase F remains independent and ships first.
**Plugin version at time of writing:** v1.20.0 (schema v1.14).
**Scope:** Restructure the skill so that the adversarial hunt runs with only hunt content in context, the output contract loads at emit time, the required-field surface shrinks to fields with actual consumers, and rationale/history prose leaves the runtime load entirely. Absorbs phase-3-plan Items 15 and 17 into the hunt content; defers Item 16 to a post-v2.0 saha test.

> **Guiding principle:** The devil is the hunt, not the ledger. Every token of process loaded during code-reading competes with code-reading. A rule earns its place in the runtime files only if it changes what the reviewer *does*; everything that explains *why* lives in docs and is enforced by fixtures.

## Diagnosis (why v2.0, not another patch)

Three facts, all recorded in this repo:

1. **The load is inverted.** Post-v1.20.0 core load is ~197 KB (~50k tokens) across SKILL.md + methodology.md + output-schema.md + rejection-memory.md, loaded before domains, project rules, or the diff. Rough split: ~30-35% hunt content (stance, attack surface, tracing disciplines), ~65-70% bookkeeping (classification axes, verdict derivation, schema contract, observability rules, 19-bullet pre-output checklist, ~15 mandatory trace_log fields).
2. **The misses are attention misses.** Saha test #4: devil-review buried a real "can't recover until app restart" bug in `considered_not_promoted` and stayed inside the diff slice, while a process-free cross-model reviewer flagged the same bug no-ship and traced upstream. The reviewer carrying 50k tokens of methodology was outperformed on the core job by a reviewer carrying none.
3. **The response pattern is a patch chain by the plugin's own definition.** Each saha-test miss produced a new rule or field (Items 15, 16, 17 pending; scope, reachability, rejection memory, evidence gate before them). Each addition grows the load, which shrinks hunt attention, which produces the next miss. The plugin's own lift hierarchy names the fix: stop adding guards, apply an **ordering lift** — restructure *when* the process content loads so hunt attention is protected by construction.

## Target architecture

Three stages, three load profiles:

```
Stage 1 — ORCHESTRATE   SKILL.md (thin)
  parse args, resolve target, collect diff, git patch-chain scan,
  rejection memory Phase A (record + load). No output rules, no checklist.

Stage 2 — HUNT          hunt.md (+ matching domains/*.md + project rules)
  stance, attack surface, all tracing disciplines, severity + block test,
  hard cap, generalization test, lift hierarchy, claim verification,
  test-trace. Rules only — no rationale narratives, no schema.
  THE DIFF AND THE CODE ARE READ IN THIS STAGE, WITH ONLY THIS IN CONTEXT.

Stage 3 — EMIT          emit.md (merged output contract)
  loaded only after candidate findings exist. Classification axes
  (finding_type, scope, reachability, prior_relation), rejection memory
  Phase B (match/suppress/re-raise), verdict derivation + decision block,
  markdown + JSON format, trace_log contract, error output.
```

The insight behind the split: classification axes are *labels applied to findings that already exist* — they contribute nothing to finding bugs. Verdict derivation is arithmetic over labeled findings. Neither needs to occupy context while the model reads code.

**Hunt-time load target: ≤ 70 KB** (hunt.md ~25-30 KB + typical 1-2 domain files + project rules cap). Emit-time total is allowed to be similar to today — by then the reading is done and attention cost is low.

## Items

### Item 1 — Hunt/emit file split (the ordering lift)

Split `methodology.md` + `output-schema.md` + `rejection-memory.md` into `hunt.md` + `emit.md` along the stage boundary above. SKILL.md instructs: load `hunt.md` at Step 5, run the review, and load `emit.md` only at Step 7. The 19-bullet pre-output checklist moves into `emit.md` and shrinks (most bullets restate field rules that sit adjacent in the same file post-merge; the backstop bullet pattern replaces per-field bullets). Rejection memory Phase A stays orchestrator-side; Phase B moves into `emit.md` where it runs anyway.

**Effort:** one focused session. **Risk:** medium — content moves, no content changes; fixture expected-findings verify behavior is preserved. **Semver:** ships only as part of the v2.0 release commit series.

### Item 2 — Schema diet (v2.0, major)

Required trace_log fields cut from ~15 to ~6: `ship_blocker_answer` + `ship_blocker_reasoning`, `domains_loaded`, `symbols_inspected`, `mutated_records_inspected`, `scenarios_considered`, `findings_dropped_in_verification`. Everything else becomes conditional (present when its trigger fired: `patch_chain_risk`, `prior_review_summary`, `acceptance_criteria_crosswalk`, `rejections_loaded` when the file exists, `project_rules_loaded` when any finding cites a rule) or is dropped (`external_claims_verified` counter — `evidence_sources` entries already carry the proof; `domains_considered_dropped`; mandatory-nonempty `classification_notes` — folds into a `scenarios_considered` line; `tracked_as_debt` — "no consumer required today" per the current schema text, which is this repo's own YAGNI test failed).

The three observability status lines collapse into one compact line: `context: prior=<status> rejections=<status> rules=<n>`.

Per-finding surface unchanged in shape (severity, confidence, finding_type, scope, reachability, test_coverage, optional rule_refs / evidence_sources / lift_considered / previously_rejected / prior_relation) — the finding-level fields all have consumers (verdict derivation, rejection matching, citation verification).

**Removed required fields = major bump.** Payload `schema_version` goes to `2.0`; `schema-history.md` gains the v2.0 entry with a consumer migration note (v1.x consumers must treat absent conditional fields as their documented defaults — the default-to-X rules already exist and carry over).

**Effort:** one session including fixture updates. **Risk:** medium — fixtures 01-03 expected-findings reference v1.14 required fields and must be rewritten alongside. **Semver:** major (v2.0.0).

### Item 3 — Rationale extraction to docs

Move every "Why this exists", "Rationale", saha-test narrative, threshold-calibration story, and interaction essay out of the runtime files into `docs/design-rationale.md` (one section per rule, linked from the rule's one-line statement). Runtime files keep: the rule, the decision tree, the enum, the example when load-bearing. Fixtures are the regression guard for rule semantics — that is what Item 1 of phase-3 built them for.

**Effort:** rides inside Items 1-2 (the split forces touching every section anyway; extraction happens in the same pass). **Risk:** low-medium — per-section claim-verification pass (has any load-bearing clause been dropped?) per the old Phase G discipline, which this item absorbs.

### Item 4 — Absorb Phase G; Phase F unaffected

`content-consolidation-plan.md` Phase G (standalone prose compression) is cancelled as standalone work: compressing prose that Items 1-3 are about to relocate and rewrite is wasted effort, by the same "structural work must land first" dependency logic Phase G itself documented. Its discipline (one section per commit, per-commit claim-verification, read-back test) is inherited by Items 1-3. Phase F (threshold rationale consolidation) is independent, ~15-20 min, and ships **before** this plan starts — it reduces the surface Items 1-3 must move.

### Item 5 — Fold phase-3 Items 15 and 17 into hunt content; defer Item 16

- **Item 15 (severity floor for user-irrecoverable findings)** is a hunt rule — one paragraph in hunt.md's severity section plus the existing LLM-floor pattern. Ships inside v2.0 instead of as a separate v1.21 minor.
- **Item 17 (upstream event-source trace)** is the single highest-value addition to the hunt: it directly closes the saha-4 "stayed in the diff slice" miss, and it is the kind of item v2.0 exists to make affordable — a new tracing discipline paid for by removed bookkeeping, not stacked on top of it. Ships inside v2.0 as a hunt.md tracing subsection + claim-verification step.
- **Item 16 (must_promote cap-bypass channel)** is deferred: it patches a symptom (high-severity findings buried by the cap) that freed hunt attention plus Item 15's floor may resolve on their own. Re-evaluate at the first post-v2.0 saha test; if the cap still buries high+ findings, the simpler v2-native fix is "the hard cap does not apply to high/critical in-diff reachable findings" — one sentence, no new channel, no schema field.

## Sequencing

**F → (Items 1+3 together) → Item 2 → post-v2.0 saha test → Item 16 decision.**

- Phase F first: smallest, independent, shrinks what moves.
- Items 1 and 3 in one series (per-section commits): the split pass touches every section once; extracting rationale in the same pass avoids touching everything twice. Behavior-preserving — fixtures must pass unchanged after this series. Plugin version: single marker minor bump at series end (à la v1.19.1), schema still 1.14.
- Item 2 (+ Item 5's folded 15/17) lands as the v2.0.0 release: schema 2.0, fixtures rewritten, README + schema-history updated in the same series.
- The first saha test after v2.0 measures both success criteria below and decides Item 16.

Splitting the behavior-preserving restructure (1+3) from the breaking release (2) keeps bisection clean: if fixture behavior drifts, it happened in the restructure, not the schema change.

## Success criteria

- [ ] Hunt-time load ≤ 70 KB measured at Stage 2 (hunt.md + median domain load), from today's 197 KB always-loaded core.
- [ ] Required trace_log field count ≤ 6 unconditional; every remaining required field names its consumer in `emit.md`.
- [ ] Runtime files contain zero "Why this exists"-class narrative paragraphs; `docs/design-rationale.md` exists and is linked per rule.
- [ ] Fixtures 01-03 pass after the Item 1+3 series with unchanged expected verdicts/findings (behavior-preservation gate).
- [ ] Fixtures rewritten for schema 2.0 in the Item 2 series; fixture 04 (rule-0 override coverage, phase-3 Item 14) reconsidered here since rejection Phase B moves into emit.md.
- [ ] Post-v2.0 saha test: re-run a saha-4-class comparison (same diff, devil-review vs cross-model reviewer) — parity or better on severity calls and upstream tracing; result recorded in the revision log and drives the Item 16 decision.

## Revision log

- 2026-07-17 — Plan created. Origin: post-ship adversarial review of the plugin (six findings, five shipped as v1.20.0) surfaced the load inversion as the top fit-for-purpose risk; follow-up analysis reframed the saha-test response pattern (miss → new rule → more load → next miss) as the plugin's own patch-chain definition applied to itself, with the hunt/emit ordering lift as the structural fix. Key scope decisions at creation: Phase G cancelled as standalone (absorbed into Items 1-3); phase-3 Items 15/17 folded into v2.0 hunt content; Item 16 deferred to post-v2.0 saha evidence; behavior-preserving restructure deliberately sequenced before the breaking schema release for bisection cleanliness.
