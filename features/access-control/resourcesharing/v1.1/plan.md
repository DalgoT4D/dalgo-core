# Chart, KPI & Metric Sharing v1.1 — Implementation Plan

## 1. Overview

**Enhancement:** charts become independently shareable — per-role General access, direct grants (Analyst/Admin only), request-access, list badges, bulk actions — and the embed-time + dashboard-broadening warnings return from the original spec. One security fix ships first: public dashboard links currently leak every chart in the org. **Extended 2026-07-16:** KPIs and Metrics also become grant-capable "similarly" (Milestone 5) — a registry flip + UI mounting, since both rtypes already have General access, list scoping, and request-access working.

- **Parent version:** `../resource-sharing-write-spec-2026-06-17.md` (spec, amended) + `../plan.md` (plan) — shipped on branch `feature/resource-sharing` (webapp `0e242336`, backend `cb30b700`).
- **This version's spec:** [`spec.md`](./spec.md) — the Q0-reversal amendment with Siddhant's three confirmed decisions.
- **Research:** [`research.md`](./research.md) — 9 code surfaces with file:line citations.
- **Services affected:** DDP_backend, webapp_v2. (prefect-proxy untouched.)
- Note: `docs/domain-map.md` (the usual blast-radius source) does not exist in the repo; the blast radius below is built from the v1.1 research and the parent feature's shipped code.

**Vocabulary used below** (defined once): *General access* = a resource's per-role levels (`analyst_level`, `member_level`, each `none|view|edit`). *Grant* = a direct share to a user or group. *Resolver* = `access_resolver.effective_permission`, the one function that answers "what can this viewer do with this resource".

## 2. Blast Radius

| Surface | Hop | Why affected | Status |
|---|---|---|---|
| Chart model + APIs (`charts_api.py`, `chart_service.py`) | 0 | gains levels, owner-routing, scoping, resolver gates | in scope |
| `shareable_types.py` registry + resolver | 1 | new `chart` entry; resolver/accessible_filter are already generic | in scope |
| Public API (`public_api.py`) | 1 | **leak fix** (M0); anonymous inline rendering unchanged | in scope |
| Dashboard editor add-chart (`chart-selector-modal.tsx`) + `update_dashboard` | 1 | embed warning (client) + server-side tile validation | in scope |
| Share modal + bulk dialog (webapp) | 1 | mounts on charts; broadening warning on dashboards; member-block states | in scope |
| Charts list page (webapp) | 1 | resolver-scoped list, access badge, share action, bulk bar | in scope |
| Request-access flow | 1 | charts requestable (Analyst+ only; Member requesters get a clear block) | in scope |
| Reports/snapshots | 2 | **immune** — `frozen_chart_configs` copies by value (`report.py:44-47`); no warning needed | not affected (verified) |
| Alerts | 2 | references never grant access — unchanged rule | not affected |
| Metrics & KPIs | 0 | grants=True flip, share modal + list share/bulk affordances (M5); reference-never-grants rule unchanged | in scope (added 2026-07-16) |
| Roles tab org defaults | 2 | new charts seed from org defaults with member forced `none` | in scope (one line + test) |
| Notifications/emails | 2 | request + share emails work generically once `chart` registers (deep-link map gains `chart`) | in scope (small) |

## 3. High-Level Design

**The one sentence:** register `chart` in the sharing registry (the machinery is generic), keep inline-context rendering exactly as today, and add an *exposure honesty* layer — warnings that fire whenever someone's action would show a narrow chart to a wider audience.

### The inheritance rule (§3 of spec.md)
- A chart **renders inline wherever its containing dashboard renders** — including public links. This is today's behavior and is what guarantees **no locked tiles, ever**.
- A chart's own General access + grants govern **standalone** surfaces: the Charts list, the chart page/editor, pickers, and its data endpoints outside dashboard context.
- **The warnings keep the two layers honest.** Example: Priya's "Salary Breakdown" chart is Private (`analyst=none`). It still renders inside the one HR dashboard it's on. If anyone tries to (a) embed it into another dashboard, or (b) widen that HR dashboard's audience (raise General access, add grants, or enable its public link), a warning names "Salary Breakdown" first, with **Cancel as the default**.
- **"Extend" semantics (v1.1):** extend raises the chart's `analyst_level` to cover the dashboard's analyst audience and copies the dashboard's direct-grant principals onto the chart at View (Analyst/Admin principals only — Member principals are skipped and the warning says so). For exposure the levels can't express in v1.1 (Members via general access, anonymous via public link), the warning still names the charts and offers **Proceed / Cancel** — proceeding acknowledges the inline exposure. Strict render-blocking coverage is deferred (§8).

### Data flow (embed warning)
```
analyst picks chart in ChartSelectorModal
        │ coverage check (new endpoint: does chart cover this dashboard?)
        ▼
  covered? ──yes──► embeds silently
        │no
        ▼
  warning modal (chart named; needs Edit on chart to extend)
   ├─ Extend → PATCH chart general/grants, then embed
   ├─ Proceed (exposure classes only) → embed, no chart change
   └─ Cancel (default) → nothing
        ▼
  update_dashboard validates server-side: new chart ids must be
  org-owned + caller passed the coverage step (guard header/flag)
```

### New/changed endpoints
- `GET /api/access/chart/{id}/` etc. — free once registered (generic routes).
- `GET /api/dashboards/{id}/chart-coverage?chart_id=` — coverage verdict + which roles/principals gap (new, one place; consolidates the tabs→chartId walk duplicated 3×: `chart_service.py:322`, `dashboard_service.py:986`, `chart_access.py:80`).
- `update_dashboard` — validates newly-added chart ids (org check + resolver View on each for the caller) — closes the blind-overwrite hole.
- `public_api.py` chart endpoints — tile-membership check (M0).
- Broadening warning: `set_general_access` / grant-add / `set_public` on a **dashboard** return `requires_confirmation` with the named under-covering charts (mirrors the shipped narrowing warn+offer contract).

## 4. Low-Level Design

### Data model (backend)
- `Chart` (`ddpui/models/visualization.py`) gains `analyst_level` / `member_level` — copy Dashboard's declaration (`dashboard.py:115-120`). No public-link fields.
- Migration **0179**: add fields, backfill `analyst_level='edit'`, `member_level='none'` (behavior-preserving; decision #3). Reverse = drop fields.
- `member_level` pinned: model `clean` + API validation reject any non-`none` value for charts in v1.1.

### Registry + gates
- `RESOURCE_TYPES['chart']`: `general=True, grants=True, public_link=False, requests=True`, share slug `can_share_charts` (new seed, Analyst/Admin roles).
- Grant validation for charts: principal must resolve to Analyst/Admin (user role check; groups: at least one non-member... **no** — simplest honest rule: user principals must be Analyst/Admin; group grants allowed but member group-members simply resolve to nothing since `member_level` stays none and the resolver checks the viewer's role level FIRST for chart grants — verify in implementation; if the resolver grants by principal without role check, add a chart-specific member exclusion in resolution). Email invites on charts: only when the resolved invite role is Analyst/Admin (admin-only per existing `_resolve_invite_role`); Member-role invites blocked with a clear error.
- `list_charts` (`chart_service.py:88`) — scope with `accessible_filter(viewer, 'chart')` like dashboards.
- Chart read endpoints (detail/data/render standalone): resolver View; chart update/delete: resolver Edit + existing slugs; container-context render path (`require_chart_view_access`) **unchanged**.
- Request-access: registry `requests=True` gives the flow; add a requester-role check — Member requesters on charts get 400 with "charts can't be shared with Members yet — request access to the dashboard instead".

### Frontend
- `ShareableResourceType` gains `'chart'` (`useResourceAccess.ts:12`).
- Charts list: share row-action + access badge (reuse `deriveGeneralAccessBadge`) + bulk bar (share + General access; no public toggle) + resolver-scoped data.
- Share modal on charts: typeahead hides Member users, groups shown with a note; unknown-email invite block shows the admin-only Analyst/Admin variant or an explanatory disabled state for non-admins.
- `ChartSelectorModal`: coverage call per selected chart → warning modal (design frames: `RBAC screens/Analyst-warning on adding charts.jpg`, `resource sharing- warning modal.jpg` — now UN-archived).
- Dashboard share modal + bulk dialog: `requires_confirmation` broadening panel naming charts, Cancel default, one aggregated prompt in bulk (mirror the shipped narrowing panel pattern).

## 5. Security Review
- **M0 leak fix** validated by tests: public chart endpoints 404 for non-tile charts, cross-org, and non-public dashboards.
- All new endpoints behind existing auth + org scoping; coverage endpoint requires dashboard Edit (it reveals chart names — same info the editor already sees).
- Grant/invite role checks server-side (member-block is backend-enforced, frontend only mirrors).
- No new PII in analytics/logs; chart names in warnings are same-org only.
- Multi-tenant: every query keeps `org=` scoping; resolver is org-checked already.

## 6. Testing Strategy
- **Regression (must stay green):** all parent sharing suites, especially `test_chart_render_gate.py`, `test_chart_column_guard.py`, `test_chart_post_gate.py` (container-context unchanged), `test_list_scoping.py`, share-modal jest suites.
- New backend: registry entry contract; migration backfill both directions; list scoping per role; member-pin validation; grant role checks; coverage verdicts (covered / role-gap / principal-gap / public); broadening `requires_confirmation` on all three dashboard-widening paths; update_dashboard tile validation; M0 leak tests; request member-block.
- New frontend: badge/bulk on charts list; modal member-block states; embed warning (extend / proceed / cancel); broadening panel naming charts; aggregated bulk prompt.
- Test data: org with 1 admin, 2 analysts, 1 member; charts at edit/none, view/none, none/none; dashboard with mixed tiles.

## 7. Milestones

#### Milestone 0: Public chart leak fix *(ships alone, first)*
- **Deliverable:** public dashboard chart endpoints only serve tiles of that public dashboard.
- **Services:** DDP_backend. **Acceptance:** leak tests above; existing public rendering unchanged.

#### Milestone 1: Charts join the sharing model (backend)
- **Deliverable:** fields + migration 0179, registry entry, gates, list scoping, member-pin + grant/invite/request role rules, org-default seeding (member forced none), deep-link map.
- **Acceptance:** generic access endpoints work for charts; all regression suites green; analyst day-one behavior unchanged.

#### Milestone 2: Coverage + warnings (backend)
- **Deliverable:** coverage endpoint (consolidating the tile-walk), broadening `requires_confirmation` on the three dashboard-widening paths, update_dashboard tile validation, extend action.
- **Acceptance:** coverage verdict tests; warning contract mirrors narrowing; no silent broadening path remains.

#### Milestone 3: Frontend
- **Deliverable:** charts list (scoped + badge + share + bulk), share modal on charts with member-block states, embed warning in ChartSelectorModal, broadening panels (single + aggregated bulk).
- **Acceptance:** jest suites; browser pass against the two un-archived frames.

#### Milestone 4: Request-access for charts + polish
- **Deliverable:** chart 403 → request screen (Analyst+), member-block message, notification/email deep links.
- **Acceptance:** request flow tests; ledger + docs updated.

#### Milestone 5: KPI & Metric direct sharing *(independent of M1–M4; can run in parallel after M0)*
- **Deliverable:** metrics and KPIs grant-capable like dashboards.
- **Services:** DDP_backend (small), webapp_v2.
- **Key tasks:**
  - [ ] Registry: `metric`/`kpi` entries flip `grants=True`; grant validation mirrors charts (user principals Analyst/Admin only — Member grants deferred v1.1-wide; email invites only at Analyst/Admin roles, i.e. admin-only)
  - [ ] Verify resolver/grant paths need nothing else (the request-approve path already writes working metric/KPI grants — extend its tests to the new POST /grants/ path)
  - [ ] Webapp: mount ShareModal on KPI and Metric pages/lists (share row-action + the existing access badge if those lists have one; SHARE_PERMISSION_BY_RTYPE already maps both)
  - [ ] Webapp: multi-select bulk bar on KPI + Metric list pages (share + General-access actions — reuses the shared bulk dialog; fixes the "no UI for metric/KPI General access" hole)
  - [ ] Emails/notifications: confirm the D1 "shared with you" email + deep links fire correctly for metric/kpi (deep-link map has both? verify NOUN_BY_RTYPE)
- **Acceptance:** admin proactively grants a metric to one analyst (modal + bulk); non-admin invite escalation 403; member-grant blocked with message; existing metric/KPI request-approve flow regression-green.

## 8. Open Questions & Risks
- **Strict coverage enforcement** (render-blocking instead of inline-context) — deferred hardening; revisit with member chart grants.
- **Group grants containing Members** on charts — v1.1 resolves them to nothing for member viewers; UX copy must make that non-surprising (warning text names it).
- **Perf:** `accessible_filter` on the charts list for large orgs — same shape as dashboards (indexed org + levels); watch the tile-walk consolidation for N+1 on the coverage endpoint.
- **Migration risk:** 0179 is additive + backfill; sandbox/dev hybrid-lineage note from 0177 applies (apply to shared dev DB when the branch deploys there).
- Design: the two un-archived warning frames need a designer once-over for the per-role vocabulary (extend copy says "Analysts" not "audience").
