# Report template

Save the report as `~/.claude/audits/<YYYY-MM-DD>/hygiene-<scope>-<name>.md`
(outside the project checkout, so writing it touches no one's working tree;
`~/.claude` itself may be synced to a private repo, so never copy secret
values, tokens or credential-bearing URLs into the report or a ledger: name
the key and redact the value), then give the owner
the summary and the approval groups in chat. Write it in English; talk to the
owner in their language.

```markdown
# Setup hygiene — <scope>: <name> — <YYYY-MM-DD>

READ-ONLY until the owner approves. Nothing below has been applied.

## Facts as of <date>
<the facts sheet from Step 0, each line with its source; NOT FETCHED lines marked>

## Snapshot
- scope: <global | project path | board key>, git HEAD <sha>, dirty files not ours: <list or none>
- board: <open cards> open at <time> (only when the board is in scope)
- before: always-loaded <chars> (~<tokens> tok), enabled plugins <n>, skill/agent listing <chars>,
  review paths <n>, verify recipe <present/absent>
- ledger: <path>, <n> entries; suppressed by the ledger: <n>

## Findings

### <id> — <one-line title>
- kind: <D1–D8 | C1–C7>, <new | re-raised: … | regressed>
- evidence: `<path:line>` "<quoted text>" · `<command>` → `<output, trimmed>`
- why it matters: <one or two lines: cost, wrong behaviour, risk>
- proposal: <the exact change: a diff, a command, a settings edit, a card action>
- risk: <what applying it could break; backups; blast radius>
- confidence: <checked | unverified against today>

## Questions (deliberate choices)
1. <"You use X for Y — on purpose?" with the evidence>

## Approval groups
- **A — safe:** <ids> (no behaviour change beyond the fix)
- **B — behaviour change:** <ids>
- **C — needs a decision first:** <ids, and the questions they hang on>
```

Number of findings is whatever the evidence supports. A run that finds
nothing says so, with the snapshot numbers; that is a result.
