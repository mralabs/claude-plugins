# human-voice

Ghostwriting style guard for Claude Code. Loaded **before** drafting any text that will be sent or published as the user — emails, PR titles/descriptions, issue and review comments, chat messages, proposals — so the output doesn't carry the telltale signs of AI writing.

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

Install via the mralabs marketplace, then reference it from your global `CLAUDE.md`:

```markdown
Before drafting ANY text that will be sent or published as me — emails, PR
titles/descriptions, issue/review comments, chat messages, proposals — invoke
the `human-voice` skill and follow it.
```

The skill is also model-invocable: its description tells Claude to load it whenever it's about to ghostwrite in your name.

If you previously kept a personal copy at `~/.claude/skills/human-voice/`, delete it after installing the plugin — two skills with the same name shadow each other and the copies will drift.
