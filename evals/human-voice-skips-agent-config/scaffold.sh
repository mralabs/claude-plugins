#!/usr/bin/env bash
# A repo that documents its conventions in CLAUDE.md, so "add another one" is an
# ordinary chore here rather than an invented task. The existing sections are
# deliberately plain prose written for an agent to follow — the category under
# test.
#
# The file sits at the repo root on purpose. Writes into .claude/ are denied
# inside the sandbox even with --allow-tools Write (verified 2026-08-18: both
# Write and a `cat >` heredoc came back "permission denied", and the companion
# grader then failed on a file the agent was never allowed to create).
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "eval"
git config commit.gpgsign false

mkdir -p src

cat > CLAUDE.md <<'MD'
# Conventions

## No default export

Every module exports named bindings only. A default export makes the imported
name a caller decision, so the same function ends up with three names across the
codebase and grep stops finding it.

## No bare timeouts

Every setTimeout carries a comment naming what it is waiting for. A bare delay
is a race condition someone tuned until it stopped reproducing.
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

git add CLAUDE.md src
git commit -q -m "chore: init"
