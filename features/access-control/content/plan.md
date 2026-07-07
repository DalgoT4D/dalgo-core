# Plan — Resource Sharing (Access Control, Layer 1: Content) — v1

**Status:** Draft v1 (2026-07-06) — re-planned from the **`feature/rbac` branch baseline**. Carries forward all product decisions from the 2026-07-02 review (recorded in [../ACCESS-MODEL-ROADMAP.md](../ACCESS-MODEL-ROADMAP.md)); supersedes the earlier deleted draft.
**Spec:** [resource-sharing-write-spec-2026-06-17.md](./resource-sharing-write-spec-2026-06-17.md) · full vision: [Spec B](./access-control-spec-B-resource-sharing-2026-06-02.md) — **both still need the Q0 amendment** (charts are not independently shareable; see §8).
**Research:** [research.md](./research.md) (verified on `feature/rbac`, 2026-07-06) · **Roadmap:** [../ACCESS-MODEL-ROADMAP.md](../ACCESS-MODEL-ROADMAP.md)
**Builds on:** Spec A — on the **`feature/rbac` branch**, PRs still open (DDP_backend [#1414](https://github.com/DalgoT4D/DDP_backend/pull/1414), webapp_v2 [#331](https://github.com/DalgoT4D/webapp_v2/pull/331)). This work stacks on that branch, not on main.
**Consumed by:** Layer 2 ([../dataset-access/plan.md](../dataset-access/plan.md)) — it waits on this plan's M1–M3 and inherits `ResourceShare`, `UserGroup`, the resolver + shareable-types table, and the `run_chart_query` seam.

**Acronyms:** FK (foreign key — a DB column pointing at another table's row) · DTO (the JSON an API returns) · RLS (row-level security — Layer 3) · PII (personal data) · TTL (cache lifetime) · IA (information architecture).

---

## 1. Overview

**What we're building:** who can View or Edit each content resource. **Shareable resources** (Dashboard, Report, Alert; Metric/KPI at general-access-only depth) get **General access** (audience × level) plus **direct grants** to people and groups. **Charts are not independently shareable** — a chart is visible wherever its dashboards are visible (2026-07-02 decision). A share modal does sharing + inviting in one place; groups, public links (Dashboards + Reports), ownership transfer, request-access, bulk sharing, and comments on Reports complete the surface.

**Decisions carried forward (2026-06-30 / 2026-07-02, all recorded in the roadmap):**

| Decision | Choice |
|---|---|
| **Sharing unit** | **Dashboards, not charts.** Charts inherit their dashboards' audiences automatically. No embed/broadening warning modals. Chart-level *data* privacy is Layer 2's dataset grants. |
| Member + Edit grant | Member stays hard-capped at View (Spec A's shipped rule wins) |
| Public global off | **Kill switch** — existing links stop rendering |
| Ownership transfer | In scope; transfer is final (no reclaim); old owner keeps Edit |
| API naming | `/api/access/…`; UI + code say **"General access"** (Drive vocabulary), not "floor" |
| Public links | Dashboards + Reports only, under one Admin global |
| Metric/KPI | General-access only (no share modal; access-requests allowed) |
| Notifications | Reuse the existing `Notification` model |

**Where we are (the `feature/rbac` baseline — research §1, §4):**

| Already on the branch | Still missing (this plan builds it) |
|---|---|
| 3 roles seeded (admin 4 / analyst 2 / member 1; super-admin untouched); Member is view-only via permission slugs | All sharing tables: `ResourceShare`, `UserGroup`, `AccessRequest` — zero exist |
| Owner-or-admin **delete** via `can_delete_resource()` — keyed off `created_by`; **no `owner` column anywhere** | `owner` column + transfer; `created_by` CASCADE→SET_NULL flip (5 models die with their creator today) |
| `can_share_dashboards` slug (admin + analyst hold it) | `can_share_reports/alerts/metrics/kpis` slugs |
| Public-link tokens + toggle + render endpoints on Dashboard and Report | Org-level kill switch (no global exists); General access; grants |
| `lib/rbac.tsx` (`useRbac`, `RoleGuard`, `PermissionGuard`), `NoAccess` page | 403→request-access handling (a 403 throws a generic error today); Groups page |
| `ShareModal` (dashboards, public toggle only); `ReportShareMenu` (reports, separate) | People/groups/General-access rows; one modal for both resource types |
| Bulk multi-select on the **Charts** list only | Bulk bars on Dashboards/Reports/Alerts (copy the Charts pattern) |
| Invitation model (no expiry); invite cap `inviter.level ≥ invitee.level` | `expires_at` + 30-day expiry; explicit "non-Admin invites Member only" (the 2 ≥ 2 loophole is live) |

**Services affected:** DDP_backend (heavily — models, resolver, access/group/request/transfer/bulk endpoints, seed, invite expiry) · webapp_v2 (share modal, Groups page, badges + "Shared with you", request-access, transfer modal, comments gating) · prefect-proxy (untouched — no user model).

**Branch strategy:** create `feature/resource-sharing` **off `feature/rbac`** in each repo. Committing straight onto `feature/rbac` would bloat the two open Spec A PRs; a stacked branch re-targets to main cleanly after they merge.

---

## 2. Blast Radius

New entities: `ResourceShare`, `UserGroup`, `UserGroupMember`, `AccessRequest`. Traversed from `docs/domain-map.md`; every status below was confirmed with the user in the 2026-06-30 scope call and the 2026-07-02 review (roadmap records the chart decision).

| Surface | Status | Notes |
|---|---|---|
| Dashboard | **in scope — full sharing** | general access + grants + public link + owner |
| Report (ReportSnapshot) | **in scope — full sharing** | + comments re-gate (create is `can_edit_dashboards` today — Members can't comment) |
| Alert | **in scope — full sharing** | `recipients` JSON stays the single recipient store; owner-or-admin delete already shipped on the branch |
| Metric / KPI | **in scope — general access only** | standalone list/detail gated; never consulted on chart render; access-requests allowed |
| **Chart** | **in scope — container-gated** | keeps ownership (delete/transfer); **no general access, no grants**. Analyst+ see all org charts (today's behavior); viewers get chart data only in a dashboard/report context they can View. Member's Charts nav (visible today, `main-layout.tsx:114-119`) gets hidden — Design to confirm (§8 Q4). |
| Groups (new) | **in scope** | org app (not `sharing`) — Layer 3 imports groups without grant machinery |
| Public links (Dash + Report) | **in scope** | toggle AND render endpoints check the new org global (kill switch); no global exists today |
| Notification | **in scope (reuse)** | request-access + share notices via `create_notification()` |
| Comments on Reports | **in scope (re-gate)** | relax create to View + add editor moderation (author-only today — §4.6) |
| Explore, data infra, AlertLog | **out of scope** | role-gated (Spec A); data plane is Layer 2 |
| RLS, audit log | **deferred** | Layer 3 / separate feature |

---

## 3. High-Level Design

### 3.1 The mental model

**The rule:** Access to a shareable resource = **general access ∪ direct grants ∪ owner/admin override**, at the most permissive level any path gives — and a Member never exceeds View.
**Example:** "Field Performance" has General access = Analysts+ / View. Priya (Analyst) can view it. The Funders group holds a View grant, so funder Sarah (Member) sees it too. Anjali owns it (Edit + delete + transfer). Admin Raj can do everything, everywhere.
**Why it matters:** one resolver answers every access question — lists, detail pages, dashboard tiles, write guards — so there is exactly one place to get right.

**Charts simply ride along.** Share a dashboard and every chart on it is visible to that audience, automatically, always — no warnings, no mismatch possible. To keep a chart from an audience, don't put it on their dashboard. Data-level protection (PII columns, restricted tables) is Layer 2's dataset grants.

**Resource-plane only (roadmap guardrail):** the resolver says nothing about the *data* plane. Layer 2 composes with it (`effective_permission AND dataset check` on authoring paths) through the `run_chart_query` seam (§3.3).

### 3.2 The API surface (plain names — one noun: *access*)

| Endpoint | Verb | Purpose |
|---|---|---|
| `/api/access/{rtype}/{id}` | GET | who has access and **via which path** (general / grant / group / owner) — feeds the share modal |
| `/api/access/{rtype}/{id}/grants` | POST / DELETE `/{grant_id}` | add / remove grants (people, groups); pending grants for new emails |
| `/api/access/{rtype}/{id}/general` | PUT | set General access (audience × level); narrowing returns the grants that would persist → "remove them too?" |
| `/api/access/{rtype}/{id}/owner` | POST | transfer ownership |
| `/api/access/bulk` | POST | shares / general-access change / public toggle across a selection; per-resource Edit check; applied/skipped counts; aggregated narrow prompt |
| `/api/access/requests` + `/{id}/approve` `/{id}/decline` | POST | request access → owner decides (can downgrade Edit→View) |
| `/api/groups` (+`/{id}`, `/{id}/members`) | CRUD | groups; name-collision check |
| `/api/charts/{id}` + `/{id}/data/` | (existing) | gain optional `?dashboard_id=` **access context** (§3.3) — distinct from the existing `dashboard_filters` param, which is a filter payload, not an access check |
| dashboard/report share toggles + `/api/v1/public/…` renders | (existing) | all four check the new `allow_public_sharing` global (kill switch) |
| `/api/orgpreferences` | (existing) | + org-default General access + `allow_public_sharing` |

`{rtype}` validity and capability (full-share / general-only / public-linkable) come from the **`RESOURCE_TYPES` table in `shareable_types.py`** (§4.0) — one table; Layer 2 adds `dataset`/`connection` as entries. This plan ships: `dashboard|report|alert` full; `metric|kpi` general-only + requests. **`chart` is not a shareable rtype.** New routers mount in `ddpui/routes.py` — `/api/access` and `/api/groups` prefixes verified free.

### 3.3 The chart render path (tiles vs standalone)

```
GET /api/charts/{id}/data/?dashboard_id=42    (dashboard tile)
   → chart 42-membership check + resolver View on dashboard 42 → serve
GET /api/charts/{id}/data/                    (standalone: builder / Charts page)
   → Analyst+/Admin (role, as today) or chart owner → serve; Member → 403
Report tiles → frozen configs via report endpoints, gated by report access (unchanged)
Public tiles → /api/v1/public/... token-gated (unchanged, plus kill switch)
```

**Query-layer hook (Layer 2/3 seam):** all warehouse-bound chart execution routes through `run_chart_query(viewer_ctx, chart, context)` — an access no-op today; Layer 2 adds the dataset check on authoring contexts, Layer 3 rewrites the query. `viewer_ctx` is typed to admit `OrgUser | PublicLinkContext`.

### 3.4 Design principles — where SOLID bites in this feature

SOLID (Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion) is not decoration here — Layers 2 and 3 only stitch in cleanly if these five rules hold. Each row is a review criterion for every PR in §7.

| Principle | The rule in this design | Concrete example |
|---|---|---|
| **S** — one job per module | The resolver only *answers* access questions — pure function, no writes, no notifications, no HTTP. Every mutation lives in `sharing_actions.py` (§4.0); API functions stay thin (validate → call the action → serialize). | `effective_permission()` never sends the "you got access" notification — the approve-request action does, by calling `create_notification()` after inserting the grant. |
| **O** — extend by data, not edits | New shareable types are **rows in `shareable_types.py`**, never resolver edits. The resolver branches on data (`general_*` fields + share rows + capability flags), never on `if resource_type == "dashboard"`. Same for principals: one `principal_match_q()` predicate; a new principal kind extends that one function. | Layer 2 adds `dataset` by registering `("dataset", Dataset, caps={general, grants})` — zero lines change in `access_resolver.py`. Layer 3's `attribute` principal ("region = North") lands only in `principal_match_q()`. |
| **L** — every registered type behaves identically | Anything in the registry must honestly satisfy the shareable contract (string pk, `general_audience`/`general_level`, owner accessor). No registered type may raise "not supported" from a contract method. Types that *can't* fulfil the contract stay out of the registry — they aren't special-cased inside it. | Chart is **not registered** (rather than registered-but-throws-on-grants); Metric/KPI are registered with `grants=False` as a declared capability, so the share endpoint rejects a grant on a metric by *reading the flag*, not by knowing what a metric is. |
| **I** — small capability flags, not one fat interface | The registry declares narrow capabilities per type — `general`, `grants`, `public_link`, `requests` — instead of one all-or-nothing "Shareable" interface. Consumers check only the capability they need. | The share modal renders its public-link section off `public_link: true` (dashboards, reports) and simply omits it for alerts — no `entityType === 'alert'` conditionals in the modal. |
| **D** — depend on the seam, not the concrete | Endpoints depend on the resolver, the resolver depends on the registry contract (it never imports `Dashboard`); chart execution depends on the `run_chart_query` hook; the resolver's group-membership cache is an injected callable so tests run without Redis. | Layer 2's dataset check plugs into `run_chart_query` without touching `charts_api.py`; resolver unit tests pass a stub `get_group_ids=lambda u: {…}`. |

**Why it matters:** the roadmap's "five get-this-right-now implications" are exactly these principles applied — break one (say, a `resource_type` branch inside the resolver) and Layer 2 becomes a rewrite instead of a registry entry.

---

## 4. Low-Level Design

### 4.0 Module layout — three files, each with one job

```
ddpui/core/sharing/
├── shareable_types.py   # the menu: WHAT can be shared, and what each type supports
├── access_resolver.py   # the bouncer: CAN this person see/edit this? (read-only)
└── sharing_actions.py   # the hands: every CHANGE to who has access
ddpui/api/access_api.py  # the front door: auth check → call sharing_actions/resolver → JSON
ddpui/api/groups_api.py  # front door for group CRUD (group models live in the org app)
```

What each file is for:

| File | The one question it answers | What lives in it | What must NEVER live in it |
|---|---|---|---|
| `shareable_types.py` | "What things can be shared, and what can you do with each?" | The `RESOURCE_TYPES` table: rtype → model + capability flags (`general`, `grants`, `public_link`, `requests`). The **only** place resource types are enumerated. Layer 2 adds `dataset` here as one entry. | Any logic. It's data. |
| `access_resolver.py` | "Can Priya view or edit this dashboard — yes or no?" | `effective_permission`, `accessible_filter`, `principal_match_q`. Pure and read-only: looks at owner + General access + grant rows, returns an answer. Truth-table tested without Redis or HTTP. Layer 2/3 import it. | Writes, notifications, HTTP, `if resource_type == "dashboard"` branches. |
| `sharing_actions.py` | "Sarah clicked something in the share modal — make it so." | All writes, as plain functions: add/remove grant, pending-email grant, set/narrow General access (+ warn-and-offer), transfer owner, bulk fan-out (a loop over the single-item functions). They change for the same reason — someone edited who has access — so they share a file. | Access *decisions* (it asks the resolver), rendering, request/approval flow (see below). |
| `api/access_api.py` | "An HTTP request arrived — who handles it?" | Thin routes: `@has_permission` → one call into the core files above → DTO. Mirrors the codebase's existing `api/` vs `core/` split. | Business logic of any kind. |

**Deliberately not files (yet):** transfer (~20 lines) and bulk (a loop) live inside `sharing_actions.py` — they don't earn separate files. Group membership logic sits with `groups_api.py`/the org app, matching existing convention. The request-access workflow (Milestone 9) gets its own `requests.py` **only if** `sharing_actions.py` feels crowded when we get there — decided then, not now.

Frontend: one hook, `useResourceAccess(rtype, id)`, is the only code that talks to `/api/access/*`; `ShareModal` renders off the capability flags the DTO echoes from `shareable_types.py` (public-link section appears for dashboards, silently absent for alerts — no per-type conditionals). We split ShareModal into child components only when it actually gets crowded.

### 4.1 New tables

```python
class ResourceShare(models.Model):                 # one grant
    org             = FK(Org, CASCADE)
    resource_type   = CharField(20)                # validated against shareable_types.py
    resource_id     = CharField(255)               # stringified pk; Layer 2 needs UUIDs + "schema.table" keys
    principal_type  = CharField(10)                # user | group | audience   (open enum — Layer 3 adds "attribute")
    principal_id    = BigIntegerField(null=True)   # OrgUser / UserGroup id
    principal_value = CharField(50, null=True)     # audience tier; future "region=North"
    permission      = CharField(5)                 # view | edit
    status          = CharField(10, default="active")   # active | pending
    pending_email   = CharField(255, null=True)
    created_by      = FK(OrgUser, SET_NULL, null=True); created_at = ...
    # indexes: (resource_type, resource_id), (principal_type, principal_id), (org, status)
```

Shape choices (all Layer 2/3 contracts — see roadmap §"five implications"): CharField(255) `resource_id`, generic `principal_value`, open `principal_type`. `audience`-type grants are valid (e.g. "grant Analysts+ Edit on this one dashboard"). No `via_container` — coverage shares don't exist in the dashboards-as-unit model.

**`UserGroup`** (`org`, `name`, `created_by`; unique (org, name)) + **`UserGroupMember`** (`orguser`/`pending_email`, status) — in the **org app**, so Layers 2–3 import groups without grant machinery.
**`AccessRequest`** (`org`, rtype, resource_id, requester, requested_permission, note, status, decided_by, expires_at).
**`RESOURCE_TYPES` table** (`core/sharing/shareable_types.py`) — rtype → model, capabilities; the shareable contract (string pk, general-access + owner accessors).

### 4.2 Columns on existing models

```python
# Dashboard, ReportSnapshot, Metric, KPI, Alert:
general_audience = CharField(15, default="all_users")   # private|admins|analysts_plus|all_users
general_level    = CharField(5,  default="view")        # view|edit
owner            = FK(OrgUser, SET_NULL, null=True, related_name="owned_%(class)ss")
# Chart: owner ONLY (delete + transfer). No general_*, no grants.
```

**Migration (M1, starts at 0168):**
- Add columns; backfill `owner = created_by`; backfill `general_*` from the org default (factory all_users/view — day-after behavior identical to day-before).
- **Flip `created_by` to SET_NULL** on the 5 CASCADE models — Dashboard (`dashboard.py:111`), Chart (`visualization.py:60`), Metric (`metric.py:62`), KPI (`metric.py:122`), Alert (`alert.py:90`); ReportSnapshot already SET_NULL. Without this, a transferred resource dies with its creator's account.
- Update `can_delete_resource()` (`core/ownership.py:5`) to check `owner_id` first, falling back to `created_by_id` — the six existing delete call-sites keep working unchanged.
- `OrgPreferences` (`models/org_preferences.py:7`) += `default_general_audience`, `default_general_level`, `allow_public_sharing` (default True).

### 4.3 Seed — new slugs

Add `can_share_reports`, `can_share_alerts`, `can_share_metrics`, `can_share_kpis` (joining the existing `can_share_dashboards`, pk 72; **no `can_share_charts`**). Admin + Analyst hold them; Member none. Data migration inserts `Permission` + `RolePermission` rows and **deletes the Redis key** (`ROLE_PERMISSIONS_REDIS_KEY`, default `dalgo_permissions_key`) — the middleware rebuilds it lazily on the next request (`auth.py:187`). Never call `set_roles_and_permissions_in_redis()` inside a migration (breaks Redis-less CI).

**Sequencing note:** existing installs must have run `migrate_rbac_v2_roles` (the Spec A management command) before this migration, so the role rows the seed references exist. Fresh installs are fine (3-role seed).

**Frontend twin:** add the four slugs to the `PERMISSIONS` const in `lib/rbac.tsx` — `hasPermission()` looks up by that const, and a missing entry fails silently.

### 4.4 Resolver (`core/sharing/access_resolver.py`)

`effective_permission(viewer, rtype, resource)` — in order: admin/super-admin → edit; owner (`owner_id or created_by_id`) → edit; general access if role tier meets audience; grants via **one** `principal_match_q(viewer)` predicate (shared by the resolver, the list filter, and any future caller); best level wins; **Member capped at View**; `getattr`-safe on null/legacy roles → default-deny, never 500. `ROLE_RANK` derives from role slugs, deliberately ≠ `Role.level`.

`accessible_filter(viewer, rtype)` — one-query Q for list endpoints: general-access tier match (excluding private) ∪ granted ids ∪ owned ∪ created. Wired into the five org-only list services (research §3): dashboards (`dashboard_service.py:273`), reports (`report_api.py:54`), alerts (`alert_api.py:192`), metrics (`metric_api.py:36`), KPIs (`kpi_api.py:46`). **Charts keep today's role-gated list** (`chart_service.py:88`) — no filter change.

**Caching (D — injected, not hardwired):** the resolver takes a `get_group_ids(viewer)` callable; the default implementation caches in Redis via `RedisClient` (`utils/redis_client.py:9`, short TTL, busted on grant/general/group/transfer changes). Unit tests pass a stub — no Redis needed to test access logic.

### 4.5 Narrowing General access (warn-and-offer — spec Flow 2)

**The rule:** narrowing never silently drops or silently keeps direct shares.
**Example:** Anjali narrows "Field Performance" from All users to Admins only. The API's first response lists the Funders-group grant that would keep Sarah in; Anjali picks "remove them too" and the client re-sends with `remove_grant_ids`.
**Why it matters:** "make it private" must actually lock it down — leftover grants are the classic over-share bug.

`PUT …/general` with a narrower audience returns the persisting grants; the client re-sends with `remove_grant_ids`. The bulk variant aggregates across a selection (one prompt, per-resource ids).

### 4.6 Invitations, requests, comments, alerts

- **Invites:** add `Invitation.expires_at` (now + 30 days); expiry check in `accept_invitation_v1` (`orguserfunctions.py:281`); daily cleanup task (match pending `ResourceShare` rows by `invited_by__org` + email — Invitation has no org FK); `resend_invitation` (`:365`) refreshes `expires_at`. **Existing-user emails never reach accept** (`invite_user_v1` short-circuits) → the share endpoint resolves existing users first; pending rows flip to active in both paths. **Close the 2 ≥ 2 loophole** (`orguserfunctions.py:223`): the share-modal invite path adds an explicit "non-Admin invites Member only" check — today's `level ≥ level` cap would let an Analyst invite an Analyst.
- **Requests:** notify the **owner** via `create_notification()` (`notifications_functions.py:114`); approve inserts a grant (all shareable rtypes incl. metric/kpi — the alert click-through case); unauthenticated visitors get a sign-in prompt; requests expire in 30 days.
- **Comments (re-gate):** `create_comment` (`report_api.py:399`) requires `can_edit_dashboards`, which Members lack → **relax** create/read to `can_view_dashboards` + resolver-View on the snapshot. Moderation of others' comments = resolver-Edit — a real `CommentService` change (`comment_service.py:147-148, :172-173` are author-only today). Anonymous/public viewers stay blocked (authenticated router) — verify in tests.
- **Alerts:** `recipients` JSON stays the delivery store; gains `{"type": "group"}` entries expanded at fire time; the notification carries trigger context. `ResourceShare` governs alert *config* access only — recipient status grants no resource access.
- **Metric/KPI general access is standalone-only** — never consulted during chart render (references ≠ shares).

### 4.7 Frontend

| Surface | Change |
|---|---|
| `components/ui/share-modal.tsx` | extend: "People with access" rows (add/remove users & groups at View/Edit), **General access** two-dropdown row, invite-role picker (client-side cap: non-Admin → Member only), pending chips, Transfer Ownership row, inline requests (approve/deny). Keep the existing public-toggle section, now hidden when the org global is off |
| Reports share entry | **unify onto the extended ShareModal** (replacing `report-share-menu.tsx`'s link dialog; keep email-PDF as an action inside the modal) — §8 Q1 confirms |
| dashboard/report/alert lists | General-access badge, 🔒 Private, "Shared with you" (Members), multi-select bulk bar — copy the Charts-page pattern (`app/charts/page.tsx:115-132`); re-scope `dashboard-list-v2.tsx`'s "Show only shared" filter (today it means `is_public`, `:271`) |
| dashboard tiles | pass `dashboard_id` (access context) on chart data/detail calls |
| Charts page | unchanged for Analyst+; nav item + route hidden for Members (§8 Q4, Design to confirm) |
| Groups settings | **new** `app/settings/groups` — CRUD, membership, name-collision, member count, resources-shared-with count; Analyst+ create, creator + Admin manage |
| request-access | **new**: intercept 403 on dashboard/report/alert/metric/kpi detail (403 currently throws a generic error — `lib/api.ts:146-191`); screen requests View/Edit + note; sign-in prompt when anonymous |
| transfer modal | confirm dialog; no reclaim copy |
| Access Mgmt settings | "Allow public sharing" global + org-default General-access picker (Admin-only, `RoleGuard`) |
| comments | moderation affordances by resolver level; `CommentPopover` gains a `readOnly`/capability prop (gating is at render sites today, keyed to `CAN_EDIT_DASHBOARDS` — `app/reports/[snapshotId]/page.tsx:40,220`) |
| `lib/rbac.tsx` | add the four new slugs to `PERMISSIONS` |

**Figma amendments needed (§8 Q3):** remove the two warning-modal frames (embed/broadening — obsolete), remove reclaim copy from the transfer flow, fix the `PEOLPE` typo, delete-group copy, and the doubled-A security notice.

---

## 5. Security Review

| Concern | Assessment |
|---|---|
| AuthZ | every access endpoint = `@has_permission(can_share_*)` (`auth.py:39`) **+** resolver `can_edit()` on the object — slug gates the route, resolver gates the object |
| Server-side truth | resolver gates lists/detail/tiles/writes; UI hiding (`PermissionGuard`) is defense-in-depth only |
| Re-share cap | grant at most your own effective level; enforced server-side |
| **Chart exposure (new model)** | putting a chart on a dashboard **is** publication to that dashboard's audience — by design there is no silent-leak *mechanism* left to guard. Residual risk (an editor forgets a dashboard's audience) is accepted; data-level protection = Layer 2. PM sign-off = the spec Q0 amendment (§8). |
| `dashboard_id` context | must verify chart-membership AND viewer's dashboard-View — else the param is an oracle for reading arbitrary charts by id |
| Multi-tenant | org FK on every new table; org-filtered queries; audience grants resolve in-org only; `x-dalgo-org` header only selects the org — the backend still authorizes per-org |
| Invite-tier cap | explicit non-Admin → Member check on the share-invite path (the live `2 ≥ 2` loophole at `orguserfunctions.py:223` documented in research §3) |
| Kill switch | all four endpoints check the global: both toggles (`dashboard_native_api.py:394`, `report_api.py:267`) AND both public renders (`public_api.py:95`, `:1105`, plus `:199` chart data) |
| Null/legacy roles | resolver default-denies, never 500s |
| Transfer | owner/Admin only; same-org active user; no reclaim; `created_by` SET_NULL so transfers survive creator deletion |
| Injection / PII | ORM-only; length-bounded strings; no new PII (pending emails are already stored by Invitation today) |

---

## 6. Testing Strategy

**Backend (pytest):** resolver truth-table as **pure-function tests** (stub `get_group_ids`, no Redis, no HTTP — possible because of §3.4's D rule) covering owner / admin / general / user-grant / group-grant / audience-grant / Member-cap / private / null-role / legacy-slug · shareable-types contract test: every registered rtype satisfies the shareable contract (string pk, `general_*`, owner accessor) and every capability flag is honored by the endpoints (grant on a `grants=False` rtype → 400, not 500) · list scoping + query-count on all five lists · **chart context**: Member with dashboard-View gets tile data with `dashboard_id`, 403 without; wrong-dashboard id → 403; charts absent from Member's world · narrowing warn-and-offer (single + bulk aggregate) · invite expiry + existing-user immediate activation + resend refresh + the non-Admin→Member cap · transfer (+ creator-deletion survival via SET_NULL, no reclaim route) · comments re-gate (Member-View creates; View can't moderate others'; resolver-Edit can) · kill switch (toggle blocked AND existing token render dies) · alert group-recipient fire-time expansion · seed migration idempotent on a fresh install *and* after `migrate_rbac_v2_roles`.
**Frontend (Vitest):** ShareModal states (people/general/pending/transfer/requests); badges; bulk summary; tiles pass context; 403 interception renders request-access; `PERMISSIONS` const covers the new slugs.
**E2E (Playwright):** share with a 30-person group in under 60s · Member sees only "Shared with you" · request-access round-trip · narrow-then-remove flow.
**Edge:** group deleted mid-share; user leaves a group but holds a direct grant; pending-then-expired invite; org with public sharing disabled mid-flight.

---

## 7. Milestones

M1–M4 are the core viewer flow (ship together to `feature/rbac`'s successor branch); M5+ are additive, same release. Layer 2 unblocks after M1–M3.

#### Milestone 1: General access + owner + resolver + org defaults (backend)
- **Deliverable:** every list and detail endpoint respects General access; ownership is a real, transferable column.
- **Services:** DDP_backend.
- **Key tasks:**
  - [ ] Migrations from 0168: `general_*` + `owner` on 5 models; `owner` on Chart; backfills; `created_by` → SET_NULL ×5; OrgPreferences ×3
  - [ ] `can_delete_resource()` reads `owner_id` first
  - [ ] `RESOURCE_TYPES` table (`shareable_types.py`) + resolver (`access_resolver.py`) + `principal_match_q` + `accessible_filter` into 5 lists
  - [ ] `dashboard_id` access context on chart data/detail; Member standalone → 403; `run_chart_query` seam
- **Acceptance:** Member sees only admitted resources; tiles work via context, standalone 403s; one query per list; day-after behavior = day-before for Analyst+/Admin.

#### Milestone 2: Grants + share modal core + badges (backend + frontend)
- **Deliverable:** share a dashboard with a person at View/Edit from the modal.
- **Key tasks:** `ResourceShare`; `/api/access/{rtype}/{id}` + `/grants` + `/general` (narrow warn-and-offer); seed slugs (Redis-key delete) + `PERMISSIONS` const; DTO fields; badges + "Shared with you"; modal people-rows + access-path view.
- **Acceptance:** share with a user at View; removing one grant leaves the rest; narrowing prompts.

#### Milestone 3: Groups (backend + frontend)
- **Deliverable:** create "Funders" once, share a dashboard with it in one action.
- **Key tasks:** models in the org app; CRUD + membership + name-collision; `app/settings/groups` page with counts.

#### Milestone 4: Invites + pending + expiry (backend + frontend)
- **Deliverable:** paste 30 emails → invited as Members, group-added, active on accept; existing users instant.
- **Key tasks:** paste-emails in modal; invite-role cap (non-Admin → Member only, client + server); pending chips; `expires_at` + both activation paths + resend refresh + daily cleanup task.

#### Milestone 5: Public links — org global + kill switch
- **Deliverable:** Admin turns the global off → toggles hidden AND old links dead.
- **Key tasks:** `allow_public_sharing` checked in both toggles + all public renders; Access-Mgmt settings global + org-default General-access picker; unify reports onto ShareModal.

#### Milestone 6: Ownership transfer
- **Deliverable:** transfer → new owner deletes/transfers; old owner keeps Edit; creator deletion safe.
- **Key tasks:** `/owner` endpoint + modal row + confirm; no reclaim.

#### Milestone 7: Alerts
- **Deliverable:** alert recipient without access lands on request-access.
- **Key tasks:** general access + owner + config grants; group recipients expanded at fire time; trigger-context in the notification.

#### Milestone 8: Comments re-gate
- **Deliverable:** a view-only Member comments on a report; can't hide others'; a report editor can.
- **Key tasks:** relax `create_comment` to `can_view_dashboards` + resolver-View; `CommentService` moderation by resolver-Edit; `CommentPopover` capability prop; verify anonymous block.

#### Milestone 9: Request-access
- **Deliverable:** request → owner approves → grant + notification.
- **Key tasks:** `AccessRequest` (rtypes incl. metric/kpi); 403 intercept + screen; sign-in prompt when anonymous; owner notification; approve (level pick) / decline; 30-day expiry.

#### Milestone 10: Bulk
- **Deliverable:** "Shared 8 of 10 — 2 skipped"; one aggregated narrow prompt.
- **Key tasks:** `/api/access/bulk` (per-resource Edit check, applied/skipped counts, aggregated narrow); multi-select bars on Dashboards/Reports/Alerts (copy Charts pattern); public toggle for public-linkable rtypes only.

#### Milestone 11: Migration verify + browser pass
- **Key tasks:** backfills verified (100% owner + general coverage); check for legacy email-share rows (migrate 1:1 if any exist); **stop and ask the user** before a Playwright-MCP pass across all three roles.

---

## 8. Open Questions & Risks

**Q0 — spec amendment (PM sign-off pending):** the spec still describes chart-level sharing (Flow 3 embed warning, broadening warnings, "lock a chart to Private" story, §Scope's "Member with an Edit floor can re-share"). The 2026-07-02 decisions delete all of that; the spec needs its Q0 rewrite before `/engineering/validate-spec` runs against it.

**Open:**
1. **Q1 — Reports share UI unification:** replace `ReportShareMenu` with the extended `ShareModal` (recommended, M5) or keep the dropdown and add a "Manage access" item? Plan assumes unify.
2. **Q2 — Edit-level General access lets everyone covered re-share** (accept + document, per spec's re-share rule).
3. **Q3 — Figma amendments** (remove 2 warning-modal frames, reclaim copy, `PEOLPE` typo, delete-group copy, security-notice doubled-A).
4. **Q4 — Member's Charts nav hidden** — Design to confirm (Members currently see the Charts nav + full org chart list via `can_view_charts`; the new model closes both).
5. **Q5 — cache-bust integration test** for the group-ids Redis cache.

**Risks:**
- **Stacked-branch coordination:** this work branches off `feature/rbac` while Spec A's PRs are open. If Spec A gets review changes, this branch must rebase. Mitigation: merge #1414/#331 promptly, or keep rebases small per milestone.
- **Migration ordering on existing installs:** the seed migration assumes `migrate_rbac_v2_roles` has run. Document in the release runbook; the migration should fail loudly (not silently skip) if legacy role pks are found.
- **`created_by` SET_NULL flip** touches 5 models with CASCADE today — verify no code path relies on cascade-deletion of resources when an OrgUser is removed (user-deletion flow test in M1).

---

Draft v1 saved. Review and tell me what to revise. When ready, run `/engineering/execute-plan features/access-control/content/plan.md`.

> **Post-build (M11):** stop and ask before the Playwright-MCP browser pass.
