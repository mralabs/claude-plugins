# Output Schema

Return your review in **two parts**: a human-readable markdown section, followed by a machine-readable JSON fence. Both sections must be present on every non-error run. Downstream tools consume the JSON; the markdown is for the reviewer reading the result.

## Pre-emit checklist

This file loads at SKILL.md Step 7 — after the hunt. Complete these before writing output (the hunt-side checklist in SKILL.md Step 6 must already be done):

- classify every finding on the axes — `finding_type`, `scope`, `reachability` — per their decision trees, and apply the LLM-compliance severity floor where it applies; when a prior review is loaded, add `prior_relation` on every finding, populate `trace_log.prior_review_summary`, and apply severity dampening to `carries-over` findings
- populate the conditional trace_log blocks whose triggers fired: `patch_chain_risk` with a non-empty `theme_assessment` whenever any Step 3b signal fired (regardless of the final `detected` value), `acceptance_criteria_crosswalk` when a spec with structured ACs loaded
- populate `lift_considered` on every finding whose recommendation is a runtime guard, OR name the system boundary in the finding body
- run rejection memory **Phase B** per `rejection-memory.md` (per-candidate hash match; suppress-silently vs re-raise-with-`previously_rejected`; chain-of-rejections override with the severity carve-out)
- derive `verdict` (rules 0–4) and the `decision` block per the derivation rules in `methodology.md`
- emit the observability `scenarios_considered` lines: `prior-review ingestion: <status>` and `rejection memory: <status>` on every non-error run, plus one `llm-field: <name> — <status>` line per consumed model-output field when the diff consumes model output
- **backstop**: verify every required field in the JSON rules below is present — a new required field added in a future schema version is caught by this bullet without a per-field checklist entry

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
  - `action` (enum, required): exactly one of `iterate | stop-and-refactor | ship`. Derivation rules live in the "Decision derivation" section of `methodology.md`.
  - `patch_chain_detected` (boolean, required): `true` iff all four hold — prior review loaded, ≥1 current finding has `prior_relation.category == "carries-over"`, current diff and prior diff share ≥1 file, and the current in-diff finding count is not materially lower than prior (< 50% reduction is "not materially lower").
  - `iteration_count` (integer, required, ≥1): count of times this session has reviewed this target. Defaults to `1` on a fresh run with no prior. When a prior snapshot exists and carries an `iteration_count`, increment by 1; otherwise set to `2` if prior exists without the field.
  - `rationale` (string, required): one sentence explaining why this action was chosen. Must be non-empty.
  Verdict ↔ decision.action agreement: typically `block`/`needs-attention` → `iterate`, `refactor-recommended` → `stop-and-refactor`, `approve` → `ship`. Disagreements are allowed and are the automation signal — e.g., `verdict: needs-attention` + `decision.action: stop-and-refactor` when `patch_chain_detected: true` at `iteration_count ≥ 2`. When they disagree, `decision.action` is the CI/automation signal and the disagreement should be called out in `rationale`.
- **`findings[].prior_relation`** is **conditionally required**: required on every finding when a prior review was loaded (Step 3b status `loaded`), omitted entirely on all findings when no prior was loaded (status `absent` or any `rejected-*` value). Two fields: `category` (enum, required — **three values**: `carries-over | new-drift-from-fix | pre-existing-orthogonal`) and `prior_finding_ref` (string or null, optional — the prior finding's title quoted verbatim, or null when no specific prior finding is referenced). Classification rules live in the "Prior-relation classification" subsection of `methodology.md`. Silent omission when a prior was loaded is a grounding failure — the attribution must be visible per finding. **`resolved` is not a permitted value here** (plugin v1.15.1 correction); the `resolved` concept lives only in `trace_log.prior_review_summary.resolved` as a count of prior findings no longer present. A finding emitted with `category: resolved` is schema-methodology invalid and downstream consumers are entitled to reject it.
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
- **`trace_log.patch_chain_risk`** is conditionally required. When SKILL.md Step 3b scans the git log and **any** of the three signals fires (`fix-prefix-cluster`, `same-file-hotspot`, `prior-review-overlap`), the field must be present and must carry a one-sentence `theme_assessment` regardless of whether `detected` ends up `true` or `false`. When no signal fires, the field may be omitted entirely. When the field is present: `detected` (boolean) records whether the reviewer's theme-vs-root judgment confirms the patch chain; `signals_fired` (array) lists which signals triggered the scan; `chain_depth` (integer) is the count of defensive commits in the window that match the prefix filter (0 if only the prior-review-overlap signal fired); `prior_commits` (array of one-line strings `"<sha> <subject>"`) records the evidence — omit or empty-array if the prior-review-overlap signal fired alone; `prior_review_file` is the resolved auto-detect path `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md` when Step 3b successfully loaded a snapshot, else `null` (file absent or rejected); `theme_assessment` is the mandatory one-sentence answer to the theme-vs-root gate; `recommendation` is a one-sentence note on what the signal means for this review. See the "Patch-chain detection" section in `methodology.md` and the data-collection rules in SKILL.md Step 3b. Emitting `detected: true` without a `theme_assessment` is the same class of grounding failure as an empty `symbols_inspected` — the reviewer skipped the gate. The `refactor-recommended` verdict rule 3 clause (a) reads `detected == true` from this field; clause (b) is independent of this field and remains reachable in v1.6 payloads.
- **`findings` length must respect the hard cap** from `methodology.md` (3 under 500 lines, 5 under 1500, 3 per split group).
- **`confidence`** is 0.0–1.0. Use it for your own uncertainty — do not soften severity to compensate for low confidence.
- **`findings[].finding_type`** is required on every finding emitted by schema v1.6 or later. Values: `correctness | design_debt | best_practice_violation | architectural_smell`. Classification rules live in the "Severity axes and finding taxonomy" section of `methodology.md`. **Default-to-correctness rule (backward compatibility):** consumers reading payloads without this field — typically v1.5-era snapshots replayed through v1.6 tooling — must treat absence as `"correctness"`. Rationale in [`methodology.md` §Calibration rules → Compatibility property](methodology.md).
- **`findings[].scope`** is required on every finding emitted by schema v1.10 or later. Values: `in-diff | pre-existing | future-work`. Classification rules live in the "Scope classification" section of `methodology.md`. **Default-to-in-diff rule (backward compatibility):** consumers reading payloads without this field — typically pre-v1.10 snapshots replayed through v1.10 tooling — must treat absence as `"in-diff"`. Rationale in [`methodology.md` §Calibration rules → Compatibility property](methodology.md). Only findings with `scope == "in-diff"` (or default) drive verdict escalation — `pre-existing` and `future-work` findings are surfaced for transparency but do not contribute to `correctness_severity`, `design_debt_severity`, or the `block`/`needs-attention`/`refactor-recommended` rules. All three scopes count toward the hard cap on findings.
- **`trace_log.rejections_loaded`** is **unconditionally required** (schema v1.14). Records which rejection entries the skill loaded from `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` during rejection memory Phase A (`rejection-memory.md`, run at Step 3b). Each entry has two required fields: `hash` (64-character lowercase sha256 hex string, computed per the normalization rule in `rejection-memory.md` substep 1 — trim + lowercase `file` + collapse `title` whitespace + `:`-joined over the `file:title` pair; line ranges are deliberately excluded from identity since plugin v1.20.0, because line drift between rounds must not re-fire a rejected finding) and `rejected_at` (ISO-8601 timestamp, preserved verbatim from the rejection entry). The emitted hash is **recomputed at load time** from each entry's stored `file` and `title` — the sidecar's stored `hash` field is audit metadata, which is what keeps `"1.0"`-era sidecar entries (recorded under the old line-bearing normalization) matching under the current rule. Empty array `[]` is valid and expected when the `rejections.json` file does not exist for the session or when the file exists with `rejections: []`. Absence of the field is a grounding failure because it means the rejection-memory load step was skipped. When the load attempt fails due to malformed JSON or missing `schema_version` in the sidecar file, emit `trace_log.rejections_loaded: []` and also emit the `scenarios_considered` line `rejection memory: rejected-malformed-json` — the empty array plus the status line together record that the load was attempted and rejected. The `rejections.json` sidecar has its own `schema_version` field (currently `"1.1"`; readers accept `"1.0"` and `"1.1"` and treat any other value as malformed) managed independently of the main payload schema; sidecar schema drift does not require a main-schema bump.
- **`findings[].previously_rejected`** is optional (schema v1.14). Populate only on findings that were re-raised despite matching a rejection hash in `trace_log.rejections_loaded`. Three required fields: `rejected_at` (ISO-8601 timestamp copied verbatim from the matching rejection entry), `prior_rationale` (the rejection rationale string from the rejection entry, or `null` when the rejection was recorded without a rationale), `new_evidence` (a **single concrete sentence** describing what concrete difference in the current analysis justifies re-raising — a new call path, a new config condition, a new sibling field, a new project rule, a new prior-review carries-over status). `new_evidence` must be specific enough that a downstream reader can understand why the finding came back; generic "additional analysis surfaced" or "reviewer reconsidered" does not qualify and a finding emitted with such `new_evidence` is subject to rejection by consumers as schema-methodology inconsistent. When a finding has `previously_rejected` populated, the finding body must lead with the literal prose preamble: `Previously rejected on <rejected_at> with rationale <prior_rationale or "(none provided)">. New evidence: <new_evidence>.` followed by the usual finding content. Suppressed rejections (candidate finding matched a rejection hash and was silently dropped per the default path) do NOT populate this field — they do not appear in `findings` at all. The field's presence is the re-raise signal; its absence is the default path. See the "User rejection memory" section in `methodology.md` for the suppress-vs-re-raise decision rule.
- **`findings[].reachability`** is required on every finding emitted by schema v1.13 or later. Values: `reachable | hypothetical | requires-specific-config`. Classification rules live in the "Reachability classification" section of `methodology.md`. **Default-to-reachable rule (backward compatibility):** consumers reading payloads without this field — typically pre-v1.13 snapshots replayed through v1.13 tooling — must treat absence as `"reachable"`. Rationale in [`methodology.md` §Calibration rules → Compatibility property](methodology.md). Only findings with `reachability == "reachable"` (or default) drive verdict escalation — `hypothetical` and `requires-specific-config` findings are surfaced for transparency but do not contribute to `correctness_severity`, `design_debt_severity`, or the `block`/`needs-attention`/`refactor-recommended` rules. All three reachability levels count toward the hard cap on findings. Reachability is **orthogonal** to `severity` and `confidence`: a `reachable` finding can have low `confidence` (reviewer is not sure their reading is right), and a `hypothetical` finding can have high `confidence` (reviewer is sure this WOULD be a bug if reached but cannot name a reaching path). The body must record supporting evidence: `reachable` findings name a concrete call path from an entry point; `requires-specific-config` findings name the specific config, flag, environment variable, or platform; `hypothetical` findings need no additional body requirement but the classification itself signals the reviewer could neither trace a path nor name a config.
- **`correctness_severity`** is an optional top-level enum (`critical | high | medium | low | none`). Derived as the max severity among findings with `finding_type == "correctness"` (including findings where `finding_type` is absent and defaults to correctness). Omit the field entirely when no correctness findings exist, or emit `"none"` — both are valid. Consumers should treat absence as `"none"`.
- **`design_debt_severity`** is an optional top-level enum with the same values. Derived as the max severity among findings with `finding_type == "design_debt"`. Same emit-or-omit rule. `architectural_smell` and `best_practice_violation` findings do not contribute to either axis — they have their own `findings[].severity` but do not roll up today.
- **`findings[].lift_considered`** is optional. Populate it when the recommendation is a runtime guard (per the Lift hierarchy rule in `methodology.md`). Each of `type_lift`, `writer_lift`, `ordering_lift` carries `{ viable: boolean, rationale: string }` where `rationale` is a one-sentence explanation of the constraint that either blocks or enables that lift. For a guard recommendation to be justified, either (a) **all three** of `type_lift`, `writer_lift`, `ordering_lift` must be `viable: false` with a specific constraint named per lift, OR (b) the finding body must name a **system boundary** (user input, external API, untrusted data, trust boundary where the producer cannot be changed) as the reason a lift is not the right primitive. If any of the three lifts is `viable: true` and no system boundary is named in the body, the recommendation should be that viable lift, not a guard — emitting a guard recommendation under these conditions is a schema-methodology inconsistency that downstream consumers are entitled to reject. If the recommendation is not a guard (e.g., recommending a lift directly, recommending a test, recommending removing code), the field may be omitted.
- **`considered_not_promoted[].design_alternative_considered`** is optional — a one-sentence description of the lift or structural change that would resolve the observation if it ever escalated to a bug. Use it when you see a latent issue that is not a bug today but has an obvious structural fix; leaves a breadcrumb for the next reviewer.
- **`considered_not_promoted[].tracked_as_debt`** is optional boolean. Set to `true` when the observation represents design debt worth tracking even though it doesn't rise to a finding. No consumer required today; metadata for future tooling.
- **Verdict consistency.** The five-rule verdict derivation (override 0 + rules 1-4, filtered on `scope == "in-diff"` AND `reachability == "reachable"` with default-to-in-diff applied to pre-v1.10 payloads and default-to-reachable applied to pre-v1.13 payloads) is stated authoritatively in [`methodology.md` §Calibration rules → Verdict derivation](methodology.md) — including the per-rule bullets for `block` / `needs-attention` / `refactor-recommended` / `approve`, the Compatibility property across schema versions, and the Override discipline rule for manual deviations. Consumers validating payload conformance must apply those rules: a `verdict` that disagrees with the rules applied to the current `findings` is a schema-methodology inconsistency and downstream consumers are entitled to reject the payload. Rule 0 (chain-of-rejections override) bypasses rules 1-4 when the resurface count reaches ≥ 2 and no re-raised finding clears the severity carve-out (reachable in-diff correctness at high/critical, plugin v1.20.0) — see the "User rejection memory" section in `methodology.md`.
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
