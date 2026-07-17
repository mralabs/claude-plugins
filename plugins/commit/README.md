# commit

> *Fast conventional commits via Haiku delegation.*

Conventional commit plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Writing a commit message is a small, structured task — classify the diff, pick a type, write one line. It doesn't need your main conversation's Opus/Sonnet budget, and the full `git diff HEAD` doesn't need to flood your context window. **commit** delegates the whole thing to a dedicated Haiku subagent that runs in an isolated fork. The main conversation only sees a one-line summary: `<hash> type(scope?): subject`.

## Usage

```bash
/commit                    # long form
/cc                        # short alias — same behavior
/cc fix the login bug      # optional hint — subagent still decides from the diff
```

Both commands do exactly the same thing. Pick whichever your fingers prefer.

## How it works

1. **Delegates to a forked Haiku subagent** — the skill runs `context: fork` into the `commit-writer` subagent (`model: haiku`, `tools: Bash`). The fork has its own context window, so the full `git diff HEAD` stays out of your main conversation.
2. **Checks for repo-specific commit conventions** — reads any `CLAUDE.md` loaded into context for a "Commit message format" section. Repo rules override the Angular defaults (see below).
3. **Probes diff size before pulling content** — `git status --short`, `git diff HEAD --stat`, `git log --oneline -10` in parallel; pulls the full diff only when it's small, targeted per-file diffs otherwise (lockfiles and generated files are classified from the stat alone, so a huge lockfile churn can't blow the fork's context either).
4. **Respects partial staging** — if you already staged files deliberately, it commits only what's staged and leaves everything else alone.
5. **Reads untracked files before committing them** — via `git diff --no-index /dev/null <file>`; nothing is committed sight-unseen.
6. **Scans for secrets** — refuses files matching `.env`, `.env.*`, `credentials.json`, `*.pem`, `*.key`, and similar patterns, plus blatant embedded secrets in content it reads (private key blocks, AWS access keys).
7. **Classifies the change** — picks one of the 11 Angular-convention commit types from the diff content.
8. **Decides on scope** — optional, based on how localized the change is and what existing `git log` entries use.
9. **Writes the subject** — `type(scope?): imperative-lowercase-summary`, max 72 chars, no emoji, no attribution.
10. **Stages files individually** — `git add <file>` per file, never `git add -A` or `git add .`.
11. **Commits via HEREDOC** — multi-line body-safe, hooks honored (never `--no-verify`, never `--amend`).
12. **Returns a one-line summary** — `<short-hash> <type>(<scope>): <subject>` to the main conversation.

The `/cc fix the login bug` hint form feeds the hint to the subagent as intent context — it shapes classification and wording, but if it conflicts with what the diff shows, the diff wins.

## Conventional commit types (Angular convention — 11 types)

| Type | Use when |
|---|---|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `docs` | Documentation only (README, *.md, comments-only diffs) |
| `style` | Formatting, whitespace, no logic change |
| `refactor` | Code restructure, no behavior change |
| `perf` | Performance improvement |
| `test` | Adding or modifying tests |
| `build` | Build system, dependencies, package.json, lockfiles |
| `ci` | CI config (GitHub Actions, pipelines, workflows) |
| `chore` | Maintenance, tooling, nothing user-facing |
| `revert` | Reverts a previous commit |

Classification hints the subagent applies:

- Multiple candidates → prefer the most user-visible (`feat` > `fix` > `refactor` > `chore`)
- Mixed feat+refactor → `feat` if the user-visible capability is new
- README/docs only → `docs`
- package.json / lockfile only → `build`
- `.github/workflows/` → `ci`

## Repo-specific format support

If a repo has its own commit message format documented in `CLAUDE.md` (e.g. requiring version numbers like `feat(plugin): v1.2.3 tagline`, or specific type meanings, or required body sections), the subagent reads those rules from context and **applies them instead of the Angular defaults**. The Angular rules are the fallback for repos without a documented convention.

This means the same `/cc` command adapts per repo — no configuration needed.

## What it does NOT do

- Ask you questions before committing (decides entirely from the diff)
- Split unrelated changes into multiple commits (always exactly one commit per invocation — split by staging deliberately and running `/cc` per batch)
- Override your partial staging (staged changes present → only those get committed)
- Commit files that look like secrets (aborts with a warning)
- Commit untracked files without reading their content first
- Use `git add -A` / `git add .` (stages files individually)
- Use `--no-verify` or skip pre-commit hooks (surfaces hook errors)
- Use `--amend` (always creates new commits)
- Add attribution, emoji, or "Generated with Claude" footers
- Push or open a PR (commit only — push separately if needed)

## Why fork to a Haiku subagent?

Two benefits stacked — **context isolation first, cost efficiency second**. Context isolation is the primary motivation; Haiku is a bonus on top.

### Context isolation (the main point)

Without forking, every `/commit` invocation pours the full `git diff HEAD`, `git status`, `git log`, and the model's own reasoning into your main conversation. On a large refactor that's thousands of tokens of diff output flooding an Opus session you were using for something else — the cache is busted and your remaining context shrinks for the rest of the conversation.

With `context: fork`, the skill body runs in an isolated second conversation window. Only the final one-line summary (`<hash> type(scope?): subject`) bubbles back up. Your main session stays clean regardless of diff size.

**Before** (inline, no fork):

```
Main conversation (Opus, 200k context)
├─ git status output
├─ git diff HEAD                  ← 500–20,000 tokens for a real diff
├─ git log --oneline -10
├─ subagent reasoning
├─ git add + git commit I/O
└─ one-line summary
```

**After** (fork + custom agent):

```
Main conversation (Opus, 200k context)
└─ "a1b2c3d feat(auth): add handler"   ← ~50 tokens, that's all you see

Forked window (Haiku, separate context)
├─ git status, diff, log, branch   ← stays here
├─ reasoning                        ← stays here
├─ git add + git commit             ← stays here
└─ summary → bubbles up to main
```

On a large monorepo diff the difference can be 100× or more in tokens landing on your main conversation.

### Cost efficiency (the bonus)

Commit message generation is mechanical: classify the diff, pick a type, write one imperative sentence. Haiku 4.5 handles it reliably for a fraction of Opus/Sonnet cost. The custom `commit-writer` subagent declares `model: haiku` in its frontmatter so the fork always runs on Haiku regardless of your main session model.

The combination is specifically valuable when:

- You're in the middle of a long Opus session and don't want diff output flooding your context
- You make frequent commits during development
- Your diffs are large (monorepos, refactors, migrations) and shouldn't burn through your main model's tokens

## Model guarantees

The `commit-writer` subagent declares `model: haiku` in its frontmatter. Claude Code resolves subagent models in this order (highest → lowest priority):

1. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable
2. Per-invocation model parameter
3. The subagent definition's `model` frontmatter — this is where we set `haiku`
4. Main conversation's model

For the vast majority of users the fork will run on Haiku. Known cases where it might not:

- **`CLAUDE_CODE_SUBAGENT_MODEL` set in your shell** — this env var overrides every subagent's `model` field. Check with `env | grep CLAUDE_CODE_SUBAGENT_MODEL`. If set to anything other than `haiku`, the commit plugin's cost profile is lost.
- **Enterprise `availableModels` restriction** — if your organization restricts the model picker to exclude Haiku, subagent behavior is undocumented. May fall back to the session model or error.
- **Foundry without `ANTHROPIC_DEFAULT_HAIKU_MODEL` pinned** — on Microsoft Foundry, the `haiku` alias may fail to resolve without an explicit pin. Bedrock and Vertex AI fall back silently to a prior Haiku version; Foundry errors.

Context isolation is unaffected by any of these — even if the fork ends up on Sonnet or Opus instead of Haiku, your main conversation still only sees the one-line summary.

### Verifying post-invocation

After running `/cc`, confirm which model actually handled the subagent by checking the subagent transcript:

```bash
ls -lt ~/.claude/projects/*/*/subagents/ | head
```

Open the most recent `agent-*.jsonl` file and look for the model ID in the entries. Subagent transcripts record the exact model used per invocation — this is the most reliable post-hoc verification.

## Secret detection is best-effort

The subagent refuses to commit files matching known secret patterns — `.env` files, SSH private keys (`id_rsa`, `id_ed25519`), `credentials.json`, AWS credentials (`.aws/credentials`), `.npmrc`, Kubernetes configs (`kubeconfig`, `.kube/config`), Java keystores (`*.keystore`, `*.jks`, `*.p12`, `*.pfx`), Terraform state (`*.tfstate`), and similar.

Content the subagent reads (diffs, untracked files) also gets a blatant-secret scan: private key blocks, AWS access keys, high-entropy literals assigned to names like `api_key`/`token`.

This is a safety net, not a guarantee. Cases the plugin will NOT catch:

- Subtle secrets embedded in otherwise-harmless files (an unlabeled token in a YAML config, keys in parts of a large diff it only saw as `--stat`)
- Uncommon file names the pattern list doesn't cover
- Repo-specific conventions (a `vault/` directory, custom secret stores, sealed-secret files)

**Always review `git status` before running `/cc` on sensitive repositories.** The plugin catches the common cases; you catch the rest. If you want to extend the pattern list for your own projects, edit the Step 3 section of `agents/commit-writer.md` — it's a single file.

## Comparison with `commit-commands`

| | `commit-commands:commit` | `commit:commit` |
|---|---|---|
| Model | Main conversation (Opus/Sonnet) | Haiku (fixed) |
| Context isolation | None — diff flows into main window | `context: fork`, isolated |
| Format enforcement | "Match repo style" (permissive) | 11 Angular-convention types (strict) |
| Secrets detection | No | Yes |
| Repo CLAUDE.md format override | No | Yes |
| Auto-invocation by Claude | Possible | Disabled (`disable-model-invocation: true`) |
| Short alias | No | `/cc` |

## File layout

```
plugins/commit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── commit/
│   │   └── SKILL.md          # /commit entry point, forks into commit-writer
│   └── cc/
│       └── SKILL.md          # /cc alias, same fork target
└── agents/
    └── commit-writer.md      # Haiku subagent — all logic lives here
```

The skills are intentionally thin — they inject the task into the forked subagent's prompt. All classification, formatting, and commit logic lives in `agents/commit-writer.md`. To customize the subagent's behavior (e.g. add your own type vocabulary, stricter scope rules, different secret patterns), edit that single file.

## License

MIT
