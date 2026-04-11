# Domain checklist — UI / View layer

**Authoritative loading rules live in `SKILL.md` Step 5.** This list is a human-readable summary of when the checklist applies. If the two drift, SKILL.md wins.

Load this checklist when the diff touches:
- `.vue`, `.tsx`, `.jsx`, `.svelte` files
- `.html` templates with dynamic bindings
- CSS/styling files that control layout (grid, flex, position, z-index, visibility)
- Composables, hooks, or stores whose output drives templates

UI bugs rarely live inside a single component. They live at the **composition boundary** — where a component is mounted by a parent, where multiple instances coexist, where one element's visibility is governed by a sibling's state.

---

## Multi-instance mounting

Do not reason about a component in isolation. For every component changed in the diff:

1. Grep for `<ComponentName`, `import ComponentName`, or the React JSX usage across the codebase.
2. For each parent that mounts it, answer:
   - **How many instances can be mounted concurrently?** Look for `v-for`, `.map()`, iteration, tabbed layouts, split views, modal stacks.
   - **What's the visibility pattern?**
     - `v-if` / conditional JSX → instance is destroyed and recreated (state resets, effects re-fire)
     - `v-show` / CSS `display:none` → instance stays mounted, effects keep running, scroll state persists
     - Neither → instance is always live
   - **What props gate per-instance state?** `active`, `visible`, `selected`, `disabled`, `hidden`.
   - **What's the layout pattern?** `absolute inset-0` stacking means paint order matters. `position: fixed` escapes normal flow.

3. **Mentally render at least 2 simultaneous instances.** For every new DOM element added in the diff, ask:
   - Is its visibility tied to the per-instance `active` prop, or is it governed by something else?
   - If a sibling element's visibility is controlled by inline style/class/JS, does that logic extend to the new element?
   - In stacked layouts, could the new element from instance B paint on top of instance A's content?
   - Does a `teleport` / `Portal` / `createPortal` escape the parent's visibility container?

---

## Sibling visibility hazards (common silent bugs)

The most dangerous UI bug pattern:

```vue
<template>
  <div ref="containerRef" />          <!-- visibility controlled by JS setting display -->
  <NewButton v-if="someCondition" />  <!-- NEW: visibility NOT tied to the JS logic -->
</template>
```

When the parent hides `containerRef` via JS (e.g., on tab switch), `NewButton` stays visible because its `v-if` doesn't track the same state. In a stacked multi-instance layout, `NewButton` from an inactive pane bleeds into the active one.

**Check**: does every new interactive/visible element inherit the same visibility contract as its siblings? If siblings are hidden via `v-show`, `display:none`, or JS class toggling, the new element must follow the same mechanism — not a disjoint `v-if`.

---

## Focus management

- Does the change steal focus on mount? On a click? On prop change?
- Does it restore focus when the element unmounts or becomes inactive?
- In multi-instance layouts, does focus leak between panes? (e.g., tab switch leaves focus on a button in the hidden pane, next keystroke goes to the wrong tab)
- Does programmatic `.focus()` respect `tabindex="-1"` and disabled states?

---

## Effect / composable cleanup

- Every `onMounted` / `useEffect` with a subscription must have matching cleanup. Grep for the subscription source in the diff and verify unsubscribe runs on unmount.
- `ResizeObserver`, `IntersectionObserver`, `MutationObserver` — disconnect on cleanup.
- Event listeners attached to `window`, `document`, or external elements — removed on cleanup.
- Intervals (`setInterval`, `requestAnimationFrame` loops) — cleared on cleanup.
- In `v-show` layouts, cleanup does NOT run when the component is hidden — effects keep firing on hidden instances. Expensive work on hidden panes is a real cost.

---

## Reactivity & ref unwrapping

- Composables returning refs in a plain object: consumers must destructure with care. `const x = useFoo(); x.someRef` is NOT auto-unwrapped in Vue templates if the ref is nested.
- React: stale closures in effects/callbacks — are dependencies complete? Does a `useCallback` capture an outdated value?
- Vue: `reactive()` vs `ref()` confusion — reassigning a `reactive` object breaks reactivity.
- Signal-based frameworks (Solid, Svelte 5 runes): is the signal read inside a tracking scope, or outside it (dead)?

---

## Transition & remount edge cases

- `<Transition>` / `<AnimatePresence>` — does the enter/leave animation correctly gate on the bound condition? Does a rapid toggle cause overlapping animations?
- `:key` on a mounted element forces remount. Does a `:key` binding to a volatile value (random, timestamp, index) cause unintended remounts that drop focus/scroll state?

---

## Transition leave window interactivity

Vue `<Transition>`, React `<AnimatePresence>` (framer-motion), and Svelte `out:` transitions all keep the element in the DOM for the **full leave duration**. During that window:

- The element is **still clickable** unless `pointer-events: none` is explicitly applied during leave
- Opacity-based transitions fade *visibility* but not *interactivity*
- If the element's click handler depends on reactive state that has already changed (e.g., `active` tab just switched, `visible` pane just hid, parent `v-if` just flipped), the click fires with **stale state** — the handler runs as if the element were still valid

This is a silent class of bug: the user sees the element fading out, the element is 20% opaque, but a click in that 150ms window dispatches an action against the already-gone context. The reviewer looks at `v-if="active && condition"` and confirms it's gated correctly — missing that the gate is *temporally* bypassed by the transition.

**Check**: For every element wrapped in a leave transition, ask — "if a user clicks this during the leave window, does the click handler still make sense given that the *reason it's leaving* has already happened?" If the answer is no, the fix is one of:

1. **Apply `pointer-events: none` during leave** (the cleanest):
   - Vue: `leave-active-class="pointer-events-none transition-opacity duration-150"`
   - React (framer-motion): `style={{ pointerEvents: isExiting ? 'none' : 'auto' }}`
   - Svelte: add a class during `out:` transition
2. **Guard the click handler itself** against the stale condition (defensive but works)
3. **Move the element inside a wrapper that's fully removed** (not just transitioned) when the gate flips — `v-if` on the wrapper, transition inside

**Repro test**: set the leave duration to 2000ms temporarily. If you can click the element during that 2-second window and trigger a stale action, the bug is real.

---

## Visibility state source tree (trace before claiming a fix)

When reviewing a change that gates an element's visibility (`v-if`, `v-show`, conditional render, CSS `display`, `opacity`, `visibility`, `pointer-events`), the **"obvious" guard on the element itself is rarely the full story**. Before accepting or recommending a visibility fix, trace the **complete state tree** that influences the element's interactivity:

1. **Immediate parent visibility**: does the parent have its own `v-if` / `v-show` / conditional render? If yes, does the element inherit that gate, or does it have an independent one that can disagree?
2. **Overlay / modal / popover painters**: is there anything in the app that can paint *on top* of this element (modals, toasts, tooltips, drawer overlays, loading shields)? Does the element's paint order / z-index / stacking context keep it below them?
3. **Transition wrappers**: is the element inside a `<Transition>` / `<AnimatePresence>` / `out:` wrapper that delays removal? If yes, apply the transition leave window checks above.
4. **State stores / composables / context providers**: which store or hook drives the `active` / `visible` / `selected` / `hidden` / `enabled` props that gate this element? Read that store — is it the single source of truth, or does another store also drive visibility-related state?
5. **Sibling CSS rules**: is there a parent selector, media query, or sibling rule that can set `pointer-events`, `display`, or `visibility` from outside the component's own template? Check the nearest stylesheet and any global CSS.

For each source, the element's interactivity must be **consistent**. If one source says "hidden" and another says "visible", there's a bug — often a race, stale state, or overlap the original author didn't anticipate.

**Output integration**: if this section applies (the diff changes visibility gating), the Trace Log's `symbols_inspected` must include at least one entry from *each relevant source* above that exists. You cannot trace the component alone and call it done — you must have read the parent, the overlay, the transition wrapper, and the visibility-driving store. Missing any of these is the same as skipping the trace entirely.

---

## Paint order & z-index

- New `position: absolute | fixed | sticky` elements: what's the stacking context? Is there a `z-index` conflict with existing overlays (modals, toasts, tooltips)?
- `isolation: isolate` creates a new stacking context — does the change rely on or break one?
- `transform`, `will-change`, `filter`, `opacity < 1` all create stacking contexts implicitly. Does a new CSS rule accidentally create one that breaks fixed-positioned children?

---

## Store-level mutation fanout (Pinia, Vuex, Redux, Zustand, Svelte stores)

UI state stores hold records whose fields are usually updated one at a time — and this is a prime location for **Mutated record fanout** bugs per `methodology.md`. When a store action writes one field on an entity, the sibling fields of that entity are candidates for stale state that the UI will happily render.

The canonical foot-gun: a user tab / item / session record has many persistent fields (title, icon, selected, error, status, planPath, lastModified, dirty). A store action named `linkTabToSession` updates `sessionId` but leaves `planPath`, `error`, and `lastModified` pointing at the *previous* session. The UI binds to those fields and keeps showing stale information. The bug is invisible to symbol-tracing because nothing in the action's callgraph is wrong — the data-model neighborhood is.

For every store action or reducer touched by the diff, trace:

1. **Which entity type is being mutated** — the store holds `Tab`, `Chat`, `User`, `Project`, etc. What's the shape?
2. **Which fields the action writes** — the obvious answer is in the diff.
3. **Which sibling fields are on the same entity** — enumerate them from the store's type definition or state shape.
4. **For each sibling, ask**: does this write leave the sibling claiming something from the previous lifecycle?
   - `title` still says the old session's name
   - `errorMessage` still holds the crash from the prior PTY
   - `planPath` still points at a file from the replaced agent
   - `lastActivityAt` is older than the new content
   - `isDirty` was true before the mutation and is still true after
5. **Who reads each sibling field** — `v-bind`, `{{ }}`, JSX `{tab.error}`, selectors, memoized derivations. Each reader is a site where stale state becomes visible.

The rule of thumb: **a store action that changes what an entity "is" must treat siblings as owned by the old identity, not the new one**. Either clear them, refresh them, or recompute derived state.

Record entity + sibling fields in `mutated_records_inspected` with `kind: store-entity`.

**Common stores to inspect for fanout** when UI diffs touch them:
- tab / pane / split / window stores (multi-instance, persistent siblings)
- chat / message / thread stores (streaming writes leave siblings mid-update)
- form stores (field value written but `touched` / `dirty` / `error` not reconciled)
- selection stores (`selectedId` changed but `selectionRange` / `anchor` / `focusRow` stale)

---

## Output integration

When this checklist is loaded, the Trace Log's `scenarios_considered` must include **at least one multi-instance scenario** if the touched component has a plural mount site. Example:

```
- "two tabs open, inactive tab has unread badge, user switches tabs"
- "modal open while underlying page scrolls"
- "component unmounted mid-fetch, stale response arrives"
```

If you cannot produce a multi-instance scenario because the component is a true singleton (e.g., app root, toplevel layout), say so explicitly: `"singleton mount — no multi-instance concerns"`.
