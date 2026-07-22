# Plan — Resource Sharing v1.2: Permission-FK Grants + Decorator Gates

**Status:** design of record (2026-07-22). Supersedes the earlier "level actions"
draft of v1.2 (see `design-review-2026-07-21.md` for that discussion; the
decision went the other way — one permission vocabulary, DB-linked grants,
decorator-only enforcement).
**Parent:** `features/access-control/resourcesharing/plan.md` (§9 as-built) and `v1.1/`.
**Owner decisions baked in:**
1. Keep `@has_permission` exactly as it is (Layer 2, slug list, untouched).
2. All resource-level access moves into decorators — endpoint bodies contain
   zero access-control code.
3. `resource_share` links to the **Permission table by FK** — one permission
   vocabulary across both layers; no separate action/level vocabulary.
4. **No hierarchy between role-permissions and resource-permissions.** Both
   are peer *sources* contributing to one pool per (user, resource); a single
   membership check decides. A Member with only view-slugs from their role,
   granted Edit on dashboard 2 by an admin, CAN edit dashboard 2.

---

## 1. Overview

### The model in one picture (flat — no gate-behind-gate)

```
SOURCES (peers — none outranks another)
   role            ──► permissions it carries        (org-wide)
   grant rows      ──► the Permission each FK names  (this resource)
   floor columns   ──► mapped to this rtype's view/edit permission
   ownership/admin ──► all of this rtype's resource permissions
            │
            ▼
   POOL(user, resource) = union of contributions (+ implied permissions)
            │
            ▼
   CHECK: required slug ∈ pool     ← the only decision, made in a decorator
```

Example: Ishan (Member) holds an admin-granted Edit on dashboard 2. His role
slug `can_view_dashboards` opens the dashboards *area* (①); per-resource,
only grants/floors/ownership count (see the §3.3 amendment):

```
pool(ishan, dashboard 2) = {can_edit_dashboards, can_view_dashboards}  grant FK + implied
   → can_edit_dashboards ∈ pool → he edits dashboard 2
pool(ishan, dashboard 5) = {} (no grant, member_level=none) → 403 even for view
```

This resolves the H2 incoherence in the **spec-original direction** (Spec B §4:
"role does not cap function on content"): a Member's Edit grant becomes true
instead of being clamped. The silent Member grant-cap in the resolver is
removed (§5.3).

### What the endpoint looks like

```python
@dashboard_native_router.put("/{dashboard_id}/")
@has_permission(["can_view_dashboards"])            # ① Layer 2 — UNCHANGED code
@extract_resource("dashboard")                      # ② NEW
@has_resource_permission("can_edit_dashboards")     # ③ NEW
def update_dashboard(request, dashboard_id):
    dashboard = request.resource                    # body: zero access code
    ...
```

Note the pattern that makes the flat model work on instance routes: ① declares
the **area/view slug** (which Members hold — it answers "may you use this part
of the app"), ③ declares the **action slug** answered by the pool. Creation
and other non-instance endpoints keep their current `can_create_*`/`can_edit_*`
slugs in ① unchanged — no resource exists there, so ③ doesn't apply.

---

## 2. Schema changes (must land inside the open-PR migration window)

Migrations 0176–0179 are unapplied anywhere durable (PRs #1433/#347 unmerged;
prod has never seen these tables) — all changes below are **edits to those
migrations in place**: no rename/alter dance, no data copy, trivially
revertable until merge. This window closes at merge; M1 is therefore first.

### 2.1 `resource_share`

```
+ permission_id   FK → permission(id), on_delete=PROTECT   ← the grant's meaning
- permission      varchar                                  ← retired after backfill
```

Backfill inside the migration, from the single RTYPE_LEVEL_SLUG map (§4.1):

```
('dashboard','view') → pk(can_view_dashboards)     ('dashboard','edit') → pk(can_edit_dashboards)
('chart','view')     → pk(can_view_charts)         … all six rtypes
```

`PROTECT` because seeds become load-bearing for grants: deleting a permission
row a grant points at must be impossible, not a silent cascade.

### 2.2 `access_request`

```
+ requested_permission_id  FK → permission(id), PROTECT
- requested_permission     varchar
```

### 2.3 `permission` — implication

The DB must know edit ⊇ view (a grant FK'd to `can_edit_dashboards` satisfies
a `can_view_dashboards` check):

```
+ implies_id  FK → permission(id), nullable, PROTECT
    seeded: can_edit_dashboards.implies → can_view_dashboards   (× 6 rtypes)
```

Checkers walk the chain (depth 1 today; the walk is written chain-safe).

### 2.4 Floors and org defaults — UNCHANGED

`analyst_level` / `member_level` stay `none|view|edit` columns; they are
*sources*, translated to permissions by the pool builder via the same map.
(A floor is "every Analyst gets this rtype's view/edit permission here" — the
columns already say exactly that; FK-ifying them would add six columns × two
roles for no new information.)

### 2.5 Naming sweep (unchanged decision from §9 of the previous draft)

`ResourceShare → ResourceGrant` (`resource_grant`) rides the same window and
the same in-place migration edits. The old `.permission → .level` rename is
**superseded** — the column is now `permission_id` and the name is finally
honest by construction.

---

## 3. The three decorators

Execution order top→bottom; each ~30–80 lines in `ddpui/core/sharing/`.

### 3.1 `@has_permission([...])` — UNTOUCHED

Byte-for-byte today's decorator (`auth.py:39`). Reads `request.permissions`
(role slugs from Redis), superset check, 404-on-fail quirk preserved.

### 3.2 `@extract_resource(rtype)` — NEW (in `auth.py`, beside ①; owner call 2026-07-22 — no separate decorators file)

- Reads the id from the route kwargs (param name from the registry entry, or
  explicit `param=` override).
- Fetches org-scoped via the registry's model: cross-org indistinguishable
  from missing → 404 (the existing wall, now in one place).
- Attaches `request.resource`, `request.resource_rtype`.
- No permission logic — extraction only, reusable by any later decorator.

### 3.3 `@has_resource_permission(slug)` — NEW

Builds the pool and decides:

```python
pool  = grant_contribution(user, resource)                     # 1 query:
      #     active grant rows for user + their groups on this  #   grants join
      #     resource → each row's permission_id → slug,        #   permission,
      #     plus implied slugs (permission map, cached)        #   group subq
      | floor_contribution(role, resource)                     # in memory:
      #     analyst_level/member_level column → RTYPE_LEVEL_SLUG
      | owner_admin_contribution(user, resource)               # in memory
if slug not in pool: raise 403 (canonical message)
request.resource_permissions = pool                            # for body reads
```

**AMENDED during the dashboard pilot (2026-07-22): role slugs are NOT a pool
source.** The original draft listed `role_contribution(request.permissions)`
as the first source — the pilot's test suite proved that wrong: every Member
role carries `can_view_dashboards`, so pooling role slugs hands every Member
view on every dashboard, erasing floors and list scoping. Role slugs answer
① ("may you use this area of the app"); the role's *per-resource*
contribution is the floor columns. The no-hierarchy decision is untouched
where it matters: grants are never capped by role.

- The Permission table (92 rows) + implication edges are **process-cached**
  (loaded once, invalidated on deploy — the table changes only via seeds).
- Query budget: ①'s existing auth queries + 1 fetch (②) + 1 grants query (③)
  ≈ today's count; pinned by `assertNumQueries` in CI.
- Failure modes decided: unknown slug at decoration time → startup error
  (fail fast, not per-request); resource missing → ② already 404'd;
  pool empty → plain 403.

### 3.4 Route-audit test

CI walks every registered route on both API instances: each must carry
③ + ② (instance routes) or `@public_ok` / a `can_*` ① (feature routes).
A new endpoint cannot ship ungated. This is the "middleware guarantee"
delivered at the route, where rtype/verb/resource are knowable.

---

## 4. Consumers that move to the pool

### 4.1 The one map

`RTYPE_LEVEL_SLUG = {("dashboard","view"): "can_view_dashboards", …}` —
single source used by: the backfill migration, floor contribution, the share
modal's dropdown mapping, and the resolver shim (§4.3). A test asserts every
registered rtype has both entries and both slugs exist in seeds.

### 4.2 Share modal, re-share cap, approvals

- Dropdown options = the permissions *in the grantor's own pool* for this
  resource (implication-aware) — you can grant only what you hold. Replaces
  `PERMISSION_RANK` math (both sites in `sharing_actions`, plus
  `access_requests.py:325`'s downgrade-only rule → "granted ∈ implied-closure
  of requested").
- Grant writes store `permission_id`. Upsert key unchanged; the H1 unique
  constraint (separate review fix) applies to the same key and should ride
  the same migration window.
- Member principals: dashboards/reports/alerts may now be granted Edit
  honestly (the point of the model). Chart/KPI/metric Member blocks
  (registry `member_sharing=False` + deferred set) stand unchanged — per-rtype
  product deferrals, not role logic.
- Approval notifications become truthful with no extra work: what's granted
  is what's delivered.

### 4.3 Resolver and lists

- `accessible_filter` (lists): visibility = floor admits ∨ any active grant
  row ∨ owner — grants of any permission imply view via the chain, so the
  SQL barely changes (grant-existence remains sufficient). Stays joinless.
- `effective_permission` internals read `permission_id` through the cached
  map for its max-merge. **The Member grant-cap (access_resolver.py:174) is
  deleted** — the flat model has no role ceiling. Coverage keeps calling it
  for visibility verdicts, unchanged behavior.
- The webapp's affordances switch to per-resource: responses carry the
  grantee's slugs/pool for the resource (field change lands in the same open
  webapp PR), so a Member with Edit sees the Edit button on dashboard 2 and
  not on dashboard 5.

### 4.4 Endpoint sweep

Instance routes: ①'s slug becomes the rtype's **view slug**, ③ carries the
action slug, in-body fetch/gate boilerplate deleted (~40 endpoints,
mechanical, batched). Non-instance routes: untouched. The six raw-payload
warehouse endpoints from the v1.1 review get ③ in the same sweep.

---

## 5. Behavior changes (explicit, product-visible)

1. **Members can hold real Edit** on dashboards/reports/alerts via grants or
   floors — edit, and (default, per Spec B §10.3) **re-share up to their own
   permission**. OPEN DECISION for sign-off: keep re-share-with-edit for
   Members (spec behavior, recommended for consistency) or exclude Members
   from re-share (one exclusion line in the pool builder). Everything else
   in this plan is independent of the answer.
2. The share modal legitimately offers Edit for Member principals on those
   rtypes; approval emails stop over- or under-promising.
3. Rollout guard: prod/staging query for existing Member edit grants/floors
   first, then a log-only week for the *newly honored* permissions (the
   inverse of a clamp dry-run: log "would now ALLOW" hits so the org isn't
   surprised by Members gaining live edit), then enable.
4. Communicate to orgs: "Members can now be granted edit on specific
   dashboards" — a feature announcement, not a fix.

## 6. Security & governance

- Default-deny preserved: empty pool denies; unknown slug fails at startup;
  cross-org 404 wall in ②; org FK on every pool source.
- Seeds are now load-bearing for grants: `PROTECT` FKs + a seed-integrity
  test (every FK'd permission exists; implication edges well-formed; every
  rtype has view+edit rows). Document loudly in the seeds: these rows serve
  BOTH role-mapping and grant-meaning — renames/removals are breaking.
- CODEOWNERS on `auth.py` (all three gates), `sharing_actions.py`, `access_resolver.py`,
  seeds `002/003`.
- Structured deny logging from ③ (actor, resource, slug, sources present) —
  feeds the future audit log; boot log line with the permission-map hash.
- TOCTOU on writes unchanged (check-then-act); the H1 unique constraint is
  the backstop and should land with M1.

## 7. Testing

1. **Pool truth-table**: pure tests on the pool builder — (role, grants,
   floor, owner) combinations × required slug, incl. implication and the
   Member rows that flip in this design.
2. **Golden matrix**: role × source-combo × slug grid committed as text; the
   M-flip rows are the review artifact for §5.
3. **Decorator tests**: extraction (param names, 404 wall), ③'s 403 wording,
   `request.resource_permissions` attachment.
4. **Route audit** (§3.4) + **seed integrity** (§6) + **map completeness**
   (§4.1) + `assertNumQueries` pin.
5. **Migration test**: backfill maps every existing row; zero rows left with
   null `permission_id`; PROTECT verified.
6. Full-suite regression: list scoping, coverage, bulk, request-flow tests
   updated only where §5's flips demand (member-cap tests change on purpose
   — each such change cites §5).

## 8. Milestones

```
M1  Schema in the open-PR window: permission_id FKs + implies + backfill +
    PROTECT + naming sweep (ResourceGrant) + H1 unique constraint together.
    Both PRs updated; suites green.                       ← FIRST; window closes at merge
M2  Pool engine + cached permission map + RTYPE_LEVEL_SLUG + resolver shim
    reading FKs (member-cap still in place) + truth-table/matrix tests.
M3  Decorators ② ③ + route-audit test + endpoint sweep (batched) +
    view-slug pattern on instance routes. Behavior-identical checkpoint:
    matrix diff vs M2 must be empty.
M4  The flip (product sign-off + §5 rollout): delete the resolver member-cap,
    modal offers Member Edit, webapp per-resource affordances, API field to
    slugs (webapp PR in tandem), re-share decision implemented.
    Matrix diff = exactly the Member rows.
M5  Consumers cleanup: grantable options / re-share cap / approval rule on
    pool containment; PERMISSION_RANK retired outside the resolver;
    coverage + bulk eligibility on can-style checks; docs (§9/§10 of the
    parent plan updated to this architecture).
```

## 9. Risks & open questions

- **Window risk**: M1 must precede PR merge or the schema change becomes a
  live-migration + API-versioning project. Treat as closing.
- **Dual-use slugs**: one vocabulary serving two layers is the accepted
  design; the mitigations are §6's PROTECT + tests + documentation. The
  known residual: a future feature-slug rename must consider grant FKs.
- **Member security posture**: §5 is a real widening for orgs that assumed
  "Members can never edit anything." The rollout guard + comms own this.
- **H3 side door** (Member request-approve on metric/kpi): unchanged by this
  plan; still tracked from the 2026-07-20 review.
- **Open (product)**: Member re-share (§5.1).
- **Deferred**: per-org custom permission sets; `resource_permissions` in all
  API responses beyond what M4 needs; audit-log `policy_ref`.
