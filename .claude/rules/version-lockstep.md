# Version lockstep

Every release commit for a plugin must update both manifests together:

- `plugins/<name>/.claude-plugin/plugin.json` — `version` field
- `.claude-plugin/marketplace.json` — `plugins[].version` for that plugin

These two values must always match. CI (`.github/workflows/ci.yml`) enforces this on every push and PR, plus weekly to catch an external repo releasing without a catalog bump. The `.githooks/pre-commit` hook blocks such commits locally too, but only in clones that opted in with `git config core.hooksPath .githooks` — CI is the guarantee, the hook is fast feedback.

Plugins living in external repos (github-source entries, e.g. `radar`) follow the same lockstep across two repos: the external repo's plugin.json and this catalog's `plugins[].version` must match. The pre-commit hook cross-checks github-source entries against the remote plugin.json (skipped with a warning when offline). Push the external repo BEFORE committing the catalog — the hook reads the pushed state. A mismatch reported by the CDN-cached `raw.githubusercontent.com` is re-checked against the uncached API before blocking, so a fresh push does not produce a phantom drift. Run the check by hand with `python3 .githooks/version_drift.py`.

The marketplace catalog's own `metadata.version` field is **independent** of individual plugin versions. Bump it only when the marketplace structure itself changes (new plugin added, plugin removed, structural refactor). A plugin bumping from v1.5 to v1.6 does NOT require touching `metadata.version`.

Authoritative source: `CLAUDE.md` — "Version bumping discipline".
