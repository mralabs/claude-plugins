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

## Paint order & z-index

- New `position: absolute | fixed | sticky` elements: what's the stacking context? Is there a `z-index` conflict with existing overlays (modals, toasts, tooltips)?
- `isolation: isolate` creates a new stacking context — does the change rely on or break one?
- `transform`, `will-change`, `filter`, `opacity < 1` all create stacking contexts implicitly. Does a new CSS rule accidentally create one that breaks fixed-positioned children?

---

## Output integration

When this checklist is loaded, the Trace Log's `scenarios_considered` must include **at least one multi-instance scenario** if the touched component has a plural mount site. Example:

```
- "two tabs open, inactive tab has unread badge, user switches tabs"
- "modal open while underlying page scrolls"
- "component unmounted mid-fetch, stale response arrives"
```

If you cannot produce a multi-instance scenario because the component is a true singleton (e.g., app root, toplevel layout), say so explicitly: `"singleton mount — no multi-instance concerns"`.
