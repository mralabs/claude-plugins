# Per-screen checklist

Run the full checklist once per screen in the primary variant (primary viewport, default
theme and language). In the other variants the scope names (second theme, other
languages, a 360 px look) check only Layout (dark theme included) and Text.

## Layout
- Nothing overflows or gets clipped at max-length text, 7+ digit amounts, long names.
- Truncation keeps the text identifiable. A row reduced to "Summer t…" when every row
  starts the same way is a finding.
- Fixed bars (top, tab, FAB) never cover content or the last list item; safe areas hold.
- The on-screen keyboard does not hide the focused field or the submit button (mobile).
- Dark theme: contrast is readable, no invisible icons or borders, and charts and badges
  are legible.

## States
- Empty, filled, loading (skeleton, not a layout jump), error with a way to retry, offline.
- Every role and ownership state the app has, including a removed or downgraded user and
  a signed-out visitor, sees only what it should.
- Pagination or "load more" works at the boundary.

## Text
- No raw i18n keys, no untranslated strings, no mixed languages on one screen.
- Tone and form of address are consistent within each language.
- Placeholders, validation messages, toasts and empty states are translated as well.

## Numbers, money, dates (where the app has them)
- If the app handles money: each currency's minor-unit rule (0, 2, 3 decimals) is applied
  in input and display.
- Thousands and decimal separators and date formats follow the active locale.
- Totals and balances add up when you check them against the seed data by hand.
- "Today" and day boundaries are right in the user's time zone, not UTC.

## Console and network
- No errors or warnings beyond the noise recorded in the log.
- No unexpected third-party requests, and no request storm on scroll or tab switch.

## Navigation
- Back (browser and hardware) goes where a user expects, never into a finished wizard or
  a deleted record.
- Deep link and reload on the screen restore it correctly.
- Leaving mid-flow does not keep half-written data, or warns before discarding it.

## Forms
- Validation messages appear at the right moment, and length limits are enforced and
  visible.
- Double submit creates one record. A save shows progress and disables the button.
- After saving, the screen shows the new state without a manual reload.

## Accessibility
- Focus order is logical, and dialogs trap and restore focus.
- Icon-only buttons have labels, and touch targets are at least 44×44 on mobile.
