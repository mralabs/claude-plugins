# Domain checklist — Mobile app

Load this checklist when the diff touches:
- **iOS native**: `.swift`, `.m`, `.mm`, `.h`, `*.xcodeproj/`, `Info.plist`, `Podfile`, `*.entitlements`
- **Android native**: `.kt`, `.kotlin`, `.java` under `android/` or `app/`, `AndroidManifest.xml`, `build.gradle` (app module), `proguard-rules.pro`
- **React Native**: `.tsx`/`.jsx`/`.js` in a project where `package.json` lists `react-native`, plus `ios/` and `android/` native shim dirs
- **Flutter**: `.dart`, `pubspec.yaml`, platform channels under `ios/` and `android/`
- **Capacitor / Cordova**: plugin code, `capacitor.config.*`, `config.xml`

Mobile bugs love the seams: **app lifecycle transitions**, **permission regressions**, **network state changes**, and **version skew across OS versions**. The same code that works on a fast wifi dev phone fails on a 3G bus with a backgrounded app and low battery.

---

## App lifecycle

- **Background → foreground**: does the change restore state correctly when the app returns from background? Are timers, subscriptions, or WebSocket connections re-established?
- **State restoration**: on iOS, does the change respect NSUserActivity / scene restoration? On Android, does it survive process death + activity recreation? Many bugs surface only when the OS kills the process for memory and restores it.
- **Suspend / resume**: does the change hold resources that should be released on background (camera, mic, location, socket)?
- **Cold vs warm start**: a feature that works on a warm start may fail on cold start because initialization order differs.
- **Memory warnings**: iOS sends `didReceiveMemoryWarning`; Android sends `onTrimMemory`. Does the change respond by releasing caches?
- **Process death without notification** (Android): the system can kill the app at any moment. Does persistent state survive, or does the user lose work?

---

## Permissions

- **Request timing**: does the change request a permission at the right moment (with clear context), or on app launch (high denial rate)?
- **Denial handling**: what happens if the user denies? Is there a graceful fallback or does the feature crash / silently fail?
- **Permission regression**: updates can revoke permissions the user granted. Does the change handle "was granted, now denied"?
- **Scoped permissions** (iOS 14+, Android 10+): limited photo library access, approximate vs precise location, one-time location. Does the code assume full access?
- **Runtime permission prompts** vs manifest-only: changing a manifest permission may require a new runtime prompt on some OS versions.
- **Privacy manifest** (iOS 17+): new required reason APIs need declaration. Does the change use an API without adding the reason?

---

## Network & connectivity

- **Offline handling**: what happens when there's no network? Queue and retry? Fail loudly? Show cached data? Silent failure is the worst option.
- **Connection transitions**: wifi → cell, cell → wifi, mid-request. Does the current request survive or does the retry storm begin?
- **Cell/metered networks**: is the change going to burn user data silently (background sync, preloading, analytics)?
- **Timeouts**: mobile networks have high and variable latency. Is the timeout tuned for mobile, or copied from a server-to-server client?
- **Certificate pinning**: does the app pin? Does the change break pinning (new host, rotated cert)?
- **TLS minimum version**: old OS versions can't negotiate newer TLS. What's the minSdkVersion / deployment target, and does the new backend support it?

---

## Battery & background

- **Wake locks** (Android): are they released? A leaked wake lock drains the battery overnight.
- **Background fetch** (iOS): is the change respecting system-imposed intervals, or does it assume it can poll freely?
- **WorkManager / BGTasks**: does the change use the OS scheduler properly, or does it rely on foreground services?
- **Location updates in background**: is there a need for always-on location? The reviewer should ask why.
- **Sensor usage**: GPS, accelerometer, camera all cost battery. Is the sensor released when not in use?

---

## Memory pressure

- **Large images**: does the change load a full-resolution image into memory, or downsample? Low-end devices OOM on 12MP images.
- **Caching strategy**: is there a cache with an upper bound? Unbounded caches crash on low-memory devices.
- **Bitmap recycling** (Android): native bitmap memory isn't tracked by GC on old API levels. Leaks add up.
- **View hierarchy depth**: deep view trees are slow and memory-hungry on Android.
- **WebView usage**: each WebView instance is expensive. Are they reused?

---

## Platform / OS version skew

- **Minimum OS version**: what is `iOS deployment target` / `minSdkVersion`? Does the new API call check for availability (`@available`, `Build.VERSION.SDK_INT`)?
- **New OS behaviors**: a new iOS / Android version may change defaults (background execution, notification permissions, storage scoping). Is the change tested on the latest OS?
- **Device variety** (Android especially): different manufacturers, screen sizes, OEM customizations. A feature working on Pixel may fail on Samsung.
- **Dark mode / dynamic type**: does the change respect user appearance settings?

---

## Push notifications

- **Token refresh**: the push token can change. Does the change re-register on refresh?
- **Background delivery**: silent notifications wake the app briefly. Is the handler async-safe and time-bounded?
- **Tap handling**: does tapping a notification route the user to the right screen, even on cold start?
- **Permission**: push requires user consent on iOS and Android 13+. Is the request moment reasonable?

---

## Storage & security

- **Keychain / Keystore**: are secrets stored there, not in plain SharedPreferences / UserDefaults?
- **Biometric unlock**: does the change gate sensitive actions behind biometric? Does it handle enrollment changes (new fingerprint invalidates old key)?
- **External storage** (Android): scoped storage rules. Can the change still write where it used to?
- **Backup exclusion**: is sensitive data excluded from iCloud / Google backups?

---

## Accessibility

- **Screen reader**: does the change add content that's announced to VoiceOver / TalkBack? Are labels meaningful?
- **Dynamic type**: does the UI scale with user font size preference?
- **Touch target size**: iOS HIG 44pt, Material 48dp minimum. Does the change add a small tap area?
- **Color contrast**: WCAG AA minimum. Does the change fail in dark mode or high-contrast?

---

## Output integration

`scenarios_considered` must include at least one **lifecycle transition** scenario and one **degraded state** scenario. Examples:

```
- app backgrounded mid-operation, user returns 10 minutes later
- permission revoked between app launches
- cold start on a low-memory device after process death
- request started on wifi, user walks out of range mid-request
- push notification tap on cold start routes to correct deep link
- user on iOS 15 (not latest) — are new API calls guarded?
```
