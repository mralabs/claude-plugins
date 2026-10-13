---
name: launch-qa
description: Phased, multi-session pre-launch QA of a whole app with a web UI (SPA, SSR, PWA, native WebView shell, Tauri/Electron desktop) — flow inventory and E2E coverage map, edge-case seed data, hands-on browser and device tours, severity-ranked findings, test-first fixes. Use when the user asks to QA or test the entire app before a launch or release ("test every screen before launch", "act as a QA engineer", "lansman öncesi test", "release öncesi bütün ekranları test et"), or to continue one ("do the next QA phase", "QA'da sıradaki fazı yap"). Not for reviewing a diff, SEO/domain launch checks or legal texts.
---

# Launch QA

A phased QA job that survives across sessions. One session runs one or two phases; the
**QA log** carries everything between sessions: a board card's spec and notes, or
`docs/qa/<yyyy-mm-dd>-launch-qa.md` when there is no board. Never rely on conversation
memory, and never end a session with the log uncommitted or the card un-updated.

## Start of every session

1. Find the QA log, and re-read it right before every write: another session may have
   updated it in the meantime. If the user named a card or file, read it. Otherwise
   look for an in-progress QA card on the project board or a `docs/qa/*-launch-qa.md`. A file log
   may live on the QA branch only: check `git worktree list` and
   `git branch --list '*qa*'` too. Ignore logs marked "QA done"; if several are open,
   ask which one.
2. The log's header names the QA branch and worktree. Switch there before doing anything
   else.
3. No log yet → **Setup**, then Phase 1. Log exists → read it fully. Take the first
   unticked phase, resuming from the last screen recorded if it is half done. Say in one
   line what you are starting.

## Setup (first session only)

Infer before asking. Read the repo: router or navigation config, package manifest and
lockfile (which runner to use), test configs (unit, E2E, visual), i18n files, theme
tokens, native folders (Flutter, Capacitor, android/, ios/, src-tauri/, Electron main),
agent instruction files (CLAUDE.md and the like), and any existing seed or fixtures
script.

Name every surface the app ships (e.g. a desktop client and a web admin panel) and its
platform type, then read the matching file in `references/platforms/`:
- `web.md`: SPA, SSR or PWA in a browser
- `webview-shell.md`: a native app wrapping the web app
- `desktop-tauri.md`: a desktop binary with a web UI

A platform file whose header says "not yet used" is a starting point, not a rule. Check
each item against the project's current docs and code, and record what held in the retro.
No matching file? Tour with `web.md` as the base and write the platform's lessons in the
retro: the next project gets a new platform file from them.

Ask the user only what the repo cannot answer, in one question round:
- Which platforms matter and how deep (e.g. mobile web full, desktop light, Android shell
  on a device). Default when unsure: primary viewport full, the others light.
- Is there an iOS or macOS audience? If yes, WebKit gets its own pass. A Chromium-only
  tour does not cover Safari, WKWebView or a Tauri app on macOS.

Create a branch/worktree for the job and the QA log from
`references/qa-log-template.md`, with the branch and worktree in its header. On a board,
one phased card is enough; do not open a card per phase.

## Safety rules (every phase)

- **Local only.** Before writing any seed or test data, confirm the app and the script
  point at a local server or emulator: read the env file the dev server uses and the
  script's connection code. If anything points at production, stop and ask.
- No real side effects: no e-mail to real addresses, push to real devices, payments or
  SMS. Use emulator inboxes and test accounts instead. Use the user's own device only
  while they are present.
- **Device builds:** point them at the local stack (e.g. `adb reverse` + a dev URL). If
  the shell can only load production, list exactly what will be written or sent there,
  use a dedicated test account, get the user's explicit go-ahead first, and clean up
  afterwards.
- **Apps that change the system** (VPN, DNS, proxy, firewall, services, drivers): agree
  with the user before running them, prefer a VM, and know how to restore the setting.
- **Third parties:** tours that make the server call outside APIs or scrape sites use
  fixtures or recorded responses. Never generate load on a third party to reproduce a bug.
- Never update visual baselines without the user's approval. Never delete data outside
  the local environment.

## Phase 1: inventory, coverage map, QA data

1. **Flow inventory.** For every route or screen (desktop apps may have no router; use
   their windows, views and menus), list what a user can do there: buttons,
   dialogs/sheets, forms, destructive actions, role- or ownership-dependent states, and
   empty/loading/error/offline states. Add global entry points (tab bar, FAB, sidebar,
   command palette, notifications, onboarding and consent dialogs). Delegate this sweep
   to a read-only subagent and keep only its condensed list.
2. **Coverage map.** Grep E2E test titles per spec file and match flows to them; confirm
   ambiguous hits by reading the test body. Mark flows with no test. Star (★) the ones
   touching money, data integrity, membership or permissions, and deletion. Note what is
   untested as a class too: second language, dark theme, desktop, other browser engines.
   No E2E setup at all? Say so in the log and ask in the session report whether the gap
   phase should add one or only list the gaps.
3. **QA seed.** Extend the existing seed or write one, behind a flag so the normal seed
   is unchanged. Cover:
   - text at each field's max length, built from (or asserted against) the app's own
     length constants: a string a few characters short never tests the limit
   - very large and very small numbers, and every decimal/locale rule the app supports
   - one account per role
   - an empty account
   - an account stuck mid-onboarding (unverified, consent not given)
   - archived, closed and deleted records
   - date-based schedules, if the app has them: starts on the 29th–31st, spans over
     February and a leap year
   Write data the way the app writes it, so it passes the backend's own rules and
   validation. A seed that bypasses those rules creates bugs that are not real. Create
   one record of each type through the UI and compare everything it wrote (side
   records, subcollections, derived fields) with a seeded one before the tour.
   Reference data that background jobs write in production (rates, generated
   schedules) goes in as a fixture; reuse the E2E suite's fixture shape if there is
   one. Leave out data that needs live external services; create it through the UI
   during the tour. Run the seed and open the app to confirm the data renders.
   Run the existing seed first, before extending it: a pre-existing break is then
   told apart from the new data. A seed that fails against the current rules is itself
   a finding. Seeded accounts record every consent and onboarding step the app gates
   on, except the one account kept to test that gate.
4. **Write the Phase 1 output to the log:** how to start the environment (commands,
   ports, readiness signal, reset command), accounts (local test accounts only, never
   real credentials), the coverage map with ★ first, and the tour split into
   sub-phases with the screens in order.

## Phase 2+: tours (primary platform first, then the others)

Split by area (auth and home, then each feature) into sub-phases. Per screen, run
`references/screen-checklist.md`. Then go beyond the happy path:
- Open owner-only or other users' pages by URL as a member, a stranger and signed out.
- Do the same action from two accounts or tabs at once.
- Go offline in the middle of a save.
- Double-click submit, and use back during a multi-step flow.
- After a destructive or admin action, check its effect from the affected side: sign in
  as that user, open the deleted record's URL. A success toast proves nothing.

Tours only log findings; do not fix during a tour. The exception is a blocker that stops
the tour itself: log it, fix it test-first, note the commit, and carry on.

Tooling notes (screenshot locations, overflow sweep, stale-state noise, switching saved
settings):
`references/tooling.md`. Device and desktop setup: the platform file.

## Findings

Before logging a finding:
1. Reproduce it twice, from a fresh page load.
2. Rule out environment noise and seed artefacts.
3. Check the board or issues for a known report.

Log it in the log's findings table: `QA-NN`, severity, screen/route, viewport + theme +
language, expected ↔ actual (steps in the session entry), screenshot path, status
(open / fixed <sha> / deferred <reason>).

Severity:
- **Blocker:** data loss, a wrong amount or total, a flow that cannot be completed, or a
  security or permission hole. Fixed before launch.
- **Major:** the flow completes but is clearly broken (overflow hiding content, wrong or
  missing text, a broken layout on a main screen). Fixed before launch.
- **Minor:** cosmetic or edge case. Listed now, fixed after launch.

A finding that is large and independent (its own context, more than a small fix) gets its
own card or issue. The QA log keeps only a reference to it. A product decision (e.g. should
an archived item still count in totals?) is logged as **needs-decision** and put to the
user in the session report, not decided silently.

## Fix and gap phases

- **Fixes:** one finding, one failing test first (unit or E2E), then the fix, then green.
  Follow the project's commit and review rules.
- **Review:** an independent review after each fix group. Tell the reviewer to grep every
  writer and caller of what changed (rules, shared helpers, stored fields), not only to
  read the diff.
- **Delegated fixes:** the QA log describes symptoms; a fix agent checks every claim about
  the code (paths, formats, how values are stored) against the code before acting. One
  writing agent per worktree at a time, or one worktree each; reviewers run read-only in
  parallel. Commit with a pathspec (`git commit -- <paths>`) and check
  `git show --stat HEAD`. Pick model and effort per task by risk (money math and
  security rules: strongest; copy, layout and their reviews: mid; running a suite:
  small), and name the choice when launching. Run each fix or gap phase in a session
  of its own, so the coordinator's context stays small.
- **Keep the QA branch in step with main.** Fixes pile up on the QA branch while other
  work merges into main; where both touch the same files they diverge. At the start of
  each fix or gap session, merge main into the QA branch. Before work started from main
  touches files the QA branch changed, offer to merge the QA branch into main first,
  under the project's merge rules.
- **Gaps:** E2E tests for the ★ flows in the coverage map first, then the rest. The map
  is stale by now: before writing a gap test, re-grep the current specs for the flow,
  read the matching test body, and record "covered by <spec › title>" or the new test in
  the log. A test that asserts on text with an open copy finding gets a note next to that
  finding, so the fix updates both. At the end, every suite is green: unit, E2E, and any
  backend/security-rule or contract tests (full-suite runs: `references/tooling.md`).

## End of every session

1. Append a dated session entry to the log. Tick finished phases; leave an unfinished
   one unticked and record the last screen covered. Add the findings and what is next.
   Commit the log file, or save the card.
2. Stop the servers you started. The next session should find the ports free.
3. Report to the user in a few lines:
   - phases done
   - findings by severity, naming any blocker or needs-decision
   - commits
   - what the next session starts with
4. Context budget: if more than half the context is used, do not start the next
   sub-phase. End here and tell the user to open a new session with one line, e.g.
   "Do the next launch-QA phase".
5. **Retro** (below) before the report goes out.

## Retro: the skill questions itself

At the end of every session, answer these about **this skill**, not the app:
1. Which instruction did I not follow, or override? Was the instruction wrong?
2. What did I have to discover that the skill or a platform file should have told me?
3. Which step cost time and found nothing?
4. Which reference item was stale, and which "not yet used" item held up?

Sort each answer:
- **Project-specific** (ports, accounts, quirks of this codebase): into the QA log's
  Environment section, or the project's own memory.
- **General** (true for any project with this stack or platform): append an entry to the
  user's field-notes inbox, `$CLAUDE_CONFIG_DIR/field-notes/launch-qa.md` (default
  `~/.claude/field-notes/launch-qa.md`), using the format and rules at the top of
  `field-notes.md` next to this file. Create the inbox with that header if it is missing.
  Never write inside this skill's own directory: an installed plugin is replaced on every
  update, and the repo copy of `field-notes.md` is the public record that only evolve
  writes. The inbox is the user's own file; still no credentials or personal data in it.

Never edit SKILL.md or `references/` during a QA session. A changing instruction set
mid-job makes the phases inconsistent. Changes reach them only through **evolve**.

Mention the number of new field notes in the session report, one line.

## Evolve: folding field notes into the skill

Run only when the user asks for it ("evolve launch-qa", "launch-qa'yı güncelle"). Also
suggest it in a session report once five or more notes are open in the inbox.
1. Work in the skill's source repository, on a branch, under that repository's rules
   (version bump, changelog or README, review).
2. For each open note in the inbox (`$CLAUDE_CONFIG_DIR/field-notes/launch-qa.md`) and in
   the repo's `field-notes.md`:
   - fold it into the right section of SKILL.md or a reference file,
   - or reject it with a one-line reason (too project-specific, contradicted by another
     project, already covered),
   - or keep it open, because one project is not enough evidence for a general rule.
   Re-date the `verified:` header of any reference file you confirmed or changed.
3. Copy every inbox note you decided on into the repo's `field-notes.md`, rewritten to
   its public rules (stack, never product), marked `folded <version>` or
   `rejected: <reason>`; mark the inbox entry the same way. Never delete a note in
   either file.
4. Keep SKILL.md lean. Platform or stack detail goes to `references/platforms/`. A
   stack seen on two projects earns its own platform file.

## Done when

- No open blocker or major findings.
- Minor findings are moved to a post-launch card or issue.
- Every ★ flow has an E2E test (or, by the user's decision, is listed as a known gap), and all suites are green.
- The QA log header (and the launch checklist, if there is one) records "QA done".
