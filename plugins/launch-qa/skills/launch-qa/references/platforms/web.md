# Platform: web (SPA, SSR, PWA)

verified: 2026-10-12 (SPA, on one Vue + Firebase app) · SSR and PWA items: not yet used in a tour

Read this when the app, or one of its surfaces, runs in a browser.

## How to tour
- Drive a real browser (Playwright MCP or the user's Chrome). Use the primary viewport
  from the scope, plus a 360 px look on mobile.
- The local stack is usually a dev server plus a backend emulator or a compose stack.
  Prefer a production build (`build` + `preview`) for one pass at the end. Dev servers
  hide minification, chunking and service-worker behaviour.

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
