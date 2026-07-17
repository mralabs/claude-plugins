# Evals

Each plugin's value lives in its SKILL.md prose — the instructions that steer an
agent. Unit tests cannot reach that layer. These cases are the regression net
for it.

## Running

`claude plugin eval` is early access. Without the env var it exits 1 with no
explanation:

```sh
CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval . --scaffold --ablation none \
  --allow-tools Bash Write Edit WebFetch WebSearch
```

Run from the repo root. Add `--case <glob>` for one case, `--runs 1` while
iterating, `--keep-temp` to inspect a run's sandbox.

**Not for CI.** Real models, ~$0.20–1.50 per case per run, 3 runs by default
because they are stochastic. Run before a release, or when a devil-review
SKILL.md sibling changes.

## Cases

| Case | Guards | Proven red |
|---|---|---|
| `devil-review-empty-diff-not-approve` | SKILL.md Step 3 — an empty diff emits `empty_diff` / verdict `null`, never `approve` | yes — inverting the rule flipped all three graders (`does-not-approve` reported "pattern found": the skill really emitted `approve`) |
| `devil-review-rule-citation` | SKILL.md Step 5.2b — findings cite a project rule file with a **verbatim** quote | yes — but only when the citation machinery is removed from *both* SKILL.md and output-schema.md; either alone leaves it working |

Both are **regression guards, not value proofs**. Both plugins are
`disable-model-invocation`, so with the plugin off the slash command does not
exist and the ablation arm is meaningless. Run with `--ablation none`.

## Why there are no `commit` cases

The eval harness (Claude Code 2.1.212) **does not load plugin subagents**. The
commit plugin's entire brain lives in `agents/commit-writer.md`, routed via
`context: fork` + `agent: commit-writer` in the skill frontmatter. In the eval
sandbox that routing silently falls back to a generic fork:

- **Canary experiment:** a system-prompt line in commit-writer.md instructing
  "begin your final output with the token ZANZIBAR" had zero effect on the run
  output. The prose is simply never in context.
- **Model evidence:** commit-writer.md declares `model: haiku`; eval-sandbox
  fork transcripts record `claude-opus-4-8`. An honored agent definition would
  have forced Haiku.
- **Behavioral evidence:** the fork's first action was Reading SKILL.md (an
  agent with commit-writer.md as system prompt has no reason to), its output
  violated Step 9's one-line format, and three successive prose hardenings
  produced identical behavior across 6+ runs.

Contrast: devil-review's skill has **no `agent:` field** — its prose loads
fine, proven by its red-proofs responding immediately to SKILL.md edits. Until
`claude plugin eval` registers plugin `agents/`, any commit-plugin case grades
a generic agent's baseline behavior: greens are fiction, reds are phantoms.
Re-add the dropped cases below when the harness gains agent support.

## House rules for adding a case

Learned the expensive way; each of these produced a case that lied at least once
here.

1. **Grade the outcome, not the mechanism.** Assert on the file or state the run
   produced, so the route does not matter. A pre-commit hook dumping
   `git diff --cached --name-only` to a file grades the real index regardless
   of how the agent staged; regex on `.git/COMMIT_EDITMSG` grades the message
   git actually recorded. Same principle in-message: grade "the exclusion was
   reported naming .env", not the exact phrasing a template mandates — models
   paraphrase, and failing right behavior on wording grades the mechanism.
2. **Grant the tools the violation needs.** A case asserting "the agent did NOT
   commit X" proves nothing if it had no Bash. Grep the run output for
   `denied tools (pass --allow-tools to grant)` — any case printing that scored
   on a fiction.
3. **Freeze the prose, then run.** Cases read SKILL.md at run time — the
   sandbox loads plugin files live from this working tree (verified: edits are
   picked up between runs with no reinstall). Editing mid-suite measures a
   moving target; break prose only deliberately, one red-proof at a time, and
   restore before the next case.
4. **Never let the answer reach the prompt.** Keep it in the scaffold. A case
   whose prompt contains its own answer passes with the plugin off too.
5. **Make every grader go red once before trusting its green.** A grader that
   has never failed is unproven. Three cases died here at this gate — see the
   dropped list.
6. **Prefer inverting prose over deleting it when red-proofing.** Deletion
   tests whether the rule does anything; inversion additionally proves the
   grader can detect the opposite behavior. `commit-no-blanket-staging`
   survived deletion AND inversion → the case measured baseline model
   behavior, not the prose.
7. **Be realistic about `max_turns`.** These skills legitimately go read the
   repo. `devil-review-rule-citation` needs 80; starving it scores
   `error_max_turns`, which is not a regression.

## Harness facts worth knowing

- `context.scaffold_script` is a **path** (`"./scaffold.sh"`), not inline bash.
  Inline gives a baffling `ENAMETOOLONG`.
- `plugins:` entries are **paths relative to the case directory**
  (`"../../plugins/devil-review"`), not plugin names.
- Plugin **skills** load live from the referenced path; plugin **agents** do
  not load at all (see the commit section above).
- `file_exists` and the `files` target only see files created via **tools**. A
  file written by Bash — including anything git writes — grades as absent
  (verified by probe). To grade real on-disk state, use `regex` with
  `target: {source: file, path: ...}`, which does read the disk.
- **The sandbox does not load a repo `CLAUDE.md`** into agent context, not even
  for the main agent (verified by probe: a CLAUDE.md instructing "append BANANA
  to every reply" had no effect). Any invariant that depends on CLAUDE.md being
  in context is untestable here.
- `tool_used` with only `max: 0` reads as "expected 1..0" and always fails. To
  assert a tool was not used, set **both** `min: 0` and `max: 0`.

## Cases that were tried and dropped

Kept as a record so they are not re-proposed.

- **`commit-repo-format-override`** — asserted that a repo CLAUDE.md commit
  format overrides the Angular defaults (commit-writer.md Step 0). Dropped: the
  sandbox never loads CLAUDE.md, so the case could only ever lie red. Injecting
  the format via `append_system_prompt` would make it pass for the wrong reason
  — a system prompt demanding a format is obeyed whether or not Step 0 exists.
- **`commit-no-blanket-staging`** — asserted the "NEVER use `git add -A`" hard
  constraint via a pre-commit hook dumping the index. Dropped: green 3/3 with
  the rule deleted, and still green with it **inverted** to "stage everything
  at once". The grader was verified correct against the real index; the case
  measured baseline model behavior, not the prose. (In hindsight this was the
  first symptom of the missing-agent problem: the prose it probed was never
  loaded.)
- **`commit-secret-refusal`** — untracked secret next to real work: exclude,
  commit the rest, report the exclusion (commit-writer.md Step 3 as of
  v0.3.0). Graders were sound (hook-dumped index + reported exclusion) and the
  case surfaced the Step 3 self-contradiction that v0.3.0 fixed. Dropped
  because its green measured a generic agent, not the plugin.
- **`commit-secret-staged-refusal`** — the dangerous corner: a secret the user
  explicitly *staged* must abort the whole commit, never be silently unstaged.
  Red across 6+ runs — but red against a generic agent that never saw the
  prose, so it proved nothing about the plugin. The scenario is the single
  most valuable commit case to resurrect once the harness loads agents:
  generic-agent behavior (unstage + commit the rest) is exactly the violation
  the prose forbids, so the case will separate prose-following from baseline
  the moment the prose is actually in context.
