#!/usr/bin/env bash
# A repo with a feature branch worth opening a PR for. The branch is real so
# "the PR for this branch" is a genuine task, not a hypothetical — the agent
# has something to read before it writes anything.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "eval"
git config commit.gpgsign false

mkdir -p src

cat > src/cache.js <<'JS'
const store = new Map();

export function get(key) {
  return store.get(key);
}

export function set(key, value) {
  store.set(key, value);
}
JS

git add src
git commit -q -m "chore: init"

git checkout -q -b feat/cache-ttl

cat > src/cache.js <<'JS'
const store = new Map();

export function get(key) {
  const entry = store.get(key);
  if (!entry) return undefined;
  if (entry.expiresAt !== null && entry.expiresAt <= Date.now()) {
    store.delete(key);
    return undefined;
  }
  return entry.value;
}

export function set(key, value, ttlMs = null) {
  store.set(key, {
    value,
    expiresAt: ttlMs === null ? null : Date.now() + ttlMs,
  });
}

export function size() {
  return store.size;
}
JS

git add src
git commit -q -m "feat: per-entry ttl on cache set"
