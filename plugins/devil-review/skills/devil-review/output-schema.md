# Output Schema

Return your review in **two parts**: a human-readable markdown section, followed by a machine-readable JSON fence. Both sections must be present on every non-error run. Downstream tools consume the JSON; the markdown is for the reviewer reading the result.

---

## Part 1 — Markdown section

```
# Devil Review

Target: <"working tree diff" | "branch diff against <ref>" | "PR #<n>">
Scope: <N files, M lines changed>  [or: "split review (N files across G groups)"]
Focus: <user's focus text, if provided>
Verdict: <block | needs-attention | approve>

<1-2 sentence ship/no-ship assessment — terse, not neutral>

## Trace Log

Ship-blocker question: <yes | no>
Reasoning: <one sentence — why yes or why no>

Domain classification:
- Loaded: <comma-separated list of domains, or "none (generic attack surface only)">
- Considered but dropped: <comma-separated list with one-word reason, or "none">
- Notes: <one sentence on any ambiguous classification calls>

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

## Findings

### [severity] Title
- **File**: `path/to/file`
- **Lines**: L<start>-L<end>
- **Confidence**: <0.0 to 1.0>

<body — what can go wrong, why this code path is vulnerable, likely impact>

**Recommendation**: <concrete change to reduce risk>

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

```json
{
  "schema_version": "1.5",
  "verdict": "block | needs-attention | approve",
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
        "reason": "out-of-scope | low-confidence | covered-by-finding-<N> | spec-accepted | test-covers-invariant"
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
    ]
  },
  "findings": [
    {
      "severity": "critical | high | medium | low",
      "title": "<short finding title>",
      "file": "<path/to/file>",
      "lines": "L<start>-L<end>",
      "confidence": 0.0,
      "what_can_go_wrong": "...",
      "why_vulnerable": "...",
      "impact": "...",
      "recommendation": "...",
      "test_coverage": {
        "covered_by": "<path/to/test:line or null>",
        "why_missed": "<code>: <one-sentence explanation>"
      }
    }
  ]
}
```

### JSON rules

- **`verdict`** is an enum: exactly one of `block`, `needs-attention`, `approve`. No other values.
- **`trace_log.ship_blocker_answer`** is required when `verdict` is `block` or `needs-attention`. Value is `"yes"` or `"no"`. May be omitted when `verdict` is `approve`.
- **`trace_log.ship_blocker_reasoning`** is required alongside `ship_blocker_answer`. One sentence.
- **`trace_log.domains_loaded`** is required on every non-error run. Empty array `[]` is valid only if no domain matched — in that case, add a scenario noting "generic attack surface only".
- **`trace_log.domains_considered_dropped`** is required on every non-error run. Empty array `[]` is valid if no candidate domain was dropped. Every dropped entry needs `{domain, reason}` where reason is one of `not-matched`, `overlap`, `not-applicable`.
- **`trace_log.classification_notes`** is **unconditionally required** on every non-error run. A single non-empty sentence explaining how classification was decided — even trivial cases ("all files under `src/components/*.vue` — straightforward ui.md load" is fine). `null` and empty strings are invalid. The field forces deliberate thought about routing; it is not an optional "notes" slot.
- **`trace_log.symbols_inspected`** cannot be empty if `findings` is non-empty. If it is, you are reporting findings without grounding — drop them or redo the trace.
- **`trace_log.considered_not_promoted`** is optional — empty array `[]` is valid and preferred over padding. Each entry requires both `observation` (one sentence) and `reason`. `reason` must be one of the literal strings `out-of-scope`, `low-confidence`, `spec-accepted`, `test-covers-invariant`, or the pattern `covered-by-finding-<N>` where `<N>` is the 1-based index of the covering finding in the `findings` array (e.g. `covered-by-finding-1` for the first finding). If the covering finding is dropped or reordered later, update the index. Do not use this field to smuggle in extra findings — if an observation deserves action, promote it to `findings` and let it earn its slot under the hard cap. Use `test-covers-invariant` when you traced a candidate bug to an existing test that actually asserts the invariant you thought was violated — record the test location in the observation for auditability.
- **`trace_log.mutated_records_inspected`** is required on every review where the diff writes to at least one record. Each entry requires `record`, `kind`, `siblings_considered` (list every sibling field on the record, even ones you concluded were safe), and optionally `note`. Empty array `[]` is valid only if the diff contains zero record writes — in that case add `no record writes in diff` as a scenario line. Skipping this field when writes exist is the same class of grounding failure as an empty `symbols_inspected`: you skipped the data-model fanout trace.
- **`findings[].test_coverage`** is required on every finding. Both `covered_by` (test file path with line, or `null`) and `why_missed` (enum: `no-test`, `mock-bypass`, `missing-assertion`, plus a one-sentence explanation) must be present. If you cannot produce a test-trace answer from one of these three categories, the finding is invalid — either re-read the tests or drop it. See the test-trace rule in `methodology.md`. This field cannot be `null` and cannot be omitted: a finding without it indicates the reviewer skipped the validation gate and the finding cannot be trusted.
- **`trace_log.acceptance_criteria_crosswalk`** is conditionally required. When the pre-review context step loads a spec with **structured acceptance criteria** (explicit "must" statements, numbered requirements, bulleted ACs, definition-of-done checklist), the crosswalk must be populated with one entry per AC — including ACs that pass. Empty array `[]` is valid only when no spec loaded OR the loaded spec has no structured ACs (prose-only narrative RFCs qualify for the empty-list exemption). In the empty-list case, `classification_notes` or a scenario line must explain why: e.g. `"no spec loaded for this diff"` or `"spec loaded but no structured ACs — crosswalk skipped"`. Each entry requires `ac` (the AC text quoted verbatim), `spec_location` (file:line or section heading), `status` (one of `implemented`, `ambiguous`, `missing`, `contradicted`), and `implementation` (file:line-range for `implemented` / `ambiguous` / `contradicted`; `null` for `missing`). `notes` is optional but recommended for non-`implemented` statuses. See the "Acceptance criteria crosswalk" section in `methodology.md`. Skipping this field when a spec with ACs is present is the same class of grounding failure as an empty `symbols_inspected` — the audit did not happen.
- **`findings` length must respect the hard cap** from `methodology.md` (3 under 500 lines, 5 under 1500, 3 per split group).
- **`confidence`** is 0.0–1.0. Use it for your own uncertainty — do not soften severity to compensate for low confidence.
- **Verdict consistency**: `block` requires at least one `critical` or `high` finding AND `ship_blocker_answer == "yes"`. `approve` requires zero findings. `needs-attention` is everything in between and requires `ship_blocker_answer == "no"` with material findings present.
- **Severity inflation guard**: if you answered the ship-blocker question `yes` but no individual finding scores critical or high by the severity definitions, your severity assignment is wrong — re-evaluate the severity of the blocking finding before inflating it to match the verdict. The block test should agree with severity naturally; if it doesn't, the finding is probably not actually ship-blocking.

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
  "schema_version": "1.5",
  "verdict": null,
  "error": "<error code: not_a_repo | gh_missing | empty_diff | shallow_clone_no_base | other>",
  "message": "<human-readable explanation>"
}
```

Do not fabricate a review. Do not return an `approve` verdict to paper over a tool failure.
