---
name: devil-review
description: "The devil is in the details — adversarial review that finds what's hiding in your diff"
argument-hint: "[--scope auto|working-tree|branch|pr] [--base <ref>] [--pr <number>] [focus text]"
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Bash(git:*)", "Bash(gh:*)"]
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
- Everything else after flags → `FOCUS_TEXT`

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

4. **Changed symbols & consumers tracing** — for every added or modified symbol in the diff, grep for its usage and read the calling sites. The methodology file defines what counts as a "symbol" and what to trace. Every symbol you inspect must appear in the Trace Log in the final output.

5. **Mutated record fanout tracing** — for every record (struct, store entity, DB row, IPC/API/queue payload) whose fields are written in the diff, enumerate all sibling fields on the same record and check each for stale references, lifecycle leakage, or silently broken invariants. This follows the data model, not the call graph, and catches bugs that symbol tracing cannot. See the "Mutated record fanout" section in `methodology.md`. Every record you inspect must appear in `trace_log.mutated_records_inspected`.

6. **Runtime contract verification** — for every type in the diff that crosses a trust or language boundary (IPC, API response, DB row, queue payload, FFI), read the producer in its native source rather than trusting the consumer-side type signature. Tests that mock the payload from the consumer's perspective do not count as verification. See the "Runtime contract verification" section in `methodology.md`.

7. **Test-trace** — every finding you plan to report must carry a test_coverage answer explaining why existing tests did not catch the bug, chosen from `no-test`, `mock-bypass`, or `missing-assertion`. If no answer is possible, the finding is invalid — re-read the tests or drop it. See the "Test-trace" section in `methodology.md`.

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

---

## Step 7 — Emit output

Read **`output-schema.md`** (sibling file in this skill directory) and produce output in **exactly** the format it specifies: markdown section followed by a JSON fence. Both parts are mandatory on every non-error run.

The Trace Log is non-negotiable. If you reported findings without a populated trace log, you skipped the grounding step — go back, trace, and try again.

If the review cannot run (not a repo, `gh` missing, empty diff, shallow clone without base), emit the error output format from `output-schema.md` instead. Do not fabricate a review.
