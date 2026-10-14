# setup-hygiene

Audits a Claude Code / Codex agent setup and proposes fixes. It applies only the ones the owner approves.

An agent setup goes stale quietly. A rule is right the day it's written; then a model ships, a CLI changes, a plugin goes away, and nothing re-reads the rule. The case that started this: "Plan = fable, Review = fable, Implement = opus" was approved on 2026-09-15, Opus 5.5 shipped a week later, and the rule stayed pinned on 29 board cards without anything flagging it.

## Scopes

| Scope | What it reads |
|---|---|
| `global` | `~/.claude` (CLAUDE.md, rules, settings, enabled plugins and their hooks and MCP servers, user skills/agents/hooks), `~/.codex` |
| `project` | every CLAUDE.md / AGENTS.md, `.claude/` (rules, settings, skills, agents), `REVIEW.md`, the `verify` recipe, git hooks, check commands, the project's memory dir |
| `board` | the project's rigo board: cards, `after` edges, board automation and prompts |
| `all` | the three together |

## How a run goes

0. **Today's facts.** It fetches the current model lineup, the Claude Code changelog and the relevant doc pages and writes a dated facts sheet. Staleness is judged against that sheet, never against training data. When a fetch fails, findings that depend on it are marked unverified and nothing based on them is applied.
1. **Ledger.** It reads earlier decisions.
2. **Inventory**, with two bundled scripts: `loaded_cost.py` (what a session loads before the first prompt; matched rigo's own instruction lint to the char) and `usage.py` (real skill, subagent, MCP and slash-command calls from transcripts, not tool listings; each plugin row is marked enabled or disabled today, so a disabled plugin's count reads as history).
3. **Findings.** The staleness pass and the setup checks run, then the ledger filters the results.
4. **Report**, saved to `~/.claude/audits/<date>/`. Every finding has evidence (`path:line`, command output) and a concrete proposal, and findings are grouped for approval (safe / behaviour change / needs a decision).
5. **Ask.** It waits for the owner. Without an answer, nothing is applied.
6. **Apply** the approved findings only, with backups of global files, proof after each change, and commits under the target repo's own rules.
7. **Record** every decision (accepted / won't-do / later) in the ledger so the next run doesn't raise it again unless its evidence or revisit trigger changed.

### The staleness pass (D1–D8)

1. Dated decisions whose premise moved: a newer model, price or CLI release after the decision date.
2. Pinned model names in settings, agent/skill frontmatter, Codex config, board automation and prose.
3. References to removed or renamed things: paths, symbols, scripts, slash commands, plugins, env vars.
4. Hooks that silently do nothing. Pure guards are run with sample payloads; hooks with side effects are only read.
5. Contradictions across instruction files, and between instructions and reality (git history, settings).
6. Memory entries the repo has outgrown.
7. Instruction size and duplicates, including prose a hook or lint already enforces.
8. Board staleness: cards already done in code, broken `after` edges, oversized and superseded cards.

### Setup checks (C1–C7)

Plugin overlap, use and placement; one review path per project (`REVIEW.md` with an accepted register); a `verify` recipe light enough to run before every commit; the documented check command is the real one; settings leftovers; the Codex side; deliberate-looking choices asked about rather than judged.

## Usage

```bash
/plugin install setup-hygiene@mralabs

/setup-hygiene project          # current directory
/setup-hygiene board            # its rigo board
/setup-hygiene global
/setup-hygiene all ~/code/app
```

The skill is `disable-model-invocation`: it runs only when you type it, and its description costs no context in other sessions.

## Ledger

- global: `~/.claude/hygiene-ledger.md`
- project: `.claude/hygiene-ledger.md` (committed), or `~/.claude/hygiene/<repo>.md` for public repos or ones that keep `.claude/` out of git. The first run in a project asks which.

## Self-improvement

Like `launch-qa`, each run ends with a retro on the skill itself. General lessons go, on your OK, to a private inbox in your Claude config directory, `~/.claude/field-notes/setup-hygiene.md` (or under `$CLAUDE_CONFIG_DIR`), outside the plugin so they survive updates. "evolve setup-hygiene", run in a checkout of this repository, folds them into the references on a branch and records each decision in `skills/setup-hygiene/field-notes.md`.

## Origin

Extracted from a manual hygiene pass on 2026-10-13 over a desktop app, a web app, the global setup and 21 projects. The mistakes of that pass's first audits are written into the references as traps: a proposed settings move the docs rule out, permission patterns deduplicated by eye, a stale file that was still linked from the docs, a dead hook whose fix would have reformatted a hundred files.
