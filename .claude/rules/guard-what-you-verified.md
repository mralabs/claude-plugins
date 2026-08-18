# Guard what you verified

When you verify something by hand — running a command under an old runtime, checking an exit code, confirming a claim about a remote — ask whether CI can hold that check permanently, and add it in the same shipping if it can.

A manual verification proves the code works today. Only a guard keeps it working.

Prioritise checks that are **invisible in normal conditions**, because nobody repeats those:

- A regression only an unsupported runtime shows — every other job runs something new enough not to care, so they stay green while the broken path ships.
- A wrong exit code — the error prints either way, so only a caller reading `$?` can see it.
- A claim about a remote or another repo — local state says nothing about it.

Two forms:

- **Assert on output, not just exit status.** A smoke test that merely runs a command passes even when its output is wrong. Where the output is the point, `grep -q` it.
- **Turn an assumption you could not test locally into a CI job** rather than shipping it as a guess. A red job is a finding; an unstated assumption is not.

A check that only runs when someone opted in is not enforcement: `.githooks/pre-commit` sits behind a manual `git config core.hooksPath .githooks`, and a clone that skipped it ran no version check at all. Local hooks are fast feedback; CI is the guarantee.

Authoritative source: `CLAUDE.md` — "Verified by hand once, guarded by CI after".
