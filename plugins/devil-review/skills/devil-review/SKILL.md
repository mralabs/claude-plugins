---
name: devil-review
description: "The devil is in the details — adversarial review that finds what's hiding in your diff"
argument-hint: "[--scope auto|working-tree|branch|pr] [--base <ref>] [--pr <number>] [focus text]"
disable-model-invocation: true
allowed-tools: ["Read", "Write", "Glob", "Grep", "Bash(git:*)", "Bash(gh:*)"]
context: fork
---

You are performing an adversarial code review. Your job is to break confidence in the change, not to validate it. Do not fix issues. Review only.

Raw slash-command arguments: `$ARGUMENTS`

This file is the **orchestrator**. It parses arguments, collects the diff, and points you at the files that define the methodology and output format. Do not attempt to review the diff until you have loaded those files.

---

## Step 1 — Parse arguments

Parse the raw arguments:
- `--scope <auto|working-tree|branch|pr>` — review target scope (default: `auto`)
- `--base <ref>` — explicit base ref for branch diff
- `--pr <number>` — GitHub PR number to review (implies `--scope pr`)
- `--reject <CSV>` — record rejections of findings from the most recent prior snapshot before running this review. `<CSV>` is a comma-separated list of 1-based finding indices (e.g. `--reject 2,5,7`). Rejections are persisted to `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` and consulted on subsequent runs per Step 3b's Rejection memory load substep.
- Everything else after flags → `FOCUS_TEXT`

**No `--prior` flag.** Prior-review auto-detection is handled inside Step 3b — the skill always looks for a snapshot at `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md` (session-scoped, target-scoped — see Step 8 for slug rules) and uses it for patch-chain detection when present. Absent prior files produce a fresh review. Users do not control this via a flag; the behavior is zero-config. To force a fresh review on a target that already has a snapshot, delete the corresponding file.

**`--reject` semantics.** The flag both *records* rejections and *runs* a new review — single code path. Rejections are applied at the start of Step 3b (before candidate-finding generation), so the new review sees the freshly-added rejections and suppresses or re-raises candidates matching them per the Rejection memory load rule. If `--reject` is passed but no prior snapshot exists for the resolved target (fresh first run), emit the error output with code `reject_without_prior` and a message pointing at the missing snapshot path. Rationale for rejections recorded via this flag is `null` — users who want rationales attached must edit `rejections.json` directly after recording.

---

## Step 2 — Resolve review target

1. **Sanity check**: run `git rev-parse --is-inside-work-tree`. If it fails, emit the error output per `output-schema.md` with error code `not_a_repo` and stop.
2. If `--pr <number>` is given or `--scope pr` → **PR mode**
3. If `--base <ref>` is given → **branch mode** against that ref
4. If `--scope working-tree` → **working-tree mode**
5. If `--scope branch` → **branch mode**, detect default branch:
   - Try `git symbolic-ref refs/remotes/origin/HEAD`
   - Fall back to checking `main`, `master`, `trunk` (local then remote)
6. If `--scope auto` (default):
   - Run `git status --short`, `git diff --shortstat`, `git diff --cached --shortstat`
   - If working tree is dirty (staged, unstaged, or untracked) → **working-tree mode**
   - If clean → **branch mode** against detected default branch

---

## Step 3 — Collect review context

### PR mode

Requires `gh` CLI. Run `gh --version` first. If it fails, emit the error output with error code `gh_missing` and stop. Do not fall back silently.

Collect the PR metadata, diff, and **both comment streams** — inline review comments and PR discussion comments — because GitHub models a PR as both a pull and an issue:

```
gh pr view <number> --json title,body,baseRefName,headRefName,additions,deletions,commits,files
gh pr diff <number>
gh api repos/{owner}/{repo}/pulls/<number>/comments --jq '.[].body'
gh api repos/{owner}/{repo}/issues/<number>/comments --jq '.[].body'
```

The `{owner}` / `{repo}` placeholders in `gh api` are expanded automatically by `gh` when run inside a cloned repository with a GitHub remote. If the current directory is not such a repository, fall through to explicit resolution via `gh repo view --json nameWithOwner`.

Assemble:
```
## PR Info
Title: <title>
Base: <baseRefName> ← <headRefName>
Additions/Deletions: +<additions> -<deletions>
Description: <body, first 500 chars>

## Changed Files
<files list>

## PR Diff
<full diff>

## Existing Review Comments (inline)
<inline comments from /pulls/N/comments, if any>

## Existing PR Discussion (issue comments)
<discussion comments from /issues/N/comments, if any>
```

Skip either comments section if empty. The point of collecting both is to avoid duplicating findings already raised by humans — whether inline or in the discussion thread.

### Working-tree mode

```
git status --short
git diff --cached --no-ext-diff --submodule=diff
git diff --no-ext-diff --submodule=diff
git ls-files --others --exclude-standard
git log --oneline -10
```

For each untracked file: skip binary, skip >24KB, otherwise read and include content.

### Branch mode

```
git merge-base HEAD <base-ref>
git log --oneline --decorate <merge-base>..HEAD
git diff --stat <merge-base>..HEAD
git diff --no-ext-diff --submodule=diff <merge-base>..HEAD
```

If `git merge-base` fails (common in shallow clones / CI), emit the error output with error code `shallow_clone_no_base` and instruct: "Run `git fetch --unshallow` or use `--scope working-tree` / explicit `--base <ref>`."

### Empty diff handling

If the resolved diff is empty (no staged, unstaged, untracked, or branch-divergent changes), emit the error output with error code `empty_diff` and verdict `null`. Do NOT return `approve` — an empty review is not an approval.

---

## Step 3b — Patch-chain scan

After collecting the diff but before the large-diff guard, scan recent commit history for patterns that indicate iterative patching on the same surface. Multi-round defensive commits on the same file set are a signal that candidate findings in this review may be artifacts of prior rounds' guards rather than organic defects — and the correct next step is then a structural refactor, not round N+1 of guard-chasing. The rule and severity implications live in the "Patch-chain detection" section of `methodology.md`; this step is the data-collection side.

### Collect the commit history

Run:

```
git log -<N> --oneline -- <changed-files>
```

Where `<N>` is `5` for working-tree and branch modes, `10` for PR mode (PRs accumulate more commits than typical local changes). `<changed-files>` is the set of files already identified in Step 3's diff.

### Signals — at least one must fire to populate `patch_chain_risk`

1. **Fix-prefix cluster.** Among the last 4 commits that touch any reviewed file, ≥50% (i.e., ≥2 of 4) have messages prefixed with any of: `fix:`, `guard:`, `prevent:`, `patch:`, `workaround:`, `hotfix:` (case-insensitive; conventional-commits scope suffix like `fix(auth):` still counts). The cluster is "same surface, repeatedly defensive".
2. **Same-file hotspot.** A single reviewed file appears in ≥3 of the last 5 commits (working-tree / branch mode) or ≥5 of the last 10 commits (PR mode). File frequency alone is not enough without a defensive-prefix cluster, but combined with signal 1 it strengthens the signal — record both when both fire.
3. **Prior-review overlap** (auto-detected — no flag required). Compute the **target slug** for the current review (see Step 8 for the slug rules) and resolve the prior-review path to `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md`. Session and target scoping ensure that stale reviews from unrelated sessions or different targets never bleed in. If the file exists, load it; extract its findings array and `considered_not_promoted` array via its JSON fence (treat the load as absent if no `schema_version` field is present, the file is malformed, or the file does not exist — emit the corresponding status per the observability rule below). If ≥50% of the current review's candidate findings reference file locations that also appeared in the prior review's findings or `considered_not_promoted`, the signal fires. Also cross-reference each current finding's `file:line` against the prior review's entries and annotate any overlaps in the finding body: "This location also appeared in the prior review as finding #N" — this annotation is body-only, not a new schema field.

**Observability requirement.** The skill **must always** emit a `scenarios_considered` line of the form `prior-review ingestion: <status>` on every non-error run, where `<status>` is exactly one of `loaded`, `absent` (file does not exist — fresh run), `rejected-no-schema-version`, or `rejected-malformed-json`. This line makes the auto-detect outcome visible; silent drops are not permitted, and neither is silently running without a prior-check signal.

### Prior-relation classification (v1.11+)

When Step 3b's `<status>` is `loaded`, the loaded prior review's findings must also be used for per-finding attribution and summary-level roll-up — see the "Prior-relation classification" and "Decision derivation" subsections in `methodology.md`. Specifically:

1. **Per-finding classification.** On every current finding, emit `findings[].prior_relation` with `category` in `{carries-over, new-drift-from-fix, pre-existing-orthogonal}` (three values per v1.15.1 — `resolved` is not a finding-level value) and optional `prior_finding_ref` (prior finding title quoted verbatim, or `null` when no specific prior finding is referenced). See methodology.md for the three-category decision tree.
2. **Summary roll-up.** Populate `trace_log.prior_review_summary` with per-category counts derived from (a) current findings' `prior_relation` categories and (b) reviewer's judgment about which prior findings are now resolved (not in current findings). Fields: `total_in_prior`, `resolved`, `still_open`, `new_drift_introduced`, `pre_existing_unrelated`.
3. **Severity dampening.** For every finding with `prior_relation.category == "carries-over"`, apply the severity dampening rule from methodology.md "Severity dampening for carries-over findings" — hold severity at prior level when the invariant is still violated, or reclassify to `pre-existing-orthogonal` with a one-notch severity drop if the prior fix was unrelated.

When Step 3b's `<status>` is `absent` or any `rejected-*` value, omit `prior_relation` on all findings and omit `trace_log.prior_review_summary` entirely. Both fields are meaningless without a loaded prior.

### Rejection memory load (v1.14+)

Check for a rejection memory file at `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json`. When the user passes `--reject <CSV>` (see Step 1), record the new rejections into this file *before* the load step so the current run sees its own new entries. Rejections persist across runs within a session and let the reviewer avoid silently re-raising findings the user has already dismissed.

#### Substep 1 — Hash normalization (authoritative)

The rejection identity is a sha256 hash over a normalized `file:lines:title` triple. All other substeps (recording via `--reject`, loading from `rejections.json`, matching candidate findings) use this same normalization:

1. Trim leading and trailing whitespace from each of `file`, `lines`, `title`.
2. Lowercase `file` and `lines`. Do NOT lowercase `title` — proper nouns, acronyms, and identifier casing are signal.
3. Collapse internal whitespace in `title` to a single space (so "re-flow   text" and "re-flow text" hash to the same value).
4. Join with `:` as separator — `<normalized_file>:<normalized_lines>:<normalized_title>`.
5. Compute sha256 of the joined UTF-8 bytes. Emit as a 64-character lowercase hex string.

Use `sha256sum` if available, else `shasum -a 256`. This normalization is intentionally conservative — small cosmetic edits to the title (whitespace, case-preserving rewrites) produce the same hash, but substantive changes (different line range, different file, different substantive title words) produce a different hash. A minor rewording of the same finding resolves to the same rejection; a genuinely different finding at the same location does not.

#### Substep 2 — Apply `--reject` flag (when present)

When Step 1 parsed a non-empty `--reject <CSV>`:

1. Resolve the target slug (Step 8 rules) for the current review target. Locate the prior snapshot at `.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md`.
2. If no prior snapshot exists, emit the error output per `output-schema.md` with error code `reject_without_prior` and a message naming the expected path. Do not continue to the review.
3. Parse the prior snapshot's JSON fence. For each index `N` in the CSV list:
   - If `N` is not a positive integer, or `N > length(findings)`, or `findings[N-1]` is missing — emit the error output with code `reject_index_out_of_range`, name the offending index and the length of the prior `findings` array, and stop. Do not record partial rejections if the CSV has any invalid entry.
   - Extract `file`, `lines`, `title` from `findings[N-1]`.
   - Compute the sha256 hash per substep 1.
4. Read (or initialize) the rejection file:
   - If `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json` does not exist, initialize it with `{"schema_version": "1.0", "rejections": []}`.
   - If it exists but fails to parse as JSON, lacks `schema_version`, or lacks a `rejections` array, emit the error output with code `rejections_file_malformed` and a message naming the path. Do not attempt to repair the file.
5. For each `(hash, file, lines, title)` from step 3, append a rejection entry `{hash, file, lines, title, rejected_at: <ISO-8601 UTC>, rationale: null}` — or **overwrite in place** when an entry with the same `hash` already exists (preserve the newer `rejected_at`, keep `rationale: null` since inline flag carries no rationale).
6. Write the updated JSON back with two-space indentation.
7. Add a `scenarios_considered` line `rejections recorded: <N1>, <N2>, ...` naming the applied indices so the action is visible in the subsequent review output.

When `--reject` was NOT passed, substep 2 is a no-op.

#### Substep 3 — Load the rejection file

1. Use `Read` on `.claude/devil-review/${CLAUDE_SESSION_ID}/rejections.json`.
   - If the file does not exist → emit `trace_log.rejections_loaded: []` (empty array). This is the canonical fresh-session state.
   - If the file exists but fails to parse as JSON, lacks the `schema_version` field, or lacks a `rejections` array, treat as malformed: emit `trace_log.rejections_loaded: []` and add a `scenarios_considered` line `rejection memory: rejected-malformed-json` so the rejected load is visible. Do not attempt suppression against a malformed file — findings flow through as if no rejection memory existed. (This path cannot fire when substep 2 ran successfully — substep 2's error handling rejects a malformed file before reaching the load step.)
   - If the file parses and has `rejections: [...]` → populate `trace_log.rejections_loaded` with one `{hash, rejected_at}` entry per rejection in the file. Empty array is valid when the file is present but `rejections: []`.

#### Substep 4 — Per-candidate-finding suppression check

For each candidate finding produced by the review (after Claim verification, before emit), compute the normalized sha256 hash per substep 1 over the candidate's `file`, `lines`, `title`. Compare against the loaded rejection hashes.

#### Substep 5 — Suppression vs. re-raise

When a candidate finding's hash matches a rejection entry, the reviewer must decide between two paths — **this is a reviewer-gated judgment, not an automatic rule**:

- **Suppress silently (default).** When the current analysis produces no materially new evidence for the finding, drop it from `findings` without emitting `previously_rejected`. Do NOT log the suppressed finding in `findings_dropped_in_verification` (that field is for Claim-verification drops, not user-rejection drops). Instead, add a `scenarios_considered` line: `rejection suppressed: <hash first 12 chars> — <file>:<lines>`. This is the visibility signal that a rejection fired.
- **Re-raise with annotation (exceptional).** When the current analysis has produced **new evidence** the prior rejection did not consider — a new call path, a new config, a new sibling field that changes the picture, a new data-flow the reviewer just traced — the finding is re-raised. Populate `findings[].previously_rejected` on the re-raised finding with `{rejected_at, prior_rationale, new_evidence}` where `new_evidence` is a one-sentence description of **what is concretely different this round**. The finding body must lead with "Previously rejected on `<rejected_at>` with rationale `<prior_rationale or "(none provided)">`. New evidence: `<new_evidence>`." followed by the usual finding content. Severity and confidence are carried from the current analysis, NOT from the prior rejection — the rejection did not set severity, and the reviewer's current read of severity may be higher or lower than any prior assessment.

If the reviewer cannot articulate concrete new evidence in one sentence, the path is **suppress silently**. Padding with "additional analysis revealed" does not clear the re-raise bar. This is the calibration signal: re-raise requires a nameable difference.

#### Substep 6 — Chain-of-rejections verdict override

Count the number of findings emitted with `previously_rejected` populated on the current run (i.e., the re-raised rejections). Call this the *resurface count*. When the resurface count is **≥ 2**, the reviewer is persistently surfacing user-dismissed findings; this is an automation signal to stop iterating, not to raise severity. Override verdict derivation as follows:

- Set `verdict: approve` and `decision.action: ship` regardless of what the standard rules would produce.
- Set `decision.rationale` to `"chain-of-rejections pattern — <resurface count> previously-rejected findings re-raised; stop iterating, ship as-is"` or equivalent.
- The re-raised findings still emit in `findings` for transparency — the override is on verdict/action, not on the findings list.
- This override fires **before** rules 1-4 in the standard verdict precedence. See the "Chain-of-rejections override" clause in `methodology.md`'s Verdict derivation section.

The threshold `≥ 2` is an uncalibrated starting value per the "threshold rationale" pattern used elsewhere. Real usage may surface the need to revise it in a v1.19.x patch; the rule is the discipline, the number is the starting guess.

#### Substep 7 — Observability requirement

The skill must always emit a `scenarios_considered` line of the form `rejection memory: <status>` on every non-error run, where `<status>` is exactly one of `loaded` (file exists and parsed), `absent` (file does not exist — fresh session for this path), or `rejected-malformed-json`. Parallels the prior-review ingestion status line.

### Theme-vs-root guard (reviewer-gated)

Before emitting `patch_chain_risk.detected: true`, answer one sanity-check sentence: *"do the prior defensive commits address the same underlying root cause, or different root causes on the same file set?"*

- **Same root** → the patch chain is real. The same invariant has been violated repeatedly; each round has added a guard on top. Emit the signal, and it satisfies clause (a) of verdict derivation rule 3 (`refactor-recommended`) in `methodology.md` — prefer refactor over further guard iteration even if individual current findings are only medium severity.
- **Different roots** → a legitimate hotfix-heavy file (e.g., a known-flaky integration test harness that genuinely receives independent hotfixes) has tripped the frequency/prefix signals without the underlying patch-chain dynamic. Do **not** emit `detected: true`; set `detected: false` with a note in `theme_assessment` explaining why. This guard exists because the deterministic signals alone over-fire on legitimate hotspots, and `refactor-recommended` is wrong for a file where every fix addresses a different invariant.

Record the theme-vs-root assessment in `patch_chain_risk.theme_assessment` — this field is mandatory whenever any of signals 1–3 fired, regardless of whether `detected` ends up `true` or `false`. The purpose is auditability: downstream consumers should see that the reviewer considered the guard and chose one way or the other.

### Threshold rationale (acknowledged uncalibrated starting values)

The specific thresholds — `N` commits scanned, the 50% cluster ratio, the 4-commit window, the 3-of-5 same-file hotspot — are not derived from data. No corpus of past reviews exists to calibrate against. They are starting values chosen to be strict enough to avoid firing on typical 1–2 hotfix sequences but permissive enough to fire on a genuine 3-round iteration. The first round of real usage after shipping is the calibration signal; if the false-positive rate is visible and persistent, revise the thresholds in a v1.10.x patch bump and record the empirical basis in the revision log. Hardcoding arbitrary starting values and iterating on them is preferable to blocking the whole feature on a calibration corpus that does not exist.

---

## Step 4 — Large diff guard

Count total lines changed. **The counting method depends on the active mode** — do not use `git diff --stat` blindly; in PR mode it counts local working tree state unrelated to the PR.

- **Working-tree mode**: total = lines from `git diff --stat` + `git diff --cached --stat` + total byte count of included untracked files.
- **Branch mode**: total = lines from `git diff --stat <merge-base>..HEAD`.
- **PR mode**: total = `additions + deletions` from the `gh pr view --json additions,deletions` call already made in Step 3. If that field is unavailable, fall back to counting lines of the captured `gh pr diff` output.

Then apply the thresholds:

- **> 1500 lines**: split review. Group files by directory/module, review each group, maintain a running list of findings. In output, note: `split review (N files across G groups)`.
- **Single file > 800 lines**: focus on public API, error handling, state mutations. Mark affected findings `[partial-review]`.
- **> 5000 lines**: warn upfront: "This diff is very large. Review will focus on high-risk areas. Consider splitting the change." Prioritize error handling, state management, concurrency, auth, data persistence. Skip test files and generated files unless they are the focus.

The findings cap still applies per group (see `methodology.md`).

---

## Step 5 — Load methodology and domain checklists

**Read these files before reviewing the diff.** They are not optional. They define the review itself.

1. **`methodology.md`** (sibling file in this skill directory) — operating stance, attack surface, severity + block test, calibration rules, finding bar, grounding rules, final check. Load it now.

2. **Pre-review context** (in this order, skip if absent):
   - **CLAUDE.md** (repo root) — read the "Architectural Decisions" section or equivalent. These are intentional choices. Findings that contradict them must be marked `[spec-accepted]` or dropped.
   - **Active specs / RFCs** — look in `docs/`, `specs/`, `rfcs/`, `.claude/rfcs/`, task board files. Same rule.

2b. **Project review rules** (cite, don't drop). Pre-review context in 5.2 is used to **drop** findings that contradict intentional architectural decisions. Project review rules are the opposite direction: the project's own rule files authorize findings to cite a specific rule as the grounding, making the finding more actionable than prose advice. A finding that says "violates `.claude/rules/no-patches.md`: enforce at the writer" is materially more useful than "this is a patch on a patch".

   **Glob for project rule candidates**, load the ones that exist (skip gracefully if nothing matches):
   - `.claude/rules/*.md`
   - `code-review.md`, `CODE_REVIEW.md`, `REVIEW.md` (at repo root)
   - `docs/review-rules.md`, `docs/contributing.md`, `CONTRIBUTING.md`
   - `**/rules/*.md` at repo root or one level deep (e.g., `apps/*/rules/*.md`)

   **Load caps** — to prevent context bloat on projects with long rule corpora:
   - At most **10 files** loaded. When more candidates exist, prefer `.claude/rules/*.md` first (explicit rule files), then root-level review/contributing docs, then deeper matches.
   - At most **30 KB** total content across all loaded rule files combined. If a single file blows the budget, truncate at the end of the last complete top-level section (markdown `##` heading) before the cap.
   - Skip any file under `node_modules/`, `vendor/`, `.git/`, build output directories, or test fixtures. `domains/*.md` inside the devil-review plugin itself is **not** a project rule file — it ships with the skill.

   **Record what was loaded** in `trace_log.project_rules_loaded` as entries of `{path, bytes}`. Empty array `[]` is valid when no rule file matched. **Absence of the field is a grounding failure** — the attempt must be visible.

   **During finding generation** (Step 6), for each finding, attempt to cite applicable rule(s) from the loaded corpus. Each citation lives on the finding as an entry in `findings[].rule_refs` with three fields:
   - `source` — the path to the rule file
   - `rule` — a short identifier (heading name, numbered rule, or one-sentence paraphrase if the rule has no heading)
   - `quote` — **a verbatim 1–2 line quote from the rule file** that directly supports the finding's framing

   The verbatim-quote requirement is the anti-hallucination gate. Findings whose `rule_refs[].quote` strings do not appear **literally** in the cited file are schema-invalid — downstream consumers are entitled to reject them. If you cannot produce a verbatim quote, you cannot cite the rule; either rewrite the finding without the citation or drop the citation. Paraphrased "quotes" are the common failure mode to avoid.

   Empty `rule_refs: []` on a finding is always valid. Citation is opportunistic: a finding that does not correspond to any loaded project rule simply has no citation, not a forced one.

3. **Domain checklists** — classify the changed files and load every matching checklist. A single diff can match more than one domain (e.g., a React Native component touches both UI and mobile; an Electron renderer touches both UI and desktop; a backend handler that writes SQL touches both API and data). Load all that apply.

   | Domain | File / marker | Checklist |
   |---|---|---|
   | **Web UI / view layer** | `.vue`, `.tsx`, `.jsx`, `.svelte`, `.html`, layout CSS files (files with `display:`, `position:`, `z-index:`, `grid`, `flex`); composables, hooks, and store files whose output drives templates (`useXxx.ts`, `stores/*.ts`, `composables/*.ts`) | `domains/ui.md` |
   | **Mobile app** | iOS: `.swift`, `.m`, `.mm`, `.h`, `*.xcodeproj/`, `Info.plist`, `Podfile`, `.entitlements`. Android: `.kt`, `.kotlin`, `.java` under `android/`/`app/`, `AndroidManifest.xml`, `build.gradle`. React Native: any `.tsx`/`.jsx` in a project whose `package.json` depends on `react-native`. Flutter: `.dart`, `pubspec.yaml`, platform channels. Capacitor/Cordova: `capacitor.config.*`, `config.xml`, plugin code | `domains/mobile.md` |
   | **Desktop app** | Electron: `main.ts/.js`, `preload.ts/.js`, references to `BrowserWindow`/`ipcMain`/`ipcRenderer`/`app.on`. Tauri: anything under `src-tauri/`, `tauri.conf.json`, `#[tauri::command]`. Native: macOS Cocoa/AppKit `.swift`/`.m` outside `ios/`; Windows Win32/WinUI `.cs`/`.cpp` with MFC/WPF/WinRT; Linux Gtk/Qt sources. Packaging: `electron-builder.yml`, `forge.config.*`, `.wxs`, `.iss`, notarization scripts | `domains/desktop.md` |
   | **Backend API / server** | route handlers, controllers, middleware; request/response DTOs; schema files `openapi.*`, `.proto`, GraphQL SDL; framework signals: Express/Koa/Fastify/NestJS route files, Rails `app/controllers/`, Django `views.py`/`urls.py`, FastAPI route files, ASP.NET `*Controller.cs`, Spring `@RestController`; directory hints: `routes/`, `controllers/`, `handlers/`, `api/`, `rpc/`, `endpoints/`; background job handlers, queue consumers, webhook receivers (same trust-boundary concerns as HTTP handlers) | `domains/api.md` |
   | **Library / SDK** | changes to `package.json` `main`/`module`/`exports`/`types`; `src/index.*`, `src/lib.*`, `lib/*`; `Cargo.toml` with `[lib]`; `pyproject.toml` / `setup.py` in a published package; `.d.ts` / `.pyi` declaration files; any file whose project publishes to a registry (npm, PyPI, crates.io, Maven, NuGet) | `domains/library.md` |
   | **Data / persistence / migrations** | `.sql` files; migration directories: `migrations/`, `db/migrate/`, `prisma/migrations/`, `alembic/versions/`, `schema/`; ORM schemas: `schema.prisma`, Drizzle `schema.ts`, Ecto migrations, SQLAlchemy models, TypeORM entities, Rails migrations, Django migrations; stored procedures, triggers, views; cache key shapes and cache layer code; queue payload schemas; blob storage keys and object storage wrappers | `domains/data.md` |
   | **CLI tool** | `bin/`, `cmd/` entry points; files with `#!/usr/bin/env` shebangs; `main()` in a project whose manifest declares a binary/script target (`package.json` `bin` field, `Cargo.toml` `[[bin]]`, `pyproject.toml` `[project.scripts]`); argument parsing libraries (`commander`, `yargs`, `clap`, `argparse`, `cobra`, `click`); signal handling, subprocess spawning, TTY detection | `domains/cli.md` |
   | **Crypto / security-critical** | calls to cryptographic libraries (`crypto`, `subtle`, `libsodium`, `openssl`, `ring`, `cryptography`, `bcrypt`, `argon2`, `scrypt`, `hashlib`, `secrets`); JWT / token signing & verification; password hashing; key generation, derivation, storage, rotation; nonce / IV / salt handling; TLS / certificate verification; session management; webhook signature verification; authentication and authorization flows | `domains/crypto.md` |

   Match inclusively — when in doubt, load the checklist. The cost of loading an extra domain file is a few KB of context; the cost of missing one is a shipped bug. Under-matching is the failure mode to avoid.

   **Classification must be recorded.** Fill in `trace_log.domains_loaded` with every domain you loaded, `trace_log.domains_considered_dropped` with any domain you considered but decided not to load (with a one-word reason), and `trace_log.classification_notes` with a one-sentence explanation of any ambiguous call (e.g., "`.tsx` file — loaded ui.md but not mobile.md because package.json does not depend on react-native"). See `output-schema.md`.

   If **no** domain matches, set `domains_loaded: []` and add a scenario `"generic attack surface only — no domain matched"`. Proceed with only the generic attack surface from `methodology.md`.

   Future domains live alongside (e.g., `domains/iac.md`, `domains/graphql.md`) — when added, extend this table.

4. **Changed symbols & consumers tracing** — for every added or modified symbol in the diff, **use the Grep tool** (not shell `grep`) to find its usages, and use the Read tool for the calling sites. Shell `grep` is not in `allowed-tools` and triggers a permission prompt per call; the Grep tool is in `allowed-tools` and runs without prompting. When searching a specific directory, pass `path` to the Grep tool — do **not** `cd` in a Bash call to change directories, as the compound-command pattern `cd X && grep Y` triggers Claude Code's path-resolution security guard and requires manual approval every time. The methodology file defines what counts as a "symbol" and what to trace. Every symbol you inspect must appear in the Trace Log in the final output. **Also run the failure-mode audit**: when the diff introduces a new caller chain that reaches an unchanged function, lifecycle, or handler, read the callee's existing failure-handling paths (auto-clear, auto-retry, default fallback, error suppression, timeout retries) and check each against the new caller's semantics — auto-recovery written for implicit/best-effort callers is often wrong for explicit-user-intent callers. Record findings under `trace_log.symbols_inspected[].failure_modes_considered`. See the "Failure-mode audit on existing callees with new callers" subsection in `methodology.md`.

5. **Mutated record fanout tracing** — for every record (struct, store entity, DB row, IPC/API/queue payload) whose fields are written in the diff, enumerate all sibling fields on the same record and check each for stale references, lifecycle leakage, or silently broken invariants. This follows the data model, not the call graph, and catches bugs that symbol tracing cannot. See the "Mutated record fanout" section in `methodology.md`. Every record you inspect must appear in `trace_log.mutated_records_inspected`. **Also run the reader-path fanout audit** for each sibling classified as "preserved": if the diff introduces a new writer→reader code path that reaches an existing reader of the preserved field, check whether the reader's implicit invariants still hold on the new path. Record findings under `trace_log.mutated_records_inspected[].new_reader_paths`. See the "Reader-path fanout" subsection in `methodology.md`.

6. **Runtime contract verification** — for every type in the diff that crosses a trust or language boundary (IPC, API response, DB row, queue payload, FFI), read the producer in its native source rather than trusting the consumer-side type signature. Tests that mock the payload from the consumer's perspective do not count as verification. See the "Runtime contract verification" section in `methodology.md`.

7. **LLM/agent output validation** — if the diff consumes structured data emitted by a language model, agent, ML pipeline, rule engine, or any other non-deterministic automation, audit every consumed field for consumer-side validation. Unvalidated fields that reach persistent state or user-visible action are findings; per the LLM-compliance severity floor in calibration rules, they start at **high** by default. Prompt-side constraints ("the prompt asks for backlog-only") are not consumer-side validation. See the "LLM/agent output validation" section in `methodology.md`. Record one line per consumed field under `scenarios_considered` in the form `llm-field: <name> — <validated|unvalidated|partial>`.

8. **Acceptance criteria crosswalk** — if the pre-review context step (5.2) loaded a spec, RFC, task file, or any document with **structured acceptance criteria** (bulleted "must" statements, numbered requirements, definition-of-done checklist), walk the AC list top to bottom. For every AC, write down the specific file:line that implements it. Flag ACs that are unimplemented, ambiguously mapped, or contradicted — these are findings at **high** by default. Record the complete crosswalk (passing and failing ACs) in `trace_log.acceptance_criteria_crosswalk`. If the spec is prose-only with no structured ACs, skip this step and note it in `classification_notes`. See the "Acceptance criteria crosswalk" section in `methodology.md`.

9. **Test-trace** — every finding you plan to report must carry a test_coverage answer explaining why existing tests did not catch the bug, chosen from `no-test`, `mock-bypass`, or `missing-assertion`. If no answer is possible, the finding is invalid — re-read the tests or drop it. See the "Test-trace" section in `methodology.md`.

---

## Step 6 — Review

Apply the methodology from `methodology.md` plus any loaded domain checklists to the collected diff. Keep the calibration rules in mind continuously — every finding you consider keeping must pass the ship-blocker question and the block test before it earns a slot under the hard cap.

### Focus text routing

If `FOCUS_TEXT` parsed in Step 1 is non-empty:

1. Treat it as an explicit weighting on the attack surface. Findings that match the focus area are prioritized over unrelated findings of equal severity when applying the hard cap.
2. Include `FOCUS_TEXT` verbatim in the `focus` field of the output (both markdown and JSON).
3. Record at least one scenario under `scenarios_considered` that directly targets the focus area, prefixed as `focus: <text>`.
4. If after applying the methodology you find **no** material issue in the focus area, say so explicitly in the summary — "focus area (<text>) reviewed, no material findings" — rather than staying silent. The user asked; answer.

If `FOCUS_TEXT` is empty, set `focus` to `null` in the JSON and omit the markdown `Focus:` line.

### Pre-output checklist

Do not start writing output until you have:
- answered the ship-blocker question (the answer goes into the Trace Log — see `output-schema.md`)
- traced consumers for every changed symbol
- routed `FOCUS_TEXT` if present
- applied the final_check to every candidate finding
- dropped weak findings to fit the hard cap
- classified every finding into one of the four `finding_type` values (`correctness`, `design_debt`, `best_practice_violation`, `architectural_smell`) — a finding without `finding_type` is a grounding failure per schema v1.6
- populated `lift_considered` on every finding whose recommendation is a runtime guard, OR named a system boundary in the finding body that explains why a lift is not the right primitive — per the Lift hierarchy rule and the v1.10.1 guard-legitimacy condition in `output-schema.md`
- populated `trace_log.patch_chain_risk` with a non-empty `theme_assessment` whenever any Step 3b signal fired, regardless of the final `detected` value — the reviewer's theme-vs-root judgment is auditable
- emitted a `scenarios_considered` line `prior-review ingestion: <status>` on every non-error run — the auto-detect outcome (loaded, absent, or rejected with reason) must always be visible per the observability rule in Step 3b
- run the **Claim verification pass** on every candidate finding per `methodology.md` and populated `trace_log.findings_dropped_in_verification` (empty array `[]` is valid when every finding survived unchanged — absence of the field means the pass was skipped and is a grounding failure). The pass is **five steps** as of schema v1.12 — step 5 is the evidence gate for cross-boundary external claims (third-party libraries including stdlib, OS runtime, protocols, shell semantics). Findings whose load-bearing claim references external behavior either carry `findings[].evidence_sources` with a specific `source` (docs URL, source file:line, runtime observation, spec identifier), or include `evidence: unverified — <reason>` in the body with severity and confidence both dropped one notch, or are dropped entirely with reason `unverified-external-claim`. `trace_log.external_claims_verified` (integer ≥0, counts verification actions not finding entries) is unconditionally required — `0` is valid when no external claims were made, absence is a grounding failure
- populated `trace_log.project_rules_loaded` with every project rule file loaded in Step 5.2b (empty array `[]` is valid when no rule file matched; absence is a grounding failure). Findings that cite a rule must emit `findings[].rule_refs` with a verbatim `quote` from the cited file — paraphrased quotes are schema-invalid
- classified every finding with a `scope` tag — `in-diff` (default), `pre-existing` (bug in code the diff did not touch), or `future-work` (suggestion, not a bug today). Only `in-diff` findings drive verdict escalation; `pre-existing`/`future-work` findings are informational. See the "Scope classification" section in `methodology.md`
- classified every finding with a `reachability` tag — `reachable` (default; a concrete call path from an entry point can be named and is in the body), `requires-specific-config` (fires under a named config, flag, env var, or platform; the specific thing is named in the body), or `hypothetical` (bug inferred from types, schemas, or code-shape reasoning without a traced path). Only `reachable` findings drive verdict escalation; `hypothetical`/`requires-specific-config` findings are informational. Reachability is orthogonal to severity and confidence — do not collapse a hypothetical bug into low severity or low confidence; emit the honest severity and let the reachability tag do the calibration work. See the "Reachability classification" section in `methodology.md`
- **if prior review loaded** — classified every finding's `prior_relation.category` (one of the three finding-level values: `carries-over | new-drift-from-fix | pre-existing-orthogonal`; `resolved` is `trace_log.prior_review_summary`-only), populated `trace_log.prior_review_summary` with per-category counts, and applied severity dampening to all `carries-over` findings. See the "Prior-relation classification" and "Severity dampening for carries-over findings" subsections in `methodology.md`. When no prior review was loaded, omit both fields entirely
- emitted the top-level `decision` block (`action | patch_chain_detected | iteration_count | rationale`) on every non-error run — `decision` is the machine-readable automation signal that pairs with prose-facing `verdict`. See the "Decision derivation" subsection in `methodology.md`
- loaded the rejection memory file per Step 3b's "Rejection memory load" subsection and populated `trace_log.rejections_loaded` (empty array `[]` is valid when no `rejections.json` exists for this session; absence of the field when the file exists is a grounding failure). If `--reject <CSV>` was passed in Step 1, applied the rejections to `rejections.json` before the load step so the subsequent review sees them. For each candidate finding whose hash matches a rejection, chose suppress-silently or re-raise-with-`previously_rejected` per the reviewer-gated rule — re-raise requires concrete new evidence articulated in one sentence. Emitted the `scenarios_considered` line `rejection memory: <loaded | absent | rejected-malformed-json>`. Applied the chain-of-rejections override when the resurface count reached ≥2 — `verdict: approve` and `decision.action: ship` with the chain-of-rejections rationale. See the "User rejection memory" section in `methodology.md`
- verified every required field listed in `output-schema.md` JSON rules is present — this is the backstop for future schema additions; when a new required field lands in a later version, the checklist does not need a per-field bullet if this backstop bullet catches it

---

## Step 7 — Emit output

Read **`output-schema.md`** (sibling file in this skill directory) and produce output in **exactly** the format it specifies: markdown section followed by a JSON fence. Both parts are mandatory on every non-error run.

The Trace Log is non-negotiable. If you reported findings without a populated trace log, you skipped the grounding step — go back, trace, and try again.

If the review cannot run (not a repo, `gh` missing, empty diff, shallow clone without base), emit the error output format from `output-schema.md` instead. Do not fabricate a review.

## Step 8 — Auto-save for future runs

After emitting the output in Step 7, use the Write tool to write the **complete emitted output** (markdown section + JSON fence, verbatim) to:

```
.claude/devil-review/${CLAUDE_SESSION_ID}/<target-slug>.md
```

`${CLAUDE_SESSION_ID}` is substituted by the runtime. Create the directory tree if it does not exist.

**Target slug** (deterministic from Step 2's resolved target):

- Working-tree mode → `working-tree`
- Branch mode → `branch-<base-ref>` with forward slashes and other non-`[A-Za-z0-9._-]` chars replaced by hyphens. Example: `feature/auth` → `branch-feature-auth`.
- PR mode → `pr-<number>`. Example: `pr-42`.

Overwrite unconditionally — each `(session, target)` pair holds one file. Different targets never collide within a session; different sessions never collide at all. Step 3b's auto-detect reads this same path on the next run.

**Skip** when the review ended in an error output (verdict `null`). No scenarios_considered line is emitted for the write — the read side (Step 3b ingestion status) already carries the observability. `.gitignore` setup is covered in the plugin README.
