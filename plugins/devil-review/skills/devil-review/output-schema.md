# Output Schema

Return your review in **two parts**: a human-readable markdown section, followed by a machine-readable JSON fence. Both sections must be present on every non-error run. Downstream tools consume the JSON; the markdown is for the reviewer reading the result.

---

## Part 1 — Markdown section

```
# Devil Review

Target: <"working tree diff" | "branch diff against <ref>" | "PR #<n>">
Scope: <N files, M lines changed>  [or: "split review (N files across G groups)"]
Focus: <user's focus text, if provided>
Verdict: <block | needs-attention | refactor-recommended | approve>

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
- <original claim as first written> — reason: <unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept>
- ...
(empty list `none` is valid when every candidate finding survived the Claim verification pass unchanged — omission is not; per methodology.md)

## Findings

### [severity] Title
- **File**: `path/to/file`
- **Lines**: L<start>-L<end>
- **Type**: <correctness | design_debt | best_practice_violation | architectural_smell>
- **Scope**: <in-diff | pre-existing | future-work>
- **Confidence**: <0.0 to 1.0>

<body — what can go wrong, why this code path is vulnerable, likely impact>

**Recommendation**: <concrete change to reduce risk>

**Rule citations** (optional, only when a loaded project rule applies):
- `<path/to/rule.md>` — *<rule identifier>*: "<verbatim 1–2 line quote from the rule file>"
- ...

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

**Schema version history:**
- `1.0` — initial schema: verdict, target, scope, findings, trace_log with symbols_inspected + scenarios_considered
- `1.1` — added `ship_blocker_answer`, `ship_blocker_reasoning`, `domains_loaded`, `domains_considered_dropped`, `classification_notes`. New `block` verdict value. No fields removed or retyped.
- `1.2` — added optional `trace_log.considered_not_promoted` for observations the reviewer saw but dropped from findings (with reason). No fields removed or retyped; older consumers that do not know the field can ignore it.
- `1.3` — added required `findings[].test_coverage` (object with `covered_by` and `why_missed`) and required `trace_log.mutated_records_inspected` (array tracking data-model fanout, parallel to `symbols_inspected` which tracks the call graph). Added `test-covers-invariant` to the allowed reasons in `considered_not_promoted`. No fields removed or retyped, but the two new required fields mean a v1.2 consumer reading a v1.3 payload will see unknown keys; strict consumers must bump.
- `1.4` — added two optional nested fields: `symbols_inspected[].failure_modes_considered` for auditing unchanged callees against new callers, and `mutated_records_inspected[].new_reader_paths` for auditing preserved siblings against new writer→reader paths. No new top-level fields; both extensions are additive and nested inside existing arrays, so v1.3 consumers parse v1.4 payloads without error. Strict consumers must bump to read the new nested data.
- `1.5` — added optional top-level `trace_log.acceptance_criteria_crosswalk` for recording per-AC proof-of-implementation walks when the review target includes a spec with structured acceptance criteria. Conditionally required: must be populated when a spec with structured ACs exists, optional (empty array) otherwise. The field exists so the "I crosswalked the spec" claim is falsifiable. No fields removed or retyped; v1.4 consumers parse v1.5 payloads without error and simply ignore the unknown key.
- `1.6` — extended `verdict` enum with a fourth value `refactor-recommended` (existing three values keep their exact prior semantics). Added optional top-level `correctness_severity` and `design_debt_severity` (same enum as `findings[].severity` plus `none`). Added required `findings[].finding_type` (enum: `correctness | design_debt | best_practice_violation | architectural_smell`) — consumers reading payloads without this field (replay of v1.5 snapshots) must treat absence as `"correctness"`. Added optional `findings[].lift_considered` (three-way object with type_lift / writer_lift / ordering_lift, each carrying `{viable, rationale}`) for recording lift evaluation when the recommendation is a guard. Added optional `considered_not_promoted[].design_alternative_considered` (string) and `considered_not_promoted[].tracked_as_debt` (boolean) for observations that are debt rather than bugs. Compatibility property: v1.5-era payloads re-validated under v1.6 rules produce identical verdicts because the default-to-correctness rule on missing `finding_type` preserves pre-v1.6 block semantics.
- `1.7` — added optional `trace_log.patch_chain_risk` object for recording the git-log patch-chain scan from SKILL.md Step 3b. Conditionally required: when any of the three signals (fix-prefix cluster, same-file hotspot, prior-review overlap) fires during Step 3b, the field must be present and must carry `theme_assessment` regardless of whether `detected` is `true` or `false` — the theme-vs-root judgment is auditable. When no signal fires, the field may be omitted entirely. No existing fields removed or retyped; v1.6 consumers ignore the unknown key and see identical verdicts on inputs without patch-chain signals. The `refactor-recommended` verdict rule 3 clause (a) becomes reachable for the first time with v1.7 — v1.6 reviewers could emit `refactor-recommended` via clause (b) (design_debt findings outnumber correctness) but not via patch-chain without v1.7 infrastructure.
- `1.8` — added required `trace_log.findings_dropped_in_verification` (array of `{original_claim, reason}` entries) for recording the output of the Claim verification pass (methodology.md). Empty array `[]` is valid and expected when every candidate finding survived the pass unchanged — absence of the field is a grounding failure because it means the pass was skipped. The `reason` enum is `unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept`. No fields removed or retyped; v1.7 consumers parse v1.8 payloads without error but see an unknown key. The verdict derivation rules and all severity axes are unchanged. Pairs with the new methodology "Claim verification pass (pre-emit)" section that runs after candidate findings are generated and before emit; findings that fail the pass are either narrowed (kept with reason `narrowed-kept`), reclassified (moved to `considered_not_promoted`), or dropped (logged here). Compatibility property: v1.7 payloads re-validated under v1.8 rules produce identical verdicts — the new field affects only the grounding-completeness check, not verdict derivation.
- `1.9` — added required `trace_log.project_rules_loaded` (array of `{path, bytes}` entries) recording which project-local rule files were loaded by SKILL.md Step 5.2b. Empty array `[]` is valid when no project rule file matched; absence is a grounding failure (the load attempt must be visible). Added optional `findings[].rule_refs` (array of `{source, rule, quote}` entries) for per-finding citations against the loaded rule corpus. Citation is opportunistic — empty array or absent field both mean "no applicable rule". The `quote` field must be a **verbatim 1–2 line string literally present in the cited file** (string-findable, modulo leading/trailing whitespace); paraphrased quotes are schema-invalid and downstream consumers are entitled to reject them. `source` must match one of the paths in `trace_log.project_rules_loaded`; citing an unloaded file is a grounding failure. No fields removed or retyped; v1.8 consumers parse v1.9 payloads without error. Verdict derivation and severity axes unchanged. Pairs with the new methodology "Project-rule citation" section. Compatibility property: v1.8 payloads re-validated under v1.9 rules produce identical verdicts — citations are additive grounding evidence, not verdict inputs.
- `1.10` — added required `findings[].scope` (enum: `in-diff | pre-existing | future-work`). Default-to-`in-diff` rule for payloads without this field (replay of pre-v1.10 snapshots) preserves pre-v1.10 verdict calculations identically. Verdict derivation rules updated to filter on `scope == "in-diff"` — only in-diff findings contribute to `correctness_severity`, `design_debt_severity`, and the block/needs-attention/refactor-recommended rules. `pre-existing` and `future-work` findings still count toward the hard cap and still emit as findings, but they do not drive verdict escalation. A review whose only findings are `pre-existing` or `future-work` lands at `verdict: approve` because the diff itself is safe to ship. No fields removed or retyped; v1.9 consumers parse v1.10 payloads without error. Pairs with the new methodology "Scope classification" section. Compatibility property: v1.9 payloads re-validated under v1.10 rules produce identical verdicts — the scope filter is a no-op on findings without the field because of the in-diff default.

```json
{
  "schema_version": "1.10",
  "verdict": "block | needs-attention | refactor-recommended | approve",
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
        "reason": "unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept"
      }
    ],
    "project_rules_loaded": [
      {
        "path": "<path/to/rule/file.md — must match a Step 5.2b glob result>",
        "bytes": 0
      }
    ]
  },
  "findings": [
    {
      "severity": "critical | high | medium | low",
      "finding_type": "correctness | design_debt | best_practice_violation | architectural_smell",
      "scope": "in-diff | pre-existing | future-work",
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
- **`trace_log.findings_dropped_in_verification`** is **unconditionally required** on every non-error run. It records the output of the Claim verification pass (see `methodology.md` section "Claim verification pass (pre-emit)"). Empty array `[]` is valid and expected when every candidate finding survived the pass unchanged — absence of the field is a grounding failure because it means the pass was skipped rather than run-and-clean. Each entry has two required fields: `original_claim` (one sentence, the load-bearing claim as first written before the pass fired) and `reason` (enum: `unsupported-reachability | asymmetry-error | scope-inflation | counterfactual-leak | no-evidence-after-trace | narrowed-kept`). Use `narrowed-kept` when the pass fired and the finding was rewritten with a tighter claim rather than dropped — the finding still appears in `findings` with its narrower version, and the original wider claim is logged here for auditability. Use `no-evidence-after-trace` when the pass could not locate supporting evidence for the claim even after re-reading the code paths the claim referenced. Do not use this field to silently smuggle in observations that were never candidate findings — it is a record of the pass's *drops and narrowings*, not a general-purpose scratchpad.
- **`trace_log.patch_chain_risk`** is conditionally required. When SKILL.md Step 3b scans the git log and **any** of the three signals fires (`fix-prefix-cluster`, `same-file-hotspot`, `prior-review-overlap`), the field must be present and must carry a one-sentence `theme_assessment` regardless of whether `detected` ends up `true` or `false`. When no signal fires, the field may be omitted entirely. When the field is present: `detected` (boolean) records whether the reviewer's theme-vs-root judgment confirms the patch chain; `signals_fired` (array) lists which signals triggered the scan; `chain_depth` (integer) is the count of defensive commits in the window that match the prefix filter (0 if only the prior-review-overlap signal fired); `prior_commits` (array of one-line strings `"<sha> <subject>"`) records the evidence — omit or empty-array if the prior-review-overlap signal fired alone; `prior_review_file` is the resolved auto-detect path `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md` when Step 3b successfully loaded a snapshot, else `null` (file absent or rejected); `theme_assessment` is the mandatory one-sentence answer to the theme-vs-root gate; `recommendation` is a one-sentence note on what the signal means for this review. See the "Patch-chain detection" section in `methodology.md` and the data-collection rules in SKILL.md Step 3b. Emitting `detected: true` without a `theme_assessment` is the same class of grounding failure as an empty `symbols_inspected` — the reviewer skipped the gate. The `refactor-recommended` verdict rule 3 clause (a) reads `detected == true` from this field; clause (b) is independent of this field and remains reachable in v1.6 payloads.
- **`findings` length must respect the hard cap** from `methodology.md` (3 under 500 lines, 5 under 1500, 3 per split group).
- **`confidence`** is 0.0–1.0. Use it for your own uncertainty — do not soften severity to compensate for low confidence.
- **`findings[].finding_type`** is required on every finding emitted by schema v1.6 or later. Values: `correctness | design_debt | best_practice_violation | architectural_smell`. Classification rules live in the "Severity axes and finding taxonomy" section of `methodology.md`. **Default-to-correctness rule (backward compatibility):** consumers reading payloads without this field — typically v1.5-era snapshots replayed through v1.6 tooling — must treat absence as `"correctness"`. This rule is what keeps v1.5 payloads producing identical verdicts under v1.6 rules; do not change it.
- **`findings[].scope`** is required on every finding emitted by schema v1.10 or later. Values: `in-diff | pre-existing | future-work`. Classification rules live in the "Scope classification" section of `methodology.md`. **Default-to-in-diff rule (backward compatibility):** consumers reading payloads without this field — typically pre-v1.10 snapshots replayed through v1.10 tooling — must treat absence as `"in-diff"`. This rule is what keeps v1.9 payloads producing identical verdicts under v1.10 rules; do not change it. Only findings with `scope == "in-diff"` (or default) drive verdict escalation — `pre-existing` and `future-work` findings are surfaced for transparency but do not contribute to `correctness_severity`, `design_debt_severity`, or the `block`/`needs-attention`/`refactor-recommended` rules. All three scopes count toward the hard cap on findings.
- **`correctness_severity`** is an optional top-level enum (`critical | high | medium | low | none`). Derived as the max severity among findings with `finding_type == "correctness"` (including findings where `finding_type` is absent and defaults to correctness). Omit the field entirely when no correctness findings exist, or emit `"none"` — both are valid. Consumers should treat absence as `"none"`.
- **`design_debt_severity`** is an optional top-level enum with the same values. Derived as the max severity among findings with `finding_type == "design_debt"`. Same emit-or-omit rule. `architectural_smell` and `best_practice_violation` findings do not contribute to either axis — they have their own `findings[].severity` but do not roll up today.
- **`findings[].lift_considered`** is optional. Populate it when the recommendation is a runtime guard (per the Lift hierarchy rule in `methodology.md`). Each of `type_lift`, `writer_lift`, `ordering_lift` carries `{ viable: boolean, rationale: string }` where `rationale` is a one-sentence explanation of the constraint that either blocks or enables that lift. For a guard recommendation to be justified, either (a) **all three** of `type_lift`, `writer_lift`, `ordering_lift` must be `viable: false` with a specific constraint named per lift, OR (b) the finding body must name a **system boundary** (user input, external API, untrusted data, trust boundary where the producer cannot be changed) as the reason a lift is not the right primitive. If any of the three lifts is `viable: true` and no system boundary is named in the body, the recommendation should be that viable lift, not a guard — emitting a guard recommendation under these conditions is a schema-methodology inconsistency that downstream consumers are entitled to reject. If the recommendation is not a guard (e.g., recommending a lift directly, recommending a test, recommending removing code), the field may be omitted.
- **`considered_not_promoted[].design_alternative_considered`** is optional — a one-sentence description of the lift or structural change that would resolve the observation if it ever escalated to a bug. Use it when you see a latent issue that is not a bug today but has an obvious structural fix; leaves a breadcrumb for the next reviewer.
- **`considered_not_promoted[].tracked_as_debt`** is optional boolean. Set to `true` when the observation represents design debt worth tracking even though it doesn't rise to a finding. No consumer required today; metadata for future tooling.
- **Verdict consistency** (schema v1.10 — four rules, strict precedence, all filtered on `scope == "in-diff"` with the default-to-in-diff rule applied to pre-v1.10 payloads):
  - **`block`** — at least one finding with `finding_type == "correctness"` (or absent, treated as correctness) AND `scope == "in-diff"` (or absent, treated as in-diff) AND severity `critical` or `high`, AND `ship_blocker_answer == "yes"`. Pre-v1.10 payloads flow through identically because both defaults preserve the filter.
  - **`needs-attention`** — at least one `in-diff` finding of material severity, `block` does not apply, AND `ship_blocker_answer == "no"`. Reviewer judges the issues are real but fixable in place.
  - **`refactor-recommended`** — `block` does not apply AND `design_debt_severity` (computed from `in-diff` findings only) is `high` or `critical`, AND either (a) a patch-chain signal fires (v1.10.0 plugin feature) OR (b) `in-diff design_debt` findings outnumber `in-diff correctness` findings in this review. `ship_blocker_answer == "no"` — by definition not a correctness ship-blocker.
  - **`approve`** — zero findings, or all findings are `pre-existing`/`future-work`, or the above three rules do not apply. A review with only pre-existing/future-work findings lands here because the diff itself is safe; unrelated issues are transparently surfaced for author triage.
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
  "schema_version": "1.10",
  "verdict": null,
  "error": "<error code: not_a_repo | gh_missing | empty_diff | shallow_clone_no_base | other>",
  "message": "<human-readable explanation>"
}
```

Do not fabricate a review. Do not return an `approve` verdict to paper over a tool failure.
