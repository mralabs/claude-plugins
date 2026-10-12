# QA log template

Use this as the board card's spec, or as `docs/qa/<yyyy-mm-dd>-launch-qa.md`. Session
entries are appended under **Log**. Findings stay in one table and are edited in place.
Write the log in the language the user works in.

```markdown
# Launch QA — <app>

Branch / worktree: <branch> — <path> · Status: in progress | QA done

## Scope
| Layer | Depth |
|---|---|
| <primary viewport, e.g. mobile 390×844> | Full: every screen and flow; themes; languages; states |
| <secondary, e.g. desktop 1440 + 1024> | Light: shell, each main screen once, dialogs, main flows |
| <device, e.g. Android WebView shell> | Native-only: sign-in bridge, push, back button, app links, splash, keyboard |
| Out of scope | <e.g. iOS (no Mac), production (smoke test lives in the launch checklist)> |

## Phases
- [ ] 1. Inventory, coverage map, QA seed
- [ ] 2a… <primary-platform tour, split by area>
- [ ] 3. <secondary platform tour>
- [ ] 4. <device tour, with the user>
- [ ] 5. Fixes (blocker + major, each with a failing test first)
- [ ] 6. Test gaps (★ flows first)

## Environment
<start command, ports, readiness signal, reset command, seed command, screenshot folder
(shot paths in Findings are relative to it), known console noise>

## Accounts
<email / role / purpose — local test accounts only, never real credentials>

## Coverage map — flows without E2E (★ = money, integrity, membership/permissions, deletion)
- ★ …
- …

## Tour order
- 2a: …

## Findings
| ID | Sev | Screen | Variant | Expected ↔ actual (steps in log entry) | Shot | Status |
|---|---|---|---|---|---|---|
| QA-01 | major | … | 390 dark <lang> | … | 2a-login-dark.png | open |

## Log
### <yyyy-mm-dd> — Phase <n>
<what was done, commits, observations not yet findings, next step>
```
