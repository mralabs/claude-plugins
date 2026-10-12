# Platform: native WebView shell (Flutter, Capacitor, plain Android/iOS WebView)

verified: 2026-10-12 (planned from one Flutter + Android WebView app; the device tour has not run under this skill yet)

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
- Keyboard: it does not cover the focused field or the submit button.
- Safe areas, notch, gesture bar, and rotation if supported.
- A newer web build in an older shell: features that need a newer bridge degrade.

## Device setup (Android)
- `adb` for install and logs. `adb reverse tcp:<port> tcp:<port>` lets the device reach
  the local dev server and emulators.
- Drive and inspect the WebView over Chrome DevTools Protocol (chrome://inspect, or CDP
  through the forwarded devtools socket).
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
