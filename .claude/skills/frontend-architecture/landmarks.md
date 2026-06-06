# webapp_v2 Landmarks

> **What this file is:** a lookup table of file paths + key locations + conventions, so planners and implementers don't have to re-explore the codebase to find where things live. Load this **before** spawning Explore agents.

> **What this file is NOT:** documentation of how to build features — see `patterns.md` (component & code patterns) and `reference.md` (feature folder structure + testing) for those.

> **Confidence:** each section ends with a `Verified` date. If a path doesn't resolve, the codebase moved — update this file rather than blindly re-exploring.

---

## Sidebar / navigation

| Concern | Location |
|---|---|
| Sidebar component + nav-item definitions | `components/main-layout.tsx`, `getNavItems()` at lines 91-231 |
| `NavItemType` interface | `components/main-layout.tsx:48` (`hide?: boolean` controls visibility) |
| Filter logic at render | `.filter(item => !item.hide)` at lines 597, 619, 653 |
| Today's drivers for `hide` | feature flags (`isFeatureFlagEnabled(...)`) + env (`PRODUCTION_HIDDEN_ITEMS` array, lines 52-88). **No role-based filtering today** — extend `NavItemType` with `visibleToRoles?: Role[]` when adding it. |

*Verified: 2026-06-05.*

---

## Auth + current user

| Concern | Location |
|---|---|
| AuthGuard wrapper (protects pages) | `components/auth-guard.tsx:7-157` — fetches `/api/currentuserv2` at line 26, redirects to `/login` at lines 86-92 |
| Next.js middleware | `middleware.ts` — only handles iframe embedding for public-share routes today. **No auth gating** lives here yet. |
| Auth store (Zustand) | `stores/authStore.ts:15-23` |
| `OrgUser` shape returned to frontend | `{ email, org, active, new_role_slug, permissions[], landing_dashboard_id?, org_default_dashboard_id? }` |
| Permission hook | `hooks/api/usePermissions.ts` — `useUserPermissions()` returns `{ hasPermission(slug), hasAnyPermission, hasAllPermissions }` reading from auth store (not SWR) |
| Source of truth endpoint | `/api/currentuserv2` (called in auth-guard) |

When the backend role-slug enum changes, search frontend for hardcoded slug strings (`'account-manager'`, `'pipeline-manager'`, `'guest'`) — none should remain after a migration.

*Verified: 2026-06-05.*

---

## Routing tree (top-level `app/` routes)

| Route | Purpose |
|---|---|
| `app/dashboards/` | Dashboards list + `[id]` detail |
| `app/charts/` | Charts list |
| `app/reports/` | Reports |
| `app/metrics/` | Metrics view |
| `app/explore/` | Superset Explore (ad-hoc) |
| `app/ingest/` | Sources + Connections + Warehouse (Warehouse is a **tab**, not a route) |
| `app/pipeline/` | Pipeline / Data overview |
| `app/transform/` + `/transform/canvas/` | dbt workspace |
| `app/orchestrate/[id]/` + `/orchestrate/create/` | Orchestration flows |
| `app/data-quality/` | DQ checks (feature-flagged) |
| `app/settings/` | Settings — see Settings IA below |
| `app/login/` | Auth |

When planning a role-gated feature, remember: **Warehouse is not a route** — it's a tab inside `/ingest`.

*Verified: 2026-06-05.*

---

## Settings IA (today — sparse)

| Route | Component |
|---|---|
| `app/settings/billing` | `components/settings/billing.tsx` |
| `app/settings/user-management` | `components/settings/user-management/UserManagement.tsx` |
| `app/settings/about` | `components/settings/about.tsx` |

Sidebar wires them at `components/main-layout.tsx:192-226` (+ conditional "Superset Usage" link). There are **no** Warehouse, Appearance, Org-defaults, or Groups settings pages — those slots are empty.

*Verified: 2026-06-05.*

---

## Users management (already substantial)

| Concern | Location |
|---|---|
| Page component | `components/settings/user-management/UserManagement.tsx` |
| Invite dialog | `components/settings/user-management/InviteUserDialog.tsx` (email + role dropdown, Shadcn Dialog/Input/Select) |
| Users table | `UsersTable` inside `UserManagement.tsx` — sort/filter on email/role, per-row dropdown (Edit Role / Delete User) |
| Invitations table | `InvitationsTable` — resend / delete pending invites |
| Delete dialog | `DeleteUserDialog` (lines ~477-485 of UserManagement.tsx) |
| Permissions consumed | `can_create_invitation`, `can_view_invitations`, `can_edit_orguser`, `can_delete_orguser` |

A "Settings > Users" feature is mostly re-skin, not rebuild. Extend; don't rewrite.

*Verified: 2026-06-05.*

---

## Resource delete + share affordances

| Resource | Delete UI | Share UI |
|---|---|---|
| Dashboard | AlertDialog inside `components/dashboard/dashboard-list-v2.tsx` + `components/dashboard/responsive-dashboard-actions.tsx` (~lines 986-1010, 1170-1194, 1547-1571) | `@/components/ui/share-modal` (imported at line 99 of dashboard-list-v2.tsx) |
| Chart | `ChartDeleteDialog` + `useDeleteChart()` hook in `app/charts/page.tsx:30-31` | n/a (charts share via dashboard) |
| Report | `app/reports/` — same shape as dashboards | uses `share-modal` |

When gating delete by ownership, the centralized place is the dropdown menu item in each list/actions component — that's the single chokepoint.

*Verified: 2026-06-05.*

---

## API client

| Concern | Location |
|---|---|
| Central client | `lib/api.ts:75-289` — `apiFetch()` |
| Auth | Cookie-based (`credentials: 'include'`); no Authorization header |
| Org header | `x-dalgo-org` (set by `apiFetch`) |
| 401 handling | Token refresh via `/api/v2/token/refresh`, then redirect to `/login` |
| Helpers | `apiGet`, `apiPost`, `apiPut`, `apiDelete`, `apiPublicGet`, `apiPublicPost`, `apiPostBinary`, `apiGetBinary` |
| Data layer | SWR (`useSWR(path, apiGet)`) — typically wrapped in `hooks/api/use{Resource}.ts` |

Don't build a new fetcher. Don't introduce React Query alongside SWR — pick one (SWR is standard).

*Verified: 2026-06-05.*

---

## Component library + form patterns

| Concern | Location |
|---|---|
| Library | Shadcn UI on top of Radix (Dialog, Select, DropdownMenu, AlertDialog, Input, Button, Table) |
| Brand styling | Tailwind v4, teal-forward; CVA variants on Button (`default`, `primary`, `destructive`, `outline`, `ghost`, `link`) — `components/ui/button.tsx` |
| Representative form (invite + role) | `components/settings/user-management/InviteUserDialog.tsx` (Dialog + Input + Select + validation error pattern at line 112 + loading state at 135-142) |
| Representative table | `UsersTable` inside `UserManagement.tsx` — sticky header, column-level filter popovers, dropdown actions per row, paginated via state |

Match these. Don't import a new UI library for a one-off feature.

*Verified: 2026-06-05.*

---

## Permission gating (today: ad-hoc; no central helper)

| Pattern | Where to find an example |
|---|---|
| Page-level guard with inline modal | `app/dashboards/[id]/page.tsx:18-42` (`hasPermission('can_view_dashboards')` → renders a Lock + back-button modal) |
| Button-level guard | `UserManagement.tsx:38` (button `disabled={!canCreateInvitation}`) |
| Dropdown-level guard | `UsersTable` — dropdown menu only renders if `canEditUser || canDeleteUser` |

**No central `<PermissionGate>` wrapper exists.** When a feature touches more than ~3 gated surfaces, the right move is to add one in `components/permission-gate.tsx` rather than spreading more inline checks.

*Verified: 2026-06-05.*

---

## Test conventions

| Concern | Location |
|---|---|
| E2E framework | Playwright |
| E2E specs | `e2e/*.spec.ts` |
| E2E auth | Env vars `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD`, `E2E_BASE_URL` |
| Example E2E | `e2e/login.spec.ts` — `test.describe` + `test.beforeEach` + `.click()` / `.fill()` chains, `toBeVisible()` / `toHaveURL()` |
| Unit framework | Vitest |
| Unit tests live next to source | `hooks/__tests__/usePipelines.test.ts` (pattern) |

*Verified: 2026-06-05.*

---

## When this file gets stale

If a `Verified:` date is more than ~6 months old, or a path no longer resolves, spawn one targeted Explore agent (not a broad re-explore) and update the affected row. Keep this file small and current.
