# Platform: desktop app with a web UI (Tauri; Electron where noted)

verified: not yet used in a tour — every item below is a starting point to confirm on the first project, then re-date this header

Read this when the app is a desktop binary whose UI is a web frontend.

## Two ways to tour, use both
1. **Frontend in a browser.** Run the frontend dev server alone with the native layer
   mocked. Tauri v2 ships IPC mocks in `@tauri-apps/api/mocks` (`mockIPC`, `mockWindows`).
   This is fast and fits Playwright, but it proves nothing about the native side.
2. **The real app.** Run the debug build and open devtools (right-click → Inspect in
   debug builds). For scripted runs, Tauri's WebDriver support (`tauri-driver`) has
   historically covered Linux and Windows but not macOS: check the current docs before
   relying on it.

Tour each screen in mode 1. Then, in mode 2, go through everything that crosses the IPC
boundary: commands, events, file system, shell, notifications, updater.

## The webview differs per OS
Tauri uses the system webview: WebView2 (Windows, Chromium), WKWebView (macOS, WebKit)
and WebKitGTK (Linux). A layout or API that works on one can break on another. The
scope must name which OSes are tested. Electron bundles Chromium, so the engine stays
the same across OSes; what still varies is native integration.

## What the desktop adds
- Window: minimum size, resize, maximize, multiple monitors and HiDPI scaling, and
  restore of size and position on the next launch.
- OS integration: tray icon and menu, app menu, notifications, autostart, deep links
  / custom URL scheme, file associations.
- Theme follows the OS setting, live.
- Permissions (Tauri capabilities): a command the UI calls but the capability set denies
  fails only at runtime. Exercise every IPC command once in the real app.
- Sleep/resume and network change while the app is open.
- Updater: from an older version to the current one; a failed or cancelled update.
- Install, first run, uninstall: what is left behind (config, caches, services).

## Safety: apps that change the system
VPN clients, DNS or proxy settings, firewall rules, services and drivers change the
machine the tour runs on. Agree with the user before running them, prefer a VM or a
spare machine, and make sure the user knows how to restore the setting (disconnect,
reset the DNS or proxy) before you start.
