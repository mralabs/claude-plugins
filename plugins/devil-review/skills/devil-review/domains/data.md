# Domain checklist — Data / persistence / migrations

**Authoritative loading rules live in `SKILL.md` Step 5.** This list is a human-readable summary of when the checklist applies. If the two drift, SKILL.md wins.

Load this checklist when the diff touches:
- `.sql` files, especially under `migrations/`, `db/migrate/`, `prisma/migrations/`, `alembic/versions/`, `schema/`
- ORM schema definitions: Prisma (`schema.prisma`), Drizzle (`schema.ts`), Ecto migrations (`priv/repo/migrations/`), SQLAlchemy models, TypeORM entities, Rails migrations (`db/migrate/`), Django migrations
- stored procedures, triggers, views, functions in the database
- changes to how the application reads/writes shared persistent state — cache layers, queue payloads, blob storage keys

Data bugs are **irreversible in production**. A failed migration can lock a table for hours, corrupt a column, or require a restore from backup. Every data change is reviewed under the assumption that you cannot hit undo.

---

## Migration safety

- **Reversibility**: is there a down migration? Has it been tested? "We'll never need to roll back" is the famous last words of every incident.
- **Non-blocking operations**: on large tables, can this migration run without taking a long lock? Specifically:
  - `ALTER TABLE ... ADD COLUMN` is usually fast (metadata only) — unless you add a default value with a backfill, which rewrites every row on some engines.
  - `CREATE INDEX` locks writes on many engines. Use `CREATE INDEX CONCURRENTLY` (Postgres) or `ONLINE` (MySQL 5.6+).
  - `DROP COLUMN` is fast but breaks any old application code that still reads it — coordinated deploy required.
  - `ALTER COLUMN TYPE` can rewrite every row.
- **Transaction wrapping**: is the migration wrapped in a transaction? DDL in a transaction has different semantics across engines — Postgres supports transactional DDL, MySQL mostly doesn't.
- **Partial success**: if the migration has multiple statements, what's the state if step 3 of 5 fails? Is there cleanup?
- **Dry-run / staging**: has this migration been run against a production-sized dataset in staging? A migration that's fast on 1k rows can be hours on 100M.

---

## NOT NULL additions

Adding a NOT NULL column to an existing table is a classic foot-gun:

1. Add column as nullable
2. Backfill existing rows in batches (to avoid long locks)
3. Verify no nulls remain
4. Add NOT NULL constraint

If the migration does step 1 and 4 in one statement with a DEFAULT, the engine may rewrite every row while holding a lock. On a large table, this is an outage.

Check: does the change follow the multi-step pattern, or does it collapse into a one-step hazard?

---

## Column renames, drops, type changes

- **Rename**: requires a coordinated deploy: (1) add new column, (2) dual-write to both, (3) backfill, (4) switch reads, (5) stop writing old, (6) drop old. A one-step rename in a migration assumes no running app code references the old name.
- **Drop**: same hazard. Anything still reading the column breaks.
- **Type change**: shrinking (VARCHAR(255) → VARCHAR(100)) risks truncation. Widening is usually safe but may not be free. Integer width changes have engine-specific behavior.
- **Charset / collation changes**: can reorder indexes and break WHERE clauses that rely on current ordering.

---

## Index changes

- **Adding an index on a hot write path**: every INSERT/UPDATE pays the index-maintenance cost. Is the read benefit worth the write cost?
- **Dropping an index**: are there queries that rely on it? Check EXPLAIN plans for queries touching the table.
- **Unique index additions**: does existing data actually satisfy uniqueness? If not, the migration fails mid-run.
- **Partial indexes**: Postgres supports `CREATE INDEX ... WHERE`. Does the predicate match the query patterns?
- **Concurrent index builds** (Postgres): `CREATE INDEX CONCURRENTLY` can't run in a transaction and can leave an invalid index on failure. Is there a check for invalid indexes?

---

## Data integrity constraints

- **Foreign key additions**: does existing data satisfy the reference? A FK added to a table with orphan rows will fail.
- **CHECK constraints**: same concern — existing data must pass.
- **DEFAULT values**: does changing a default value affect existing rows? (Usually no, but some engines re-evaluate defaults on updates.)
- **Triggers**: a new trigger runs on every write to the table. Is it fast? Idempotent? What happens on replication?
- **Cascade rules**: `ON DELETE CASCADE` can delete more than the author expected. Trace the cascade chain.

---

## Transaction scope

- **Migrations mixed with data**: DDL followed by `UPDATE ... SET ...` in the same transaction. If the UPDATE fails on row 10,000,000, does the DDL roll back too? Engine-dependent.
- **Row-locking in data migrations**: a backfill that `UPDATE`s millions of rows in one statement holds locks for the duration. Batch it.
- **Isolation level**: does the application code change the default isolation level? Does the change rely on repeatable-read semantics that aren't the default?

---

## Soft vs hard delete

- **Removing a soft-delete column**: does any code still filter `WHERE deleted_at IS NULL`? If deleted rows become visible, that's a data leak.
- **Adding soft delete**: does every existing SELECT now need a `WHERE deleted_at IS NULL` clause? Are they all updated?
- **Hard-deleting rows referenced by FKs**: cascade or restrict? Orphans or errors?

---

## Replication, replicas, high availability

- **Replication lag**: does the change assume a write is immediately visible on a replica? Read-after-write consistency requires routing to the primary or waiting for replication.
- **Schema changes on replicas**: DDL replicates but may take different time on replicas. Does the application handle the transient skew?
- **Logical vs physical replication**: changes that break logical replication (e.g., no primary key on a replicated table) can stall the pipeline.

---

## Row-level security / multi-tenancy

- **RLS policy changes**: does the change add a policy that accidentally hides rows users should see, or exposes rows they shouldn't?
- **Tenant ID column**: every query on a multi-tenant table should filter by tenant. Does the change add a query that forgets?
- **Cross-tenant leakage**: does a new JOIN cross a tenant boundary without a WHERE clause?

---

## Caching & derived data

- **Cache invalidation**: if the change alters the shape of cached data, does the cache need to be purged on deploy? Is there a version in the cache key?
- **Materialized views**: does the change affect a view that must be refreshed?
- **Search indexes** (Elasticsearch, Meilisearch, Algolia): does the change affect fields that are indexed externally? Is there a reindex step?
- **Denormalized columns**: if the source of truth changes, does the denormalized copy get updated? Is there a reconciliation job?

---

## Column-level mutation fanout

Database migrations are a specialized case of the **Mutated record fanout** rule from `methodology.md`. Every column the migration touches has siblings — other columns on the same row, and downstream data derived from it. Writing or removing one column without updating the siblings is a silent data-integrity bug.

For every column the migration adds, renames, drops, retypes, or backfills, enumerate:

- **Other columns on the same row**: did the retype of `amount` from `INT` to `DECIMAL` leave `currency_code` now referring to a different precision? Did renaming `user_id` to `account_id` leave a stale `user_email` denormalized column claiming the old ownership?
- **Indexes involving the column**: renaming a column invalidates indexes that name it. Dropping a column silently removes it from composite indexes. Does the migration drop/recreate the affected indexes explicitly?
- **Triggers and stored procedures that read the column**: `CREATE OR REPLACE VIEW ...` that selects the column breaks when the column is renamed. So does a trigger. Use the Grep tool to find references in the schema.
- **Check constraints referencing the column**: a CHECK expression that uses `old_name` fails after rename. Engines differ on whether the check is rewritten automatically.
- **Foreign keys pointing to the column**: retyping a PK column from `INT` to `BIGINT` requires all FK columns in other tables to be widened too, or the FK constraint will be silently invalid on some engines.
- **Generated columns depending on the column**: computed/generated columns reference source columns by name. Renames and drops break them.
- **Application code that SELECTs the column by name**: use the Grep tool to find string literals of the old column name in the app. ORMs generally handle this via migrations, but raw SQL in application code does not.

Record the column and its siblings in `mutated_records_inspected` with `kind: db-row`.

---

## ORM shape vs runtime row format (contract boundary)

The database row is a contract-boundary type per the **Runtime contract verification** step in `methodology.md`. The ORM model (SQLAlchemy class, Prisma type, ActiveRecord, Drizzle schema, TypeORM entity) is the consumer's view — the actual column types in the migration are the producer's view. These can drift:

- **Timestamp types**: the migration declares `TIMESTAMP WITHOUT TIME ZONE` but the ORM maps it to a JavaScript `Date`, which forces an implicit timezone interpretation. Different drivers make different choices; some return strings, some return `Date`, some return epoch numbers.
- **Decimal precision loss**: `DECIMAL` / `NUMERIC` columns used for financial math (prices, tax, balances) are returned as **strings** by well-behaved drivers precisely because IEEE 754 `float64` cannot represent `0.1 + 0.2 === 0.3` exactly. ORMs that type them as `number` and cast through `parseFloat` silently introduce rounding errors in ledger arithmetic — the bug is invisible per-row and only appears as a cumulative reconciliation drift. Read the driver docs for the column's actual return type, not the ORM's declared type.
- **Integer overflow on wide numeric types**: `NUMERIC(38,0)` (used for blockchain-scale IDs, very large counters, some analytics sums) holds values far exceeding `Number.MAX_SAFE_INTEGER` (~9 × 10^15). ORMs that cast the string-returning driver output to `number` truncate silently above 2^53. Use `bigint` / `BigInt` / string-preserving mappers for any column declared wider than ~15 digits of integer precision.
- **JSON / JSONB columns**: the column type is just "some object"; the ORM type is whatever the developer wrote. A migration that widens the JSON schema on the producer side does not update the consumer type.
- **Array columns**: Postgres arrays, MySQL JSON-as-array, SQLite comma-separated — each driver handles them differently. The consumer type `string[]` does not guarantee the wire format.
- **Enum columns**: a migration that adds a new enum variant does not update ORM-generated TypeScript/Python enum types. Consumers will crash on unknown variants at read time.
- **NULL vs missing**: in document stores and JSON columns, `{foo: null}` and `{}` are different. ORM typings usually conflate them.

When the migration touches a column whose ORM type is declared elsewhere in the repo, read **both sides** — the migration and the ORM model — and verify they agree on runtime format, not just declared shape.

---

## Backups & recovery

- **Is there a backup before the migration**? For destructive changes (DROP COLUMN, DROP TABLE, data deletion), is there a verified backup within the recovery window?
- **Can the migration be replayed from a backup**? If you restore from a backup taken mid-migration, is the state recoverable?

---

## Output integration

`scenarios_considered` must include at least one **rollback** scenario and one **load** scenario. Examples:

```
- migration fails mid-run on row 5M of 10M — what state is the table in?
- rollback to previous deploy while new migration is already applied
- long-running transaction holds a lock during index creation
- replica lag exceeds 10s under the migration load
- existing data violates the new unique constraint
- old application code deployed simultaneously reads a dropped column
```
