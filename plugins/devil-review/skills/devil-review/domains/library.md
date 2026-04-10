# Domain checklist — Library / SDK

**Authoritative loading rules live in `SKILL.md` Step 5.** This list is a human-readable summary of when the checklist applies. If the two drift, SKILL.md wins.

Load this checklist when the diff touches:
- published entry points: `src/index.*`, `src/lib.*`, `lib/*.ts`, `pkg/*.go`, `__init__.py` in a published package
- package manifests that declare the public surface: `package.json` (`main`, `module`, `exports`, `types`), `pyproject.toml`, `Cargo.toml`, `setup.py`
- type declaration files: `.d.ts`, `.pyi`, Go exported identifiers (capitalized), Rust `pub` items
- projects that publish to a registry (npm, PyPI, crates.io, Maven, NuGet) — any change under the published path

Libraries have one unique property: **consumers you will never meet**. Every change is a contract change with an unknown audience. The review must optimize for "consumers upgrading without reading the changelog" — because most of them won't.

---

## Semver discipline

For every exported symbol touched by the diff, classify the change:

- **Breaking**: removed export, renamed export, signature change (parameter added/removed/reordered/retyped, return type changed or narrowed, thrown error type changed), type narrowing in response shape, removed enum variant, changed default parameter value *in a way that affects existing callers*.
- **Minor (additive)**: new exported symbol, new optional parameter at the end, new field in a returned object, new enum variant.
- **Patch**: bug fix that doesn't change observable behavior for correct callers.

Ask: **is the version bump on this change consistent with the classification?** If the PR is labeled "fix" but introduces a breaking change, that's the finding.

A subtle trap: adding a required field to a **parameter** object is breaking. Adding a required field to a **returned** object is also breaking (consumers' type checkers will complain). Most reviewers only catch the first.

---

## Behavioral stability

- **Default changes**: has a default value changed? Existing consumers relying on the old default will silently get different behavior. This is breaking even when the type signature is identical.
- **Error types**: does a function now throw a different error class? Consumers catching the old type will miss it.
- **Null/undefined semantics**: did a function start returning `null` where it used to return `undefined` (or vice versa)? TypeScript won't always catch this.
- **Side effects at import time**: does importing the module now run new code (global registration, singleton init, environment check)? Tree-shaking breaks on side effects.
- **Async vs sync**: has a previously-sync function become async (returns a promise)? Consumers calling it synchronously will break.
- **Iteration order**: did a function that returns an array/map change its ordering? Consumers often rely on undocumented ordering.

---

## Dependency hygiene

- **New dependencies**: what's in the transitive tree? Any with known CVEs, maintenance issues, or conflicting licenses? A 3-line feature that pulls in 200 transitive deps is a bad trade.
- **Peer dependencies**: did the peer range tighten (breaks consumers with older versions) or widen (may pull in incompatible versions)?
- **Dev → runtime promotion**: a package that was devDependency becoming runtime is a new obligation on consumers.
- **Version pinning**: is a new dep pinned too loosely (`^`) for a library, or too tightly for an app? Libraries should be *loose* on ranges; apps should be *tight* on locks.

---

## Runtime assumptions

- **Environment**: does the change assume Node? browser? Deno? Bun? workers? Edge runtime? A library consumed across runtimes breaks when it uses a runtime-specific API (e.g., `fs`, `window`, `process.env`).
- **Thread safety**: if the language has threads (Rust, Go, Java, C#, Swift), does the change introduce shared mutable state without synchronization? Does it document its thread-safety guarantee?
- **Allocation**: did a hot path gain a new allocation (`new`, `malloc`, `Vec::new`)? For libraries claiming zero-alloc or low-alloc paths, this is a regression.
- **Blocking I/O in async contexts**: a `fs.readFileSync` inside an async library blocks the event loop for all consumers.
- **Global state**: module-level `let`/`var`, singletons, process-wide config. Does the change introduce state that makes multiple instances of the lib conflict?

---

## Documentation & types

- **Public API without doc comment**: every exported symbol should have a doc comment describing purpose, params, return, throws. Missing docs on new exports is a finding.
- **Type exports**: are types that appear in public signatures also exported? Consumers need them to write their own types.
- **JSDoc/TSDoc accuracy**: does the doc still match the code after the change? Stale docs are worse than missing docs.
- **Deprecated markers**: if an old symbol is replaced, is the old one marked `@deprecated` with a migration note, or silently removed?

---

## Bundle / distribution

- **Tree-shakeability**: are there new side effects in module init that break tree-shaking? `sideEffects: false` in package.json makes promises to bundlers.
- **Bundle size**: did a new dependency blow up the minified size? For libraries, every KB matters.
- **Source maps**: are source maps still emitted? Are they published? Are they stripped of source content in closed-source libs?
- **CJS/ESM dual export**: did the change break one of the two entry points?

---

## Output integration

`scenarios_considered` must include at least one **consumer upgrade scenario**:

```
- consumer on v1.2.x runs `npm update` — do their existing call sites still type-check and behave identically?
- consumer catching the old error class — does their catch still fire?
- consumer importing in a browser bundle — does the new code path pull in a Node-only dep?
- consumer using tree-shaking — is the new code reachable only via explicit import?
```
