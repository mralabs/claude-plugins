# mralabs — Claude Code Plugins

Claude Code plugin marketplace by [mralabs](https://github.com/mralabs).

## Install

```bash
# Add marketplace
/plugin marketplace add mralabs/claude-plugins

# Install plugin
/plugin install mra@mralabs
```

## Skills

### mra:devil-review

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

[Full documentation](plugins/mra/)

## License

MIT
