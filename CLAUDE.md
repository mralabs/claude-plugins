# mralabs claude-plugins

Collection of Claude Code plugins published via a marketplace manifest. Each plugin is self-contained and versioned independently.

## Repo layout

- `plugins/<name>/` — individual plugin, self-contained
- `plugins/<name>/.claude-plugin/plugin.json` — per-plugin manifest (`name`, `version`, `description`, `author`)
- `plugins/<name>/skills/<skill-name>/SKILL.md` — skill entry point(s) loaded by Claude Code
- `plugins/<name>/skills/<skill-name>/*.md` — supporting skill files (methodology, output schemas, domain checklists, etc.)
- `plugins/<name>/agents/<worker>.md` — (optional) custom subagents for delegating isolated work
- `.claude-plugin/marketplace.json` — root marketplace catalog listing all published plugins
- `.githooks/pre-commit` — repo-local hook enforcing version drift checks (see below)

## Plugin components

A plugin can contain any combination of:

- **Skills** (`plugins/<name>/skills/<skill-name>/SKILL.md`) — slash command entry points. A plugin can have multiple skills; each lives in its own directory. When a plugin exposes both a long name and a short alias (e.g. `/commit` and `/cc`), create one skill directory per name — Claude Code does not have a native alias mechanism, so two thin SKILL.md files pointing at the same logic is the standard pattern. The `commit` plugin uses this for its `/commit` + `/cc` pair.
- **Subagents** (`plugins/<name>/agents/<worker>.md`) — custom workers. Use these when a plugin benefits from delegating expensive or noisy work to an isolated subagent context so the full diff/output/logs never flood the main conversation. Combine with `context: fork` + `agent: <worker>` in the skill frontmatter to route the skill's body into the custom subagent as its task prompt. This is an alternative route to the "cheap model for mechanical task" goal described in *Model selection per skill* below: instead of setting `model` on the skill, set it on the subagent — you get the same cost control plus full context isolation and reusability across multiple skills. The `commit` plugin uses this pattern — the `commit-writer` subagent runs on `model: haiku` and is shared by both `/commit` and `/cc`.
- **Plugin README.md** — user-facing documentation.

Plugin subagents do not support `hooks`, `mcpServers`, or `permissionMode` frontmatter fields (enforced by Claude Code for security). All other subagent frontmatter fields (`name`, `description`, `tools`, `model`, `color`, `disallowedTools`, etc.) work normally. See [Claude Code subagent docs](https://code.claude.com/docs/en/sub-agents) for the full field reference.

## Version bumping discipline

**Every release commit for a plugin MUST update both manifests in lockstep**:

1. `plugins/<name>/.claude-plugin/plugin.json` `version` field
2. `.claude-plugin/marketplace.json` `plugins[].version` for that plugin

These two values must always match. The pre-commit hook blocks commits where they drift.

The marketplace catalog's own `metadata.version` field is **independent** of individual plugin versions — bump it only when the marketplace structure itself changes (new plugin added, plugin removed, structural refactor). A plugin bumping from v1.5 to v1.6 does NOT require touching `metadata.version`.

### Semver for plugins

- **patch (v1.5.0 → v1.5.1)**: clarifications, bug fixes, typos, factual corrections to reference material. No new rules, no schema changes.
- **minor (v1.5.0 → v1.6.0)**: new methodology axes, new mandatory trace-log fields, domain checklist extensions, any change that expands what the plugin emits or checks. Backward-compatible in the sense that older consumers can still parse the output.
- **major (v1.x → v2.0)**: breaking output schema changes, removed fields, renamed enum values, verdict semantics redefined. Older consumers will break.

When in doubt between patch and minor: if you're adding new content (even docs/examples), it's minor. Patch is reserved for corrections to existing content.

## Commit message format

- `feat(<plugin>): v<X.Y.Z> <tagline>` — minor or major bump introducing new capability
- `fix(<plugin>): v<X.Y.Z> <tagline>` — patch bump for clarifications and corrections
- `fix(<plugin>): sync manifest <old> -> <new>` — manifest-only fix when versions drifted from actual state
- `chore(<plugin>|repo): <...>` — docs, README, tooling, hooks; no version bump
- `refactor(<plugin>|repo): <...>` — structural changes without semantic version impact
- `docs(<plugin>|repo): <...>` — docs-only commits that are not part of a release

Commit body should explain the **reasoning**, not just the what. Self-review findings rolled into the same commit must be called out in a dedicated section (e.g., "Self-review fixes rolled into this commit:") so the rationale for each fix is auditable.

## Adding a new plugin

Checklist:

1. Create `plugins/<name>/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "<name>",
     "version": "0.1.0",
     "description": "<one-line tagline>",
     "author": { "name": "mralabs", "url": "https://github.com/mralabs" }
   }
   ```
2. Create one or more skills under `plugins/<name>/skills/<skill-name>/SKILL.md` with appropriate frontmatter (`name`, `description`, `disable-model-invocation` if slash-command-only, `allowed-tools`, etc.). For plugins exposing multiple slash commands (aliases or variants), create one skill directory per command name.
3. (Optional) Create custom subagents under `plugins/<name>/agents/<worker>.md` if the plugin needs dedicated workers. Reference them from skill frontmatter via `context: fork` + `agent: <worker>`. Set `model: haiku` (or another cheap model) on the subagent for mechanical tasks — see *Plugin components* and *Model selection per skill* for when this pattern is preferable to skill-level `model`.
4. Add sibling files as needed (`methodology.md`, `output-schema.md`, `domains/*.md`, examples, plugin README.md).
5. Add an entry in `.claude-plugin/marketplace.json` `plugins[]` with matching `name`, `version`, `description`, `author.name`, and `source: "./plugins/<name>"`.
6. Bump `.claude-plugin/marketplace.json` `metadata.version` (minor) — this is a marketplace-level structural change.
7. Commit with `feat(<name>): v0.1.0 <tagline>`.

The pre-commit hook will verify the two plugin manifests match before allowing the commit.

## Model selection per skill

Each skill's `SKILL.md` frontmatter can specify a `model` field that overrides the user's session model. The decision depends on the skill's quality vs. cost profile — pick one of three patterns when adding a new plugin:

**Pattern 1 — Inherit session (default, recommended for most plugins)**

Omit the `model` field entirely. The skill runs on whatever model the user has selected for their session — Opus, Sonnet, or Haiku. This satisfies the implicit user contract "I'm paying for Opus this session, I want Opus everywhere I go". Use this when the skill's value scales with reasoning quality and the user's session-level model choice is the right signal of how much reasoning they want spent.

Examples: adversarial review, deep refactoring, careful planning, security audits, root-cause investigation. **`devil-review` follows this pattern** — no `model` field in its `SKILL.md`, runs on whatever the user is using.

**Pattern 2 — Force a cheap model (recommended for mechanical / repetitive skills)**

Set `model: haiku` (or `model: sonnet` if a little more reasoning is genuinely needed). This forces a cheap model regardless of session, because:

- The task doesn't benefit meaningfully from Opus-level reasoning.
- The skill is invoked frequently, so per-invocation cost compounds.
- The user explicitly chose Opus for *other* work, not for this mechanical step — paying Opus prices for Haiku-quality output is waste.

Examples: commit message generation, lint check, format normalization, simple lookups, status reports, file rename suggestions, changelog drafting from a diff. **The `commit` plugin applies this principle** — message generation is mechanical, Haiku is sufficient, and the user invokes commits often enough that the cost matters. Note that `commit` routes through a forked subagent with `model: haiku` on the subagent rather than setting `model` on the skill itself (see *Plugin components* for why subagent-level is preferable when you also want full context isolation).

**Pattern 3 — Force Opus regardless of session (rare, use sparingly)**

Set `model: opus` to force Opus even when the user is in Sonnet. Reserve for skills where session-model fallback would silently degrade quality in ways the user would not notice — typically deep audits where missing a subtle bug is more expensive than the extra Opus tokens.

Use this pattern only when you can articulate a concrete failure mode that Sonnet would miss. "Quality is important" is not enough — Pattern 1 already gives quality when the user is in Opus. Pattern 3 is for when you don't trust the user's session choice for *this specific skill*.

Examples (rare): cryptographic key generation review, irreversible data migration audit, production deploy plan review.

**Picking when in doubt**: default to Pattern 1. Override only when you can name a specific reason — predictable cost ceiling (Pattern 2) or quality floor that Sonnet would breach (Pattern 3).

## Self-review discipline

When making non-trivial changes to methodology, schemas, or domain checklists:

1. Draft the change.
2. **Apply the plugin's own methodology to its own diff** before committing. For devil-review, this means running the generalization test, mutation fanout trace, runtime contract verification, and test-trace on the doc changes themselves.
3. Roll any self-review findings into the same commit under a clearly labeled "Self-review fixes rolled into this commit" section in the body.
4. Do NOT create a separate "v1.X.Y" + "v1.X.Y+1 self-review patch" sequence unless the self-review was done by a different reviewer or discovered issues after the fact.

This is a learned practice: every release in this repo so far has benefited from applying the plugin's rules to its own changes before shipping.

## Hooks setup (one-time)

After cloning, run:

```sh
git config core.hooksPath .githooks
```

This points git at the repo-local hooks directory so the version drift check runs on every commit. Without this, commits are not checked.
