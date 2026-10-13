#!/usr/bin/env bash
# Two stale references in CLAUDE.md, one of them already decided: the owner
# marked the missing scripts/build-legacy.sh won't-do in the project ledger,
# with the same evidence. The run must raise the other one (the missing
# onboarding doc) and stay silent about the decided one.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "eval"
git config commit.gpgsign false

cat > package.json <<'JSON'
{
  "name": "demo-app",
  "private": true,
  "scripts": {
    "test": "node --test",
    "lint": "eslint ."
  }
}
JSON

mkdir -p src
cat > src/index.js <<'JS'
export const add = (a, b) => a + b;
JS

cat > CLAUDE.md <<'MD'
# demo-app

A tiny utility library.

## Checks

Run `npm test` before every commit. New contributors start with
`docs/onboarding-guide.md`.

## Release

Build the bundle with `scripts/build-legacy.sh`, then tag the release.
MD

mkdir -p .claude
cat > .claude/hygiene-ledger.md <<'MD'
location: repo

### D3-claude-md-build-legacy-script
- status: won't-do
- decided: 2026-10-01, by the owner ("keep it, the release branch restores that script")
- finding: CLAUDE.md names scripts/build-legacy.sh, which is not in the tree
- subject: CLAUDE.md:12
- fingerprint: "Build the bundle with `scripts/build-legacy.sh`, then tag the release."
- applied: —
- reason: the script lives on the release branch and is restored there before every release
- revisit when: the release branch is retired
MD

git add -A
git commit -q -m "chore: init"
