# Field notes

Each run's retro appends general lessons, on the owner's OK, to the owner's
private inbox, `$CLAUDE_CONFIG_DIR/field-notes/setup-hygiene.md` (default
`~/.claude/field-notes/setup-hygiene.md`), which starts with this header.
"evolve setup-hygiene" folds them into SKILL.md or `references/` and copies
each decided note here. This file is the public record of those decisions.

Rules:
- One entry per lesson. General only: true for any setup, not one project's
  quirk (that goes to the project's ledger or memory).
- The inbox may name the project in `<project>`; when a note is copied here,
  it becomes "a project" or the stack, since this file is public. No
  credentials or personal data in either file.
- Never delete an entry. Mark it `folded <version>` or `rejected: <reason>`.
- One project is weak evidence. Keep a note open until a second run agrees,
  unless it fixes an outright error in the skill.

Format:

```markdown
### <YYYY-MM-DD> — <project or "global"> — <one-line lesson>
- seen: <what happened, with evidence>
- proposal: <which file and section should change, and how>
- status: open
```

The 2026-10-13 manual pass that this skill was extracted from is already
folded into v0.1.0; its evidence lives in a board card.

## Notes

### 2026-10-13 — a project — usage.py counts calls to plugins that are no longer enabled
- seen: `usage.py --since <90 days>` listed a plugin's code-reviewer agent with 30 calls; the plugin had been disabled earlier that day, so the count read as a live review path.
- proposal: scripts/usage.py — mark each plugin-qualified skill/agent/MCP/slash row with its current enabled state (from every settings scope); inventory.md — "a count for a disabled plugin is history, not a review path".
- status: folded 0.1.2

### 2026-10-13 — a project — path checks miss filenames inside ASCII directory trees
- seen: a regex over backticked/linked paths found nothing stale in a CLAUDE.md directory tree; listing the tree's filenames explicitly found a component file that had been renamed.
- proposal: staleness.md D3 "paths" — also extract `├──`/`└──` tree entries, resolve them against their parent dirs in the tree, and `test -e` each.
- status: folded 0.1.2

### 2026-10-14 — a project — a changed checks/commands section was not run as written
- seen: a run changed a project's checks/commands section; two of its seven rows did not run as written — one needed a tool not installed locally, one (container-compose and reverse-proxy config validation) needed CI's preparation: placeholder `${VAR:?}` values, every profile, a rendered config.
- proposal: SKILL.md Step 6.4 + references/checks.md C4 — after changing a checks/commands list, run every listed command once as written before finishing; make each row runnable as written, or say what it needs in one clause.
- status: folded 0.1.2
