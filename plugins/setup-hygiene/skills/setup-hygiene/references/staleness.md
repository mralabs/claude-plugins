# Staleness pass — eight detectors

verified: 2026-10-13. Every detector here was found by hand in the
2026-10-13 hygiene pass (a desktop app, a web app, the global setup and 21
projects).

A setup goes stale silently: a rule is right on the day it is written, the
world moves, and nothing re-reads it. The trigger case: "Plan = fable,
Review = fable, Implement = opus" was owner-approved on 2026-09-15, Opus 5.5
shipped on 2026-09-22, and the rule stayed pinned on 29 cards (9 open) with
nothing flagging it.

Each detector lists **look for → how to check → traps → proposal**. A
detector's output is a lead until the check ran; only checked leads become
findings, each with evidence (`path:line` plus the command and its output).

---

## D1. Dated decisions whose premise moved

**Look for:** decisions that carry a date and depend on a moving target —
model lineup, prices, plan limits, CLI versions and behaviour, a vendor
feature. Words: decided, approved, chosen, as of, since, "for now", "until",
"currently", a `YYYY-MM-DD` near model / price / version names. In instruction
files, memory, `docs/decisions/`, plan docs, board cards and their notes.

**How to check:** for each, take the decision date and the fact it rests on,
then look in the facts sheet (Step 0) for a release or change after that
date that touches the fact. A newer release alone is a lead; it becomes a
finding when the decision's reasoning names something the release changed
(the strongest model, a price, a missing feature that now exists).

**Traps:** a decision can survive its premise moving (a cheaper model may
still be the right call). The finding is "revisit", never "switch to the
newest". Undated decisions cannot be checked; that is its own finding (see
the authoring rule below).

**Proposal:** a question for the owner with the new fact, plus the authoring
rule applied: `decided <date>, based on <facts>, revisit when <trigger>`.

## D2. Pinned model names

**Look for:** full model IDs and version-bearing names (`claude-opus-5`,
`claude-sonnet-4-6`, `gpt-5.1-codex`, "Opus 4.8") in: settings `model`,
`ANTHROPIC_DEFAULT_*_MODEL` / `ANTHROPIC_MODEL` env, agent and skill
frontmatter `model:`, Codex `config.toml` `model =`, rigo `board_config`
(`automation`, action overrides), card frontmatter `model:`, prose rules
("use Sonnet 4.6 for reviews").

**How to check:** `grep -rnE 'claude-(opus|sonnet|haiku|fable)-[0-9]|(Opus|Sonnet|Haiku|Fable) [0-9]'`
across the scope, plus `sqlite3 -readonly board.db "select value from board_config where key in ('automation','columns')"`.
Compare each against the facts sheet: retired, superseded, or still current.
An alias (`opus`, `fable`, `best`) moves with releases on its own; a full ID
does not.

**Traps:** pinning can be deliberate (reproducible evals, cost ceilings, a
provider where the alias lags). Ask before proposing a change. A prose rule
naming a model by its marketing name is the same finding as a pinned ID.

**Proposal:** name a ROLE (strongest / workhorse / cheap) in the rule and map
roles to models in ONE place, or use the alias. When the owner keeps the pin,
the ledger records why.

## D3. References to removed or renamed things

**Look for:** pointers to things that may no longer exist: file paths,
symbols, script names, npm scripts, slash commands (`/cc`), skills, plugins
(`pr-review-toolkit`), subagent names, env vars (`$CLAUDE_TOOL_INPUT`), MCP
servers, settings keys, URLs to internal docs, board card ids.

**How to check, by kind:**
- paths: `git ls-files | grep -F` or `test -e`; symbols: `git grep -n`.
  A regex over backticked or linked paths misses ASCII directory trees:
  also take each `├──` / `└──` entry, rebuild its path from its parent
  entries (indentation depth), and `test -e` each one.
- npm scripts: the package's `package.json`; commands in a monorepo resolve
  per package.
- skills / slash commands / subagents: installed plugin dirs, user and
  project skill dirs, the bundled list in the skills doc. Plugin agents need
  the plugin-qualified name (`plugin:agent`); a bare name silently falls back
  to a generic agent.
- plugins: `installed_plugins.json` + `enabledPlugins` in every scope.
- env vars the CLI is claimed to set: the hooks doc, then
  `strings "$(readlink -f "$(command -v claude)")" | grep -c VAR` — absent
  from the binary means never set (how the dead `$CLAUDE_TOOL_INPUT` guards
  were proven on 2026-10-13).
- board ids: `tasks/<id>.md` exists and is not done.

**Traps:** history is not a pointer. "Codex review was removed 2026-09-22"
is fine; "run the Codex review" is stale. Before proposing to delete a stale
file, grep for references to it (2026-10-13: `.claude/codex-review.md` was
inert but still linked from `docs/GETTING-STARTED.md`, so it stayed).
Disabled is not removed: a disabled plugin's skill may be enabled per
project.

**Proposal:** point at the successor (`TerminalContainer` → `PaneShell` /
`TabContentRouter`), or delete the sentence when nothing replaced it.

## D4. Hooks that silently do nothing

**Look for:** every hook in user, project and local settings, plugin
`hooks/hooks.json`, and git hooks (`core.hooksPath`, `.githooks/`, husky,
lefthook).

**How to check:** read each hook command and script first, then classify:
- **Pure guard** (reads input, prints or exits a decision, writes nothing,
  calls no network): run it with sample payloads built from the hooks doc's
  schema for that event: one input it should block and one it should allow.
  Compare exit code and stdout JSON with what the hook claims. Run from a
  scratch directory with a payload whose paths point into scratch; a guard
  that decides from the cwd (e.g. by lockfile) needs those fixture files in
  the scratch directory, one fixture per case.
- **Side-effecting** (formatters, telemetry, network, writes to the repo or
  `~/.claude`): never run it. Check statically that what it reads is what the
  CLI provides: stdin JSON vs env vars the CLI does not set, matcher tool
  names that still exist, paths relative to an assumed cwd.

**What dead looks like (all seen 2026-10-13):** reading `$CLAUDE_TOOL_INPUT`
(the CLI passes JSON on stdin; that var is not set — one project's `.env`
guard had never blocked anything and another's prettier hook had never run); a git `commit-msg` hook doing `cd sub && tool --edit $1`
with a relative `$1` (breaks when git runs from the repo root); a matcher
naming a renamed tool; a guard that "fails open" on every input because its
parse throws.

**Traps:** fixing a dead hook turns its effect on for the first time. A
PostToolUse prettier hook, revived, would have reformatted 35/128 API and
76/111 app files on first touch; the owner chose delete. Measure the blast
radius (run the tool in check mode over the tracked files) and offer **fix vs
delete** as the owner's call.

**Proposal:** the corrected hook plus the sample payloads that prove it (a
test table), or deletion with the reason.

## D5. Contradictions across files

**Look for:** the same topic ruled twice with different answers: review
cadence, the check / test command, commit and push rules, package manager
and runner, model choice, language, permission preferences. Across: global
vs project CLAUDE.md, root vs package CLAUDE.md, `.claude/rules/`, REVIEW.md,
skills, memory, settings, board prompts.

**How to check:** per topic, collect each file's imperative sentences with
`path:line`, then compare. Also compare instruction with reality and with
settings:
- prose vs git: "never push to main" while `git log --first-parent origin/main`
  shows direct pushes; "every package has a CLAUDE.md" while `mobile/` has
  none;
- prose vs settings: "keep rigo MCP permission prompts" while
  `settings.local.json` allows `mcp__rigo__*`;
- prose vs hooks: a rule a hook already enforces (keep the hook, cut the
  prose to a pointer).

**Traps:** a package file narrowing a root rule for its package is not a
contradiction. Name which file wins and why before proposing.

**Proposal:** one home per fact; the other file points to it or says
nothing.

## D6. Memory entries the repo has outgrown

**Look for:** in the project's memory dir and the global one: entries whose
claim the repo now contradicts ("no CLAUDE.md by design" after a CLAUDE.md
landed), RESOLVED / DONE entries still in the index, entries duplicating a
CLAUDE.md rule, entries naming files, flags or commands that no longer exist,
an index past the load cap (Step 0 facts; was the first 200 lines / 25 KB).

**How to check:** read `MEMORY.md` and each linked file; for each factual
claim, run the check D3 uses. Count the index lines and bytes.

**Traps:** memory is the owner's private record and may hold decisions not
written anywhere else; "duplicate" needs the other home quoted. Never delete
a memory without approval; prefer rewriting it to the current truth.

**Proposal:** rewrite / merge / delete per entry, and the index line edit.

## D7. Instruction size and duplicates

**Look for:** always-loaded chars per file and total (`loaded_cost.py`),
files over the docs' size guidance, the same rule stated in two places,
prose a hook / lint / test already enforces, incident narratives (dates,
versions, war stories) where a one-line rule would do, content relevant to
one area only.

**How to check:** the criterion is Anthropic's: "Would removing this cause
Claude to make mistakes? If not, cut it." For duplicates, quote both places.
For "already enforced", name the hook / lint rule / test and show it runs
(run the hook with a payload, the lint on a violating sample).

**Traps (2026-10-13, rigo):** tripwires and "locked by <test>" clauses encode
reversals tests cannot see; they stay. Moving content to a path-scoped rule
hides it from a planner who has not opened a matching file and from a
reviewer working from `git diff`; that move is a risk tier of its own, done
after the safe cuts are measured. Imports (`@file`) do not reduce load.

**Proposal:** tiered: (1) safe — duplicates, enforced prose, history → docs;
(2) moves with a visibility cost; (3) trims inside large entries. Each tier
with its char saving and what it risks.

## D8. Board staleness

**Look for:** on the project's board: cards already done in code, `after`
edges pointing at done or deleted cards, dependencies written as prose but
not as edges, cards untouched for months at the bottom of a column, pinned
models in card frontmatter or board automation (D2), umbrella cards that are
maps rather than work, duplicates and merge candidates, oversized cards (a
96 KB card is ~25–30k tokens; no reviewer reads it whole), cards whose
premise a later decision superseded.

**How to check:** done-in-code: grep the card's key paths/symbols and
`git log --since=<card created> --grep` for its id or title words, then read
the code. Edges: `select task_id, depends_on from task_deps` joined with
`tasks.status` / `deleted_at`. Size: `wc -c tasks/*.md | sort -n | tail`.
Age: `tasks.updated_at` + `task_order`.

**Traps:** "done in code" needs the code read, not a matching commit title.
The board changes while you read it (158 → 165 open cards during the
2026-10-13 audit); re-read a card right before proposing a write to it. The rigo MCP
server cannot do everything (it could not delete a ghost row, edit the
roadmap card or move `todo` cards on 2026-10-13); list those for the owner.

**Proposal:** close with the commit as evidence, merge (absorbed card →
done, its content in a dated note on the survivor), split, add the `after`
edge, re-title, or move to a won't-do decision.

---

## The authoring rule (propose it wherever D1 or D2 fires)

A rule that depends on a moving target carries its own expiry:

> decided <date>, based on <facts>, revisit when <trigger>

and names a ROLE (strongest / workhorse / cheap) mapped to models in one
place, never a model name. The next run of this skill can then check the
trigger instead of guessing.
