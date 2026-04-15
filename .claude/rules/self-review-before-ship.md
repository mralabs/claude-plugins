# Self-review before ship

When making non-trivial changes to methodology, schemas, or domain checklists:

1. Draft the change.
2. **Apply the plugin's own methodology to its own diff** before committing. For devil-review, this means running the generalization test, mutation fanout trace, runtime contract verification, test-trace, claim verification pass, scope classification, and rule citation on the doc changes themselves.
3. Roll any self-review findings into the same commit under a clearly labeled "Self-review fixes rolled into this commit" section in the body.
4. Do NOT create a separate "v1.X.Y" + "v1.X.Y+1 self-review patch" sequence unless the self-review was done by a different reviewer or discovered issues after the fact.

A plugin that does not apply its own discipline to its own diff cannot claim the discipline works. Dogfooding is not optional.

Authoritative source: `CLAUDE.md` — "Self-review discipline".
