# Plan — Resource Sharing (Access Control, Layer 1: Content) — v1

**Status:** Draft v1 (2026-07-06, restructured 2026-07-07) — re-planned from the **`feature/rbac` branch baseline**. Carries forward all product decisions from the 2026-07-02 review (recorded in [../ACCESS-MODEL-ROADMAP.md](../ACCESS-MODEL-ROADMAP.md)); supersedes the earlier deleted draft.

| Link | What it is |
|---|---|
| [resource-sharing-write-spec-2026-06-17.md](./resource-sharing-write-spec-2026-06-17.md) | The spec this plan implements |
| [Spec B](./access-control-spec-B-resource-sharing-2026-06-02.md) | The full product vision (superset of this plan) |
| [research.md](./research.md) | Codebase facts, verified on `feature/rbac` (2026-07-06) — every `file:line` in this plan comes from there |
| [../ACCESS-MODEL-ROADMAP.md](../ACCESS-MODEL-ROADMAP.md) | The 3-layer roadmap; records the 2026-07-02 decisions |
| [../dataset-access/plan.md](../dataset-access/plan.md) | Layer 2 — waits on this plan's M1–M3 and inherits `ResourceShare`, `UserGroup`, the resolver + shareable-types table, and the `run_chart_query` seam |

**Builds on:** Spec A (the 3-role system) — lives on the **`feature/rbac` branch**, PRs still open (DDP_backend [#1414](https://github.com/DalgoT4D/DDP_backend/pull/1414), webapp_v2 [#331](https://github.com/DalgoT4D/webapp_v2/pull/331)). This work stacks on that branch, not on main.

✅ The write-spec carries the **Q0 amendment** (v1.1, 2026-07-07 — charts are not independently shareable). Spec B remains unamended by design (historical vision doc).

---

## 0. How to read this plan

**If you're new to the feature:** read the Glossary below, then §1 (what we're building), §3.1 (the one rule everything follows), and §4.0 (which file does what). That's enough to pick up any task.

**If you're reviewing the design:** §3.4 (the five SOLID rules — they're the PR review criteria), §5 (security), §8 (open questions).

**If you're implementing a milestone:** §7 names your milestone; §4 has the code-level detail; every `file:line` reference is verified in [research.md](./research.md).

### Glossary — the ten terms this plan uses

| Term | Plain meaning | Example |
|---|---|---|
| **Shareable resource** | A thing that can appear in the share modal: Dashboard, Report, Alert (fully), Metric/KPI (General access only). **Not Chart.** | Anjali opens "Share" on the "Field Performance" dashboard. |
| **General access** | The resource's audience dial: *who in the org* (audience) × *what they may do* (level). Google Drive's "General access" section, same idea. | "Analysts and up can **view**" — Priya (Analyst) sees it; Sarah (Member) doesn't. |
| **Audience** | The "who" half of General access: `private` \| `admins` \| `analysts_plus` \| `all_users`. | `all_users` = every member of the org. |
| **Level** | The "what" half: `view` or `edit`. | View = look; Edit = change, re-share. |
| **Grant** | One row saying "this person / group / tier gets View-or-Edit on this one resource". Stored in the `ResourceShare` table. | "The Funders group → View on Field Performance." |
| **Principal** | Whoever a grant points at. In v1: a **user** or a **group**. The model's shape also admits `audience` and (Layer 3) `attribute` principals — schema-ready, behavior deferred (§1.1). | The Funders group is the principal in the grant above. |
| **Owner** | The one person with full control (edit, delete, transfer). A new column, separate from `created_by` (who made it — a historical fact that never changes). | Priya created it, then transferred it — Sarah is now `owner`; `created_by` still says Priya. |
| **Resolver** | The one read-only function that answers "can this viewer view/edit this resource?" Every list, page, tile, and write-guard asks it. | See the decision ladder in §4.4. |
| **rtype** | The resource-type string in URLs and the grants table: `dashboard`, `report`, `alert`, `metric`, `kpi`. | `PUT /api/access/dashboard/42/general` |
| **Kill switch** | One org-wide setting (`allow_public_sharing`) that disables public links everywhere — including links that already exist. | Admin Raj flips it off → every public dashboard link stops rendering, immediately. |

**Acronyms:** FK (foreign key — a DB column pointing at another table's row) · DTO (the JSON shape an API returns) · RLS (row-level security — Layer 3) · PII (personal data) · TTL (cache lifetime).

### The whole feature in one picture

```
                       "Can Sarah see the Field Performance dashboard?"
                                          │
                                          ▼
                              access_resolver (one function)
                                          │
        ┌──────────────────┬──────────────┼───────────────────┐
        ▼                  ▼              ▼                   ▼
   Is she Admin?      Is she the      General access     Any grant rows?
   (always Edit)      owner?          admit her tier?    (her, her groups,
                      (always Edit)   (dial on the       her tier)
                                      resource)
        └──────────────────┴──────────────┴───────────────────┘
                                          │
                              take the BEST answer found;
                              if she's a Member, cap at View
```

---

## 1. Overview

**What we're building:** who can View or Edit each content resource.

> **The rule:** shareable resources get **General access** (audience × level) plus **direct grants** to people and groups; charts are **not** independently shareable — a chart is visible wherever its dashboards are visible (2026-07-02 decision).
> **Example:** Anjali sets "Field Performance" to *Analysts+ / View* and additionally grants the Funders group View. Every chart on that dashboard renders for those viewers automatically — no per-chart settings exist.
> **Why it matters:** one sharing unit (the dashboard) means no chart-vs-dashboard permission mismatches, which deleted an entire class of warning modals from the spec.

One share modal does sharing + inviting in one place. Groups, public links (Dashboards + Reports, under one Admin global), ownership transfer, request-access, bulk sharing, and comments on Reports complete the surface.

### 1.1 Decisions carried forward (2026-06-30 / 2026-07-02, recorded in the roadmap)

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
| Audience grants (2026-07-08) | **Schema-ready, behavior deferred.** The open principal model stays (Layer 3 contract), but v1 creates and matches only `user` and `group` principals — no endpoint accepts `audience`, the resolver ignores such rows. Enabling later = one resolver clause + endpoint validation, no schema change. |

### 1.2 Where we are (the `feature/rbac` baseline — research §1, §4)

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

### 1.3 Services and branches

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

> **The rule:** access to a shareable resource = **general access ∪ direct grants ∪ owner/admin override**, at the most permissive level any path gives — and a Member never exceeds View.
> **Example:** "Field Performance" has General access = Analysts+ / View. Priya (Analyst) can view it. The Funders group holds a View grant, so funder Sarah (Member) sees it too. Anjali owns it (Edit + delete + transfer). Admin Raj can do everything, everywhere.
> **Why it matters:** one resolver answers every access question — lists, detail pages, dashboard tiles, write guards — so there is exactly one place to get right.

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

SOLID (Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion) is not decoration here — Layers 2 and 3 only stitch in cleanly if these five rules hold. **Each row is a review criterion for every PR in §7.**

| Principle | The rule in this design | Concrete example |
|---|---|---|
| **S** — one job per module | The resolver only *answers* access questions — pure function, no writes, no notifications, no HTTP. Every mutation lives in `sharing_actions.py` (§4.0); API functions stay thin (validate → call the action → serialize). | `effective_permission()` never sends the "you got access" notification — the approve-request action does, by calling `create_notification()` after inserting the grant. |
| **O** — extend by data, not edits | New shareable types are **rows in `shareable_types.py`**, never resolver edits. The resolver branches on data (`general_*` fields + share rows + capability flags), never on `if resource_type == "dashboard"`. Same for principals: one `principal_match_q()` predicate; a new principal kind extends that one function. | Layer 2 adds `dataset` by registering `("dataset", Dataset, caps={general, grants})` — zero lines change in `access_resolver.py`. Layer 3's `attribute` principal ("region = North") lands only in `principal_match_q()`. |
| **L** — every registered type behaves identically | Anything in the shareable-types table must honestly satisfy the shareable contract (string pk, `general_audience`/`general_level`, owner accessor). No registered type may raise "not supported" from a contract method. Types that *can't* fulfil the contract stay out of the table — they aren't special-cased inside it. | Chart is **not registered** (rather than registered-but-throws-on-grants); Metric/KPI are registered with `grants=False` as a declared capability, so the share endpoint rejects a grant on a metric by *reading the flag*, not by knowing what a metric is. |
| **I** — small capability flags, not one fat interface | Each type declares narrow capabilities — `general`, `grants`, `public_link`, `requests` — instead of one all-or-nothing "Shareable" interface. Consumers check only the capability they need. | The share modal renders its public-link section off `public_link: true` (dashboards, reports) and simply omits it for alerts — no `entityType === 'alert'` conditionals in the modal. |
| **D** — depend on the seam, not the concrete | Endpoints depend on the resolver; the resolver depends on the shareable contract (it never imports `Dashboard`); chart execution depends on the `run_chart_query` hook; the resolver's group-membership cache is an injected callable so tests run without Redis. | Layer 2's dataset check plugs into `run_chart_query` without touching `charts_api.py`; resolver unit tests pass a stub `get_group_ids=lambda u: {…}`. |

**Why it matters:** the roadmap's "five get-this-right-now implications" are exactly these principles applied — break one (say, a `resource_type` branch inside the resolver) and Layer 2 becomes a rewrite instead of a one-row addition.

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

| File | The one question it answers | What lives in it | What must NEVER live in it |
|---|---|---|---|
| `shareable_types.py` | "What things can be shared, and what can you do with each?" | The `RESOURCE_TYPES` table: rtype → model + capability flags (`general`, `grants`, `public_link`, `requests`). The **only** place resource types are enumerated. Layer 2 adds `dataset` here as one entry. | Any logic. It's data. |
| `access_resolver.py` | "Can Priya view or edit this dashboard — yes or no?" | `effective_permission`, `accessible_filter`, `principal_match_q`. Pure and read-only: looks at owner + General access + grant rows, returns an answer. Truth-table tested without Redis or HTTP. Layer 2/3 import it. | Writes, notifications, HTTP, `if resource_type == "dashboard"` branches. |
| `sharing_actions.py` | "Sarah clicked something in the share modal — make it so." | All writes, as plain functions: add/remove grant, pending-email grant, set/narrow General access (+ warn-and-offer), transfer owner, bulk fan-out (a loop over the single-item functions). They change for the same reason — someone edited who has access — so they share a file. | Access *decisions* (it asks the resolver), rendering, request/approval flow (see below). |
| `api/access_api.py` | "An HTTP request arrived — who handles it?" | Thin routes: `@has_permission` → one call into the core files above → DTO. Mirrors the codebase's existing `api/` vs `core/` split. | Business logic of any kind. |

**Deliberately not files (yet):** transfer (~20 lines) and bulk (a loop) live inside `sharing_actions.py` — they don't earn separate files. Group membership logic sits with `groups_api.py`/the org app, matching existing convention. The request-access workflow (Milestone 9) gets its own `requests.py` **only if** `sharing_actions.py` feels crowded when we get there — decided then, not now.

**Frontend:** one hook, `useResourceAccess(rtype, id)`, is the only code that talks to `/api/access/*`; `ShareModal` renders off the capability flags the DTO echoes from `shareable_types.py` (public-link section appears for dashboards, silently absent for alerts — no per-type conditionals). We split ShareModal into child components only when it actually gets crowded.

### 4.1 New tables

**Entity relationship diagram** — the 4 new tables, the new columns on existing models, and how they connect. "Soft link" = the column stores a type name + stringified id (`"dashboard"`, `"42"`) instead of a real FK — the deliberate Layer 2/3 trade-off explained under the `ResourceShare` shape choices below.

```
┌──────────────────────────────────── Org ────────────────────────────────────┐
│   every table below carries an org FK — hard multi-tenant isolation          │
│   OrgPreferences (1:1): + default_general_audience, default_general_level,   │
│                          + allow_public_sharing (the kill switch)            │
└──────────────────────────────────────────────────────────────────────────────┘

  RESOURCES (existing models, new columns)              PEOPLE
┌─────────────────────────────────┐             ┌────────────────────┐
│ Dashboard │ ReportSnapshot │    │             │      OrgUser       │
│ Metric    │ KPI  │ Alert       │◄────owner────│  (existing)        │
│  + general_audience             │  (SET_NULL)  └──┬──────────────┬──┘
│  + general_level                │                 │              │
│  + owner (FK OrgUser)           │        requester│       member │ N:M via
│  (created_by: CASCADE→SET_NULL) │                 │              ▼
├─────────────────────────────────┤                 │   ┌──────────────────┐
│ Chart: + owner ONLY             │                 │   │ UserGroupMember  │
│ (no general_*, no grants —      │                 │   │  orguser FK OR   │
│  rides along with dashboards)   │                 │   │  pending_email   │
└───────────────┬─────────────────┘                 │   └────────┬─────────┘
                │                                   │            │ N:1
                │ soft link:                        │   ┌────────▼─────────┐
                │ (resource_type, resource_id)      │   │    UserGroup     │
                │  — no FK, string pk               │   │ unique(org,name) │
                ▼                                   │   └────────┬─────────┘
┌─────────────────────────────────┐                 │            │
│         ResourceShare           │                 │            │
│  resource_type  + resource_id ──┼── points at any resource     │
│  principal_type: user|group|…  ─┼── points at OrgUser ─────────┤
│  principal_id / principal_value │        or UserGroup ─────────┘
│  permission: view | edit        │        (soft link too)
│  status: active | pending       │
│  pending_email (invite flow)    │
└─────────────────────────────────┘
                ▲
                │ approving a request INSERTS a grant here
┌───────────────┴─────────────────┐
│         AccessRequest           │
│  resource_type + resource_id    │
│  requester FK OrgUser           │
│  requested_permission, note     │
│  status, decided_by, expires_at │
└─────────────────────────────────┘
```

Reading the diagram: `general_audience`/`general_level` live as **columns on the resource** (every resource has exactly one General-access setting — that's a column, and list queries check it with zero joins), while explicit shares are **rows in `ResourceShare`** (a resource can have many). The resolver (§4.4) combines both plus the owner/admin override, best answer wins.

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

Shape choices (all Layer 2/3 contracts — see roadmap §"five implications"): CharField(255) `resource_id`, generic `principal_value`, open `principal_type`. **`audience`-type grants are schema-valid but behavior-deferred** (2026-07-08 decision, §1.1): no v1 endpoint creates them and the resolver does not match them — the endpoint rejects `principal_type="audience"` with a 400, and a test pins that a manually-inserted audience row grants nothing. No `via_container` — coverage shares don't exist in the dashboards-as-unit model.

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

**Migration (M1, starts at 0168)** — four steps, and why each is needed:

| Step | What breaks without it |
|---|---|
| Add columns; backfill `owner = created_by`; backfill `general_*` (factory `all_users`/`view`) | No owner → nothing to transfer, delete rights can't move. Backfills mean day-after behavior = day-before: nobody gets locked out by the migration. |
| **Flip `created_by` to SET_NULL** on the 5 CASCADE models — Dashboard (`dashboard.py:111`), Chart (`visualization.py:60`), Metric (`metric.py:62`), KPI (`metric.py:122`), Alert (`alert.py:90`); ReportSnapshot already SET_NULL | Today, deleting Priya's account **silently deletes every dashboard, chart, and alert she created** — even org-critical ones, even ones she transferred away. This is a live bug the feature makes fatal (transfer would be a lie). Behavior change on its own — flag in the PR description. |
| Update `can_delete_resource()` (`core/ownership.py:5`) to check `owner_id` first, falling back to `created_by_id` | Sarah becomes owner via transfer but still can't delete — the check only knows `created_by`. One edit fixes all six existing delete call-sites at once. |
| `OrgPreferences` (`models/org_preferences.py:7`) += `default_general_audience`, `default_general_level`, `allow_public_sharing` (default True) | Org-level defaults for new resources + the kill switch. UI lands in M5, but adding the columns now means the "read the org default" code is written once. |

### 4.3 Seed — new permission slugs

Add `can_share_reports`, `can_share_alerts`, `can_share_metrics`, `can_share_kpis` (joining the existing `can_share_dashboards`, pk 72; **no `can_share_charts`**). Admin + Analyst hold them; Member none.

> **The rule:** the data migration inserts `Permission` + `RolePermission` rows and **deletes the Redis key** (`ROLE_PERMISSIONS_REDIS_KEY`, default `dalgo_permissions_key`); the middleware rebuilds it lazily on the next request (`auth.py:187`).
> **Why it matters:** calling `set_roles_and_permissions_in_redis()` inside a migration breaks Redis-less CI — key-delete is the established safe pattern.

**Sequencing note:** existing installs must have run `migrate_rbac_v2_roles` (the Spec A management command) before this migration, so the role rows the seed references exist. Fresh installs are fine (3-role seed).

**Frontend twin:** add the four slugs to the `PERMISSIONS` const in `lib/rbac.tsx` — `hasPermission()` looks up by that const, and a missing entry fails silently.

### 4.4 Resolver (`core/sharing/access_resolver.py`)

`effective_permission(viewer, rtype, resource)` walks this ladder and returns `edit`, `view`, or nothing:

```
1. Admin / super-admin?                          → Edit  (org-wide override)
2. Owner? (owner_id, falling back to created_by) → Edit
3. General access admits viewer's role tier?     → the resource's general_level
4. Grant rows matching the viewer?               → best level among them
   (her user id, her groups' ids — via ONE principal_match_q(viewer)
    predicate, shared with the list filter; audience rows are NOT
    matched in v1 — deferred, §1.1)
5. Take the highest level steps 3–4 produced;
   viewer is a Member?                           → cap at View
6. Nothing matched, or role is null/legacy?      → no access (default-deny, never a 500)
```

Notes: `ROLE_RANK` derives from role slugs, deliberately ≠ `Role.level`. All role reads are `getattr`-safe so a null/legacy role denies instead of crashing.

`accessible_filter(viewer, rtype)` — the same logic as **one ORM Q object** for list endpoints (one query, no N+1): general-access tier match (excluding private) ∪ granted ids ∪ owned ∪ created. Wired into the five org-only list services (research §3): dashboards (`dashboard_service.py:273`), reports (`report_api.py:54`), alerts (`alert_api.py:192`), metrics (`metric_api.py:36`), KPIs (`kpi_api.py:46`). **Charts keep today's role-gated list** (`chart_service.py:88`) — no filter change.

**Caching (the D rule — injected, not hardwired):** the resolver takes a `get_group_ids(viewer)` callable; the default implementation caches in Redis via `RedisClient` (`utils/redis_client.py:9`, short TTL, busted on grant/general/group/transfer changes). Unit tests pass a stub — no Redis needed to test access logic.

### 4.5 Narrowing General access (warn-and-offer — spec Flow 2)

> **The rule:** narrowing never silently drops or silently keeps direct shares.
> **Example:** Anjali narrows "Field Performance" from All users to Admins only. The API's first response lists the Funders-group grant that would keep Sarah in; Anjali picks "remove them too" and the client re-sends with `remove_grant_ids`.
> **Why it matters:** "make it private" must actually lock it down — leftover grants are the classic over-share bug.

`PUT …/general` with a narrower audience returns the persisting grants; the client re-sends with `remove_grant_ids`. The bulk variant aggregates across a selection (one prompt, per-resource ids).

### 4.6 The four side-flows

**Invites (share modal can invite non-members):**
- Add `Invitation.expires_at` (now + 30 days); expiry check in `accept_invitation_v1` (`orguserfunctions.py:281`); `resend_invitation` (`:365`) refreshes `expires_at`; daily cleanup task (match pending `ResourceShare` rows by `invited_by__org` + email — Invitation has no org FK).
- **Existing-user emails never reach accept** (`invite_user_v1` short-circuits) → the share endpoint resolves existing users first; pending rows flip to active in both paths.
- **Close the 2 ≥ 2 loophole** (`orguserfunctions.py:223`): today's cap is `inviter.level ≥ invitee.level`, so an Analyst (level 2) can invite another Analyst (level 2). The share-modal invite path adds an explicit "non-Admin invites Member only" check.

**Access requests:**
- Requester hits a locked resource → request lands with the **owner** via `create_notification()` (`notifications_functions.py:114`).
- Approve inserts a grant (all shareable rtypes incl. metric/kpi — the alert click-through case); owner can downgrade Edit→View. Unauthenticated visitors get a sign-in prompt. Requests expire in 30 days.

**Comments on Reports (re-gate):**
- Create is gated by `can_edit_dashboards` today (`report_api.py:399`) — Members can't comment at all. **Relax** create/read to `can_view_dashboards` + resolver-View on the snapshot.
- Moderating *others'* comments = resolver-Edit — a real `CommentService` change (`comment_service.py:147-148, :172-173` are author-only today).
- Anonymous/public viewers stay blocked (authenticated router) — verify in tests.

**Alerts:**
- `recipients` JSON stays the delivery store; gains `{"type": "group"}` entries expanded at fire time; the notification carries trigger context.
- `ResourceShare` governs alert *config* access only — being a recipient grants no resource access.
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
| Chart-tile payloads (added during build, 2026-07-11) | Context-admitted viewers (Members on dashboard tiles) can only reference columns from the saved chart's config — a column-set guard 403s anything else. **A chart's saved filters (`extra_config.filters`) are NOT a confidentiality boundary:** a context viewer can re-query displayed columns with the saved WHERE clause dropped or altered (row-set widening within displayed columns). Example: a tile shows counts of `beneficiaries WHERE status=active`; a Member can also get counts for `status=suspended` — but can never read `phone_number` if the chart doesn't display it. Row-level policy belongs to Layer 2/3 at the `run_chart_query` seam. Do not use saved chart filters to hide sensitive rows. |

---

## 6. Testing Strategy

**Backend (pytest)** — the resolver truth-table runs as **pure-function tests** (stub `get_group_ids`, no Redis, no HTTP — possible because of §3.4's D rule):

| Area | What we prove |
|---|---|
| Resolver truth table | owner / admin / general / user-grant / group-grant / Member-cap / private / null-role / legacy-slug — every cell of the ladder in §4.4 — **plus:** a manually-inserted `audience` grant row grants nothing (deferred behavior stays off), and the grants endpoint 400s on `principal_type="audience"` |
| Shareable-types contract | every registered rtype satisfies the contract (string pk, `general_*`, owner accessor); every capability flag is honored by the endpoints (grant on a `grants=False` rtype → 400, not 500) |
| List scoping | all five lists show exactly the admitted resources, **one query each** (query-count asserted) |
| Chart context | Member with dashboard-View gets tile data with `dashboard_id`; 403 without; wrong-dashboard id → 403; charts absent from Member's world |
| Narrowing | warn-and-offer round-trip, single + bulk aggregate |
| Invites | expiry, existing-user immediate activation, resend refresh, the non-Admin→Member cap |
| Transfer | new owner's powers; creator-deletion survival via SET_NULL; no reclaim route exists |
| Comments | Member-View creates; View can't moderate others'; resolver-Edit can |
| Kill switch | toggle blocked AND existing token render dies |
| Alerts | group recipients expanded at fire time |
| Seed migration | idempotent on a fresh install *and* after `migrate_rbac_v2_roles` |
| User deletion | deleting an OrgUser no longer cascades their content (the SET_NULL flip, §4.2) |

**Frontend (Vitest):** ShareModal states (people/general/pending/transfer/requests) · badges · bulk summary · tiles pass `dashboard_id` · 403 interception renders request-access · `PERMISSIONS` const covers the new slugs.

**E2E (Playwright):** share with a 30-person group in under 60s · Member sees only "Shared with you" · request-access round-trip · narrow-then-remove flow.

**Edge cases:** group deleted mid-share · user leaves a group but holds a direct grant · pending-then-expired invite · org disables public sharing mid-flight.

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

**Q0 — spec amendment: ✅ RESOLVED (2026-07-07).** The write-spec is amended in place (v1.1, amendment note at top): charts not shareable (Flow 3 rewritten, warning modals deleted), "floor" → "General access", Member View-cap made explicit, kill-switch semantics written into the public-links rule and Admin story. `/engineering/validate-spec` can now run against it. [Spec B](./access-control-spec-B-resource-sharing-2026-06-02.md) is deliberately unamended — historical vision doc only.

**Open:**
1. **Q1 — Reports share UI unification:** replace `ReportShareMenu` with the extended `ShareModal` (recommended, M5) or keep the dropdown and add a "Manage access" item? Plan assumes unify.
2. **Q2 — Edit-level General access lets everyone covered re-share** (accept + document, per spec's re-share rule).
3. **Q3 — Figma amendments** (remove 2 warning-modal frames, reclaim copy, `PEOLPE` typo, delete-group copy, security-notice doubled-A).
4. **Q4 — Member's Charts nav hidden** — Design to confirm (Members currently see the Charts nav + full org chart list via `can_view_charts`; the new model closes both).
5. **Q5 — cache-bust integration test** for the group-ids Redis cache.

**Risks:**

| Risk | Mitigation |
|---|---|
| **Stacked-branch coordination** — this work branches off `feature/rbac` while Spec A's PRs are open; review changes there force rebases here | Merge #1414/#331 promptly, or keep rebases small per milestone |
| **Migration ordering on existing installs** — the seed migration assumes `migrate_rbac_v2_roles` has run | Document in the release runbook; the migration fails loudly (not silently skips) if legacy role pks are found |
| **`created_by` SET_NULL flip** changes behavior on its own (deleting a user stops deleting their content) | Deliberate — protects NGO data; user-deletion test in M1; called out in the PR description |

---

Draft v1 saved. Review and tell me what to revise. When ready, run `/engineering/execute-plan features/access-control/resourcesharing/plan.md`.

> **Post-build (M11):** stop and ask before the Playwright-MCP browser pass.

---

## 9. Architecture — as built (v1 + v1.1, recorded 2026-07-20)

This section describes the system as it exists on `feature/resource-sharing`
(backend PR #1433, webapp PR #347) — including the v1.1 additions (chart/KPI/metric
sharing, coverage engine, warning modals). Where it disagrees with the planning
sections above, this section wins.

### 9.1 The three layers

The system is three stacked layers, each answering a different question:

```
┌────────────────────────────────────────────────────────────┐
│ Layer 1 — WHO ARE YOU            (identity & role)         │
│   User ── OrgUser ── Role        "Priya is an Analyst      │
│                                   in Test NGO"             │
├────────────────────────────────────────────────────────────┤
│ Layer 2 — WHAT FEATURES CAN      (role permissions/RBAC)   │
│ YOUR ROLE USE                                              │
│   Role ── RolePermission ── Permission                     │
│   "Analysts hold can_share_dashboards, can_create_charts…" │
├────────────────────────────────────────────────────────────┤
│ Layer 3 — WHAT CAN YOU DO WITH   (resource sharing)        │
│ THIS SPECIFIC RESOURCE                                     │
│   per-role floors + grants + ownership + public links      │
│   "Priya can EDIT dashboard 17, VIEW dashboard 20,         │
│    can't see dashboard 13 at all"                          │
└────────────────────────────────────────────────────────────┘
```

Layer 2 is coarse and org-wide ("may use the feature anywhere"). Layer 3 is
fine-grained and per-resource ("on this one thing"). Almost every action must
pass **both**: the permission slug opens the feature, the resolver decides the
resource.

### 9.2 Data model

```
auth_user ──< OrgUser >── Org                    (multi-tenant spine)
                 │
                 └── new_role ──> Role ──< RolePermission >── Permission
                                  (admin/analyst/member,      (slugs:
                                   ranked by level)            can_share_charts…)

Every shareable resource (Dashboard, Report, Alert, Chart, Metric, KPI):
    owner ──> OrgUser              who governs it
    analyst_level  ∈ none|view|edit ┐ per-role GENERAL ACCESS floors
    member_level   ∈ none|view|edit ┘ (admins never stored — always edit)

resource_share (the grants table):        access_request:
    org                                       org, resource_type, resource_id
    resource_type + resource_id (soft ptr)    requester ──> OrgUser
    principal_type user|group                 requested_permission view|edit
    principal_id                              status pending|approved|declined|expired
    permission view|edit   ← grant level      expires_at (30 days, celery sweep)
    status active|pending|revoked
    pending_email (invitee not signed up)

OrgPreferences: default_analyst_level / default_member_level   (seeds new resources)
                enable_public_sharing                          (org kill switch)
Dashboard/Report: is_public + public_share_token               (anonymous links)
UserGroup ──< membership >── OrgUser                           (grant targets)
```

The registry (`core/sharing/shareable_types.py`) — code, not DB — declares each
rtype's capabilities: general access? grants? public links? requests? member
sharing? + its share slug. Everything downstream reads this table instead of
branching on rtype.

| rtype | general access | grants | public link | requests |
|---|---|---|---|---|
| dashboard | ✓ | ✓ | ✓ | ✓ |
| report | ✓ | ✓ | ✓ | ✓ |
| alert | ✓ | ✓ | — | ✓ |
| chart | ✓ | ✓ | — | ✓ (member excluded) |
| metric / kpi | ✓ | ✓ | — | ✓ |

### 9.3 Read path — "can Priya see this?"

Single source of truth: `access_resolver.effective_permission()`. Every gate,
list, and export goes through it. Nothing else re-derives permissions.

```
request → @has_permission(view slug)     Layer 2: role may use feature
        → resolver:                      Layer 3:
            same org?          no → None (404/403)
            admin/super-admin? ──────► "edit"   (never stored, computed)
            owner?             ──────► "edit"
            otherwise, MAX of:
               direct user grant          resource_share
               any group grant            resource_share via memberships
               role's general floor       analyst_level / member_level
            (member + chart rtype ────► None — member sharing deferred)
        → "edit" / "view" / None
```

- **Grant level** = the view/edit value on one grant row. Grants only ever
  *raise* access above the role floor; removing a grant drops back to the
  floor, never below it.
- List pages use the same logic compiled into a queryset
  (`accessible_filter`) — a narrowed resource silently disappears from lists
  rather than 403ing on click.
- **The one inheritance exception:** charts render *inside* any dashboard you
  can view, even when you can't open them standalone (container context).
  This is why a Member's tile CSV export works on a member-visible dashboard
  whose charts are `member=none`.

### 9.4 Write path — sharing something

```
Share modal SHARE
  → @has_permission + registry slug check     (may you share this rtype at all)
  → resolver == "edit" on THIS resource       (may you share this one)
  → sharing_actions.upsert_grant():
       principal role rules   Member principal on chart/kpi/metric → 400
       invite role rules      Analyst/Admin invites are admin-only
       ── dashboards only ──
       coverage check         does this widen the dashboard past its
                              inner charts? → requires_confirmation
                              payload naming the under-covered charts
  → write resource_share row → notify grantee (deep-link email)
```

The **coverage engine** (`core/sharing/coverage.py`, v1.1) exists because
dashboards *contain* charts. Any widening move — adding a grant, raising a
general level, enabling the public link, saving a new tile — is checked
against every inner chart. The webapp turns `requires_confirmation` into the
warning dialogs: **Extend** (raise the charts to match — requires Edit on each
chart, re-validated server-side) or **Proceed** (charts stay inline-visible
only). `update_dashboard` validates new tiles itself, so the warning cannot be
bypassed by saving the layout directly.

### 9.5 The other flows

- **Request access** — a resolver-`None` wall renders the request screen, not
  a bare 403. A request row (view or edit, including View→Edit upgrades) goes
  to the owner, who approves / downgrades / declines from the notification.
  Approval writes a grant *for that one requester* — org policy never moves.
  Requests expire in 30 days via a daily celery sweep. Members requesting
  charts get the permanent inline answer ("request the dashboard instead").
- **Public links** — dashboards and reports only. `is_public` + unguessable
  token, behind the org-wide `enable_public_sharing` kill switch that
  dead-ends every existing link at once. Public endpoints serve only charts
  belonging to that dashboard.
- **Ownership** — owner ≈ admin *for that resource*: full control, decides
  requests, can transfer to an existing grantee. Ownership outranks role: a
  Member owner can approve requests despite holding no share slug.
- **Defaults** — new resources seed `analyst_level`/`member_level` from org
  preferences (view/view out of the box; charts clamp member to none).
  Existing charts were migrated `analyst=edit` to preserve day-one behavior.

### 9.6 Who enforces what, where

| Rule | Lives in |
|---|---|
| role → feature slugs | `@has_permission` decorator, seeds `002/003` |
| rtype capabilities + share slugs | `core/sharing/shareable_types.py` |
| effective access (the merge) | `core/sharing/access_resolver.py` |
| all writes: grants, general, transfer, public, bulk | `core/sharing/sharing_actions.py` |
| dashboard↔chart coverage + warnings | `core/sharing/coverage.py`, `chart_access.py` |
| request lifecycle | `core/sharing/access_requests.py` |
| endpoint guards / kill switch / emails | `gates.py`, `public_sharing_gate.py`, `deep_links.py` |
| UI mirror (hide buttons only) | webapp `lib/rbac.tsx`, `components/sharing/*` |

### 9.7 Design principles

1. **One resolver** — permission logic lives in `access_resolver.py` and
   nowhere else; every surface calls it.
2. **Registry-driven** — capabilities are data (`shareable_types.py`), not
   per-rtype if/else.
3. **Grants only raise** — the role floor is the minimum; exceptions stack on
   top; highest wins.
4. **Admins computed, never stored** — no admin grant rows exist; the
   resolver short-circuits on role rank.
5. **Backend is the enforcement** — the webapp hides what you can't do, but
   every rule is re-checked server-side.

---

## 10. Target architecture — permission-FK grants + decorator gates (v1.2, PLANNED)

§9 above is what runs today. The approved evolution is `v1.2/plan.md`
(2026-07-22 design of record — an earlier "level actions" draft was
considered and superseded; see `v1.2/design-review-2026-07-21.md`).

### 10.1 The model: flat sources, one pool, one check

Role slugs answer ① — "may you use this area of the app" (`@has_permission`,
untouched). Per resource, the peer sources — none outranks another — are:

```
grant rows (FK → Permission, + implied)
   ∪  floors (mapped rtype×level → slug)  ∪  owner/admin
   =  POOL(user, resource)   →   required slug ∈ pool ?  (the only gate)
```

(Amended during the dashboard pilot: the draft also pooled role slugs, but
that hands every Member `can_view_dashboards` on every dashboard, erasing
floors and list scoping — the role's per-resource contribution is the floor
columns. See `v1.2/plan.md` §3.3.)

Consequence (deliberate, spec-original §4): a Member granted Edit on
dashboard 2 edits dashboard 2 — role does not cap content function. The
resolver's silent Member grant-cap is removed.

**Status: LIVE for dashboards** (pilot, 2026-07-22 — registry flag
`member_edit_grants`, decorators on `dashboard_native_api`; other rtypes
unchanged, see `v1.2/tasks.md`).

### 10.2 What changes

| area | change |
|---|---|
| `resource_grant` (renamed) | `permission` varchar → `permission_id` FK → Permission (PROTECT); backfilled in-place inside the still-unmerged migrations |
| `permission` | + `implies_id` self-FK (edit → view, per rtype) |
| `access_request` | `requested_permission_id` FK |
| endpoints | three stacked decorators — `@has_permission` (untouched) + `@extract_resource` + `@has_resource_permission`; bodies carry zero access code; route-audit CI test makes gates unforgettable |
| floors, registry, groups, public links | unchanged |

Full detail, milestones (M1 schema must land before PRs #1433/#347 merge),
rollout guards, and the one open product decision (Member re-share):
`v1.2/plan.md`.
