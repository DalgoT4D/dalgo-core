# Research: Help Menu (v1)

## Linear Ticket
**DALGO-1433** — "Add Linear style ? to the bottom of Dalgo portal"
- A "?" icon at the bottom of the left sidebar that fans upward to reveal: View Documentation, View Dalgo Videos, See Uptime, Discord Community.
- The user's prompt uses the labels: "Get Support", "See Uptime", "Docs", "Video Tutorials".

---

## Codebase Findings

### 1. Primary file: `components/main-layout.tsx`
The entire sidebar (desktop + mobile) is in this one file. The `<aside>` element:
- Uses `flex flex-col` layout — already set up to accept a pinned bottom section.
- Has a `div` (`main-layout-sidebar-nav`) with `flex-1 overflow-y-auto` for nav items.
- Sidebar collapses to `w-16` (icons only) / expands to `w-64`.
- Mobile uses a Shadcn `Sheet` component (drawer), separate from the desktop `<aside>`.

The bottom section can be added as a sibling `div` after the nav `div` inside `<aside>` — it will naturally anchor to the bottom since `flex-1` makes the nav take remaining space.

### 2. Existing patterns to follow

**Popover** (`components/ui/popover.tsx`):
- Wraps Radix UI `@radix-ui/react-popover`. Supports `side` prop (`"top"`, `"bottom"`, `"left"`, `"right"`) via `PopoverContent` — use `side="top"` to make the menu fan upward.
- Already handles fullscreen portal edge case.

**DropdownMenu** (`components/ui/dropdown-menu.tsx`, used in `components/header.tsx`):
- Pattern used for the user avatar menu in the header. Could also work with `side="top"` on `DropdownMenuContent`.

**Recommendation: Use `Popover`** rather than `DropdownMenu`. Reason: each help-menu item is a plain `<a>` to an external URL — there are no internal router actions (unlike the header's dropdown which uses `router.push()`). `Popover` imposes no `role="menuitem"` semantics on links, allowing proper `target="_blank"` link behavior inside.

**DocsLink** (`components/ui/docs-link.tsx`):
- Already uses `NEXT_PUBLIC_DOCS_BASE_URL` env var to build the docs URL. We can reuse this for the "Docs" menu item.

**Collapsed sidebar item pattern** (`CollapsedNavItem` in `main-layout.tsx`):
- Uses `TooltipProvider` + `Tooltip` to show label on hover. The help button in collapsed mode should follow the same pattern.

### 3. URL configuration
All 4 link targets are external. Following Dalgo's convention (env vars for external URLs, see `NEXT_PUBLIC_DOCS_BASE_URL`):

| Menu item | Env var | Notes |
|-----------|---------|-------|
| Docs | `NEXT_PUBLIC_DOCS_BASE_URL` | Already exists — use homepage (`/`) |
| Video Tutorials | `NEXT_PUBLIC_YOUTUBE_URL` | New. Dalgo YT channel homepage |
| See Uptime | `NEXT_PUBLIC_UPTIME_URL` | New. Uptime Kuma public dashboard |
| Get Support | `NEXT_PUBLIC_SUPPORT_URL` | New. Discord invite or #ngo-support deep link |

If an env var is not set, the corresponding menu item should be hidden (graceful degradation), same pattern as `DocsLink`.

### 4. Analytics
Event naming follows `category:object_action` snake_case convention from `constants/analytics.ts`. New events needed:
- `help:menu_opened` — when the "?" button is clicked to open the popover
- `help:link_clicked` — when any help item is clicked, with a `{ link: 'docs' | 'videos' | 'uptime' | 'support' }` property

No `FEATURES` map entry needed — this is not a page/route, so no `feature:viewed` automation.

### 5. Icon choices (lucide-react)
Already imported in `main-layout.tsx`. Additional icons needed:
- Help button trigger: `HelpCircle` (or `CircleHelp`) — matches the "?" metaphor
- Docs: `BookOpen`
- Video Tutorials: `PlayCircle`
- See Uptime: `Activity`
- Get Support: `MessageCircle`

### 6. Collapsed vs expanded rendering
- **Collapsed (`w-16`)**: Show just the `HelpCircle` icon centered, with a Tooltip on hover showing "Help". No label text.
- **Expanded (`w-64`)**: Show icon + "Help" label text, styled consistently with nav items (`flex items-center gap-3 p-3`).
- **Mobile drawer**: Show icon + label text (drawer is always expanded-style).

---

## External References
- [Radix UI Popover — side/align props](https://www.radix-ui.com/primitives/docs/components/popover)
- [Linear help menu UI pattern](https://linear.app) — the "?" circle in bottom-left fans up to show 4–6 items with icons
- Shadcn PopoverContent already has `data-[side=top]:slide-in-from-bottom-2` animation built in — the open animation will naturally slide up, matching the fan-up visual.
