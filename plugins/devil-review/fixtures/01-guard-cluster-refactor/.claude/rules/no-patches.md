# no-patches

When a correctness issue is discovered, prefer consolidation over another guard.

## Enforce at the writer, not downstream

Every new guard on the read side is evidence that the write side has too many entry points. If two or more readers need to check the same invariant, collapse to a single writer that guarantees the invariant by construction. Multiple writers maintaining the same invariant is a duplication smell.

## When a guard is acceptable

Guards are the correct primitive at trust boundaries — user input, external API payloads, IPC from untrusted processes. Internal invariants between your own modules are not trust boundaries; a guard there is a patch on a bug that should have been a type or writer change.

## Pattern to watch for

A file that accumulates `if (restoring) return; if (sessionRestored) return; if (dirty) return; if (loading) return;` is not being defensively programmed — it is revealing that the caller graph has fragmented and nobody owns the invariant. The refactor is to consolidate; the patch is to add a fifth guard.
