# launch-qa

> *Test the whole app before launch, and get better at it every time.*

A phased, multi-session QA job for apps with a web UI: SPA, SSR, PWA, a native WebView
shell, or a Tauri/Electron desktop app. Run it before a launch or a major release.

**Status: 0.x, experimental.** Every phase has run once, on one project (a Vue SPA with
an Android WebView shell): mobile and desktop browser tours, a device tour, fixes and test
gaps. The SSR, PWA and Tauri/Electron items are specified but not yet proven. The
platform files say which of their items are verified.

## What it does

| Phase | Output |
|---|---|
| 1. Inventory | every route's flows, a map of which flows have E2E tests (risky untested ones starred), an edge-case seed |
| 2+. Tours | each screen walked in a real browser or device, per a checklist (layout, states, text, numbers, theme, console, navigation, forms, a11y), plus permission and concurrency probes |
| Fixes | blocker and major findings fixed, each with a failing test first and an independent review per fix group; the QA branch is kept in step with main |
| Test gaps | E2E tests for the starred flows |

State lives in a **QA log**: a board card or `docs/qa/<date>-launch-qa.md`. Any session
can resume the job from it with one line:

```
Do the next launch-QA phase
```

## Safety

- Seeds and tours run against a local stack. The skill checks this before writing data.
- Real e-mail, push, payments or SMS are never triggered without explicit approval.
- Apps that change the system (VPN, DNS, firewall) run only after agreement, ideally in
  a VM.
- Visual baselines are never updated without approval.

## It improves itself, with review

Every session ends with a **retro**: the skill asks which of its instructions misled,
what it had to discover on its own, which step was wasted, and which reference was
stale. General lessons are appended to a private inbox in your Claude config
directory, `~/.claude/field-notes/launch-qa.md` (or under `$CLAUDE_CONFIG_DIR`); project
specifics stay in the project's log. The inbox lives outside the plugin, so it survives
plugin updates and works the same from an installed plugin or a checkout.

The skill never edits its own instructions mid-job. An **evolve** pass, run on request in
a checkout of this repository, folds the open inbox notes into `SKILL.md` and
`references/`, or rejects them with a reason, and records each decision in
`skills/launch-qa/field-notes.md`. The pass follows this repository's rules: a branch,
review and a version bump.

## Files

```
skills/launch-qa/
  SKILL.md                      the workflow
  field-notes.md                public record of folded lessons (stack names only, no product data)
  references/
    screen-checklist.md         what to check on every screen
    qa-log-template.md          the QA log
    tooling.md                  browser tooling and console-noise notes
    platforms/
      web.md                    SPA, SSR, PWA
      webview-shell.md          Flutter / Capacitor / native WebView wrappers
      desktop-tauri.md          Tauri (and Electron) desktop apps
```
