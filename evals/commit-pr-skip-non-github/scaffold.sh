#!/usr/bin/env bash
# A repo whose origin is NOT GitHub (file:// bare repo), plus a change worth
# committing, invoked with --pr. Step 7.5's guard must drop PR mode: commit
# normally on the trunk, create no work branch, and report the skip.
#
# The remote is deliberately a REACHABLE file:// bare repo, not a dead URL:
# if the guard is skipped, `git push` SUCCEEDS and a work branch appears —
# the wrong path runs to completion instead of dying early, so the graders
# see the violation rather than a masking network error.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "eval"
git config commit.gpgsign false

cat > app.js <<'JS'
export function greet(name) {
  return `hello ${name}`;
}
JS

git add app.js
git commit -q -m "chore: init"

git init -q --bare remote.git
git remote add origin "file://$PWD/remote.git"

# Record the branch the commit actually lands on, at commit time. The guard
# under test drops PR mode BEFORE branch creation, so plain-commit behavior
# means the trunk (master) — a feat/* here proves the guard was skipped.
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
git diff --cached --name-only > staged-list.txt
git branch --show-current > branch-at-commit.txt
exit 0
HOOK
chmod +x .git/hooks/pre-commit

# Real work, worth committing on its own.
cat > app.js <<'JS'
export function greet(name) {
  return `hello ${name}`;
}

export function farewell(name) {
  return `bye ${name}`;
}
JS
