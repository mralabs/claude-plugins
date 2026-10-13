# Inventory — what to read per scope

verified: 2026-10-13

Inventory is read-only. Record the **before** numbers; the run's record needs
them for before/after.

## Before you read: is someone else working here?

- `git status --short`, `git worktree list`, `git stash list`. Uncommitted
  changes you did not make belong to another session. Never stage, revert,
  format or "clean up" them; note them in the report.
- A plan that edits a repo with someone else's dirty checkout runs in a
  detached worktree off `origin/<main>` (verified 2026-10-13: fairsettle's
  CLAUDE.md fix went in that way with the other session's checkout untouched).

## Scope: global

| Read | Why |
|---|---|
| `~/.claude/CLAUDE.md`, `~/.claude/rules/**` | always-loaded in every project |
| `~/.claude/settings.json` (+ `settings.local.json`) | model/effort, permissions, hooks, `enabledPlugins`, `autoMode`, `statusLine`, `extraKnownMarketplaces`, legacy keys |
| `~/.claude/plugins/installed_plugins.json`, `known_marketplaces.json` | installed vs enabled vs per-project records |
| enabled plugins' `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json` under their `installPath` | listing cost, hooks that run on every event, MCP servers started per session |
| `~/.claude/skills/*`, `~/.claude/agents/*` | user skills/agents (symlinks: resolve, note the target repo) |
| `~/.claude/hooks/*` | user hook scripts |
| `~/.codex/config.toml`, `~/.codex/AGENTS.md` | Codex model, MCP entries, trusted projects |
| `~/.claude/projects/*/memory/MEMORY.md` | only when the run covers several projects |

## Scope: project

| Read | Why |
|---|---|
| every `CLAUDE.md` / `CLAUDE.local.md` / `AGENTS.md` in the repo (`git ls-files` + untracked) | root and package files; subdirectory files load on demand |
| `.claude/rules/**` (note `paths:` frontmatter = path-scoped) | always-loaded vs on-demand |
| `.claude/settings.json`, `.claude/settings.local.json` | project plugins, hooks, permissions |
| `.claude/skills/**`, `.claude/agents/**`, `.claude/commands/**` | one-job skills, the `verify` recipe, duplicates of board actions |
| `REVIEW.md` (repo root) | review rules + accepted / won't-do register |
| `.githooks/`, `.husky/`, `git config core.hooksPath`, `lefthook.yml` | git hooks are hooks too |
| `package.json` scripts / `Makefile` / `justfile`, lockfiles, CI workflows | the real check commands; what CI already enforces |
| memory dir: `~/.claude/projects/<key>/memory/` where `<key>` = the absolute project path with every non-alphanumeric char replaced by `-` | outgrown entries, index size |
| the project's hygiene ledger (see `ledger.md`) | decisions already made |

## Scope: board (rigo)

- Board key: `git-` + first 16 hex chars of sha256 of the canonical path of the
  main worktree (parent of `git rev-parse --git-common-dir`). Monorepo
  sub-projects append a suffix; if the computed dir does not exist, grep
  `~/.local/share/com.mralabs.rigo/projects/*/tasks/` for a card that names the
  repo.
- Data: `~/.local/share/com.mralabs.rigo/projects/<key>/board.db` (open with
  `sqlite3 -readonly`; tables `tasks`, `task_deps`, `task_order`, `task_tags`,
  `board_config` incl. `automation` / `promptTemplates` / `columns`) and
  `tasks/<id>.md` (the canonical card text).
- The rigo MCP server addresses the board of the session's own project only.
  For another project's board, read the files; never write them by hand
  without telling the owner that rigo must "Rebuild index from markdown"
  afterwards.
- The board can change while you read it. Record the snapshot time and the
  open-card count in the report.

## Measurements (scripts next to this skill)

- `python3 <skill-dir>/scripts/loaded_cost.py <project>` — always-loaded
  chars per instruction file, memory index, enabled plugin listings, user /
  project skills and agents. A project's own counter (an instruction lint)
  wins; matched rigo's `lint:instructions` exactly on 2026-10-13.
- `python3 <skill-dir>/scripts/usage.py <project> --since <date>` (or
  `--all`) — real invocations from transcripts: slash commands typed, Skill
  calls, subagent types, MCP servers. A plugin that is listed but never
  called is a candidate; one that is called is a question, not a cut.

## Delegation

Wide read-only sweeps (every card on a 160-card board, every path in 13
instruction files) may go to a subagent on a cheaper model with a precise
brief: what to list, the exact output shape, and "read-only". The judging,
the asking and every write stay in the main session. A subagent's claim that
something is stale is a lead; re-check it before it becomes a finding (the
2026-10-13 audits proposed moving `autoMode` to project settings, which the
docs rule out, and deduplicating permission patterns that are not
guaranteed equivalent).
