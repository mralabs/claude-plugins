# Platform: native WebView shell (Flutter, Capacitor, plain Android/iOS WebView)

verified: 2026-10-13 (one device tour on a Flutter + Android WebView app; bridges, back button, app links, splash and push permission held as written)

Read this when a native app wraps the web app. Tour the web app in the browser first;
the device tour covers only what the shell adds.

## What the shell adds (the device tour's list)
- Native bridges: sign-in (e.g. native Google Sign-In handing a token to the web),
  share sheet, push token handover, haptics. Each bridge has a failure path: cancelled,
  refused, older shell without the handler.
- Push: permission prompt timing, delivery in foreground/background/killed, and the tap
  that opens the right screen.
- Hardware back button: it pops web history first and leaves the app only at the root.
- App/universal links: a link opens the app on the right screen, cold and warm.
- Launch: splash → first paint without a blank or black frame.
- Keyboard: it does not cover the focused field or the submit button, and does not push
  other parts off screen (a sheet's title and amount while an in-app keypad stays). The
  IME action key (Enter, next, done) does something on every form.
- File downloads and exports (blob `<a download>`, a PDF library's save): without a
  download or share handler in the shell, the tap does nothing, with no error. Tap each
  export once on the device.
- Safe areas, notch, gesture bar, and rotation if supported.
- A newer web build in an older shell: features that need a newer bridge degrade.

## Device setup (Android)
- `adb` for install and logs. `adb reverse tcp:<port> tcp:<port>` lets the device reach
  the local dev server and emulators.
- Serve a production build of the web app (`build` + `preview`, reversed to the port the
  shell loads), never the dev server: a Vite-style dev server answers `sw.js` with the
  HTML fallback, so a service worker left by an earlier session never updates and the
  shell shows an old bundle. Relaunch two or three times after each rebuild. A screen
  with text that is not in the codebase: suspect a stale service worker first.
- Drive and inspect the WebView over Chrome DevTools Protocol (chrome://inspect, or CDP
  through the forwarded devtools socket).
- No CDP (release builds): `adb shell uiautomator dump` exposes the WebView's text and
  bounds. Drive the tour with `adb shell input tap` / `input text`, assert screens by
  text, capture with `adb exec-out screencap`. A switch's checked state is not carried
  in the dump; that is not an accessibility bug.
- Record each main push/pop once (`adb shell screenrecord`, frames extracted at 30 fps
  with ffmpeg) and look at the frames between skeleton and data. A flash of the empty
  state lasting a few frames never shows in a screenshot.
- After sharing to another app, back stays in that app's history: return to the shell
  with `adb shell am start -n <package>/<activity>`. Delete screenshots that caught the
  user's personal notifications.
- Agree a time with the user before starting. Undo every device setting you change, such
  as stay-awake, permissions you reset or debug flags.
- Before installing a build with a different signing key, ask whether the app's data on
  the device can be wiped; the install will require uninstalling first.

## Production exposure
A shell often loads only the production URL. If a debug build cannot point at the local
stack, follow the device-build rule in SKILL.md: list what will be written or sent,
use a test account, get explicit approval, and clean up.

## iOS
Needs macOS + Xcode (Simulator or device, Safari Web Inspector). Without a Mac, put iOS
out of scope in the log. Do not assume the Android results hold for WKWebView.
