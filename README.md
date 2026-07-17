# mralabs — Claude Code Plugins

Claude Code plugin marketplace by [mralabs](https://github.com/mralabs).

## Install

```bash
# Add marketplace (once)
/plugin marketplace add mralabs/claude-plugins

# Install plugins you want
/plugin install devil-review@mralabs
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
```

[Full documentation](plugins/devil-review/)

### commit

> *Fast conventional commits via Haiku delegation.*

Delegates commit message generation to a dedicated Haiku subagent running in a forked context, so the main conversation stays clean and the token cost stays low. Enforces Angular 11 conventional commit types, respects repo-specific commit formats defined in `CLAUDE.md`, and refuses to commit files that look like secrets.

```bash
/commit                    # long form
/cc                        # short alias — same behavior
/cc fix typo in readme     # optional hint — subagent still decides from diff
```

[Full documentation](plugins/commit/)

### radar

> *Release radar for your repo.*

Track competitors, upstream tools and dependencies — release tracking for changelogs you care about. Lives in its own repository; this marketplace catalogs it from there.

```bash
/plugin install radar@mralabs
```

[Full documentation](https://github.com/mralabs/radar)

## License

MIT
