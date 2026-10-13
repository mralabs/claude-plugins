# mralabs — Claude Code Plugin Marketplace

Claude Code plugin marketplace by [mralabs](https://github.com/mralabs).

## Install

```bash
# Add marketplace (once)
/plugin marketplace add mralabs/claude-plugins

# Install plugins you want
/plugin install devil-review@mralabs
/plugin install radar@mralabs
/plugin install commit@mralabs
/plugin install human-voice@mralabs
/plugin install launch-qa@mralabs
/plugin install setup-hygiene@mralabs
```

## Plugins

### devil-review

> *The devil is in the details.*

Adversarial code review that finds the subtle bugs, race conditions, and violated invariants hiding in your diff.

```bash
/devil-review                          # auto-detect scope
/devil-review --scope working-tree     # working tree only
/devil-review --scope branch           # branch diff against main
/devil-review --pr 42                  # review a GitHub PR
/devil-review --base develop           # diff against specific ref
/devil-review concurrency handling     # focus on specific area
/devil-review --reject 2,5             # reject prior findings by index, then re-review
```

[Full documentation](plugins/devil-review/)

### radar

> *Release radar for your repo.*

Track competitors, upstream tools and dependencies — release tracking for changelogs you care about. Optional weekly GitHub Actions check keeps a rolling "Radar digest" issue up to date. Lives in its own repository; this marketplace catalogs it from there.

```bash
/radar init      # creates .radar/ (git-tracked), proposes what to track
/radar           # check → changelogs → analysis grounded in YOUR repo
/radar add <url> # track a new tool
/radar discover  # find new tools in your categories
/radar deep <x>  # research one tool in depth — tracked or not
```

[Full documentation](https://github.com/mralabs/radar)

### commit

> *Fast conventional commits via Haiku delegation.*

Delegates commit message generation to a dedicated Haiku subagent running in a forked context, so the main conversation stays clean and the token cost stays low. Enforces the 11 Angular-convention commit types, respects repo-specific commit formats defined in `CLAUDE.md`, and refuses to commit files that look like secrets. Opt-in PR flow for solo work: commit → push → PR → squash merge in one command.

```bash
/commit                    # long form
/commit fix typo in readme # optional hint — subagent still decides from diff
/commit --pr               # commit, push, open a PR (branch auto-created on default branch)
/commit --merge            # --pr + squash merge + branch cleanup (also: --m, --prm)
```

[Full documentation](plugins/commit/)

### human-voice

> *Ghostwriting that doesn't read as AI.*

Style guard loaded before drafting any text a human will read as the user's own words — emails, PR descriptions, issue/review comments, chat messages. Text a machine consumes (prompts for other agents, tool input) stays out of scope. A compact rule sheet distilled from [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), plus ghostwriting-specific tone/register/no-fabrication rules. Applies in whatever language the text is written. Invoke on demand or let it load automatically — the description model-invokes it when Claude is about to write as you; pair it with a `CLAUDE.md` directive for guaranteed loading.

```bash
/human-voice reply to this email: <paste>
/human-voice rewrite this sentence so it doesn't sound AI-written: <sentence>
```

[Full documentation](plugins/human-voice/)

### launch-qa

> *Test the whole app before launch, and get better at it every time.*

Phased, multi-session pre-launch QA for apps with a web UI (SPA, SSR, PWA, WebView shell, Tauri/Electron desktop): flow inventory and E2E coverage map, an edge-case seed, hands-on tours per platform, severity-ranked findings, test-first fixes. The QA log on a board card or in `docs/qa/` carries the job between sessions. Every session ends with a retro whose general lessons collect in a private inbox (`~/.claude/field-notes/launch-qa.md`) until an evolve pass folds them in. Experimental (0.x).

```bash
/launch-qa                          # start: inventory, coverage map, QA seed
Do the next launch-QA phase         # resume from the QA log in any session
evolve launch-qa                    # fold collected field notes into the skill
```

[Full documentation](plugins/launch-qa/)

### setup-hygiene

> *An agent setup goes stale quietly. This re-reads it.*

Audits the agent setup at three scopes: user-global (`~/.claude`, `~/.codex`), one project (CLAUDE.md / AGENTS.md, `.claude/`, `REVIEW.md`, the verify recipe, memory) and its rigo board. It starts by re-reading the current vendor docs, so a pinned model or an outdated rule is judged against today rather than the model's training data. A staleness pass with eight detectors runs alongside checks for plugin overlap, review paths and dead hooks. Every finding comes with evidence and a concrete proposal. Nothing is applied until the owner approves it, and every decision goes into a ledger so the next run doesn't raise it again.

```bash
/setup-hygiene project        # the current repo
/setup-hygiene all ~/code/app # global + project + its board
```

[Full documentation](plugins/setup-hygiene/)

## License

MIT
