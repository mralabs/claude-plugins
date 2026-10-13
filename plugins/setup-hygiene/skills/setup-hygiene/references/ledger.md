# The decision ledger

The ledger is what makes the next run cheaper than this one: every finding the
owner has decided on is recorded, so it is not raised again unless something
changed.

## Where

| Scope | File |
|---|---|
| global | `~/.claude/hygiene-ledger.md` |
| project + its board | `.claude/hygiene-ledger.md` in the repo, committed after the change commits (its `applied:` lines name their shas) |

If the project does not track `.claude/` in git, or the repo is public and
the owner does not want setup decisions in it, use
`~/.claude/hygiene/<repo-dir-name>.md` instead. Ask once, with the first
run's other questions (Step 5), and write the answer as the ledger's first line
(`location: repo` / `location: home`). Neither file is loaded into sessions.

Review findings are not hygiene findings: a review won't-do still goes to
`REVIEW.md`'s accepted register.

## Entry format

Append entries; never rewrite another run's entry except its `status` line.

```markdown
### <id>
- status: accepted | won't-do | later
- decided: <YYYY-MM-DD>, by the owner ("<their words, short>")
- finding: <one line>
- subject: <path[:line] | settings key | plugin | card id>
- fingerprint: <what the evidence looked like, short: the quoted line, the value, the count>
- applied: <commit sha | "settings edit, backup <path>" | —>
- reason: <won't-do / later: the owner's reason>
- revisit when: <trigger, e.g. "a new Opus release", "pylix adopts Vue", 2027-01-01>
```

`<id>` is stable across runs: `<detector>-<subject slug>`, e.g.
`D2-board-automation-plan-model`, `C1-nuxt-skills-user-scope`.

## How a run reads it (Step 1)

Check both possible locations for a project (repo file and
`~/.claude/hygiene/<repo-dir-name>.md`); reading only one re-raises what the
other recorded.

For each finding produced this run, look up its entry: by id, or, when the
id is worded differently, by the same subject and fingerprint. Then:

- **won't-do / later** with the same fingerprint and no fired trigger →
  suppressed. The report gives the count of suppressed items only
  ("Suppressed by the ledger: 3"), never their content: a decided item shown
  again reads as re-raised.
- **won't-do / later** whose fingerprint changed or whose revisit trigger has
  fired (check it against the facts sheet / repo) → raised again, marked
  `re-raised: <what changed>`.
- **accepted** → check it is still applied. A regression (the stale line came
  back, the plugin was re-enabled) is a finding marked `regressed`.
- no entry → a new finding.

## How a run writes it (Step 7)

After the owner answers: one entry per decided finding, with their words in
`decided`. An item with no answer gets no entry; it is raised again next run.
