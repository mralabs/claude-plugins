# Domain checklist — Backend API / server

**Authoritative loading rules live in `SKILL.md` Step 5.** This list is a human-readable summary of when the checklist applies. If the two drift, SKILL.md wins.

Load this checklist when the diff touches:
- route handlers, controllers, middleware, request/response DTOs
- API schema files: `openapi.yaml`, `openapi.json`, `.proto`, GraphQL SDL
- server framework wiring: Express/Koa/Fastify routes, Rails controllers, Django views, FastAPI routes, ASP.NET controllers, Spring `@RestController`
- common directory hints: `routes/`, `controllers/`, `handlers/`, `api/`, `rpc/`, `endpoints/`
- background job handlers, queue consumers, webhook receivers

API bugs are rarely isolated to one endpoint. They compound at the **trust boundary** (where untrusted input first meets trusted code) and the **persistence boundary** (where requests turn into side effects on shared state). Every request is three separate review targets: what comes in, what happens, what goes out.

---

## Request boundary (what comes in)

- **Authentication**: is the endpoint behind auth? What identity does it trust? Does a change accidentally widen access (e.g., removed middleware, changed route prefix that bypasses a guard)?
- **Authorization**: does the handler enforce per-tenant / per-user access on the *specific resource* being touched, not just "is logged in"? Look for IDOR — a resource ID in the URL that isn't checked against the caller's scope.
- **Input validation**: every field from the request body, query, headers, path must be validated for type, range, length, format *before* it's used. Trust nothing the client sent.
- **Size limits**: body size, array length, nested depth. A missing limit is a DoS vector.
- **Content type**: does the handler assume JSON but accept form-urlencoded? Does it blindly `JSON.parse` untrusted input without try/catch?
- **Rate limiting**: is this endpoint behind a limiter? If the change lowers the cost-per-request but raises the cost-per-response (e.g., expensive query), the old rate limit may no longer protect the DB.

---

## Business logic (what happens)

- **Idempotency**: does a POST create two records if the client retries? Is there an idempotency key, or a uniqueness constraint, or a deduplication window?
- **Transaction scope**: which writes are inside a transaction? If the handler does `writeA(); callExternalAPI(); writeB()`, the external call can succeed while writeB fails — leaving an inconsistency you can't roll back.
- **Ordering assumptions**: does the handler assume `createFoo` always runs before `createBar`? What happens under concurrent requests from the same user?
- **Stale reads**: does the handler read-modify-write without locking? Two concurrent requests can read the same snapshot and both write, losing one update.
- **N+1 queries**: a loop that triggers a query per iteration. Does the ORM eager-load, or is a new query firing per row? Count the SQL statements for one request.
- **Connection pool exhaustion**: long-running handlers that hold a DB connection while doing external I/O. Under load the pool drains and all requests queue.
- **External calls**: what happens if the downstream is slow, errors, or returns unexpected shape? Is there a timeout? A retry? Does retry risk duplicating a side effect?
- **Background work**: does the handler enqueue a job? Is the job idempotent? Is the queue at-least-once or exactly-once (almost always at-least-once)? Can the job run before the transaction commits (ordering bug)?

---

## Response boundary (what goes out)

- **Response shape stability**: removing a field, changing a type, or making an optional field required is a breaking change for clients. Is there a version scheme, or are clients tightly coupled to this shape?
- **Error shape consistency**: do errors follow the same envelope as success responses? Do they leak internal details (stack traces, SQL, hostnames)?
- **Status codes**: 200 for errors inside a 200 body is a common pattern but inconsistent with HTTP semantics — does the change mix conventions?
- **Nullable fields**: is a field that clients expect to be present suddenly nullable under some code path? Document or refuse to return null.
- **PII leakage**: does the response include user data that shouldn't be exposed (email, phone, internal IDs, tokens)? Has a new field been added that exposes previously-hidden data?
- **Pagination**: changes to list endpoints — is `limit` still enforced? What's the max? Is the cursor stable across writes?

---

## Contract boundary (producer ↔ consumer drift)

API endpoints are a runtime contract between a producer (server handler) and consumers (frontend, mobile, third parties) that compile-time types cannot enforce across the network. Apply the **Runtime contract verification** step from `methodology.md` to every request DTO and response DTO in the diff:

- **Documented schema vs actual handler**: does the OpenAPI spec / GraphQL SDL / `.proto` in the repo still match what the handler actually returns? A field renamed in code but not in schema produces a silent drift; consumers generated from the schema will deserialize against the old shape.
- **Handler return type vs framework serialization**: the handler signature says `UserDTO` but the framework's JSON serializer may include private fields, omit optional ones based on null-handling config, or flatten nested types differently than the TypeScript model suggests. Read the serializer configuration, not just the return type.
- **Enum widening on response**: adding a new enum variant to a response field is breaking for strict consumers even if the type signature looks identical. The producer now emits values the consumer's parser rejects.
- **OpenAPI `format` drift**: the OpenAPI spec has precise format modifiers — `format: date-time` means RFC 3339 (ISO 8601 subset with timezone), `format: date` means `YYYY-MM-DD`, `format: int64` means values up to 2^63-1. These are machine-checkable contracts. Handlers that emit naive datetimes (`Date.now().toString()`, `datetime.now().isoformat()` without timezone, epoch-millis as integers), or backends that return `int64` values serialized as JSON numbers (silently truncating above 2^53 at JS consumers), silently violate the declared format even though the JSON Schema `type: string` / `type: integer` still passes. Verify the serializer respects the declared `format`, not just the base type. For `int64`, the spec requires string serialization when consumers are JS — check whether the handler and the generated client agree.
- **Discriminated unions across the boundary**: a sum type `{ kind: 'success', ... } | { kind: 'error', ... }` works in-process but serializes based on whatever the framework decides. Consumers may need the discriminator field in a specific name/position. Verify.
- **Tests-as-proof does not count.** If the handler test asserts against a hand-written expected shape, that test is the consumer's mental model — not the wire format. Real verification reads the serializer output or uses contract tests (Pact, consumer-driven contracts).

Record contract-drift findings with the producer location in the finding body (e.g., "producer: `routes/users.ts:42` returns `{createdAt: Date.now()}` — epoch-millis — consumer OpenAPI spec declares `string` without format").

---

## Mutated record fanout (within the handler)

API handlers frequently mutate records — session objects, cached entities, DB rows, outgoing DTOs — where the diff updates one field but leaves sibling fields pointing at the prior lifecycle. Apply the **Mutated record fanout** step from `methodology.md` to each record the handler writes:

- **Session / auth context**: when the handler rotates an access token, does it also update `expires_at`, `scope`, `issued_at`, `device_id`, `last_seen`? A rotation that updates only the token leaves the session claiming the old expiry.
- **Cached entity invalidation**: when the handler writes to the primary store, are all cached representations (Redis, memoized, CDN) updated or evicted? A write that updates the row but leaves a denormalized counter stale is a classic fanout bug.
- **Response DTO vs record**: when the handler builds a response DTO from a freshly-mutated record, does the DTO re-read every field, or does it copy pre-mutation values for some fields and post-mutation for others? Partial-refresh DTOs leak stale siblings to the client.
- **Join tables / polymorphic refs**: updating one side of a relation without the other leaves stale `*_type` / `*_id` pairs.

For every record written, list sibling fields in `mutated_records_inspected` — even the ones you concluded were safe.

---

## Observability

- **Structured logs**: does the handler log enough to debug a failure (request ID, user ID, resource ID, outcome) *without* logging secrets (tokens, passwords, full request bodies containing sensitive fields)?
- **Metrics**: counters for success/error/latency. Histogram for request duration. Does the change add a code path that isn't instrumented?
- **Trace context**: is the trace header propagated to downstream calls?
- **Error reporting**: do uncaught exceptions reach Sentry/equivalent, or are they swallowed into a 500 with no trace?

---

## Output integration

When this checklist is loaded, `scenarios_considered` must include at least one **concurrent request scenario** and one **failure scenario**. Examples:

```
- two concurrent POSTs from the same user, same payload — deduplication correct?
- downstream service timeout mid-transaction — partial write left behind?
- client sends oversized payload (10MB array) — handler OOMs or rejects cleanly?
- auth token expires mid-request — handler returns 401 cleanly or crashes?
- DB pool exhausted — handler queues or fails fast?
```
