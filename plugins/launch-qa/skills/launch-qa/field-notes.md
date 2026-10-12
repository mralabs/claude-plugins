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
