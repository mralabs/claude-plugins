# Rejection memory (schema v1.14+)

User rejection memory lets the reviewer avoid silently re-raising findings the user has already dismissed. Rejections are recorded via the `--reject <CSV>` flag (SKILL.md Step 1), persisted to `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json`, and consulted on every subsequent run within the session. Rationale, calibration notes, and the authoritative chain-of-rejections override rule live in `output-schema.md` §User rejection memory (emit-time rules); this file is the Phase A execution spec.

**Run timing — two phases.** Only Phase A lives in this file:

- **Phase A — Record & load (substeps 1–3, below)** runs during SKILL.md Step 3b, right after diff collection. It records any `--reject` entries and loads the rejection file into `trace_log.rejections_loaded`.
- **Phase B — Match & emit (substeps 4–6)** runs much later — after the Claim verification pass, before emit — and is therefore specified in `output-schema.md` §User rejection memory → Phase B execution spec, which loads at Step 7. It cannot run earlier: there are no candidate findings to match at Step 3b time.
- **Substep 7 (observability, below)** applies to every non-error run regardless of phase outcomes.

---

## Phase A — Record & load (runs at SKILL.md Step 3b)

### Substep 1 — Hash normalization (authoritative)

The rejection identity is a sha256 hash over a normalized `file:title` pair. All other substeps (recording via `--reject`, loading from `rejections.json`, matching candidate findings) use this same normalization:

1. Trim leading and trailing whitespace from each of `file` and `title`.
2. Lowercase `file`. Do NOT lowercase `title` — proper nouns, acronyms, and identifier casing are signal.
3. Collapse internal whitespace in `title` to a single space (so "re-flow   text" and "re-flow text" hash to the same value).
4. Join with `:` as separator — `<normalized_file>:<normalized_title>`.
5. Compute sha256 of the joined UTF-8 bytes. Emit as a 64-character lowercase hex string.

Use `sha256sum` if available, else `shasum -a 256`. This normalization is intentionally conservative — small cosmetic edits to the title (whitespace, case-preserving rewrites) produce the same hash, but substantive changes (different file, different substantive title words) produce a different hash. A minor rewording of the same finding resolves to the same rejection; a genuinely different finding at the same location does not.

**Line ranges are deliberately excluded from the hash** (plugin v1.20.0 correction — the original normalization was `file:lines:title`). Between review rounds the diff itself evolves: fixes above a finding's location shift its line numbers, so a line-bearing hash re-fired the exact finding the rejection was meant to suppress — the round-N+1 scenario the feature exists for. `lines` is still recorded in each rejection entry for audit, but never participates in identity. Accepted tradeoff: a genuinely different finding at the same file with an identical title now matches the rejection — the title is the substantive discriminator, and two findings that cannot be told apart by file + title are close enough that suppress-vs-re-raise judgment (Phase B substep 5, in `output-schema.md`) is the right arbiter.

### Substep 2 — Apply `--reject` flag (when present)

When Step 1 parsed a non-empty `--reject <CSV>`:

1. Resolve the target slug (SKILL.md Step 8 rules) for the current review target. Locate the prior snapshot at `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md`.
2. If no prior snapshot exists, emit the error output per `output-schema.md` with error code `reject_without_prior` and a message naming the expected path. Do not continue to the review.
3. Parse the prior snapshot's JSON fence. For each index `N` in the CSV list:
   - If `N` is not a positive integer, or `N > length(findings)`, or `findings[N-1]` is missing — emit the error output with code `reject_index_out_of_range`, name the offending index and the length of the prior `findings` array, and stop. Do not record partial rejections if the CSV has any invalid entry.
   - Extract `file`, `lines`, `title` from `findings[N-1]`.
   - Compute the sha256 hash per substep 1 (over `file` and `title`; `lines` is recorded but not hashed).
4. Read (or initialize) the rejection file:
   - If `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` does not exist, initialize it with `{"schema_version": "1.1", "rejections": []}`.
   - If it exists but fails to parse as JSON, lacks `schema_version`, has a `schema_version` value other than `"1.0"` or `"1.1"`, or lacks a `rejections` array, emit the error output with code `rejections_file_malformed` and a message naming the path. Do not attempt to repair the file.
5. For each `(hash, file, lines, title)` from step 3, append a rejection entry `{hash, file, lines, title, rejected_at: <ISO-8601 UTC>, rationale: null}` — or **overwrite in place** when an entry with the same `hash` already exists (preserve the newer `rejected_at`, keep `rationale: null` since inline flag carries no rationale).
6. Write the updated JSON back with two-space indentation, setting the top-level `schema_version` to `"1.1"` (upgrading a `"1.0"` file in place is correct — hashes are recomputed at load time per substep 3, so no entry rewrite is needed).
7. Add a `scenarios_considered` line `rejections recorded: <N1>, <N2>, ...` naming the applied indices so the action is visible in the subsequent review output.

When `--reject` was NOT passed, substep 2 is a no-op.

### Substep 3 — Load the rejection file

1. Use `Read` on `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json`.
   - If the file does not exist → omit `trace_log.rejections_loaded` entirely (schema v2.0) and set `rejections=absent` in the `context:` observability line. This is the canonical fresh-session state.
   - If the file exists but fails to parse as JSON, lacks the `schema_version` field, has a `schema_version` value other than `"1.0"` or `"1.1"`, or lacks a `rejections` array, treat as malformed: emit `trace_log.rejections_loaded: []` and set `rejections=rejected-malformed-json` in the `context:` line so the rejected load is visible. Do not attempt suppression against a malformed file — findings flow through as if no rejection memory existed. (This path cannot fire when substep 2 ran successfully — substep 2's error handling rejects a malformed file before reaching the load step.)
   - If the file parses and has `rejections: [...]` → **recompute** each entry's hash from its stored `file` and `title` per substep 1, then populate `trace_log.rejections_loaded` with one `{hash, rejected_at}` entry per rejection, using the recomputed hash. The stored `hash` field is audit metadata, not the matching key — recomputation is what lets `"1.0"`-era sidecar entries (hashes recorded under the old line-bearing normalization) keep matching under the current rule. Empty array is valid when the file is present but `rejections: []`.

---

## Substep 7 — Observability requirement (every non-error run)

The load outcome must always be visible in the `rejections=` slot of the single `context: prior=<...> rejections=<...> rules=<...>` observability line (SKILL.md Step 3b, schema v2.0), where the value is exactly one of `loaded` (file exists and parsed), `absent` (file does not exist — fresh session for this path), or `rejected-malformed-json`.
