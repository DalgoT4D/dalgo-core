# Implementation Plan: Help Menu (v1)

**Draft v1** — Pradeep to review; revise before executing.

---

## 1. Overview

Add a Linear-style "?" help button anchored to the bottom of the left sidebar. Clicking it opens a popover menu that fans upward with four external links: **Get Support**, **See Uptime**, **Docs**, and **Video Tutorials**. The button adapts to collapsed (icon-only) and expanded sidebar states, and also appears in the mobile drawer.

- **Linear ticket:** [DALGO-1433](https://linear.app/dalgo/issue/DALGO-1433/add-linear-style-to-the-bottom-of-dalgo-portal)
- **Research:** `workdocs/help-menu/v1/research.md`
- **Services affected:** `webapp_v2` only — no backend changes required.

---

## 2. Blast Radius

This is a pure UI chrome change. It adds a new component to the sidebar navigation shell — it does not create, read, update, or delete any product entity from the domain map.

| Surface | Hop | Why affected | Status | Notes |
|---------|-----|--------------|--------|-------|
| Desktop sidebar (expanded) | Direct | New bottom section added to `<aside>` in `main-layout.tsx` | In scope | |
| Desktop sidebar (collapsed) | Direct | Icon-only mode of the same component | In scope | |
| Mobile drawer (Sheet) | Direct | Mobile nav in `main-layout.tsx` needs the same button | In scope | |
| All page routes | Transitive (layout) | `MainLayout` wraps every authenticated page, so the button appears everywhere | In scope — by design |

**Not affected** (domain-map entities untouched):
- Source, Warehouse, Transform, Pipeline, Data Quality — no data-layer changes.
- Chart, Metric, KPI, Dashboard, ReportSnapshot, Share link — no analytics-layer changes.
- Alert, Notification — no output-layer changes.
- Organization, OrgUser — no platform-layer changes.
- No new API endpoints. No backend (DDP_backend) changes.
- No prefect-proxy changes.

---

## 3. High-Level Design (HLD)

```
Browser
  └── MainLayout (main-layout.tsx)
        ├── Header bar (unchanged)
        └── Content area
              ├── <aside> Desktop sidebar
              │     ├── Collapse toggle button (unchanged)
              │     ├── Nav items (flex-1, unchanged)
              │     └── [NEW] HelpMenuButton   ← bottom section, border-t
              │
              ├── Sheet (Mobile drawer)
              │     ├── Logo header (unchanged)
              │     ├── Nav items (unchanged)
              │     └── [NEW] HelpMenuButton   ← same component, mobile variant
              │
              └── Main content area (unchanged)
```

**Popover anchoring:**
- `Popover` from `components/ui/popover.tsx` with `side="top"` and `align="start"`.
- The popover content appears **above** the trigger button, anchored to its left edge.
- Radix UI's built-in `data-[side=top]:slide-in-from-bottom-2` animation produces the fan-up effect automatically.

**No new routes, no API calls, no server-side changes.**

---

## 4. Low-Level Design (LLD)

### 4.1 New component: `components/help-menu.tsx`

```tsx
'use client';

// Props
interface HelpMenuButtonProps {
  collapsed?: boolean;  // true = icon-only (collapsed sidebar), false = icon + label
}
```

**State:**
- `isOpen: boolean` — controls popover open/close (local `useState`).

**Env var constants (defined inline in the component file):**

```ts
const DOCS_URL = process.env.NEXT_PUBLIC_DOCS_BASE_URL?.replace(/\/$/, '') ?? null;
const YOUTUBE_URL = process.env.NEXT_PUBLIC_YOUTUBE_URL ?? null;
const UPTIME_URL = process.env.NEXT_PUBLIC_UPTIME_URL ?? null;
const SUPPORT_URL = process.env.NEXT_PUBLIC_SUPPORT_URL ?? null;
```

**Menu item definition:**

```ts
const HELP_ITEMS = [
  { label: 'Get Support',      icon: MessageCircle, url: SUPPORT_URL },
  { label: 'See Uptime',       icon: Activity,      url: UPTIME_URL },
  { label: 'Docs',             icon: BookOpen,      url: DOCS_URL },
  { label: 'Video Tutorials',  icon: PlayCircle,    url: YOUTUBE_URL },
] as const;
```

Items with `url === null` are hidden (env var not set).

**Trigger button:**
- Collapsed: `h-10 w-10` circle button with `HelpCircle` icon centered, wrapped in `Tooltip` showing "Help" on hover (matching `CollapsedNavItem` pattern).
- Expanded: full-width button styled like a nav item — `flex items-center gap-3 p-3 rounded-lg hover:bg-[#0066FF]/3 hover:text-[#002B5C]` — with `HelpCircle` icon + "Help" text.
- Mobile: same as expanded style.

**Popover content:**
- `w-52` panel with a list of `<a>` link items.
- Each item: icon (left) + label text, `target="_blank" rel="noopener noreferrer"`.
- Hover: same `hover:bg-[#0066FF]/3 hover:text-[#002B5C]` as nav items.

**Analytics:**

```ts
// On popover open
trackEvent(ANALYTICS_EVENTS.HELP_MENU_OPENED);

// On each link click
trackEvent(ANALYTICS_EVENTS.HELP_LINK_CLICKED, { link: 'support' | 'uptime' | 'docs' | 'videos' });
```

**Full component structure:**

```tsx
export function HelpMenuButton({ collapsed = false }: HelpMenuButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const visibleItems = HELP_ITEMS.filter((item) => item.url !== null);
  if (visibleItems.length === 0) return null;

  const trigger = collapsed ? (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" data-testid="help-menu-trigger-collapsed" ...>
            <HelpCircle className="h-5 w-5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">Help</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  ) : (
    <Button variant="ghost" data-testid="help-menu-trigger" className="w-full justify-start gap-3 p-3 ...">
      <HelpCircle className="h-5 w-5 flex-shrink-0" />
      <span className="font-medium">Help</span>
    </Button>
  );

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild onClick={() => { if (!isOpen) trackEvent(ANALYTICS_EVENTS.HELP_MENU_OPENED); }}>
        {trigger}
      </PopoverTrigger>
      <PopoverContent side="top" align="start" className="w-52 p-1">
        {visibleItems.map(({ label, icon: Icon, url, key }) => (
          <a
            key={key}
            href={url!}
            target="_blank"
            rel="noopener noreferrer"
            data-testid={`help-menu-item-${key}`}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md hover:bg-[#0066FF]/5 hover:text-[#002B5C] transition-colors text-sm"
            onClick={() => { trackEvent(ANALYTICS_EVENTS.HELP_LINK_CLICKED, { link: key }); setIsOpen(false); }}
          >
            <Icon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
            <span>{label}</span>
          </a>
        ))}
      </PopoverContent>
    </Popover>
  );
}
```

### 4.2 Changes to `components/main-layout.tsx`

**Desktop sidebar** — add a bottom section div after `main-layout-sidebar-nav`:

```tsx
{/* [NEW] Help Menu — bottom of sidebar */}
<div className="p-2 border-t">
  <HelpMenuButton collapsed={isSidebarCollapsed} />
</div>
```

**Mobile drawer** — add before the closing `</div>` of the mobile sidebar wrapper:

```tsx
{/* [NEW] Help Menu — bottom of mobile drawer */}
<div className="p-2 border-t">
  <HelpMenuButton collapsed={false} />
</div>
```

### 4.3 New analytics events in `constants/analytics.ts`

```ts
// Help menu
HELP_MENU_OPENED: 'help:menu_opened',
HELP_LINK_CLICKED: 'help:link_clicked',
```

### 4.4 New env vars (`.env.local` / deployment config)

| Variable | Example value | Required? |
|----------|---------------|-----------|
| `NEXT_PUBLIC_DOCS_BASE_URL` | `https://docs.dalgo.in` | Already exists |
| `NEXT_PUBLIC_YOUTUBE_URL` | `https://www.youtube.com/@dalgo-data` | New |
| `NEXT_PUBLIC_UPTIME_URL` | `https://status.dalgo.in` | New |
| `NEXT_PUBLIC_SUPPORT_URL` | `https://discord.gg/...` | New |

If any variable is unset, the corresponding menu item is silently hidden. If all are unset, the entire `HelpMenuButton` renders nothing (early return).

---

## 5. Security Review

| Concern | Assessment |
|---------|------------|
| **Auth / access control** | No backend API calls. Feature is rendered on authenticated routes only (inside `MainLayout` which is inside `AuthGuard`). No new permissions needed. |
| **Input validation** | No user input. All URLs are env-var-configured at build time, not user-supplied. |
| **Data access control** | No data queried or displayed. |
| **Sensitive data** | No PII or credentials. Env vars are all public (`NEXT_PUBLIC_*`) — appropriate since they are non-secret external URLs. |
| **Injection risks** | `href` values come from env vars, not user input. No dynamic template rendering. |
| **External links** | All links use `target="_blank" rel="noopener noreferrer"` — correct for external links; prevents tab-napping. |
| **Analytics** | `help:link_clicked` sends only the link key (`'docs'`, `'videos'`, etc.) — no URL, no user data, no PII. Safe per analytics rules. |

**No security concerns.** This is a read-only UI chrome addition with no backend surface.

---

## 6. Testing Strategy

### Unit tests: `components/__tests__/help-menu.test.tsx`

| Test | What it checks |
|------|----------------|
| Renders nothing when all env vars are unset | Graceful degradation |
| Renders only items whose env vars are set | Partial config |
| Renders all 4 items when all env vars are set | Happy path |
| Clicking trigger opens the popover | Open state |
| Each link has `target="_blank"` and `rel="noopener noreferrer"` | Security |
| Each link has correct `href` from env var | URL wiring |
| `trackEvent(HELP_MENU_OPENED)` fires on open | Analytics |
| `trackEvent(HELP_LINK_CLICKED, { link: 'docs' })` fires on link click | Analytics |
| Collapsed mode renders Tooltip | Collapsed UX |

**Mock setup:**
- Mock `next/navigation` (no hooks used but SWR may need it)
- Mock `@/lib/analytics` to assert `trackEvent` calls
- Set `process.env.NEXT_PUBLIC_*` per test via `beforeEach`/`afterEach`

### Manual / integration testing
- Verify fan-up animation in expanded sidebar.
- Verify icon-only collapsed sidebar with tooltip.
- Verify mobile drawer shows the button at the bottom of the menu.
- Verify all 4 links open in new tabs.
- Verify that unsetting an env var hides the corresponding item.

### No backend tests needed.

---

## 7. Milestones

#### Milestone 1: `HelpMenuButton` component
- **Deliverable:** Self-contained component with popover, env-var link hiding, analytics.
- **Services:** `webapp_v2`
- **Key tasks:**
  - [ ] Create `components/help-menu.tsx` with `HelpMenuButton`
  - [ ] Add 2 analytics events to `constants/analytics.ts` (`HELP_MENU_OPENED`, `HELP_LINK_CLICKED`)
  - [ ] Add `data-testid` attributes to trigger and all link items
- **Acceptance criteria:**
  - Component renders a "?" button that opens a popover on click
  - All 4 items appear when env vars are set; individual items hide when their var is unset
  - Links open in `target="_blank"`
  - `trackEvent` is called on open and on each click

#### Milestone 2: Desktop sidebar integration
- **Deliverable:** Help button visible at the bottom of the desktop sidebar in both collapsed and expanded states.
- **Services:** `webapp_v2`
- **Key tasks:**
  - [ ] Import `HelpMenuButton` into `components/main-layout.tsx`
  - [ ] Add `<div className="p-2 border-t">` bottom section inside desktop `<aside>`
  - [ ] Pass `collapsed={isSidebarCollapsed}` prop
  - [ ] Verify icon-only + tooltip in collapsed mode (`w-16`)
  - [ ] Verify icon + "Help" label in expanded mode (`w-64`)
- **Acceptance criteria:**
  - Button visible at bottom of sidebar on desktop viewport
  - Collapses/expands with sidebar toggle
  - Popover appears above the button (fans upward)

#### Milestone 3: Mobile drawer integration
- **Deliverable:** Help button at the bottom of the mobile slide-out drawer.
- **Services:** `webapp_v2`
- **Key tasks:**
  - [ ] Add `HelpMenuButton` inside the mobile `Sheet` content's bottom section
  - [ ] Test on mobile viewport (375px–768px)
- **Acceptance criteria:**
  - Button appears at the bottom of the mobile drawer
  - Popover opens correctly inside the `Sheet` overlay

#### Milestone 4: Unit tests
- **Deliverable:** Test coverage for the new component.
- **Services:** `webapp_v2`
- **Key tasks:**
  - [ ] Create `components/__tests__/help-menu.test.tsx`
  - [ ] Cover all test cases from §6
  - [ ] `npm run test` passes
- **Acceptance criteria:**
  - All tests pass; no skipped assertions

---

## 8. Open Questions & Risks

| # | Question | Owner | Impact if unresolved |
|---|----------|-------|---------------------|
| 1 | **Exact URLs for the 4 links** — what are the Uptime Kuma public URL, Discord invite link, YouTube channel URL? | Pradeep | Can implement with placeholders; must be filled before deploy |
| 2 | **"Get Support" destination** — Discord invite, or a support form / email? Linear ticket says Discord Community. Prompt says "Get Support". Which? | Pradeep | Affects the label and icon choice |
| 3 | **Help button label** — should the label in expanded sidebar say "Help" or something else? Linear uses no label (icon only even when expanded). | Pradeep | Minor; cosmetic |
| 4 | **Collapsed sidebar: show "?" or "Help" tooltip** — tooltip content is "Help" — is that the right label? | Pradeep | Minor |
| 5 | **Should mobile drawer show the help button?** — The Linear issue doesn't mention mobile. Since the mobile drawer replaces the desktop sidebar, it should have it too, but confirm. | Pradeep | Scope |
