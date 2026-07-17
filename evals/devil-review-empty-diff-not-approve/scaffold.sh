#!/usr/bin/env bash
# A real repo with a spotless working tree. Nothing to review.
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
