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
