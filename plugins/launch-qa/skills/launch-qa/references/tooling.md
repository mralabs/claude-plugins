# Tooling notes for the tours

verified: 2026-10-13

Platform-specific setup (devices, desktop builds) lives in `platforms/`.

## Browser
- Use Playwright MCP or the user's own Chrome (browser extension). Playwright MCP
  writes files only under its allowed roots, usually the directory it was started in. A
  path outside them fails with "outside allowed roots".
- Save screenshots in a gitignored folder under that root, e.g.
  `<repo>/.playwright-mcp/qa/<phase>-<screen>-<variant>.png`. Run
  `git check-ignore <path>` before the first save. Record the folder in the log's
  Environment section, and give screenshot paths relative to it.
- Full-page screenshots draw fixed bars (tab bar, FAB) in the middle of the page. That is
  a side effect of the capture, not a layout bug. Check against a viewport shot.
- Overflow sweep, per route and breakpoint: compare
  `document.documentElement.scrollWidth` with `innerWidth`, list elements whose right
  edge passes `innerWidth`, and leaf text whose right edge passes its nearest card or
  tile. Text with `overflow: visible` spills without clipping, so a
  `scrollWidth > clientWidth` check alone misses it.
- For a WebKit pass (iOS or macOS audience), use a Playwright WebKit project or a real
  Safari. Chromium results say nothing about WebKit.

## Data and console noise
- Resetting data while a page is open can leave stale subscriptions or caches. They
  produce spurious permission or not-found errors in the console. Reload the page before
  treating a console message as a finding.
- Record known environment noise once in the log's Environment section, e.g.
  bot-protection or analytics warnings on localhost. Filter it out afterwards.
- A user's saved settings (language, theme) may live on the server rather than in the
  browser. Switching them for a variant may mean writing the setting through the backend
  or the emulator's admin API, then reloading.
- Accounts created only in an auth emulator may lack the profile record the app writes on
  first sign-in, and backend fan-outs (notifications) can skip them. Sign each test
  account in once before asserting on anything sent to it.

## Running the full suite
- On a machine shared with other work, a full E2E run can be killed for low memory. Run
  it in batches (about 15 specs, each with a fresh backend/emulator stack), nothing else
  heavy in parallel (no test-running reviewers), and record which batches passed so a
  stopped run resumes instead of restarting.

## Waiting
- Verify a readiness probe (log line, health URL) once by hand before waiting on it in
  a loop. Keep long-running servers in the background.
