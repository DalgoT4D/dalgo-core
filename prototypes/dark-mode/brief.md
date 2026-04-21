# Prototype: Dark Mode Toggle

**Date**: 2026-04-21
**Status**: Prototype — not production-ready
**Goal**: Validate whether dark mode reduces eye strain for NGO data coordinators who review dashboards for extended periods

## Problem
Dalgo currently has no dark mode. Staff who work evening shifts or use the platform for extended data review sessions have no way to reduce screen brightness or eye strain. The brand teal (`#00897B`) needs to remain recognisable in both modes.

## What We're Building
- A sun/moon toggle icon in the sidebar footer (next to existing controls in `main-layout.tsx`)
- Preference stored in `localStorage` — persists across sessions, no backend changes needed
- Seamless theme switching using `next-themes` — applies a `.dark` class to the `<html>` element
- No visual flash on page load (next-themes handles this with `suppressHydrationWarning`)
- Works instantly across all pages because all colours use CSS variables that already have `.dark` overrides

## What We're NOT Building
- Per-org or per-user theme preference synced to the backend
- A "system preference follows OS setting" option (auto mode)
- Theme customisation beyond light/dark

## How We'll Know It Works
- [ ] User can toggle dark mode from any page in one click
- [ ] Theme persists after page refresh and browser restart
- [ ] All pages (Charts, Dashboards, Pipeline, Settings) look correct in dark mode
- [ ] Teal brand colour is still clearly visible in dark mode

## Quick Plan

1. **Install `next-themes`**: `npm install next-themes` in `webapp_v2/` → package available
2. **Wrap the root layout**: Add `<ThemeProvider attribute="class" defaultTheme="light" disableTransitionOnChange>` around `<SWRProvider>` in `app/layout.tsx` → theme class applied to `<html>`
3. **Add the toggle**: Create `components/theme-toggle.tsx` — a `Sun`/`Moon` icon button using `useTheme()` from `next-themes` and Shadcn `Button variant="ghost"` → toggle component ready
4. **Place it in the sidebar**: Add `<ThemeToggle />` to `components/main-layout.tsx` sidebar footer, next to the existing org/user controls → visible on all pages
5. **Fix the sidebar dark CSS variables**: In `globals.css`, the `.dark` sidebar variables currently keep the sidebar white (`--sidebar: oklch(1 0 0)`). Override them so the sidebar also goes dark → sidebar looks correct in dark mode

### Where It Lives
- **Backend**: No backend changes
- **Frontend**:
  - `webapp_v2/app/layout.tsx` — add `ThemeProvider` wrapper
  - `webapp_v2/components/theme-toggle.tsx` — new toggle component (30 lines)
  - `webapp_v2/components/main-layout.tsx` — add `<ThemeToggle />` to sidebar footer
  - `webapp_v2/app/globals.css` — fix sidebar dark variables

### Pattern to follow
- `next-themes` is the standard Next.js App Router dark mode library; same pattern used by Shadcn's own docs
- Toggle icon pattern: `Sun` when dark (click to go light), `Moon` when light (click to go dark)
- CSS variables for light/dark are already defined in `globals.css` — minimal CSS changes needed

## Shortcuts We're Taking
- No system-preference sync (user explicitly chooses, doesn't follow OS)
- Not testing every page in dark mode before shipping prototype — validate on Charts + Dashboards only
- ECharts inside dark mode may render with light backgrounds (ECharts uses its own theming); out of scope for this prototype
- No tests for the toggle component
