# Update docs on change

When shipping a change, check whether it needs to be reflected in documentation surfaces, and update them in the same shipping or as a same-day follow-up.

Surfaces to check:

- **`plugins/<name>/README.md`** — capability descriptions, output format templates, schema field lists, verdict semantics, version-specific call-outs. A README that mentions v1.N schema fields but describes v1.N-4 behavior is stale documentation that misleads users.
- **`README.md` (repo root)** — only when a plugin is added/removed or install flow changes. Most per-plugin changes do not touch root.
- **`plugins/<name>/docs/*.md`** — plan docs. Mark items shipped, update status line, append revision log entries. A plan that shows items as "unstarted" when they landed hours ago is the same category of staleness.
- **`CLAUDE.md`** — when a repo-wide discipline is learned or revised (not per-plugin content).
- **`.claude/rules/*.md`** — short citeable rule files; keep in sync with CLAUDE.md authoritative text.

The shipping commit body's "Self-review fixes rolled into this commit" section should call out which documentation surfaces were checked — either updated or explicitly confirmed unaffected. "README unchanged for this change — no user-facing behavior shifted" is a valid entry; silent omission is not.

Documentation drift is invisible at commit time and only surfaces when a user hits the gap. Proactive update-or-confirm at shipping beats reactive "I saw a doc that didn't match" months later.

Authoritative source: `CLAUDE.md` — "Documentation updates on change".
