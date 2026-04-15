# No batch shipping

Each shipping commit addresses one plugin item. Do not bundle multiple unrelated items into a single commit, even when they would ship in sequence.

Rationale:

- Batching obscures which change caused which behavior shift — bisection gets harder.
- Batched schema changes make fixture regression bisection harder. When a test fails, you need to know which of N batched changes broke it, not search through all of them.
- Rollback of a batched commit either reverts too much (losing unrelated changes) or too little (leaving partial state).

What is acceptable: multiple items shipped in the same session as **separate commits**, in a deliberate sequence, with each commit passing tests and self-review independently. A "shipping series" in the plan docs is a sequence of commits, not a single commit with multiple items.

Authoritative source: `plugins/devil-review/docs/phase-3-plan.md` sequencing recommendation.
