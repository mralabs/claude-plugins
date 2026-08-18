# human-voice

Ghostwriting style guard for Claude Code. Loaded **before** drafting any text a human will read as the user's own words — emails, PR titles/descriptions, issue and review comments, chat messages, proposals — so the output doesn't carry the telltale signs of AI writing. Text a machine consumes (prompts for other agents, tool input) is out of scope.

## What it does

The skill is a compact rule sheet distilled from [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (maintained by WikiProject AI Cleanup), plus tone/register rules specific to ghostwriting that the Wikipedia page (which targets article prose) doesn't cover:

- **Banned vocabulary** — the post-2023 AI-tell words ("delve", "tapestry", "leverage", ...) and their equivalents in whatever language the text is written.
- **Banned sentence patterns** — negative parallelism, copula avoidance, significance inflation, rule-of-three padding, participle-tail analysis, false ranges, authority tropes, filler constructions, formulaic wrap-ups.
- **Structure** — no bold-label bullets, no gratuitous headers/emoji, em-dash budget, varied sentence length.
- **Tone** — no sycophancy, no hedging stacks, match the register of the thread.
- **Facts** — no fabrication: everything in a message sent as the user must come from the user or the thread.

## How it differs from humanizer

[blader/humanizer](https://github.com/blader/humanizer) — prior art, built on the same Wikipedia source — is a **rewrite pass**: you give it AI-written text and it cleans it. human-voice is a **proactive guard**: it loads before drafting, so the text is written in the user's voice from the start. It also stays deliberately compact — one file, no scripts — and applies across languages, not just English.

## Usage

Two ways to use it:

**On demand** — like any skill, it's also a slash command. Invoke it with text (or a request) and the rules apply to what Claude writes next:

```
/human-voice reply to this email: <paste>
/human-voice rewrite this sentence so it doesn't sound AI-written: <sentence>
/human-voice draft a PR description for this branch
```

**Automatic** — install via the mralabs marketplace, then reference it from your global `CLAUDE.md`:

```markdown
Before drafting any text a HUMAN will read as my own words — emails, PR
titles/descriptions, issue/review comments, chat and forum messages, proposals —
invoke the `human-voice` skill and follow it.

The test is whether a person reads those exact words as mine, not whether the
text was sent under my name. A prompt telling an agent to open a PR is out of
scope; the PR description it will publish verbatim is in scope.

Out of scope: commit messages, instruction and configuration files written for
agents (CLAUDE.md, rules files, skill definitions), and other text written for a
machine to consume — prompts, tool input, anything an agent will rewrite before
a person sees it.
```

Phrase the rule around **who reads the words**, not around whose name they go out under. Text handed to another agent is technically sent in your name too, so a rule worded as "anything sent as me" pulls agent prompts into scope — and once the skill loads for a prompt, its em-dash budget and paragraph rules start shaping instructions that no human will ever read.

Keep the test above the exclusion list. A list read before the criterion gets mistaken for the criterion: "anything an agent will rewrite before a person sees it" is one example of machine-bound text, not the definition of it, and a `CLAUDE.md` is never rewritten yet still belongs out of scope.

The skill is also model-invocable: its description tells Claude to load it whenever it's about to ghostwrite in your name.

If you previously kept a personal copy at `~/.claude/skills/human-voice/`, delete it after installing the plugin — two skills with the same name shadow each other and the copies will drift.
