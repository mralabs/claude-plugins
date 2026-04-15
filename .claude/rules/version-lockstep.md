# Version lockstep

Every release commit for a plugin must update both manifests together:

- `plugins/<name>/.claude-plugin/plugin.json` — `version` field
- `.claude-plugin/marketplace.json` — `plugins[].version` for that plugin

These two values must always match. The `.githooks/pre-commit` hook blocks commits where they drift.

The marketplace catalog's own `metadata.version` field is **independent** of individual plugin versions. Bump it only when the marketplace structure itself changes (new plugin added, plugin removed, structural refactor). A plugin bumping from v1.5 to v1.6 does NOT require touching `metadata.version`.

Authoritative source: `CLAUDE.md` — "Version bumping discipline".
