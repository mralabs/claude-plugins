# Platform: web (SPA, SSR, PWA)

verified: 2026-10-13 (SPA: mobile and desktop tours on one Vue + Firebase app) · SSR and PWA items: not yet used in a tour

Read this when the app, or one of its surfaces, runs in a browser.

## How to tour
- Drive a real browser (Playwright MCP or the user's Chrome). Use the primary viewport
  from the scope, plus a 360 px look on mobile.
- The local stack is usually a dev server plus a backend emulator or a compose stack.
  Prefer a production build (`build` + `preview`) for one pass at the end. Dev servers
  hide minification, chunking and service-worker behaviour.

## Languages
- Run the second-language pass with the browser locale set to the *other* language too.
  Grep for locale-less formatting (`toLocale*String(undefined`, `Intl.*(undefined`): it
  follows the browser's language, not the app's language switch.
- Grep the locale files for message syntax from another i18n library: ICU
  `{n, plural, …}` in vue-i18n fails to compile, vue-i18n `a | b` pipe plurals in an
  ICU-based library render literally. Parity tests pass and the message breaks only at
  render. Log each hit as a finding.

## Desktop viewports
- Run the overflow sweep (`references/tooling.md`) on every route at each breakpoint before the
  screen-by-screen pass; it finds the worst breaks in one go.
- A common cause: CSS grid `fr` tracks without `minmax(0, …)` widen on long unbreakable
  text. Grep for them, and try the fix in the page (override `grid-template-columns`)
  so the finding carries a confirmed fix.

## SPA
- Deep link and reload on every route, signed in and signed out. Client-side guards are
  not security: also check that the backend refuses what the UI hides.
- Back/forward through multi-step flows, and through pages whose record was just deleted.

## SSR (Nuxt, Next, SvelteKit, Astro islands…)
- Check the console for hydration mismatch warnings on first load of every route, in
  every language and theme: server and client must render the same markup.
- Server errors do not reach the browser console. Watch the dev server's own log during
  the tour.
- Open a page with JavaScript disabled once. Know what still renders and whether that is
  intended.
- Pages that call third-party services on the server (APIs, scraping): use recorded
  responses or fixtures for the tour, and never hammer a third party to reproduce a bug.
  Rate limits and terms of service apply to QA traffic too.

## PWA
- Install, then open offline: what loads, what says it is offline.
- Ship a new build while an old tab is open: does the update prompt or reload work,
  and does an old service worker serve stale chunks?
