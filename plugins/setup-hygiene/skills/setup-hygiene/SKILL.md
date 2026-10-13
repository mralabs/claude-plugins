---
name: setup-hygiene
description: Audit an agent setup — user-global (~/.claude, ~/.codex), one project (CLAUDE.md/AGENTS.md, .claude/, REVIEW.md, verify recipe, memory) and its rigo board — for stale, wasteful or contradictory pieces, judged against today's vendor docs. Reports findings with evidence and concrete proposals, asks, applies only what the owner approves, and keeps a decision ledger the next run reads.
argument-hint: "[global|project|board|all] [project-path]"
disable-model-invocation: true
---

# Setup hygiene

An agent setup goes stale quietly: a rule is right the day it is written, then
a model ships, a CLI changes, a plugin is removed, and nothing re-reads it.
This skill re-reads it. It is an audit first and an editor second.

Arguments: `$ARGUMENTS`. Scope is `global`, `project` (default: the current
directory), `board` (the project's rigo board) or `all` (the three). An
optional path names the project.

## Ground rules

1. **Nothing changes without the owner's approval.** Until the owner answers,
   the run is read-only: no edits to instruction files, settings, hooks,
   memory, plugins, skills or board cards, no commits. The only file a run
   writes before approval is its report, saved outside the project checkout.
2. **Approval comes after the owner has seen the findings,** names what it
   covers (finding ids, a group from the report, or "all of them"), and
   lasts for this run. Silence, a question back, or a request phrased before
   the report ("fix whatever you find") is not approval of a finding the
   owner has not seen: show the report first, then ask once.
3. **No finding without evidence.** Each one carries `path:line` with the
   quoted text and/or the command that proves it with its output. A lead you
   could not check is not a finding; say what would check it.
4. **Judge against today, not training data.** Facts about models, CLI
   versions and features come from Step 0, or are marked unverified.
5. **Never run a hook that has side effects** (formatters, network,
   telemetry, writes). Read it; run only pure guards, with sample payloads,
   from a scratch directory.
6. **Other sessions share checkouts.** Do not stage, revert or reformat
   changes you did not make. Edit a dirty repo through a detached worktree.
7. **A proposal is checked against the docs before it is proposed.** If you
   claim a setting can move, a key is legacy or a feature exists, Step 0's
   pages say so.

## Step 0 — today's facts

Follow `references/vendor-sources.md`: fetch the model lineup, Claude Code's
changelog and the doc pages it lists, note installed vs latest CLI versions,
and write the dated facts sheet. A fetch that fails is recorded as failed;
findings resting on it are `unverified against today` and are not applied
this run.

## Step 1 — scope and ledger

Resolve the scope and the project path. Read the ledger(s) for that scope
(`references/ledger.md`): global and/or project. A project with no ledger
yet: add "where should the ledger live?" to Step 5's questions; do not stop
to ask now.

## Step 2 — inventory

Read what `references/inventory.md` lists for each scope in the run, check
for other sessions' work first, and record the before numbers:

- `python3 ${CLAUDE_SKILL_DIR}/scripts/loaded_cost.py <project>`
- `python3 ${CLAUDE_SKILL_DIR}/scripts/usage.py <project> --since <date 90 days before today>`

Wide read-only sweeps may go to a subagent on a cheaper model; judging,
asking and writing stay here. A subagent's "this is stale" is a lead: check
it yourself before it becomes a finding.

## Step 3 — findings

Run the staleness pass (`references/staleness.md`, D1–D8; D8 only when the
board is in scope) and the setup checks (`references/checks.md`, C1–C7).
Then filter through the ledger: suppress decided items whose evidence and
triggers have not changed, re-raise the ones that changed, flag accepted
items that regressed. Suppressed items are only counted in the report
("suppressed by the ledger: 3"), never named or described: a decided item
shown again reads as re-raised.

Anything that could be deliberate becomes a question, not a finding.

## Step 4 — report

Write the report from `references/report-template.md` to
`~/.claude/audits/<date>/`. In chat: the facts sheet's key lines, the before
numbers, each finding in one or two lines with its id, the questions, and
the approval groups (A safe / B behaviour change / C needs a decision).

## Step 5 — ask

Ask the owner to decide each finding or group: **apply**, **won't do**
(with a reason, or none), or **later** (with a revisit trigger; "after
comparing X and Y on the next real diff" is a trigger). Then stop and wait. If this run
cannot get an answer (no one is there to reply), end here: the report is the
deliverable and nothing is applied.

## Step 6 — apply what was approved

For each approved finding, in the order that keeps the setup working:

1. Re-read the target right before editing; the board and checkouts move.
2. Back up global files before editing them:
   `~/.claude/audits/<date>/<file>.before-<topic>`.
3. Make exactly the approved change. A new problem found while applying is
   a new finding: report it, do not fold it in.
4. Prove it: re-run the detector that found it, parse edited JSON, run the
   hook with its payloads, run the project's checks after instruction or
   config changes. A check that fails on files you did not touch (another
   session's work) is reported with that attribution, not fixed.
5. Commit only under the target repo's own rules (its commit format, its
   review-before-commit rule, explicit staging). Before committing, check
   `git diff --cached --stat` names only your files. A repo hook that blocks
   the commit because the hook itself is broken: never `--no-verify` without
   asking; report it as a new finding. Work done in a detached worktree goes
   on a named branch; ask the owner whether to push or merge it. Never push
   without the owner's OK.
6. A step only the owner or a UI can do (a board setting, rigo's "Rebuild
   index from markdown" after hand-edited card files, a plugin toggle in a
   dialog) is handed to the owner as an exact instruction, and recorded as
   pending, not done.

## Step 7 — record

- Ledger: one entry per decided finding (`references/ledger.md`), including
  won't-do and later with the owner's words. In a repo, the ledger is its own
  commit after the change commits, under the same commit rules.
- Before/after numbers for what changed.
- If the run was started from a board card, a dated note on that card: the
  report path, what was applied (with commits), what was declined.

## Retro and evolve

At the end of the run, ask about **this skill**: which instruction was wrong
or missing, which detector cost time and found nothing, which fact in a
`references/` file was stale. Propose general lessons to the owner as
entries in the format at the top of `field-notes.md` next to this file; on
the owner's OK, append them to the owner's field-notes inbox,
`$CLAUDE_CONFIG_DIR/field-notes/setup-hygiene.md` (default
`~/.claude/field-notes/setup-hygiene.md`; create it with that header if it
is missing). Never write inside this skill's own directory: an installed
plugin is replaced on every update, and the repo copy of `field-notes.md` is
the public record that only evolve writes. A run that ended at Step 5 still
gives its retro in the report. Never edit SKILL.md or `references/` during
an audit run; fold notes in only when the owner asks to "evolve
setup-hygiene", on a branch, under the plugin repo's rules: fold each open
inbox note, copy it into the repo's `field-notes.md` with no project name
(that file is public), and mark it `folded <version>` or `rejected:
<reason>` in both files.
