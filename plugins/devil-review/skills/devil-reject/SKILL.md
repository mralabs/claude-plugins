---
name: devil-reject
description: "Record a rejection of a devil-review finding — suppresses that finding on subsequent runs in the same session unless new evidence surfaces"
argument-hint: "<finding-index> [rationale]"
disable-model-invocation: true
allowed-tools: ["Read", "Write", "Glob", "Bash(date:*)", "Bash(sha256sum:*)", "Bash(shasum:*)"]
---

You are recording a user rejection of a devil-review finding. A rejected finding is one the user has decided is not actionable — it does not describe a real bug in their system, or the bug does not matter for their use case. On subsequent `/devil-review` runs in the same Claude Code session, a finding whose hash matches a rejection entry is either suppressed silently (default) or re-raised with a `previously_rejected` annotation that forces the reviewer to state what new evidence justifies re-raising.

Raw slash-command arguments: `$ARGUMENTS`

---

## Step 1 — Parse arguments

Parse `$ARGUMENTS` as: `<finding-index> [rationale...]`

- `<finding-index>` is a 1-based integer matching the position of the finding in the most recent `/devil-review` run's `findings` array. Example: `/devil-reject 2` rejects the second finding of the most recent review.
- `[rationale...]` is everything after the index — optional free-form text (max one sentence, ~200 characters). Captures the user's reason for rejecting.

If `$ARGUMENTS` is empty or the first token does not parse as a positive integer, emit:

```
# Devil Reject

Error: finding index is required. Usage: /devil-reject <N> [rationale]
```

And stop. Do not write anything to disk.

## Step 2 — Locate the most recent review snapshot

`${CLAUDE_SESSION_ID}` is substituted by the runtime. The session's review snapshots live at `.claude/devil-review/${CLAUDE_SESSION_ID}/*.md`.

Use `Glob` to find all `.md` files under that directory. If zero files exist, emit:

```
# Devil Reject

Error: no review snapshot found in this session at .claude/devil-review/${CLAUDE_SESSION_ID}/. Run `/devil-review` before rejecting findings.
```

And stop.

If multiple files exist (different targets in the same session), pick the **most recently modified** file by `mtime`. This is the "last review the user saw" — rejection is always against the most recent review for the current target cycle. If the user wants to reject against a specific target, they must run `/devil-review` on that target first, then `/devil-reject`.

## Step 3 — Extract the finding

Read the selected snapshot file. The file is the verbatim output of a prior `/devil-review` run — markdown section followed by a JSON fence.

Parse the JSON fence. Locate `findings[<N-1>]` where `N` is the 1-based finding index from Step 1. If the index is out of range (N > length of findings, or N < 1), emit:

```
# Devil Reject

Error: finding index <N> out of range. The most recent review (<target-slug>) has <length> findings (valid indices 1..<length>).
```

And stop.

If the review had zero findings (`findings: []`), emit:

```
# Devil Reject

Error: the most recent review (<target-slug>) emitted zero findings — nothing to reject.
```

And stop.

Extract from `findings[<N-1>]`:
- `file`
- `lines` (string, format `L<start>-L<end>`)
- `title`

## Step 4 — Compute the rejection hash

The rejection hash is a sha256 over a normalized `file:lines:title` string. Normalization rules:

1. Trim leading and trailing whitespace from each of `file`, `lines`, `title`.
2. Lowercase `file` and `lines`. Do NOT lowercase `title` — proper nouns, acronyms, and identifier casing are signal.
3. Collapse internal whitespace in `title` to a single space (so "re-flow   text" and "re-flow text" hash to the same value).
4. Join with `:` as separator — `<normalized_file>:<normalized_lines>:<normalized_title>`.
5. Compute sha256 of the joined UTF-8 bytes. Emit as a 64-character lowercase hex string.

Use `sha256sum` if available, else `shasum -a 256`. Emit a clear error if neither is available.

This normalization is intentionally conservative — small cosmetic edits to the title (whitespace, case-preserving rewrites) produce the same hash, but substantive changes (different line range, different file, different substantive title words) produce a different hash. This is the right behavior: a minor rewording of the same finding should resolve to the same rejection; a genuinely different finding at the same location should not.

## Step 5 — Append the rejection entry

The rejection file lives at `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json`.

If the file does not exist, initialize it with:

```json
{
  "schema_version": "1.0",
  "rejections": []
}
```

If it exists, read it. If it fails to parse as JSON or lacks the `schema_version` field, emit an error and stop — do not silently overwrite a malformed file. Tell the user the file path so they can inspect and repair manually.

Construct the new entry:

```json
{
  "hash": "<sha256 from Step 4>",
  "file": "<original file path from Step 3, preserving case>",
  "lines": "<original lines string from Step 3>",
  "title": "<original title from Step 3>",
  "rejected_at": "<ISO-8601 timestamp — use `date -u +%Y-%m-%dT%H:%M:%SZ`>",
  "rationale": "<trimmed rationale from Step 1, or null when no rationale was provided>"
}
```

Append the entry to the `rejections` array. If an entry with the same `hash` already exists, **overwrite it in place** (keep `rejected_at` updated to the latest rejection, keep the latest rationale). Do not duplicate.

Write the updated JSON back to the file with two-space indentation.

## Step 6 — Emit confirmation

Emit a short confirmation to the user:

```
# Devil Reject

Recorded rejection for finding #<N> from <target-slug>:
- File: <file>
- Lines: <lines>
- Title: <title>
- Hash: <first 12 chars of sha256>...
- Rationale: <rationale or "(none provided)">

Future `/devil-review` runs in this session will suppress this finding unless new evidence surfaces. Rejection file: `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` (<rejections.length> total rejection(s) in this session).
```

No JSON fence — this skill is UX-only, not a data-emitter. `/devil-review` is the skill that reads `rejections.json` and acts on it; `/devil-reject` only records.

## Design notes

- **Session scoping**: rejections are session-scoped by `${CLAUDE_SESSION_ID}`, same discipline as review snapshots. A new Claude Code session starts fresh. Rationale: stale rejections from weeks ago should not mask findings that are now valid because surrounding code changed. If long-term rejection memory is needed, that is a future feature (see Item 10 plan doc).
- **Target-agnostic within a session**: rejections are keyed by `hash`, not by target. A rejection recorded after reviewing the working tree also applies when the same hash surfaces in a later branch-mode or PR-mode review within the session. This is intentional: the hash is the identity, not the review mode.
- **Overwrite-in-place for repeated rejections**: if the user rejects the same finding twice (same hash), the second rejection overwrites the first. Do not treat repeated rejections as separate events — they are the same decision restated.
- **No un-reject mechanism today**: if the user wants to reverse a rejection, they can edit `rejections.json` directly. The skill does not provide `/devil-unreject`. Rationale: un-rejection is rare, manual edit is visible and auditable, adding a new slash command for it would pressure the plugin's UX surface without a clear use case.
