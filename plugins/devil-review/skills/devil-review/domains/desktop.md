# Domain checklist — Desktop app

**Authoritative loading rules live in `SKILL.md` Step 5.** This list is a human-readable summary of when the checklist applies. If the two drift, SKILL.md wins.

Load this checklist when the diff touches:
- **Electron**: `main.ts`/`main.js`, `preload.ts`/`preload.js`, references to `BrowserWindow`, `ipcMain`, `ipcRenderer`, `app.on`, `session`, `protocol.register*`
- **Tauri**: `src-tauri/**`, `tauri.conf.json`, `#[tauri::command]` exports, Rust commands bridged to JS
- **Native**: macOS Cocoa/AppKit (`.swift`, `.m`, `.mm` outside iOS), Windows Win32/WinUI (`.cs`, `.cpp` with MFC/WPF/WinRT), Linux Gtk/Qt (`.cpp`, `.py` with Gtk/Qt imports)
- packaging / signing configs: `electron-builder.yml`, `forge.config.*`, `.entitlements`, `Info.plist` for macOS apps, `.iss` (Inno Setup), `.wxs` (WiX), notarization scripts

Desktop apps cross the web↔OS boundary. Most bugs live at that boundary: **unsafe IPC**, **file system assumptions**, **single-instance violations**, **update safety**, and **OS-specific quirks** that only manifest on one platform.

---

## IPC security (Electron & Tauri)

- **Context isolation**: in Electron, is `contextIsolation: true`? If a preload script exposes something to the renderer, is it wrapped through `contextBridge` or attached directly to `window` (unsafe)?
- **Node integration**: is `nodeIntegration: false`? If true, a compromised renderer (XSS, malicious page) has full Node access.
- **Remote module**: still enabled anywhere? It's been deprecated and is a well-known escape hatch.
- **IPC surface**: every `ipcMain.handle(channel, ...)` is an RPC endpoint exposed to the renderer. Does the handler validate arguments? A renderer controlled by an attacker can pass anything.
- **Path arguments over IPC**: a renderer sending a file path to main process is passing untrusted input. Does main validate the path isn't `../../../etc/passwd`?
- **Tauri allowlist**: does the change unnecessarily enable a permissive command permission (`fs.all`, `shell.execute`)? Principle of least privilege.
- **Deep link / protocol handlers**: if the app registers a custom URL scheme, does it validate payloads from that scheme (they arrive over IPC from the OS, untrusted)?

---

## Window & state lifecycle

- **Multi-window coordination**: how many BrowserWindows can exist? Do they share state via a central store, or do they race? When window A writes state, does window B see it?
- **Window restoration**: on app restart, does the change restore window position, size, maximized state, monitor? What if the monitor is unplugged (position is off-screen)?
- **Multi-display**: has the user unplugged the monitor since last launch? Coordinates from last session may be off-screen. Clamp or reset.
- **Focus handling**: does the change assume window is focused? `document.hasFocus()` vs `BrowserWindow.isFocused()` can diverge.
- **Hidden-but-not-closed**: on macOS, closing the last window typically hides the app rather than quits it. Does the change handle `window.close()` vs `app.quit()` correctly?
- **Tray / menu bar apps**: does the change assume there's a visible window? An app running only in the tray has `BrowserWindow.getAllWindows().length === 0` sometimes.

---

## Auto-update safety

- **Signature verification**: does the update mechanism verify the signature of the downloaded binary before applying? An unsigned update path is a supply-chain risk.
- **Rollback**: can the user downgrade? Is there a record of previously-installed versions?
- **Update-in-use**: on Windows, a running executable cannot be replaced. Does the updater handle `ERROR_SHARING_VIOLATION` and defer until restart?
- **Partial downloads**: if the update download is interrupted, does the next attempt resume or restart from scratch?
- **Channel confusion**: stable vs beta channel — does the change accidentally ship beta builds to stable users, or vice versa?
- **Config migration**: does a new version read an old config file correctly? If the schema changed, is there a migration?

---

## File system

- **Path separators**: `\` on Windows, `/` elsewhere. Does the change use `path.join` / `Path::new` consistently?
- **Case sensitivity**: macOS and Windows are case-insensitive by default; Linux is case-sensitive. A file named `Config.json` and `config.json` collide on the first two but not the third.
- **Long paths** (Windows): paths over 260 characters fail without the `\\?\` prefix or registry opt-in.
- **Junction / symlink handling**: does the change follow symlinks into unexpected locations? This is a classic path-traversal vector.
- **Networked drives** (Windows, macOS SMB): file operations can fail with EACCES, EPERM, or hang. Are errors handled?
- **Watchers**: `fs.watch` / `FSEvents` / `ReadDirectoryChangesW` have platform quirks. A watcher leaking on macOS silently stops firing. Does the change add a watcher with proper cleanup?
- **Atomic writes**: renaming a temp file to the target path is atomic on POSIX *if same filesystem*. Across filesystems it falls back to copy+delete and can leave the temp file on failure.
- **User data directory**: `app.getPath('userData')`, `%APPDATA%`, `~/Library/Application Support`, `~/.config`. Does the change write outside these conventional locations?

---

## Packaging, signing, distribution

- **Code signing**: is the signing identity configured? On macOS, notarization is required for Gatekeeper-approved distribution outside the App Store. Unsigned builds get a scary warning.
- **Entitlements** (macOS): hardened runtime exceptions (`com.apple.security.cs.allow-jit`, `com.apple.security.cs.disable-library-validation`) — are they necessary or excess attack surface?
- **Windows Defender / SmartScreen**: unsigned or new-signed binaries get flagged. Is the build signed with a cert that has a reputation?
- **Auto-update endpoint** (URL): is it HTTPS? Is the host pinned?
- **Bundled binaries**: does the change include native binaries (ffmpeg, helper processes)? Are they signed with the same identity?
- **Installer behavior**: does the installer write to HKLM (admin) or HKCU (per-user)? Does it clean up on uninstall?

---

## Native API boundary

- **Error propagation**: errors crossing native↔JS (Electron native modules, Tauri commands) — are they typed and caught, or do they surface as opaque strings?
- **Async deadlocks**: blocking the main process on a renderer-initiated sync IPC call is a classic deadlock pattern.
- **Memory ownership**: in native modules, who frees what? Electron's worker `Buffer` passed across isolates has ownership rules.
- **Main process blocking**: the main process in Electron is a single thread. A long-running sync operation there freezes all windows.

---

## OS-specific quirks

- **macOS App Nap**: system may suspend the app when hidden. Does the change rely on timers running while hidden?
- **macOS Gatekeeper quarantine**: files downloaded by the app get the quarantine attribute. Does the change launch downloaded content without handling this?
- **Windows high DPI**: is the manifest set for per-monitor DPI awareness? Mixed-DPI setups break layout in non-aware apps.
- **Linux Wayland vs X11**: clipboard, screen capture, global shortcuts behave differently. Does the change assume X11?
- **Dock / taskbar state**: badge count, progress, jump lists — are they set on the right OS with the right API?

---

## Crash reporting & telemetry

- **PII in crash dumps**: does the crash report include file paths, environment variables, or user data? Are they scrubbed?
- **Opt-in**: is telemetry opt-in or opt-out? What's the default, and does it respect the user's choice?
- **Dump upload size**: large minidumps over metered connections — is there a gate?

---

## Output integration

`scenarios_considered` must include at least one **cross-platform** scenario and one **update/relaunch** scenario. Examples:

```
- user on Windows with a file path containing spaces and unicode
- second app instance launched via deep link while first is running
- auto-update downloaded, applied, user launches and config is an older schema
- macOS user closes all windows; tray icon still responds to menu actions
- file watcher running when user unmounts the watched volume
- main process IPC handler called with a malformed argument from compromised renderer
```
