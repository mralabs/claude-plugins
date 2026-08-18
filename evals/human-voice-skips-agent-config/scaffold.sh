#!/usr/bin/env bash
# A repo that already keeps rule files, so "add another rule" is an ordinary
# chore here rather than an invented task. The existing rule is deliberately
# plain prose written for an agent to follow — the category under test.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "eval"
git config commit.gpgsign false

mkdir -p .claude/rules src

cat > .claude/rules/no-default-export.md <<'MD'
# No default export

Every module exports named bindings only. A default export makes the imported
name a caller decision, so the same function ends up with three names across the
codebase and grep stops finding it.
MD

cat > src/queue.js <<'JS'
export function enqueue(queue, job) {
  queue.push(job);
  return queue.length;
}

export function drain(queue, handler) {
  while (queue.length > 0) {
    handler(queue.shift());
  }
}
JS

git add .claude src
git commit -q -m "chore: init"
