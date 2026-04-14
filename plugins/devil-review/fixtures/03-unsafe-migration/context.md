# Fixture 03 — Unsafe migration

## Scenario

A PostgreSQL migration adds a `NOT NULL` column without a default value to the `users` table. Production `users` holds ~50M rows. The application code is updated in the same diff to expect `tenantId` on every `User` object.

Classic `domains/data.md` territory: `NOT NULL` + no default + large existing table = the migration will fail on any row that lacks the new column value, i.e., every existing row. Even if the migration somehow succeeds (e.g., via a parallel backfill done earlier), the brief period between `ALTER TABLE` acquiring an exclusive lock and completing the column-add is a production-wide write block.

This fixture exercises:
- Domain loading (`data.md`)
- Verdict escalation to `block`
- `finding_type: correctness` on the migration finding
- `ship_blocker_answer: yes`

## Repo context the skill needs

- **Database:** PostgreSQL 14. Production `users` table: ~50M rows.
- **Deploy context:** migration and application code change in the same commit. Deploy target: Friday this week. No backfill migration precedes this one.
- **Framework:** Node.js API server, TypeORM for migrations.
- **No CLAUDE.md exception** for this migration style — the project's migration discipline, if any, expects backward-compatible column additions.
- **No active spec** with acceptance criteria that would pre-approve the destructive form.
- **Test files:** there are unit tests for `User` typing (`src/__tests__/user.model.test.ts`) but no migration smoke test that would catch the NOT NULL-without-default issue.

## Commit history

Recent commits on `migrations/*.sql` are unrelated previous migrations — no defensive prefixes. The patch-chain detector should not fire.

Example:

```
xxx9999 feat(migrations): 0041 add user email_verified_at column
yyy8888 feat(migrations): 0040 create audit_log table
zzz7777 chore(migrations): 0039 rename legacy index
```

## Domain classification expected

- Loaded: `data.md` (SQL migration file present)
- Optionally also `api.md` if the scratch project's src/models/user.ts sits in an API-handling tree. Loading both is defensible.
- `classification_notes`: should explain the data.md load based on the `.sql` file and `migrations/` directory.

## Focus text

Run `/devil-review` without a focus argument. The finding should surface from natural domain loading, not from a hint.
