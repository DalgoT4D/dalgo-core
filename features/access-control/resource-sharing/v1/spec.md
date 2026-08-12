# Resource Sharing

**Status:** Draft
**Owner:** Product
**Depends on:** Access Control — Role System (Spec A)
**Replaces:** access-control-spec-B-resource-sharing-2026-06-02.md, resource-sharing-write-spec-2026-06-17.md, and the two July 2026 amendments

---

## Overview

Dalgo orgs have a small editing team (1–5 staff) producing content consumed by a much larger audience — program staff, leadership, funders, field partners. Today a consumer either sees everything in the org or nothing. This feature introduces per-resource sharing so editors can share specific dashboards, charts, and reports with specific people, while keeping the dominant flow (share one dashboard with a group of 30) under a minute.

The model has two layers on top of an org-wide baseline:

1. **Org-level floor** — a default permission per role that applies to all resources in the org.
2. **Direct shares** — additive grants to specific users or groups on a specific resource.

For dashboards specifically, direct shares **cascade automatically** to all inner charts and KPIs, so sharing a dashboard shares everything inside it without any extra steps.

---

## Goals

1. Safe to share one dashboard with an external funder without exposing the rest of the org's data.
2. Sharing a dashboard automatically covers all its inner charts — no extra steps, no locked tiles.
3. Dominant flow — share one dashboard with a group of 30 — under 60 seconds.
4. External people (not yet on Dalgo) can be invited directly from the share modal.
5. Groups so sharing with 30+ people doesn't require per-person operations.

## Non-goals (this version)

- Dataset-level gating for Metrics and Alerts (Spec C — table-level access grants)
- Row-level security and column masking on datasets
- Audit log of who viewed / shared
- Time-bound / expiring access
- Sharing on Data infrastructure (Ingest, Transform, Orchestrate, Warehouse) — stays role-gated
- Custom roles, cross-org sharing, comments on anything other than Reports

---

## Target Users

- **Admin** (e.g. M&E Lead) — governs all resources, sets org-wide defaults, onboards staff.
- **Analyst** (e.g. M&E Officer) — creates dashboards, charts, reports; shares with consumers; manages groups.
- **Member** (e.g. program staff, funder, field partner) — consumes content by default; can also create charts and KPIs from existing library metrics. Creating resources is a role permission, independent of the org floor — Members can always create regardless of floor settings. Editing a specific existing resource requires a direct Edit share on that resource.

Org shape to design for: 1–5 editors, 30+ consumers, PII common in the data.

---

## Success Metrics

| Metric | Target |
|---|---|
| Members (consumers) active per org | 5+ within 3 months of GA |
| External partners onboarded | ≥1 per active org |
| "Can't see the dashboard" support tickets | ↓80% |
| Active orgs using resource-level sharing | 50% within 3 months |
| Active orgs using groups | 30% within 3 months |
| Time to share a dashboard with 30 people | <60 seconds |

---

## The Sharing Model

### Org-level floor

The Admin sets a default resource permission for each role in **Settings > Access > Roles tab**. This floor applies to every resource in the org.

| Role | Metrics *(fixed)* | Alerts *(fixed)* | Resources *(configurable)* | Factory default (Resources) |
|---|---|---|---|---|
| Admin | CRUD all | CRUD all + transfer | All access (fixed) | All access |
| Analyst | CRUD any (referential guardrail on delete) | Create on accessible sources; read any; edit/delete own only | No access / View / Edit | Edit |
| Member | View all; use inline in chart builder | View config; be a recipient | No access / View / Edit | View |

Metrics and Alerts permissions are **fixed** — they cannot be changed by the Admin. Resources permissions are **configurable** via the 3-way toggle.

- Changing the floor affects all resources immediately.
- Setting a role's floor to **No access** removes that role's baseline everywhere; per-resource access is then granted by direct shares.
- The floor cannot invert the role hierarchy: **Member floor ≤ Analyst floor ≤ Admin (always Edit)**. The Roles tab blocks any change that would set Member above Analyst.

### Direct shares

On top of the org floor, owners and editors can grant specific users or groups **View** or **Edit** on individual resources.

- Direct shares override the floor **upward** on a per-resource basis — even when the role's floor is No access, a direct share grants access on that specific resource.
- Effective permission = max(floor, direct shares).
- Removing a direct share removes only that grant; the org floor and other direct shares remain.

### Cascade: Dashboard → Charts / KPIs

When a user or group is granted View or Edit on a **Dashboard**, that same permission automatically cascades to every Chart and KPI inside that dashboard.

- **Adding a share is silent and immediate** — no warnings, no prompts.
- Cascade is **direct-share only** — the org floor already applies to all resources equally, so only explicit direct shares on a dashboard propagate down.
- **View cascade** — the chart appears in the user's `/charts` list as view-only and renders inside the dashboard.
- **Edit cascade** — the chart appears in the user's `/charts` list with full edit access.
- Cascade is **one level only**: Dashboard → its direct Charts/KPIs. Reports are fully independent (see Resource Taxonomy).
- To change a user's access on a chart that came via cascade, change their share on the parent dashboard. The chart's share modal will show "Edit/View via Dashboard X" for cascaded permissions and block direct changes — directing the user to the dashboard instead.

**Any removal or downgrade on a dashboard share warns before applying.** When a user or group's share on a dashboard is removed or downgraded (Edit → View, or View removed), the system shows a generic confirmation before applying: *"Removing or downgrading access on this dashboard will also affect access on its inner charts and KPIs. Continue?"* The user confirms before the change takes effect.

### Effective permission resolution

```
EffectivePermission(user, resource) =
    Admin → full access always
    max across:
      — Org floor for user's role  [skipped if resource is Private]
      — Direct grants to the user on this resource
      — Direct grants to any group the user belongs to on this resource
      — Cascaded grants from any dashboard that contains this resource
    If none → no access (resource is invisible)
```

The share modal shows the **resolved effective permission** per user/group — not the breakdown of which path contributed.

### Public links

A per-resource toggle available on **Dashboards and Reports only** (Charts and KPIs do not have public links).

- Available on a resource only when the Admin global **"Allow public sharing"** is on (Settings > Access > Roles, default on).
- **Turning the org toggle off immediately makes all existing public links inaccessible** — not just new ones. Turning it back on restores them.
- Public links are **view-only, no sign-in required, no comments.**
- For a **Dashboard**: the public link grants anonymous view on the dashboard and all its inner charts — no floor or direct-share constraints apply for anonymous viewers.
- For a **Report**: the public link grants anonymous view of the frozen snapshot.
- Logged-in users who open a public-link URL go through normal permission resolution — the public link is an additional anonymous path, not a bypass for authenticated users.
- Toggling on/off requires ownership or effective Edit on the resource.

---

## Metrics & Alerts Governance

Metrics and Alerts live under the **Data** section in the sidebar (not Visualisations). They are governed by **role only** — no per-resource floor or direct shares. Metrics and Alerts have deliberately different governance models.

### Metrics

Metrics are shared canonical definitions — **no ownership concept**. Nobody "owns" a metric; any Analyst can create, edit, or delete any metric (referential guardrail prevents deleting one that is in use).

| Role | Access |
|---|---|
| **Admin** | CRUD all metrics |
| **Analyst** | CRUD — create, read, update, delete any metric |
| **Member** | View metric list; use metrics inline in the chart builder (see below) |

**Referential guardrail:** a metric cannot be deleted until it is unlinked from all resources.

**Edit blast-radius warning:** editing a metric updates every chart and KPI that uses it simultaneously. Before saving an edit, the system must surface the impact: *"This metric is used in N resources. Saving will update all of them."*

### Member access to metrics

Members can view the Metrics list page (read-only). If a Member has Edit on a chart (via direct share or cascade), they can:
- Select from existing **library metrics** when building or editing that chart.
- Build **inline** (chart-scoped) metric calculations in the chart builder.

Members cannot save or promote an inline calculation to the metric library — that is an Analyst+ action.

### KPI rule

A KPI must be backed by a **library metric**. Members can create KPIs from existing library metrics.

### Alerts

Alerts are **creator-owned personal automation** with a recipient list. An Analyst creates an alert on a KPI or Metric; the alert fires notifications to a recipient list when the trigger condition is met.

| Role | Access |
|---|---|
| **Admin** | CRUD all alerts; transfer ownership |
| **Analyst** | Create alerts on accessible sources; read any alert on accessible sources; edit and delete **only their own** alerts |
| **Member** | Cannot create alerts; can view alert config on accessible sources; can be a recipient |

Rules:
- **Trigger source:** a KPI or a Metric.
- **Ownership is transferable** — the owner or an Admin can transfer ownership to another Analyst.
- **View (config):** anyone who can access the trigger source (including a Member) can view the alert config. Creator always sees it. **Sensitive-source lock:** if the trigger source becomes restricted, the alert drops to creator + Admin visibility only.
- **Edit and Delete:** owner + Admin only (chosen over "any analyst with access" to prevent ambiguity over who can modify shared automation).
- **Recipient list is a separate axis.** Receiving alert notifications ≠ any config right. Members can be recipients regardless of edit rights. Managing the recipient list is an edit action — owner/Admin only.
- **Two entry points:** a **bell-in-context** on a KPI or Metric to create an alert in context, plus a **manage/list page under Data** ("alerts I own or receive").

### Dataset access scope

Access to Metrics & Alerts is governed by role only — no dataset gating. Admins and Analysts see all metrics and alerts. Members see all metrics and alerts read-only.

---

## Resource Taxonomy

| Resource | Cascade | Public link | Notes |
|---|---|---|---|
| **Dashboard** | Source — direct shares cascade to inner Charts/KPIs | Yes | |
| **Chart** | Target — receives cascaded shares from parent Dashboards | No | Both View and Edit cascade surface the chart in `/charts`; Edit cascade additionally grants edit access |
| **KPI** | Target — same as Chart | No | Must be backed by a library metric (when Metrics ship) |
| **Report** | None | Yes | Frozen point-in-time snapshot of one Dashboard. Own permissions, fully independent. Even if source charts/KPIs are deleted, the Report still loads. Report-Edit = regenerate snapshot, edit executive summary, moderate comments — not edit the source dashboard or charts. When creating a Report, the user only sees Dashboards they have access to. |

---

## Groups

- **Analyst+ can create** a group. Members cannot.
- Only the group's **creator and Admins** can edit (membership, rename) or delete a group. Other Analysts may use groups they can see — share resources with them — but cannot edit them. The ⋮ Edit/Delete actions appear only for creator/Admin.
- Groups are org-wide and reusable across resources.
- **Group-list visibility by role:** Admin sees all groups; Analyst sees groups they created or belong to; Member sees only groups they belong to.
- Name-collision warning on create to prevent duplicate group names.
- Adding a member to a group grants them access to everything the group is shared on. Removing a member revokes group-derived access (unless they hold a direct grant). Deleting a group revokes all access it conferred.

### Group management UI (Settings > Access > Groups tab)

Groups list — table with Group Name, member avatar stack (+ overflow count), Created By, Created date, and a ⋮ actions menu per row (Edit Group / Delete Group). **+ Create Group** button top right.

Create / Edit group modal:
- **Group name** field (name-collision warning on save)
- **Add people or paste emails** — search existing users or paste comma-separated emails to add members
- **Existing Members** list — each member shown with their role and an ✕ to remove
- CANCEL / CREATE GROUP (or SAVE) actions

---

## Share Modal & Invite Flow

### The modal

One modal, opened from a resource page or a resource list.

```
Share "Field Performance Dashboard"

┌──────────────────────────────────────────────────┐
│ Search for people, group or add emails            │
│ [ field-staff@ngo.org, anjali@ngo.org ... ]       │
├──────────────────────────────────────────────────┤
│ ✔ anjali@ngo.org  Analyst          View  ▼  ✕    │
│ ⚠ xyz@partner.org (external)       View  ▼  ✕    │
│   → will be invited as Member                     │
├──────────────────────────────────────────────────┤
│ People with access                                │
│   priya@ngo.org    Admin           Owner          │
│   Field Staff (group)              Edit           │
├──────────────────────────────────────────────────┤
│ 🔒 Private                                        │
│    Only shared users/groups can see this  [ toggle ] │
├──────────────────────────────────────────────────┤
│ 🔗 Public sharing                                 │
│    Anyone with the link can view    [ toggle ]    │
└──────────────────────────────────────────────────┘
             [ CANCEL ]        [ SHARE ]
```

### Behaviors

- **Dashboard sharing** — when sharing a Dashboard, the modal displays: *"All inner charts and KPIs will inherit this permission."*
- **Matched emails / names** — existing users or groups get the chosen permission immediately on Share.
- **Unmatched emails** — flagged inline as external; invited as Member on accept; share applied on accept; shown as **pending** until then.
- **Bulk paste** — comma- or newline-separated emails accepted in one paste.
- **Default permission** = View; owner or editor can switch to Edit.
- **Re-sharing is limited to the owner and Edit-holders.** View-holders cannot open the share modal to add others. An Edit-holder can share at View or Edit (never above their own level). A View-holder who wants to give a colleague access must ask the owner or an Edit-holder to do it.
- **Revoking a share** — an ✕ next to each entry in the "People with access" list removes that direct share immediately.
- **Private toggle** — available on all access-controlled resources (Dashboards, Charts, KPIs, Reports). When on, the org floor is ignored for this resource — access is determined solely by grants (direct shares, cascade, or Admin). Anyone with a grant still has access; the floor no longer provides a baseline. This is the mechanism for making a single resource private without changing the org-wide floor. Requires ownership or Edit to toggle. **Turning Private on immediately disables any active public link on the resource; turning it off does not restore the public link — the owner must re-enable it manually.** The public sharing toggle is hidden while Private is on (and also hidden when the org disallows public sharing).

### Ownership transfer

Ownership transfer is available directly from the share modal — it is a third option in the permission dropdown alongside "Can View" and "Can Edit" for any user in the "People with access" list.

**Rules:**
- Only the **current owner or an Admin** can initiate a transfer.
- Ownership can only be transferred to a user who holds **effective Edit** on the resource — via the role floor or a direct Edit share. A Member with a direct Edit share qualifies.
- When the recipient becomes owner they receive full ownership rights (Edit + delete + share) regardless of their current share level on the resource.
- The **previous owner's direct shares are not changed**. Their effective access after the transfer = max(org floor for their role, any existing direct share). If they had no direct share and their org floor is No access, they lose access entirely.
- A **confirmation dialog is required** before the transfer applies: *"Transfer ownership of [Resource] to [Name]? You will lose owner status. Your access will revert to your role permissions or any direct share you hold."*

---

### Pending invites & expiry

- Pending invitees appear in the share list with a **pending** badge until they accept.
- All pending grants and group memberships activate on acceptance.
- Pending invites **expire after 30 days** — a platform-wide constant, not configurable per org. Expired invites drop from the list and must be re-sent.

### Request access

When an authenticated user opens a resource link they don't have access to:

- A **request-access screen** lets them request View or Edit with an optional note.
- The request routes to the **resource owner only** — as a notification and an entry in the Requests section of the share modal.
- The owner picks the level to grant (can downgrade an Edit request to View). Approval creates a direct share and notifies the requester. Decline notifies the requester.
- Granting resource access never changes the requester's platform role.
- Unauthenticated visitors (e.g. public-link off, non-user opens a link) are prompted to sign in or ask to be invited.
- Pending access requests expire on the same **30-day** constant.

### Bulk sharing from resource lists

Every resource list (Dashboards, Charts, Reports) supports **multi-select + bulk Share**.

- Applies to resources the actor has effective Edit on; skips the rest with a count: *"Shared 8 of 10 — 2 skipped: you don't have Edit on those."*
- The same share modal applies grants / public-link to all selected resources at once.

---

## Edge Cases & Explicit Rules

**Edit cascade does not confer delete.** A user with Edit on a chart via cascade can edit the chart's content but cannot delete it. Delete requires ownership or Admin.

**Chart removed from a dashboard.** When an editor removes a chart from a dashboard, any cascaded shares that came from that dashboard are immediately revoked for all users and groups — unless they hold a direct share on the chart or have access via another dashboard.

**Chart in multiple dashboards.** If a user has Edit on Dashboard A (containing Chart C) and View on Dashboard B (also containing Chart C), their effective permission on Chart C = Edit (max). If their share on Dashboard A is removed, their effective permission on Chart C drops to View (from Dashboard B). The system recalculates on every share change.

**Share level ceiling.** An effective View-holder cannot see the share modal at all (see Re-sharing). Edit-holders can share up to their own level, never above.

**Derived Edit confers re-share rights.** If a user holds Edit on a chart only via cascade (from a parent dashboard, no direct chart grant), their effective Edit is full Edit — they can re-share that chart from its share modal.

**Public link bypasses inner chart access.** Anonymous viewers of a public dashboard see all inner charts regardless of those charts' access settings. Public links are frictionless external sharing — chart-level restrictions do not apply to anonymous viewers.

**Org floor change is immediate.** Changing the org floor (e.g. Members from View to No access) affects all resources immediately. Direct shares are unaffected — users with a direct share keep access even after a floor tightening.

**Member empty state.** If the org floor is No access for Members, Members who log in see blank list pages (no Dashboards, Charts, Reports) until explicitly shared on specific resources. If the floor is View, Members see all resources in read-only.

---

## Comments (Reports only)

- Comments exist on **Reports only**. Dashboards, Charts, and KPIs have no comments in v1.
- Anyone with **View on a Report** can read and add comments.
- **Edit on a Report** includes comment moderation (delete/hide).
- Public-link (anonymous) viewers cannot comment.

---

## UI Surface

| Surface | Description |
|---|---|
| **Settings > Access** | Single page with three tabs: **People** (user management, collapsed from the previous two-tab structure), **Groups** (group management), **Roles** (permission matrix with two columns — Metrics & Alerts fixed permissions and Resources configurable 3-way toggle; Allow public sharing org toggle). |
| **Share modal** | Search people/groups/emails; per-share permission picker (View/Edit); pending state for external emails; People with access list; Private toggle; public sharing toggle (hidden if org disallows or Private is on). |
| **Resource list pages** | Main-app pages (Dashboards, Charts, Reports, KPIs) — not a Settings surface. Effective-access indicator per resource (e.g. View / Edit / Owner); multi-select with bulk Share action and skipped-count summary; "Shared with you" section for Members. All sharing is done via the resource share modal, opened from the resource page or the list. |
| **Request-access screen** | Shown on access-denied for authenticated users; request View/Edit with note; routes to owner. States: form → submitted → decided (approved/declined). |
| **Requests section** (in share modal) | Pending access requests with approve (pick level) / decline. |
| **Groups (Settings > Access > Groups tab)** | Table: Group Name, member avatar stack, Created By, Created date, ⋮ actions (Edit Group / Delete Group). Create/Edit modal: group name + add people/emails + existing members list with ✕ per member. Scoped by role — Members only see groups they belong to. |
| **Reports** | Comments panel for viewers; moderation for report editors. |

---

## Migration

| Today | After this feature |
|---|---|
| Dashboards/Reports have existing shares | Migrate 1:1 into direct shares. |
| Charts have no sharing | Effective access from the org floor (factory: Analysts = Edit, Members = View). |
| Interim "Members see all content" window (Spec A) | Narrows to org floor + direct shares. Members now see only what the floor admits + what's explicitly shared. Communicate before launch. |
| Public links | Existing links preserved; gated going forward by the org "Allow public sharing" toggle (default on). |

---

---

## Dependencies

**Requires:** Access Control — Role System (Spec A) — Admin/Analyst/Member roles, ownership primitive (creator = owner, transferable, Admin = effective owner, owner-only delete), Settings IA, invitation role-tier rules (anyone invites as Member; only Admins elevate).

**Enables:** Dataset-level row/column security in a later version; Metrics and Alerts governance.

---

## Worked Examples

**A. Share a dashboard with 30 funders in under 60 seconds**
Analyst opens the Dashboard share modal, pastes 30 funder emails, sets permission to View, hits Share. Non-users receive invites as Members. Dashboard-View cascades to all inner charts — no separate chart-sharing needed. Funders see only this dashboard and its charts; the rest of the org's content is unaffected.

**B. Restrict access to a sensitive area**
M&E Lead wants Members to stop seeing all dashboards and only see what's explicitly shared. She sets the org floor: Members → No access. All Members immediately lose ambient access. She then opens the "Field Operations Dashboard" share modal and adds the Field Staff group at View. Field Staff now see only that dashboard (and its inner charts via cascade). All other Members see nothing until explicitly shared.

**C. Funder gets Edit on a dashboard — charts follow**
Analyst shares "Donor Pipeline Dashboard" with Priya (a funder) at Edit. Priya immediately has Edit on the dashboard and, via cascade, on all its inner charts. Priya's `/charts` list now shows those charts as editable. To revoke, the Analyst removes Priya from the dashboard share — Priya loses Edit on all the inner charts simultaneously.

**D. Downgrade blocked by cascade**
Admin tries to set Priya to View on a specific chart. Priya holds Edit on that chart via cascade from "Donor Pipeline Dashboard." The chart's share modal shows "Priya — Edit (via Donor Pipeline Dashboard)" and blocks the direct change: *"Priya has Edit via Donor Pipeline Dashboard. Change her access there to update it here."* Admin goes to the dashboard, changes Priya's share to View; the chart immediately reflects View.

**E. Request access from a shared link**
A program officer receives a dashboard link in a WhatsApp message. She opens it, has no access. She sees the request-access screen, requests View with a note: "Need this for the quarterly review." The request goes to the dashboard owner. The owner approves at View; the program officer gets a direct share and can now open the dashboard.

**F. External funder invited via share modal**
Analyst shares "Impact Dashboard" with xyz@funder.org — an email not in the system. The modal flags it as external and will invite them as Member on accept. The funder receives an invite email, joins Dalgo as a Member, and immediately gets View on the dashboard (and its inner charts via cascade).
