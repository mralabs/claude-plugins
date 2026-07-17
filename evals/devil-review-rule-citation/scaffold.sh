#!/usr/bin/env bash
# A repo carrying its own review rule, plus an uncommitted change that violates
# it in a way that is also a genuine ship blocker — the finding has to clear
# devil-review's severity bar before it can ever carry a citation.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "eval"
git config commit.gpgsign false

mkdir -p .claude/rules src

# Kept to two sentences on purpose: both are quotable, and the grader accepts
# either. A longer rule file would let a correct run quote a sentence the
# grader does not know about and go red for no reason.
cat > .claude/rules/no-silent-catch.md <<'MD'
# No silent catch

A catch block that swallows an error and returns a fallback value is never acceptable, no matter how unlikely the error path looks. Every catch block must either rethrow or report the error via `reportError()`.

Authoritative source: incident 2024-11-03, when a swallowed write error dropped four hours of orders without a single alert firing.
MD

cat > src/report.js <<'JS'
export function reportError(err, context) {
  console.error(`[${context}]`, err);
}
JS

cat > src/db.js <<'JS'
export async function write(table, row) {
  throw new Error("not implemented");
}
JS

cat > src/orders.js <<'JS'
import * as db from "./db.js";

export function buildOrder(cart) {
  return { id: crypto.randomUUID(), items: cart.items, total: cart.total };
}
JS

git add .claude src
git commit -q -m "chore: init"

# The change under review: the write can fail, the failure is swallowed, the
# caller ignores the return value, and checkout reports success anyway.
cat > src/orders.js <<'JS'
import * as db from "./db.js";

export function buildOrder(cart) {
  return { id: crypto.randomUUID(), items: cart.items, total: cart.total };
}

export async function saveOrder(order) {
  try {
    await db.write("orders", order);
    return true;
  } catch (e) {
    return false;
  }
}

export async function checkout(cart) {
  const order = buildOrder(cart);
  await saveOrder(order);
  return { ok: true, id: order.id };
}
JS
