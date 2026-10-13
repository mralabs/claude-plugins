# Step 0 — today's facts

verified: 2026-10-13 (Claude Code 2.1.296, Codex CLI 0.162.1)

Staleness is judged against what is true **today**, never against training
data. The model running this skill was trained months before the run; a
model released after its cutoff is invisible to it unless a source below says
so. Fetch first, judge second.

## What to fetch

Fetch the `.md` form of each page (plain markdown, smaller than the HTML).
Read only what the facts sheet needs; do not paste whole pages into context.

| Fact | Source | Extract |
|---|---|---|
| Model lineup | https://platform.claude.com/docs/en/about-claude/models/overview.md | current IDs and aliases per model, release dates if shown, legacy/deprecated list |
| Aliases in Claude Code | https://code.claude.com/docs/en/model-config.md | what `opus` / `sonnet` / `haiku` / `fable` / `best` / `opusplan` resolve to, version history of the aliases |
| Claude Code releases | https://code.claude.com/docs/en/changelog.md | latest version + date; entries since the oldest date the setup's decisions cite |
| Docs index | https://code.claude.com/docs/llms.txt | find any page below that moved |
| Instruction files | https://code.claude.com/docs/en/memory.md | size guidance (was: under 200 lines per CLAUDE.md), load order, `CLAUDE.local.md`, AGENTS.md handling, auto-memory index limit (was: first 200 lines or 25 KB), `/doctor prompt-audit` |
| Skills | https://code.claude.com/docs/en/skills.md | frontmatter fields, listing cap (was: 1,536 chars per description), bundled skills, the pre-commit `verify` behaviour |
| Hooks | https://code.claude.com/docs/en/hooks.md | events, matcher tool names, the stdin payload schema per event, which env vars the CLI sets |
| Settings | https://code.claude.com/docs/en/settings.md | keys that moved or became legacy; which keys are read from which scope (e.g. `autoMode` is user-scope only) |
| Code review | https://code.claude.com/docs/en/code-review.md | `REVIEW.md` conventions, severity vocabulary |
| Codex | `codex --version`; https://developers.openai.com/codex/changelog | latest version; AGENTS.md and config changes |

Installed versions: `claude --version`, `codex --version`. Do not ask a package
registry for the latest version (`npm view`, `npx`): on some machines a
registry call hangs. The changelog pages carry the latest version.

## The facts sheet

Write it at the top of the report, dated, each line with its source:

```
Facts as of <date> (fetched <time>):
- Claude Code: installed 2.1.296, latest 2.1.296 (changelog.md)
- Models: Fable 5.1 (claude-fable-5-1), Opus 5.5 (claude-opus-5-5, released 2026-09-22), … (models/overview.md)
- Aliases: opus → claude-opus-5-5, … (model-config.md)
- Codex CLI: installed 0.162.1, latest … (codex changelog)
- Doc changes that matter here: … (one line each, with page)
```

Every staleness finding that depends on a fact cites the sheet line.

## When a fetch fails

Say so in the facts sheet (`models: NOT FETCHED — <error>`). Findings that
depend on the missing fact are marked `unverified against today` and are never
applied in that run. Do not fill the gap from memory.

## Built-in overlap

Claude Code ≥ 2.1.283 ships `/doctor prompt-audit`: wording-level findings in
instruction files (instructions written for older models, missing references,
contradictions), report first, edits on request. This skill goes wider
(settings, plugins, hooks run with payloads, memory, board, ledger) and checks
every claim with a command. When the owner wants a second opinion on prose,
point them at `/doctor prompt-audit`; do not re-implement its wording advice.
Re-check this paragraph each run: if the built-in grows to cover a detector
here, say so in the report and propose dropping that detector.
