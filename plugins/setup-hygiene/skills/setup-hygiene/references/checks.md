# Setup checks — what a healthy setup has

verified: 2026-10-13. Criteria from Anthropic ("Would removing this cause
Claude to make mistakes? If not, cut it."), OpenAI ("A short, accurate
AGENTS.md is more useful than a long file"; "keep each skill scoped to one
job"), and the 2026-10-13 hygiene pass: one source per concern,
deterministic rules become lint/hooks, and skill/agent descriptions load in
every session, so an unused plugin costs context everywhere.

Same shape as the staleness detectors: look for → check → traps → proposal.

## C1. Plugins: overlap, use, placement

- **Overlap:** two mechanisms for one job (e.g. three code reviewers: a plugin
  agent, another plugin's agent and bundled `/code-review`; a plugin
  simplifier vs bundled `/simplify`; an automatic per-turn security hook vs
  on-demand `/security-review`; two statuslines; two time trackers; a skill
  alias that duplicates another skill).
- **Use:** `usage.py` over the projects that enable the plugin. Count real
  calls (Skill / Agent / MCP tool use, typed slash commands), never the
  listing. Listed but 0 calls → candidate to disable. Called often → ask;
  usage is the owner's evidence, not a verdict (on 2026-10-13 fairsettle had
  105 calls to a plugin reviewer the global audit had marked "overlap").
- **Placement:** a stack-specific plugin (Nuxt/Vue skills, an MCP-server dev
  kit) enabled user-wide loads in every unrelated project. Propose project
  scope (`.claude/settings.local.json` when the repo should not carry it).
- **Leftovers:** disabled but installed plugins, marketplaces with nothing
  enabled, stale per-project install records. Before proposing an uninstall,
  check every project's settings for a per-project enable (2026-10-13:
  playwright was disabled globally but enabled in fairsettle), and whether
  the capability comes from elsewhere too (the context7 MCP server stayed
  connected after its plugin was removed).
- **Per-session cost beyond listings:** plugin hooks that run on every
  event; MCP servers started per session, especially `npx -y pkg@latest`
  (a registry call each start; hangs where the registry is unreachable).

Trap: a plugin agent cited by name in project rules (e.g.
`silent-failure-hunter`) breaks when the plugin goes. Copy the agent to
`~/.claude/agents/` or update the rule in the same change.

## C2. One review path per project

- Exactly one documented way to review a task's change. Count the paths:
  CLAUDE.md, rules, skills, board review prompt, memory.
- A root `REVIEW.md` (Claude Code's convention, readable by any agent) with:
  what Important means here (money, auth, data integrity, …), Nit cap,
  Pre-existing kept apart, `file:line` evidence, skip what CI/lint enforce,
  always-check rules, and the **accepted / won't-do register**.
- No unbounded loops: "fix and re-review until PASS", "flag every issue" plus
  a binary verdict. One review, one bounded resolve round.
- Style rules in a review prompt → lint/hooks; reviewers do not police style.

## C3. A verify recipe that is safe to run before every commit

- Claude Code ≥ 2.1.286 runs a skill named `verify` or `simplify` right
  before each commit (docs and tests excepted) when a session starts with one
  in a personal, project or additional-directory location; bundled and plugin
  skills do not count. So `.claude/skills/verify/SKILL.md` must be the LIGHT
  per-change recipe (how to start and drive the app, the quick checks), and a
  project or personal `simplify` skill must be cheap enough to run on every
  commit. A heavier task-level method lives under another name (fairsettle:
  `verify` = recipe, `verify-task` = method).
- Missing recipe → propose one written with bundled `/verify` or
  `/run-skill-generator` (Step 0: confirm they still exist), not by hand.
- The recipe must not start a second copy of a dev server the owner already
  runs (rigo's lesson: verify must not start a second rigo-dev by default).

## C4. The check command is right and documented

- CLAUDE.md names the real check command(s), per package in a monorepo, with
  the project's package manager and runner (a default `pnpm check` is wrong
  in an npm project, and a single command is wrong in a monorepo).
- Board implement / verify prompts name the same command (D5 if they differ).
- Run it once (or `--help` / dry) to prove it exists; a missing script is D3.

## C5. Settings leftovers

- Project-specific blocks in global settings. Check the docs before
  proposing a move: `autoMode` is read from user settings only, so it cannot
  move to a project (the 2026-10-13 audit proposed exactly that move; it was
  wrong). Within `autoMode.environment`, a list without `$defaults` REPLACES
  the built-in defaults in every project.
- Legacy keys (Step 0 settings page).
- `statusLine` pointing at a dev build or a temp path.
- Broad allows that contradict a prose prohibition (D5). Do not dedupe
  permission patterns by eye: `Bash(x:*)` and `Bash(x *)` are not guaranteed
  equivalent.
- After any settings edit: the file still parses (`python3 -m json.tool`).

## C6. Codex side

- `~/.codex/config.toml`: MCP entries for projects that no longer exist or
  are no longer trusted; pinned `model` (D2); `AGENTS.md` presence where the
  owner uses Codex in that repo.
- A repo with both `CLAUDE.md` and `AGENTS.md`: Claude Code reads only
  CLAUDE.md unless it imports AGENTS.md (Step 0 memory page). One should
  import or point to the other.

## C7. Deliberate choices are questions

Anything that looks odd but could be on purpose (a pinned model, a kept
plugin with low use, a broad permission, an extra review lens, a big
always-loaded section) is asked, not judged: "You use X for Y — on purpose?"
A yes goes to the ledger as won't-do with the owner's reason.
