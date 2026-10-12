# Field notes — inbox for lessons from real QA runs

Every session ends with a retro (SKILL.md, "Retro"). Lessons that would help on any
project are appended here. They do not change the skill by themselves. An "evolve" pass
folds them into SKILL.md or `references/` with review and a version bump, then marks them
`folded <version>` here. Entries are never deleted, so the reasoning stays traceable.

Rules for an entry:
- Describe the stack, never the product. Write "Vue SPA + Firestore emulator", not the
  app's name. No URLs, paths inside a project, data or credentials: this file is public.
- One lesson per entry, phrased as what the skill should say or do differently.
- Say which kind it is:
  - **wrong:** an instruction misled
  - **missing:** something had to be discovered that the skill should have said
  - **unused:** a step cost time and found nothing
  - **stale:** a tool or platform changed
  - **confirmed:** an unverified reference item held up; re-date its header

Format:

```
## <yyyy-mm-dd> · <stack> · <phase> · <kind> · open
<the lesson, 1–4 lines> → <proposed change: file + section>
```

---

## 2026-10-12 · Vue SPA + Firestore emulator · Phase 1 · missing · folded 0.1.0
A project's existing seed script had silently broken after a security-rule tightening
(field allowlist). Running the seed was the first finding of the QA. → SKILL.md Phase 1
step 3 already says a failing seed is a finding; also say to run the existing seed
*before* extending it, so a pre-existing break is separated from the new data.

## 2026-10-12 · Vue SPA + Firestore emulator · Phase 1 · missing · folded 0.1.0
Seeded accounts opened on a terms re-accept dialog on every sign-in, because the seed did
not record consent. → Phase 1 seed list: seed accounts record every consent/onboarding
step the app gates on, except the one account kept for that gate.

## 2026-10-12 · any · Phase 2 · missing · folded 0.1.0
A parallel session ran the next phase while another session was still editing the log;
a note claimed the wrong "next phase". → Start of session: re-read the log right before
writing to it, not only at the start.

## 2026-10-12 · any app with two-party approval · Phase 2 · missing · open
A record the other party had acknowledged could be edited by its owner afterwards; the
status stayed "acknowledged" and nobody was told. The checklist never prompts this. Add:
"for records one party writes and another approves, edit and delete after approval and
check the status resets, the other party is notified and history shows it."
→ references/screen-checklist.md, States

## 2026-10-12 · any app storing derived money values · Phase 2 · missing · open
Values computed at write time and stored on the record (balance after payment, interest
so far) were wrong at creation and never recomputed after an edit. The tour only caught it
by comparing the stored column with the live total. Add: "after editing or deleting a
money record, compare every stored derived number on screen with a fresh computation."
→ references/screen-checklist.md, Numbers

## 2026-10-12 · Vue SPA + Firestore emulator · Phase 1 · missing · open
Three seed artefacts cost tour time: side documents the app writes (an invite-token
registry, a generated schedule subcollection) were missing, and a derived field was
hard-coded instead of derived from a date. Add to QA seed: "create one record of each type
through the UI and diff its documents (and subcollections) with a seeded one before the
tour." → SKILL.md Phase 1, QA seed

## 2026-10-12 · any app with job-written reference data · Phase 1 · missing · open
Exchange/inflation rates are written by a scheduled job in production, so the emulator
had none and every indexed flow showed "no data". It cannot be created through the UI.
The E2E suite already had a fixture of the document's shape. Add: "reference data written
by background jobs goes into the QA seed as a fixture; reuse the E2E fixture's shape."
→ SKILL.md Phase 1, QA seed

## 2026-10-12 · Vue SPA + vue-i18n · Phase 2 · missing · open
A locale message used ICU plural syntax, which vue-i18n cannot compile; it failed only at
render, dropping a table cell. Locale parity tests passed. Add to Phase 1: "grep locale
files for message syntax the i18n library does not support (ICU `{n, plural,` in
vue-i18n, pipes in ICU libraries) and log hits as findings."
→ references/platforms/web.md, or SKILL.md Phase 1

## 2026-10-12 · any app with user-visible names · Phase 2 · missing · open
A display name made only of spaces saved fine (the button checked emptiness without
trimming, the backend rule checked length only), and the app then rendered that user as
"Deleted account" to everyone. The checklist names length limits but not blank input.
→ references/screen-checklist.md, Forms: "whitespace-only and leading/trailing-space
input on every required text field; check how the saved value renders to *other* users."

## 2026-10-12 · any app with admin or destructive actions · Phase 2 · missing · open
An admin "Delete user" said "Success" but removed only the profile document; the user
signed straight back in with groups and balances intact. Only signing in as the affected
account showed it. → SKILL.md Phase 2 "beyond the happy path": "after a destructive or
admin action, verify its effect from the affected side (sign in as that user, open the
deleted record's URL), not from the success toast."

## 2026-10-12 · SPA with an in-app language switch · Phase 2 · missing · open
One screen formatted a month with `toLocaleDateString(undefined, …)`, so it followed the
browser's language, not the app's: "October 2026" on a Turkish UI. A tour whose browser
locale matches the app language never sees it. → references/platforms/web.md: "run the
second-language pass with the browser locale set to the *other* language, and grep for
locale-less `toLocale*String(undefined` / `Intl.*(undefined` calls."

## 2026-10-12 · SPA with a CSS-grid desktop layout · Phase 3 · missing · open
On desktop the worst break (a two-column page wider than the viewport, money column
off-screen at the 1024 breakpoint) came from `fr` grid columns without `minmax(0, …)`:
long unbreakable text in the seed widens the track. A per-route sweep at each breakpoint
measuring `document.documentElement.scrollWidth` and elements past `innerWidth` found it
in one pass; overriding `grid-template-columns` in the page confirmed the fix before
logging. → references/platforms/web.md (desktop pass): run that sweep first, grep for
`fr` grids without `minmax(0,`, and try the fix in-page so the finding carries it.

## 2026-10-12 · any SPA · Phase 3 · missing · open
The automated overflow check (leaf text with `scrollWidth > clientWidth` and clipped
overflow) missed amounts spilling out of fixed-width stat tiles, because that text has
`overflow: visible`; the user spotted it in a screenshot. → references/screen-checklist.md
or tooling.md: also flag leaf text whose right edge passes its nearest card/tile
container, and look at every screenshot rather than trusting the detector.

## 2026-10-12 · Flutter WebView shell + Vite PWA · Phase 4 · missing · open
Pointed at a Vite dev server, the shell kept showing a weeks-old bundle: the dev server
answers `sw.js` with the HTML fallback, so the service worker left from an earlier device
session never updates. It looked like a real regression until the strings were grepped.
→ references/platforms/webview-shell.md (device setup): serve a production build of the
web app (`vite build` + `vite preview`, reversed to the shell's port) and relaunch two or
three times after each rebuild; if a screen shows text missing from the codebase, suspect
a stale service worker first.

## 2026-10-12 · Android WebView shell · Phase 4 · missing · open
Every file download in the shell (blob `<a download>`, a PDF library's `save()`) did
nothing at all: no file, no toast, no error. Browser and desktop tours had passed them.
It became a launch blocker. → webview-shell.md "What the shell adds": add file
downloads/exports to the list; check the shell has a download or share handler and tap
each export once on the device.

## 2026-10-12 · Android WebView shell · Phase 4 · missing · open
A release build has no CDP socket, but `uiautomator dump` exposed the WebView's text and
bounds, enough to drive the whole tour with `input tap`/`input text` and assert screens
by text. (Switch `checked` state is not carried; don't log it as an a11y bug.) → webview-
shell.md device setup: use uiautomator + screencap when CDP isn't available.

## 2026-10-12 · any WebView shell or mobile SPA · Phase 4 · missing · open
A detail page flashed its empty state ("no items yet", totals 0) for 1-4 frames mid push
transition. No screenshot ever catches it; `adb shell screenrecord` + ffmpeg at 30 fps,
tiled around the tap, found it in the first recording. → screen-checklist.md (loading
states) or webview-shell.md: record each main push/pop once and look at the frames
between the skeleton and the data.

## 2026-10-12 · Android WebView shell · Phase 4 · missing · open
The keyboard item ("does not cover the focused field") passed, yet the problems were
next to it: in a bottom sheet the keyboard pushed the amount and title off the top while
an in-app keypad stayed on screen, and the IME's Enter/next key did nothing on
single-field forms. → webview-shell.md "Keyboard": also check what else the keyboard
pushes off screen, and what the IME action key does.

## 2026-10-12 · Android WebView shell · Phase 4 · confirmed · open
The device list held up on its first real run: bridge cancel path, back button (sheet →
page → history root), app links cold+signed-out and warm, splash → first paint, push
permission grant/deny/settings round trip. Also: leaving to another app (share to a
messenger) lands back in that app's own history; return with `am start`, and delete
screenshots that caught the user's personal notifications. → re-date the webview-shell.md
header; add the return/privacy note to device setup.

## 2026-10-12 · any repo, fixes delegated to subagents · Phase 5 · missing · open
Two fix agents committing in the same worktree share one git index: one agent's staged
test hunks landed in the other's commit, leaving an intermediate commit whose rules
suite was red. → SKILL.md "Fix and gap phases": one writing agent per worktree at a
time (or one worktree each); reviewers run read-only in parallel; commits use a
pathspec (`git commit -- <paths>`) and are checked with `git show --stat HEAD`.

## 2026-10-12 · any app · Phase 5 · missing · open
An independent review after each fix group found real problems in about half the groups:
a rule fix that still let one party approve their own change, a stored display name that
survived account deletion, a validation tightening that broke sign-up through another
writer, a new mobile layout that broke an existing E2E. → "Fix and gap phases": require
an independent review per fix group, and tell the reviewer to grep every writer/caller of
what changed (rules, shared helpers, stored fields), not only the diff.

## 2026-10-12 · Vue SPA + Firestore emulator, dev machine shared with other work · Phase 5 · missing · open
The full E2E suite was stopped twice by the host for low memory while other sessions and
browsers ran. Batches of ~15 specs, each with a fresh emulator stack, finished; review
agents running tests at the same time made it worse. → references/tooling.md: run the
final suite in batches, nothing else heavy in parallel, and record which batches passed
so a stopped run resumes instead of restarting.

## 2026-10-12 · any app with date-based schedules · Phase 1 · missing · open
A month-end overflow (start on the 31st + 1 month → March, February dropped from the
schedule and the interest ledger) went unseen through every tour; a reviewer of the seed
script spotted it in the shared date helper. → Phase 1 seed list: include records
starting on the 29th–31st and spanning February (and a leap year), and check their
schedules and per-month figures during the tour.

## 2026-10-12 · any · Phase 5 · wrong · open
The coordinator's fix brief carried a fact from the QA log that was wrong about the code
("days are stored at noon UTC"; the app stores local midnight). The fix agent caught it by
reading the code. → "Fix and gap phases": the QA log describes symptoms; a fix agent
verifies every claim about code (paths, lines, formats) against the code before acting.

## 2026-10-12 · any repo, fixes delegated to subagents · Phase 5 · missing · open
A fix phase run with every fix and review agent on the strongest model used about half
of a subscription's quota in one session. Fix groups differ: rules and money math need
the strongest model at high effort; copy, layout and their reviews do not; running a
suite and reporting is mechanical. → "Fix and gap phases": the coordinator picks model
and effort per delegated task by risk, says the choice when launching, and starts a new
session per phase so its own re-read context stays small.

## 2026-10-12 · Vue SPA + Firestore emulator · Phase 6 · missing · open
The coverage map written in Phase 1 was stale by the gap phase: the fix phase had added
tests for several ★ flows, and one map entry was misleading (a "payment delete" spec
covered a different kind of payment). → "Fix and gap phases", Gaps: before writing a gap
test, re-grep the current specs for that flow, read the matching test body, and record
"covered by <spec › title>" or the new test in the log.

## 2026-10-12 · any · Phase 6 · missing · open
The QA seed's "max length" strings were 1–5 characters short of the real limits, so the
tour never tested the limit itself. → Phase 1 seed list: build boundary strings from the
app's own length constants (or assert their length), and in the gap phase move them into
a shared E2E helper with a unit check that each one is exactly at its limit.

## 2026-10-12 · Firestore + notification fan-out · Phase 6 · missing · open
A new E2E test saw no notification for a freshly created account: the fan-out skipped
recipients without a profile document, which only a first sign-in creates. Not an app
bug. → references/tooling.md: accounts created only in the auth emulator may lack the
profile doc the backend reads; sign each test account in once before asserting on
anything sent to it.

## 2026-10-12 · any · Phase 6 · missing · open
A locale smoke set pins today's translated strings, including ones already logged as
minor copy findings; fixing those findings later turns the smoke set red. → Gaps: when a
smoke test asserts on text that has an open copy finding, note it in the log next to the
finding so the fix updates both.
