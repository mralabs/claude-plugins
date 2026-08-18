# Evals

Each plugin's value lives in its SKILL.md / agent prose — the instructions that
steer an agent. Unit tests cannot reach that layer. These cases are the
regression net for it.

## Running

`claude plugin eval` is early access. Without the env var it exits 1 with no
explanation:

```sh
CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval . --scaffold --ablation none \
  --allow-tools Bash Write Edit WebFetch WebSearch
```

Run from the repo root. Add `--case <glob>` for one case, `--runs 1` while
iterating, `--keep-temp` to inspect a run's sandbox.

**Not for CI.** Real models, ~$0.02 (Haiku forks) to ~$1.50 (devil-review) per
case per run, 3 runs by default because they are stochastic. Run before a
release, or when the prose a case guards changes.

**Sandbox escape hazard (observed 2026-07-20).** One run in a batch escaped
its sandbox: the forked subagent resolved its working directory to THIS repo
(the plugin source path) instead of the eval cwd, ran the real `/commit --pr`
flow here, committed the dirty working tree as author `Plugin Eval`, created a
branch, and pushed it to origin over the real ssh agent (`gh pr create` died
only because the sandbox HOME had no gh token). Until the harness pins the
fork cwd: run eval batches ONLY with a clean committed tree, and check
`git log` + `git branch -a` after every batch. The escaped run looks like a
0.00 score with "focus file does not exist" grader errors — its work landed
here, not in its sandbox.

## Cases

| Case | Guards | Proven red |
|---|---|---|
| `devil-review-empty-diff-not-approve` | SKILL.md Step 3 — an empty diff emits `empty_diff` / verdict `null`, never `approve` | yes — inverting the rule flipped all three graders (`does-not-approve` reported "pattern found": the skill really emitted `approve`) |
| `devil-review-rule-citation` | SKILL.md Step 5.2b — findings cite a project rule file with a **verbatim** quote | yes — but only when the citation machinery is removed from *both* SKILL.md and output-schema.md; either alone leaves it working |
| `commit-secret-refusal` | commit-writer.md Step 3, untracked match — exclude the secret, commit the rest, report the exclusion | yes — inverting to "refuse everything" went 0.00 (hook never ran) |
| `commit-secret-staged-refusal` | commit-writer.md Step 3, staged match — refuse the ENTIRE commit, never unstage | yes — inverting to "unstage and commit the rest" went 0.00 |
| `commit-pr-skip-non-github` | commit-writer.md Step 7.5 guard (v0.4.x) — `--pr` with a non-GitHub origin commits plainly on the trunk, creates no work branch, pushes nothing, reports ` — PR skipped` | yes — organically, during authoring: pre-v0.4.2 prose failed 2/9 runs, both creating a work branch despite the guard; the autopsied one also pushed to the file:// remote (successfully) and reported "PR failed" instead of "PR skipped". The v0.4.2 fix: 15/15 valid post-fix runs passed with zero guard violations (a 16th run escaped the sandbox entirely — see the hazard note above) |
| `human-voice-skips-agent-prompt` | SKILL.md frontmatter description + Scope (v0.2.0) — drafting a task prompt for a subagent must NOT load the skill; the words go out under the user's name but no person reads them as the user's own | yes — inverting the description to claim machine-bound text is in scope fired the skill 3/3, reproducing the field drift that caused v0.2.0 |
| `human-voice-guards-published-text` | the same scope rule from the other side — same scaffold, same shape of request, only the reader differs: a PR description MUST load the skill | yes — an inversion pulling repository text out of the trigger list dropped invocations to 0/3 |
| `human-voice-skips-agent-config` | the description's trigger list must not broaden far enough to swallow agent config files — adding a section to a repo's CLAUDE.md must not load the skill | yes, with a caveat worth knowing: it goes red only when the **description** names config files. An inversion that flipped the Scope body alone left it green 3/3 — see the invocation note under harness facts. What this case guards is the trigger list staying narrow, not the exclusion sentence |

All eight are **regression guards, not value proofs**. `devil-review` and
`commit` are `disable-model-invocation`, so with the plugin off the slash
command does not exist and the ablation arm is meaningless. `human-voice` is
model-invocable, so a baseline arm would mean something there — but its graders
assert on whether the skill fired, which the harness marks `with-only` and
drops from the score under `with-without` anyway. Run the suite with
`--ablation none`.

## The bare-agent-name incident (why the commit cases exist twice over)

The commit cases were originally authored, went red/green in ways that made no
sense, and were dropped with the diagnosis "the eval harness does not load
plugin agents". That diagnosis was **wrong**. The real bug was in the plugin:
the skills referenced the subagent as `agent: commit-writer` (bare name). A
bare name silently fails to resolve against plugin agents — in the eval
sandbox AND in real interactive sessions — and `context: fork` then runs a
generic agent on the session model with no error anywhere. Every `/commit`
invocation since v0.1.0 had been running without commit-writer's rules.

Evidence chain that finally pinned it: a canary instruction planted in
commit-writer.md had zero effect on runs; fork transcripts recorded
`claude-opus-4-8` despite `model: haiku` frontmatter; the fork's first act was
Reading SKILL.md (an agent whose system prompt IS the ruleset has no reason
to); and a probe skill with the plugin-qualified name `commit:commit-writer`
immediately produced the mandated one-line refusal on `claude-haiku-4-5`.

Fix: `agent: commit:commit-writer` in both skills (v0.3.1). With the qualified
name the eval sandbox loads the real subagent (Haiku, ~$0.02/run) and the
commit cases went green — then were red-proofed by inverting each Step 3 rule.

Standing lesson: **when a case refuses to respond to prose edits, suspect the
wiring before the model.** Three prose hardenings in a row with identical
behavior means the prose is not in context.

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
3. **Freeze the prose, then run.** Cases read plugin files live from this
   working tree at run time (verified: edits are picked up between runs with no
   reinstall). Editing mid-suite measures a moving target; break prose only
   deliberately, one red-proof at a time, and restore before the next case.
4. **Never let the answer reach the prompt.** Keep it in the scaffold. A case
   whose prompt contains its own answer passes with the plugin off too.
5. **Make every grader go red once before trusting its green.** A grader that
   has never failed is unproven. Two cases died permanently at this gate (see
   below) and the commit cases' first life ended here too.
6. **Prefer inverting prose over deleting it when red-proofing.** Deletion
   tests whether the rule does anything; inversion additionally proves the
   grader can detect the opposite behavior. `commit-no-blanket-staging`
   survived deletion AND inversion → the case measured baseline model
   behavior, not the prose (in hindsight: because the prose was never loaded —
   see the incident above).
7. **Be realistic about `max_turns`.** These skills legitimately go read the
   repo. `devil-review-rule-citation` needs 80; starving it scores
   `error_max_turns`, which is not a regression.

## Harness facts worth knowing

- `context.scaffold_script` is a **path** (`"./scaffold.sh"`), not inline bash.
  Inline gives a baffling `ENAMETOOLONG`.
- `plugins:` entries are **paths relative to the case directory**
  (`"../../plugins/commit"`), not plugin names.
- Plugin skills AND agents load live from the referenced path — but skill
  frontmatter `agent:` references must be **plugin-qualified**
  (`commit:commit-writer`). Bare names fall back silently to a generic agent.
- `file_exists` and the `files` target only see files created via **tools**. A
  file written by Bash — including anything git writes — grades as absent
  (verified by probe). To grade real on-disk state, use `regex` with
  `target: {source: file, path: ...}`, which does read the disk.
- A `regex` file target whose file does not exist **fails the grader** (grader
  throws → 0), it does not vacuously pass. Convenient: "the hook never ran"
  automatically reads as red.
- **The sandbox does not load a repo `CLAUDE.md`** into agent context, not even
  for the main agent (verified by probe: a CLAUDE.md instructing "append BANANA
  to every reply" had no effect). Any invariant that depends on CLAUDE.md being
  in context is untestable here.
- `tool_used` with only `max: 0` reads as "expected 1..0" and always fails. To
  assert a tool was not used, set **both** `min: 0` and `max: 0`.
- **Writes into `.claude/` are denied inside the sandbox**, even with
  `--allow-tools Write`. The protection is path-based, not tool-based: `Write`
  and a `cat >` heredoc through Bash both came back "permission denied" while
  the same run wrote to the cwd root fine. Put files the agent must create at
  the root — a root `CLAUDE.md` works. Costs a batch to learn, because the
  companion grader fails on a file the agent was never allowed to create.
- **Model-invocation is decided from the skill's frontmatter `description`
  alone.** Prose in the skill body cannot change whether a skill loads, only
  what it does once loaded. A case grading "did the skill fire" is therefore
  grading the description; inverting a `## Scope` section and expecting the
  trigger to move measures nothing (verified: Scope-only inversion left
  `human-voice-skips-agent-config` green 3/3, the same claim added to the
  description flipped it red 3/3).
- Headless `claude -p "/commit"` does not spawn the skill fork at all — the
  main loop improvises inline. Don't use `-p` to test fork-routed skills.

## Cases that were tried and dropped

Kept as a record so they are not re-proposed.

- **`commit-repo-format-override`** — asserted that a repo CLAUDE.md commit
  format overrides the Angular defaults (commit-writer.md Step 0). Dropped: the
  sandbox never loads CLAUDE.md, so the case could only ever lie red. Injecting
  the format via `append_system_prompt` would make it pass for the wrong reason
  — a system prompt demanding a format is obeyed whether or not Step 0 exists.
- **`commit-no-blanket-staging`** — asserted the "NEVER use `git add -A`" hard
  constraint via a pre-commit hook dumping the index. Dropped: green with the
  rule deleted AND inverted. At the time this read as "baseline model behavior
  masks the rule"; the bare-agent-name incident later explained it — the rule
  was never in context. Worth re-trying now that routing works, but only if
  the baseline-masking concern is addressed: the generic agent also stages
  selectively, so the case may still be unable to go red on prose alone.
