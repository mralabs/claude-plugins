---
name: human-voice
description: Style rules for any text written in the user's name or voice — emails, PR titles/descriptions, issue comments, Slack/Discord messages, cover letters, proposals, replies sent from the user's accounts. Load BEFORE drafting such text. Not for text a machine consumes — prompts for other agents, tool input, anything rewritten before a person sees it. Goal: avoid the telltale signs of AI writing (distilled from Wikipedia:Signs of AI writing) so the output reads like the user wrote it.
---

# Human Voice

When ghostwriting for the user, the output must not read as AI-generated. These rules override default writing habits, and they apply in whatever language the text is written — banned words and patterns include their natural equivalents in that language.

## Banned vocabulary and phrasing

Never use the AI-tell words unless quoting someone:
delve, tapestry, testament, pivotal, crucial, vital, intricate, interplay, landscape (figurative), meticulous, boasts, garner, underscore, bolster, foster, showcase, vibrant, groundbreaking, renowned, seamless, robust (figurative), leverage (as verb), journey (figurative), elevate, empower, unlock, "valuable insights", "diverse array", "rich cultural heritage", "in the heart of", "nestled".

Banned sentence patterns:
- Negative parallelism: "It's not just X, it's Y", "not only ... but also", "It's not about X, it's about Y".
- Copula avoidance: "serves as", "stands as", "functions as", "represents a" → just write "is".
- Significance inflation: "plays a vital role", "marks a key turning point", "sets the stage", "reflects a broader shift", "leaves an indelible mark".
- Rule of three padding: adjective/phrase triads ("fast, reliable, and scalable") used as filler.
- Participle-tail analysis: sentences ending in ", highlighting/underscoring/ensuring/reflecting ...".
- Vague authority: "experts argue", "industry reports", "observers note" — name the source or cut it.
- Authority tropes: "at its core", "the real question is", "what really matters", "fundamentally".
- False ranges: "from X to Y" where the endpoints don't form a real scale.
- Aphorism formulas: "X is the Y of Z" — make the concrete claim instead.
- Fake-candid openers: "Honestly?", "Let's be real", "Here's the thing".
- Filler constructions: "in order to" → "to", "due to the fact that" → "because", "it is worth noting that" → cut.
- Formulaic wrap-ups: "In conclusion", "Overall", "Moving forward", "Despite these challenges, the future looks...".
- Sentence-starting "Additionally," / "Moreover," / "Furthermore," chains.

## Structure and formatting

- No headers, bullet lists, or bold in emails and chat messages unless the user's own past style uses them. Default is plain paragraphs.
- No bullet items shaped as "**Bold label:** explanation" — that's the most recognizable AI list format.
- Em dashes: at most one per message, ideally zero. Use commas, periods, or parentheses.
- No emoji unless the user asked or the thread already uses them.
- No title case headings; sentence case if a heading is truly needed.
- Don't restate the request back ("As you mentioned...") or summarize what you just wrote at the end.
- Vary sentence length; allow short ones. Uniform medium-length sentences are a tell — but so are runs of clipped fragments faking drama.
- Don't chase synonyms to avoid repeating a word; repeating the natural word is human.

## Tone

- No sycophancy or throat-clearing: "I hope this finds you well", "Thank you for reaching out", "Great question" — cut, get to the point.
- No hedging stacks ("it may perhaps be possible that"); commit or say plainly you're unsure.
- No pedagogical framing ("In this message, we will..."), no "I hope this helps" closers.
- Plain, direct, slightly informal unless the context demands formality. Small imperfections are fine; do not sand every edge.
- Match the register of the thread/repo: read the user's earlier messages or existing PR descriptions and mirror their length, greeting style, and sign-off.

## Facts

Every fact, name, number, date, and commitment must come from the user, the thread, or the material being replied to. Never invent detail to fill a gap — compress, or ask the user. A plausible fabrication sent in the user's name is worse than any style slip.

## Scope

The test is whether a **person will read these exact words as the user's own** — not whether the text goes out under the user's name.

In scope: Gmail drafts, `gh pr create` bodies, PR review comments, issue replies, forum/chat posts, proposals, blog posts, presentation copy.

Out of scope: code, commit message conventions, technical docs governed by a project's own style, agent instruction and configuration files (CLAUDE.md, rules files, skill definitions), and other text written for a machine to consume — prompts, tool input, anything an agent will rewrite before a person sees it.

The boundary runs between those two, not around who sends the text. A prompt telling an agent to open a PR is out of scope; the PR body that agent will publish verbatim is in scope. When a single message carries both, apply the rules to the part that gets published.
