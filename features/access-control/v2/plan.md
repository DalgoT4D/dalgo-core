# Plan — Access Control v2: Role System

**Status:** Draft v1 (for engineering review)
**Spec:** [v2 spec](./spec.md) · scoped from [Spec A](../v1/access-control-spec-A-role-system-2026-06-02.md) (the role-system doc)
**Research:** [research.md](./research.md)
**Date:** 2026-06-17

Acronyms used here: RBAC (role-based access control — who can do what, by role) · FK (foreign key — a DB column pointing at another row) · IA (information architecture — how Settings is organized) · DQ (data quality) · HLD/LLD (high-/low-level design).

---

## 1. Overview

**What we're building:** collapse Dalgo's 4 customer roles into 3 (Admin / Analyst / Member), gate the sidebar and routes by role, make Members strictly view-only, give Analysts read-only access to data infrastructure, consolidate Settings, and add an `owner` column with owner-or-Admin delete. Resource-level sharing and ownership *transfer* are deferred to Spec B.

**Services affected:**

| Service | Touched? | What |
|---|---|---|
| DDP_backend | ✅ heavily | role remap migration, permission seed, `owner` column + backfill, owner-or-admin delete, 2 OrgPreferences fields |
| webapp_v2 | ✅ heavily | sidebar role filter, route guards, No Access page, Settings re-IA, `<PermissionGate>` |
| prefect-proxy | ❌ | no user/role model lives here (see research §7) |

---

## 2. Blast Radius

Primary entities changed: **Role** + **OrgUser** (the role model), and **every content resource** (gets `owner`). Because role gates the whole product, the radius is wide. Every surface below was traversed from `docs/domain-map.md` and given a confirmed status — none left as TBD.

| Surface | Hop | Why affected | Status | Notes |
|---|---|---|---|---|
| OrgUser / Role | 0 | The thing being changed | in scope | 4 customer roles → 3; `super-admin` untouched |
| Dashboard | 1 | `owner` + owner-or-admin delete + Member view-only | in scope | delete already creator-gated (research §2) |
| Chart | 1 | same | in scope | charts share via dashboard; still get own `owner` |
| ReportSnapshot ("Report") | 1 | same | in scope | delete uses `can_delete_dashboards` slug |
| Metric | 1 | same | **in scope** | confirmed with user 2026-06-17; closes a delete-check gap |
| KPI | 1 | same | **in scope** | confirmed with user 2026-06-17; closes a delete-check gap |
| Source / Ingest | 1 | Data-infra gating | in scope | Analyst read-only, Member hidden |
| Transform (dbt) | 1 | Data-infra gating | in scope | Analyst read-only, Member hidden |
| Warehouse | 1 | Data-infra gating | in scope | Analyst read-only, Member hidden |
| Pipeline / Orchestration | 1 | Data-infra gating | in scope | Analyst read-only, Member hidden |
| Data Quality check | 1 | Data-infra-adjacent | **in scope** | confirmed "gate like Data" 2026-06-17 |
| Explore | 1 | Data-infra-adjacent | **in scope** | confirmed "gate like Data" 2026-06-17 |
| OrgPreferences | 1 | Org-defaults storage | in scope | 2 inert fields |
| Billing (Settings) | 1 | Settings consolidation | **in scope (gating only)** | Admin-only, confirmed 2026-06-17 |
| Notification | 2 | recipient = OrgUser | **out of scope** | role change doesn't alter delivery; no Member view-only concept applies |
| Alert | 1 | nav item shown to all roles | **partial** | Alerts *nav item* shows; alert *resource* CRUD + ownership is Spec B (no Alert model to own yet) |
| Share link (public) | 2 | unauthenticated view | **out of scope** | no logged-in role → role gating N/A; "allow public sharing" toggle ships **inert** |

**Surfaces deliberately NOT affected, and why:**
- **Notification** — delivery is addressed to OrgUsers regardless of role; nothing in v2 changes who receives what.
- **Public share links** — viewers are anonymous, so the three roles don't apply. The org-defaults toggle that governs them is stored but not read until Spec B.
- **Alert resource management** — there is no Alert model to assign an `owner` to in v2; only the nav item is shown. Full Alert handling is Spec B.

---

## 3. High-Level Design (HLD)

### 3.1 The one-paragraph mental model

**The rule:** v2 is mostly **data + gating**, not new engines. "Member view-only" and "Analyst read-only on infra" are achieved by changing which permission slugs each role has — not by writing new permission logic. The only genuinely new server *logic* is the owner-or-Admin delete check.
**Example:** James (Member) is blocked from creating a dashboard because the `member` role's permission set has no `can_create_dashboards` slug — the existing `@has_permission` decorator does the rest.
**Why it matters:** it keeps the change small and low-risk, and it slots into Spec B cleanly (Spec B adds the resource-grant layer on top of the same resolver).

### 3.2 Permission resolution (unchanged plumbing, new data)

```
login / token refresh
   → CustomJwtAuthMiddleware (auth.py:176-188)
   → role's slugs loaded from Redis (auth.py:81-91)
   → request.permissions : set[str]
   → @has_permission(["can_edit_dashboards"]) (auth.py:30-51) → 403 if missing
```

We change the *contents* of each role's slug set (via migration + seed), not this flow.

### 3.3 Owner-or-Admin delete (the only new backend logic)

```
DELETE /api/dashboards/{id}/
   → @has_permission(["can_delete_dashboards"])     # role can delete *something*
   → service.delete_dashboard(orguser, id)
        → if resource.owner_id == orguser.id: OK
          elif orguser.new_role.slug == "admin": OK   # NEW: effective-owner override
          else: HttpError(403, "Only the owner or an admin can delete this")
```

Today the check is `created_by != orguser → blocked` with **no** admin branch (research §2). v2 swaps `created_by` for the new `owner` field and adds the admin branch. Metric and KPI get this check for the first time.

### 3.4 Frontend gating (two layers)

```
Layer 1 — sidebar:   getNavItems() filters by item.visibleToRoles vs new_role_slug
Layer 2 — routes:    a role guard redirects a hidden direct-URL hit
                     → first accessible page, or No Access page
```

Both read `new_role_slug` (already in the `/api/currentuserv2` payload — no new endpoint).

### 3.5 New / modified endpoints

| Endpoint | Change |
|---|---|
| `OrgPreferences` GET/PUT (`org_preferences_api.py`) | add `default_visibility_floor`, `allow_public_sharing` fields |
| content delete handlers (5) | swap creator-check → owner-or-admin check |
| invite (`user_org_api.py:470-477`) | no signature change; relies on Admin-only gating + level cap |
| Data-infra modules (ingest/transform/warehouse/pipeline/orgtask/data_quality) | no code change — permission seed removes Analyst write slugs |

No brand-new endpoints are required for v2. The Settings > Users surface already exists (research §4).

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

**Role remap (data migration, not schema).** Reuse the existing `Role` rows; do not drop and recreate.

| pk | before (slug / level) | after (slug / name / level) |
|---|---|---|
| 1 | super-admin / 5 | **unchanged** |
| 2 | account-manager / 4 | `admin` / "Admin" / 4 |
| 3 | pipeline-manager / 3 | **merge into pk 2**: repoint OrgUsers, then delete pk 3 (see decision below) |
| 4 | analyst / 2 | `analyst` / "Analyst" / 2 (permissions trimmed) |
| 5 | guest / 1 | `member` / "Member" / 1 (permissions fixed) |

**Open decision (flag for review):** how to collapse AM + PM into one Admin. `slug` is `unique`, so two rows can't both be `admin`. The real path: **rename pk 2 → `admin`; repoint every `pipeline-manager` OrgUser's `new_role` FK to pk 2; delete pk 3.** Reverse migration recreates pk 3 and repoints back (best-effort; the AM/PM distinction is lost — note in reverse).

**`owner` column (schema migration).** Add to each of the 5 content models:

```python
owner = models.ForeignKey(
    OrgUser, on_delete=models.SET_NULL, null=True, blank=True,
    related_name="owned_%(class)ss",
)
```

- `SET_NULL` matches ReportSnapshot's existing `created_by` behavior and avoids blocking user deletion.
- Backfill in the same migration's `RunPython`: `owner = created_by`; where `created_by` is null, `owner =` oldest active Admin in that resource's org (`OrgUser.objects.filter(org=..., new_role__slug="admin", user__is_active=True).order_by("user__date_joined").first()`).

**OrgPreferences (schema migration).** Add:
```python
default_visibility_floor = models.CharField(max_length=50, null=True, blank=True)
allow_public_sharing = models.BooleanField(default=True)
```
Stored, not consumed (Spec B reads them).

### 4.2 Permission seed changes (`seed/003_role_permissions.json` + remap migration)

**The rule:** edit the seed so each new role has exactly its allowed slugs; the migration applies the same delta to existing DBs.
**Example:** the `member` role gets every `can_view_*` content slug and **none** of `can_create_* / can_edit_* / can_delete_* / can_share_*`. The `analyst` role keeps content `view/create/edit/delete` but loses `can_create_source`, `can_edit_source`, `can_edit_dbtworkspace`, `can_create_pipeline`, `can_edit_pipeline`, `can_create_orgtask`, etc. — keeping the `can_view_*` infra slugs.
**Why it matters:** this is where ~90% of the behavior lives. Get the slug lists right and the decorators enforce everything for free.

Concrete slug deltas (from the 85 slugs in `seed/002_permissions.json` — research §1):

| Role | Keeps | Loses vs. its predecessor |
|---|---|---|
| `admin` (was account-manager) | everything | nothing |
| `analyst` | all content view/create/edit/delete/share; all `can_view_*` infra (sources, dbt, warehouse, pipeline, orgtask, dataquality) | every infra `create/edit/delete/run` slug |
| `member` (was guest) | all content `can_view_*` (dashboards, charts, reports, metrics, kpis); the fix is **adding** `can_view_dashboards`/`can_view_charts` which Guest was missing | any create/edit/delete/share; all infra slugs (hidden) |

Migration pattern: follow `ddpui/migrations/0137_update_landing_page_permissions.py` (RunPython forward + reverse, `apps.get_model`, then `set_roles_and_permissions_in_redis()` at the end — backend landmark, Migration conventions).

### 4.3 Backend logic — owner-or-Admin delete helper

Add one shared helper (e.g. `ddpui/core/orguserfunctions.py` or a new `ddpui/core/ownership.py`):

```python
def can_delete_resource(orguser, resource) -> bool:
    if resource.owner_id == orguser.id:
        return True
    return orguser.new_role.slug == "admin"
```

Call it inside each of the 5 service delete functions (research §2 has the file:line of each), replacing the current `created_by != orguser` block for Dashboard/Chart/Report, and **adding** it to Metric/KPI which have no check today. Error: `raise HttpError(403, "Only the owner or an admin can delete this")`.

### 4.4 Frontend components

| Component | Change | Reference |
|---|---|---|
| `NavItemType` (`main-layout.tsx:48`) | add `visibleToRoles?: Role[]` | frontend landmark, Sidebar |
| `getNavItems()` (`main-layout.tsx:91-231`) | tag each item with roles; the existing `.filter(item => !item.hide)` gains a role check | — |
| Route guard | new: redirect hidden-route hits → first accessible page / No Access | pattern at `app/dashboards/[id]/page.tsx:18-42` |
| `No Access` page | new component; shows org Admin contact | — |
| `<PermissionGate>` | new `components/permission-gate.tsx`; wraps create/edit/delete/share buttons | frontend landmark recommends this once >3 surfaces |
| Settings re-IA | new pages for Warehouse, Appearance, Org-defaults, Groups (placeholder); Billing + Users gated Admin-only | Settings IA landmark (slots empty today) |
| Settings > Users | extend existing `UserManagement.tsx` — no rebuild | Users landmark |
| Data section read-only | hide create/edit/run affordances for Analyst; hide nav entirely for Member | — |
| Slug cleanup | grep + replace `'account-manager'`/`'pipeline-manager'`/`'guest'` | frontend landmark, Auth |

### 4.5 Integration points

Frontend reads `new_role_slug` + `permissions[]` from `/api/currentuserv2` (already present — frontend landmark). No new contract. Backend stays the single source of truth: even if the UI hides a button, the `@has_permission` decorator + delete helper reject the request server-side.

---

## 5. Security Review

| Concern | Assessment |
|---|---|
| **AuthZ — new endpoints protected?** | No new endpoints. Modified delete handlers keep `@has_permission`; the new owner-or-admin check is an *additional* gate, not a replacement. |
| **Server-side enforcement of Member view-only** | ✅ Enforced by the permission seed (Member has no write slugs) + decorators. UI hiding is defense-in-depth, not the only guard (spec Story 7 criterion). |
| **Admin override scope** | Admin override applies only to `delete` (and later transfer in Spec B). It is a deliberate governance escape hatch. Note: this *grants* a power AMs didn't have before (research §2) — call out at review. |
| **Multi-tenant isolation** | Unchanged — every query still filters by `org=request.orguser.org` (backend landmark, API conventions). The `owner` FK is within-org by construction (OrgUser is org-scoped). |
| **Migration safety** | Role remap is reversible (with the noted AM/PM-merge caveat). `owner` backfill is idempotent. Redis cache cleared at migration end or permissions silently stale. |
| **Input validation** | OrgPreferences new fields validated via Ninja Schema (bool + constrained char). No raw SQL. |
| **`super-admin` untouched** | Migration must touch only pks 2–5. A test should assert pk 1 (`super-admin`) slug/level/permissions are unchanged. |
| **PII / secrets** | None newly handled. Warehouse credentials remain in their existing store; v2 only gates *who sees the Settings page*. |
| **Privilege escalation (PM→Admin)** | Wholesale PM→Admin is a confirmed escalation (spec risk note). Not a code risk; a governance one. Any Admin can downgrade via Settings > Users. |

---

## 6. Testing Strategy

**Backend (pytest + pytest-django — backend landmark, Test conventions):**

- **Role migration:** after migrate, assert the 3 customer slugs (`admin`/`analyst`/`member`) exist + `super-admin` intact; assert every former AM and PM OrgUser now points at `admin`; assert former Guests point at `member`.
- **Permission seed:** `member` has `can_view_dashboards` + `can_view_charts` (the bug fix) and lacks all `can_create/edit/delete/share`; `analyst` lacks infra write slugs but keeps infra `can_view_*`.
- **Owner backfill:** resource with `created_by` set → `owner == created_by`; resource with null `created_by` → `owner ==` oldest active Admin.
- **Delete helper:** owner can delete; non-owner Analyst cannot; Admin (non-owner) **can** (new); Metric/KPI now enforce it.
- **Reverse migration:** runs without error; `super-admin` survives a forward+reverse round-trip.

Use the `seed_db` + `mock_request` fixtures (backend landmark) — don't re-derive them.

**Frontend (Vitest + Playwright — frontend landmark):**

- Vitest: `getNavItems()` returns 4 items for Member, the content+read-only-data set for Analyst, everything for Admin.
- Playwright E2E: log in as each role; assert Member sees only Dashboards/Charts/Reports/Alerts and no Create button; Analyst sees Data sections with no edit affordance; direct-URL to `/ingest` as Member redirects.

**Edge cases:** org with zero active Admins at backfill time (fallback target missing); a user who is both creator and Member (owner check passes even though role is view-only — confirm desired, see Open Questions).

---

## 7. Milestones

Ordered to match the spec's implementation order; each is independently shippable and reviewable.

#### Milestone 1: Role collapse + permission remap (backend)
- **Deliverable:** 3 customer roles live; AM/PM→admin, analyst→analyst (infra write removed), guest→member (view fixed); `super-admin` untouched.
- **Services:** DDP_backend.
- **Key tasks:**
  - [ ] Update `seed/001_roles.json` + `seed/003_role_permissions.json` for the 3 roles.
  - [ ] Data migration: remap OrgUser roles + apply permission deltas + `set_roles_and_permissions_in_redis()`; implement reverse.
  - [ ] Tests per §6 (migration + permission seed).
- **Acceptance:** every OrgUser has a valid new role; Analyst API write to a pipeline returns 403; Member can read dashboards.

#### Milestone 2: Analyst read-only / Member hidden on Data + DQ + Explore
- **Deliverable:** Data sections (incl. Data Quality, Explore) render read-only for Analyst, hidden for Member.
- **Services:** DDP_backend (already done via M1 seed) + webapp_v2.
- **Key tasks:**
  - [ ] Frontend: hide create/edit/run affordances in ingest/transform/warehouse/pipeline/orchestrate/data-quality/explore for Analyst; hide nav for Member.
  - [ ] Confirm DQ + Explore permission slugs trimmed for Analyst in M1 seed.
- **Acceptance:** Priya (Analyst) sees Pipelines but no Run/Edit; James (Member) has no Data nav.

#### Milestone 3: Sidebar + route gating + No Access page (frontend)
- **Deliverable:** nav filtered by role; hidden direct-URLs redirect; No Access page exists.
- **Services:** webapp_v2.
- **Key tasks:**
  - [ ] Add `visibleToRoles` to `NavItemType`; tag items; extend filter.
  - [ ] Route guard + No Access component.
  - [ ] Grep-replace old slug strings.
- **Acceptance:** each role sees exactly its nav map (spec sidebar table); `/transform` as Member redirects.

#### Milestone 4: Settings consolidation + Org-defaults (inert)
- **Deliverable:** one Settings area; Admin-only globals (Warehouse, Appearance, Org-defaults, Users, Billing); Groups slot reserved; org-defaults toggles persist.
- **Services:** webapp_v2 + DDP_backend.
- **Key tasks:**
  - [ ] Add `default_visibility_floor` + `allow_public_sharing` to OrgPreferences + schema + API.
  - [ ] Settings IA pages; gate globals Admin-only; Billing Admin-only.
  - [ ] Org-defaults controls render + save (no consumer).
- **Acceptance:** Sarah (Admin) sees all Settings; Priya sees only Groups; toggle value round-trips.

#### Milestone 5: Ownership — owner column, backfill, owner-or-admin delete
- **Deliverable:** `owner` on all 5 content models; backfilled; delete is owner-or-admin everywhere (incl. Metric/KPI).
- **Services:** DDP_backend (+ minor frontend: delete button visibility).
- **Key tasks:**
  - [ ] Schema migration + backfill (oldest-active-Admin fallback).
  - [ ] `can_delete_resource()` helper; wire into 5 delete services.
  - [ ] **No transfer UI** (spec deferral).
  - [ ] Tests per §6.
- **Acceptance:** non-owner Analyst can't delete; Admin can; 100% of resources have an owner.

#### Milestone 6: Settings > Users invite surface
- **Deliverable:** Admin creates/changes-role/deletes users via the existing (re-skinned) Users page.
- **Services:** webapp_v2 (+ verify backend invite endpoint).
- **Key tasks:**
  - [ ] Extend `UserManagement.tsx` for the 3-role dropdown; Admin-only.
  - [ ] Verify invite endpoint role-cap + Admin-only gating.
- **Acceptance:** Sarah invites a Member and an Analyst; Priya can't see the Users page.

#### Milestone 7: Browser testing with Playwright MCP (post-build verification)
- **Deliverable:** the role-gating flows verified live in a real browser, not just in unit/E2E test files.
- **Services:** webapp_v2 (running locally) + DDP_backend (running locally).
- **When:** only after Milestones 1–6 are implemented and all automated tests pass.
- **Key tasks:**
  - [ ] **Once the feature is fully built, stop and ask the user** whether to run browser testing with the Playwright MCP before declaring the work done. Do not assume — confirm first.
  - [ ] If confirmed, drive the real UI via the Playwright MCP tools: log in as each role (Admin / Analyst / Member) and walk the sidebar, route guards, No Access page, read-only Data affordances, Settings gating, and owner-or-admin delete.
  - [ ] Capture snapshots/screenshots of each role's nav map and any blocked action; report mismatches against the spec's sidebar table.
- **Acceptance:** user has reviewed the Playwright walkthrough results for all three roles (or explicitly declined the browser pass).

---

## 8. Open Questions & Risks

1. **AM/PM merge mechanics** — recommend repoint-then-delete pk 3 (§4.1). Confirm reverse-migration loss of AM/PM distinction is acceptable.
2. **Org with no active Admin at backfill** — what owner do un-attributable resources get if an org has zero active Admins? Proposed fallback: leave `owner` null (delete then falls to Admin-only). Confirm.
3. **Creator-who-is-now-a-Member** — a former Analyst demoted to Member still `owner`s their old dashboards, so they *can* delete them (owner check passes) despite being view-only. Confirm intended, or add "Members can't delete even as owner".
4. **`can_delete_dashboards` reused for Reports** — ReportSnapshot delete uses the dashboard slug, not a report-specific one. Leave as-is for v2 or split? (Low priority.)
5. **Org-defaults inert toggles** — spec Open Question 1 still open: ship the controls in v2 or hold the whole section for Spec B? Plan assumes ship-inert.
6. **Redis cache in dev/staging** — migrations must call `set_roles_and_permissions_in_redis()`; if a deploy skips it, permissions look wrong until next login. Verify deploy hook.

---

Draft v1 saved. Review the plan and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/access-control/v2/plan.md` to implement.

> **Post-build reminder (Milestone 7):** once the feature is fully built and automated tests pass, the executor must stop and ask the user whether to run browser testing with the Playwright MCP across all three roles before declaring the work complete. Don't skip this — confirm with the user first.
