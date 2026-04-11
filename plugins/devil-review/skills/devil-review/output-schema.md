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
- `<symbol>` → consumers: <file:line>
- ...

Architectural decisions checked:
- <CLAUDE.md section, spec path, or "n/a">

Scenarios considered:
- <one-line adversarial scenario — what you mentally rendered>
- <another scenario>
- ...

Considered but not promoted:
- <observation> — reason: <out-of-scope | low-confidence | covered-by-finding-<N> | spec-accepted>
- ...

## Findings

### [severity] Title
- **File**: `path/to/file`
- **Lines**: L<start>-L<end>
- **Confidence**: <0.0 to 1.0>

<body — what can go wrong, why this code path is vulnerable, likely impact>

**Recommendation**: <concrete change to reduce risk>

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
- **Deletions count as changes.** If the diff removes a symbol, trace its former callers and list them in `symbols_inspected` with a `(deleted)` suffix on the symbol name.
- **One line per symbol, one line per scenario.** Do not prose-explain; the JSON block carries structured data for chain-consumers.
- If a domain checklist was loaded (e.g., `domains/ui.md`), list the domain under "Scenarios considered" as `domain: <name>` alongside concrete scenarios.
- **`considered_not_promoted` captures observations you noticed but decided not to report.** Use it when you see something during the trace — a smell, a secondary symptom, a speculative risk — that did not clear the finding bar. Each entry is one line with a reason from the fixed set: `out-of-scope`, `low-confidence`, `covered-by-finding-<N>` (where `<N>` is the 1-based index of the covering finding in the `findings` array — e.g. `covered-by-finding-2`), or `spec-accepted`. The field is optional: empty list `[]` is valid, and you should not pad it to look thorough. Its purpose is the opposite — it exists so the reviewer can see *what you thought about and dropped*, so those observations are not silently lost and can be promoted manually if the user disagrees with your triage. If you used it to drop an observation because it was "just a symptom", check that the underlying invariant did not also escape your main findings list — see the generalization test in `methodology.md`.

---

## Part 2 — JSON fence

Emit immediately after the markdown section, in a fenced code block tagged `json`.

**Schema version history:**
- `1.0` — initial schema: verdict, target, scope, findings, trace_log with symbols_inspected + scenarios_considered
- `1.1` — added `ship_blocker_answer`, `ship_blocker_reasoning`, `domains_loaded`, `domains_considered_dropped`, `classification_notes`. New `block` verdict value. No fields removed or retyped.
- `1.2` — added optional `trace_log.considered_not_promoted` for observations the reviewer saw but dropped from findings (with reason). No fields removed or retyped; older consumers that do not know the field can ignore it.

```json
{
  "schema_version": "1.2",
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
        "consumers": ["<path/to/caller>:<line>", "..."]
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
        "reason": "out-of-scope | low-confidence | covered-by-finding-<N> | spec-accepted"
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
      "recommendation": "..."
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
- **`trace_log.considered_not_promoted`** is optional — empty array `[]` is valid and preferred over padding. Each entry requires both `observation` (one sentence) and `reason`. `reason` must be one of the literal strings `out-of-scope`, `low-confidence`, `spec-accepted`, or the pattern `covered-by-finding-<N>` where `<N>` is the 1-based index of the covering finding in the `findings` array (e.g. `covered-by-finding-1` for the first finding). If the covering finding is dropped or reordered later, update the index. Do not use this field to smuggle in extra findings — if an observation deserves action, promote it to `findings` and let it earn its slot under the hard cap.
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
  "schema_version": "1.2",
  "verdict": null,
  "error": "<error code: not_a_repo | gh_missing | empty_diff | shallow_clone_no_base | other>",
  "message": "<human-readable explanation>"
}
```

Do not fabricate a review. Do not return an `approve` verdict to paper over a tool failure.
