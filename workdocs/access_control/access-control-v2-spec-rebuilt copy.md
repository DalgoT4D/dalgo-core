# Dalgo Access Control — V2 Spec (Rebuilt)

**Status:** Draft for review
**Owner — Product:** Abhishek Nair
**Owner — Engineering:** Siddhanth (model), Pradeep Kaushik (delivery)
**Date:** 2026-05-18
**Replaces:** "Dalgo Charts and Dashboards Sharing Auth – V2 Access Control Spec" + engineering rewrite at `Experiments/dalgo-core/workdocs/access_control/spec.md`

---

## 1. Overview

Dalgo's current role-based access control is too coarse to safely serve the realistic NGO setup: a small editing team (1–5 staff) producing dashboards consumed by a much larger audience (30+ viewers — program staff, leadership, funders, field partners), where data often contains beneficiary-level PII.

Today the platform forces an all-or-nothing choice — Viewers see every dashboard in the org or none at all — which means NGOs cannot safely invite external partners. This spec replaces the model with a clean primitive (WHO × WHAT × WHERE) and adds resource-level sharing, user groups, and per-resource visibility controls — while keeping the user-facing experience friction-free.

---

## 2. Goals

1. Make it safe to invite external Viewers (funders, field partners, leadership) without exposing all org data.
2. Allow Editors to share specific dashboards, charts, and reports with users or groups, with view or edit access.
3. Default visibility that's frictionless for internal collaboration but safe for sensitive content.
4. Support user groups so resource sharing scales to 30+ viewers without per-person operations.
5. Build on a model that scales cleanly to future resources (alerts, KPIs, metrics, datasets, chat-with-dashboards) without rewriting.

### Non-goals (V2 features deferred — see §15)

Row-level security on datasets, audit logs, time-bound access, email-domain auto-signup, restricted groups, custom roles, cross-org sharing.

---

## 3. Problem Statement

The current access model has structural and functional gaps:

1. **Viewer role is broken.** The `can_view_dashboards` and `can_view_charts` permissions are missing — the role exists but does nothing useful.
2. **Analyst has full pipeline/dbt write access.** An M&E officer can accidentally break data infrastructure.
3. **No per-resource sharing.** Viewers see all org dashboards or none. No way to share one dashboard with one funder.
4. **No user groups.** Sharing with a team of 30 requires 30 individual actions.
5. **Charts have no sharing surface at all** — they inherit nothing and can't be shared independently.
6. **Sidebar isn't gated by role.** Viewers see nav items they can't use.
7. **No route protection.** Unauthorized pages are accessible by direct URL.
8. **`has_schema_access()` is a TODO** — any authenticated user can query any warehouse table. (Flagged; full fix is RLS in V2.)

These gaps mean NGOs handling beneficiary data, funder relationships, or external partnerships cannot safely use Dalgo as a sharing surface.

---

## 4. Target Users & Personas

| Persona | Role | Real-world context |
|---|---|---|
| **Sarah** (M&E Lead) | Account Manager | Owns the org's data setup, onboards staff, manages users and billing |
| **Raj** (Implementation Partner) | Pipeline Manager | Builds and operates pipelines and transforms; may serve multiple NGOs |
| **Priya** (M&E Officer) | Analyst | Creates dashboards/charts to track program outcomes |
| **James** (Program Staff / Funder) | Viewer | Checks specific dashboards regularly; may be external; doesn't create content |
| **Leadership** | Viewer | Wants exec-level summaries; can't navigate a full BI tool |

**Most underserved persona today:** James — currently no safe way to invite him because the platform shows him everything or nothing.

**Typical org shape:** 1–5 editors (Sarah/Raj/Priya bucket) and 30+ viewers (James bucket). The viewer flow is the hottest path.

---

## 5. Access Control Model: WHO × WHAT × WHERE

### 5.1 The primitive

Every access grant is a binding of three independent dimensions:

| Axis | Question | Examples |
|---|---|---|
| **WHO** (Principal) | Who is requesting access? | A user (James), a group (Field Staff) |
| **WHAT** (Permission) | What can they do? | View, Edit (resource layer); Admin (org layer) |
| **WHERE** (Scope) | On which resource? | A specific dashboard, the Dashboards module, the entire org |

Example grants:

```
(WHO: James,         WHAT: View,   WHERE: Dashboard "Field Performance")
(WHO: Field Staff,   WHAT: View,   WHERE: Dashboards module)
(WHO: Priya,         WHAT: Edit,   WHERE: Dashboards module)
(WHO: Raj,           WHAT: Edit,   WHERE: Pipelines module)
(WHO: Sarah,         WHAT: Admin,  WHERE: Organization)
```

### 5.2 Permission levels

Two levels at the **resource** layer:

| Level | Means |
|---|---|
| **View** | See the resource, interact with filters, export |
| **Edit** | View + create, modify, delete, **and share** the resource |

One level at the **organization** layer:

| Level | Means |
|---|---|
| **Admin** | Edit + manage users, billing, org settings, force-edit/delete any resource, change org-level defaults |

Plus an implicit concept:

- **Owner** = creator of a resource (or whoever it's transferred to). Has Edit + delete + transfer ownership. Not a grantable level.

### 5.3 Roles as templates, not enforcers

Roles still exist as the UX for inviting users. But each role is a **template** that generates default grants on invite. After invite, individual grants can be added or removed.

**Role hierarchy** (top to bottom):
Account Manager > Pipeline Manager > Analyst > Viewer

**Default grants generated by each role:**

| Role | Default grants on invite | Rationale |
|---|---|---|
| **Viewer** | None — inviter selects specific resources or groups during invite | External/restricted by nature. Blanket access defeats the purpose. |
| **Analyst** | (Edit, Dashboards module), (Edit, Charts module), (Edit, Reports module), (View, Data Explorer module) | Internal content staff. Broad reporting access. |
| **Pipeline Manager** | All Analyst grants + (Edit, Pipelines module), (Edit, Transforms module), (Edit, Orchestration module) | Infrastructure operators. Superset of Analyst. |
| **Account Manager** | (Admin, Organization) | Single grant covers everything. |

### 5.4 Module-level vs resource-level grants

| Grant type | Example | Covers future resources? |
|---|---|---|
| **Module-level** | (Priya, Edit, Dashboards module) | Yes — any new dashboard automatically accessible |
| **Resource-level** | (James, View, Dashboard "Field Performance") | No — only this specific resource |

This means Editors automatically see new resources as the org grows; Viewers only see what was explicitly shared with them.

### 5.5 Permission resolution

```
Effective Access(User, Resource) =
    max permission level across:
      - Direct grants on this resource
      - Direct grants on the parent module
      - Direct grants on the organization
      - Group grants on this resource
      - Group grants on the parent module
      - Group grants on the organization
```

Direct shares stack additively. Module and org grants are additive ceilings, never subtractive. If no grants match and the visibility floor doesn't include the user, access is denied.

---

## 6. Default Visibility

### 6.1 The default rule

Every content resource (dashboard, chart, report) has a **compulsory visibility floor** plus an optional **direct share list**. There is no "inherit" or implicit-default state — every resource carries an explicit setting.

**Default visibility floor for all new content resources: Internal** — visible to all internal users (Analyst+) in the org. No Viewers see new resources unless explicitly shared.

This satisfies the "friction-free for internal collaboration" instinct without exposing beneficiary data to funders/leadership by accident.

### 6.2 Visibility floor + direct share list

Every content resource has two access dimensions:

**Visibility floor (compulsory)** — sets the baseline audience:

| Floor | Who sees the resource via the floor |
|---|---|
| **Private** | Only the owner (+ Account Manager via governance override) |
| **Internal** *(default)* | All internal users (Analyst+) |
| **All Viewers in org** | Every authenticated user in the org |
| **Public link** | Anyone with the link (view-only, no auth required) |

**Direct share list (additive)** — specific groups and/or users granted View or Edit access, on top of the floor.

**Effective audience = visibility floor ∪ direct share list.**

A chart with floor = Private and direct shares = [Field Staff group] is visible to: the owner, the AM (via override), and Field Staff group. No one else.

**Strictness ordering of the floor** (most restrictive → least restrictive):
`Private < Internal < All Viewers < Public link`

This ordering powers the embed-time and dashboard-broadening guardrails in §6.4.

### 6.3 Org-level default threshold (Account Manager only)

Account Manager can change the default visibility threshold for the org. Options:

- All internal users (Analyst+) — *factory default*
- Pipeline Manager and above only — *for orgs with stricter internal walls*
- Private (creator only) — *for high-sensitivity orgs*

This is a single setting in Org Settings. 95% of orgs will never touch it. It exists for the edge.

### 6.4 Embed-time and dashboard-share guardrails

Two warnings ensure no viewer ever sees a dashboard with charts they can't access (no locked tiles, ever):

#### 6.4.1 Embed-time warning

Fires when an editor adds a chart to a container (dashboard or report) whose audience is broader than the chart's effective audience.

> *"This chart is not visible to some viewers of 'Field Operations Dashboard' (Field Staff group, 15 people). Add Field Staff group to this chart's share list?"*

Two choices:
- **Yes, share** — Field Staff group is added to the chart's direct share list. Chart's visibility floor is unchanged. Effective audience now covers the dashboard's audience.
- **Cancel** — embed is aborted. Chart's audience and floor stay as they were.

The chart's visibility floor (Private/Internal/etc.) is never bumped by this flow — only the direct share list extends.

#### 6.4.2 Dashboard-broadening warning

Fires when an editor changes a dashboard's sharing to add an audience that isn't covered by all charts inside the dashboard.

> *"This dashboard's new audience includes Funders group. 7 of the 10 charts in this dashboard aren't currently shared with Funders. Add Funders group to all 7 charts' share lists?"*

Two choices:
- **Yes, extend** — Funders group is added in bulk to every covered-deficit chart's direct share list. Dashboard share proceeds.
- **Cancel** — dashboard share is aborted. If the editor wants to exclude a specific chart, they remove it from the dashboard first and retry the share. (No per-chart pick — the bulk-or-cancel choice keeps the flow tight.)

#### 6.4.3 What the warnings achieve

- **No locked tiles, ever.** Either every dashboard viewer can see every chart in it, or the action doesn't go through.
- **Every grant on a chart is explicit and auditable.** "Why does James see this chart? Because Funders group was added to the share list on 12 May when Sarah shared Field Ops with Funders."
- **Private and Internal-floor charts stay restricted** unless the owner explicitly extends them via a warning prompt.

#### 6.4.4 Edit-on-chart still required to embed

Per §7.2, only an editor with Edit on a chart can place it in a container. For a Private chart with no direct shares, only the owner (plus AM) can embed. Other editors can't pull a Private chart into a dashboard because the chart isn't visible to them at all.

This is the primary structural defense against accidental oversharing. The warnings handle the cases where the editor *does* have Edit on the chart and is making an explicit broadening decision.

#### 6.4.5 AM behavior

Account Manager can see and embed any chart via the §6.6 governance override. The warnings still fire for the AM — the override is governance access, not silent broadening.

#### 6.4.6 Why no Inherit / no locked tiles

A previous draft had a third visibility option, "Inherit from containers," where chart audience was computed from containers dynamically. Dropped because:
- Every grant should be explicit and auditable, not implicit
- "Inherit" was a UX concept users didn't actually pick — it was the default state pretending to be a setting
- Compulsory visibility + direct share list captures the same outcomes with a flatter model

The locked-tile experience (viewer sees a dashboard with some charts hidden) is also explicitly avoided — the bulk-broaden-or-cancel choice means access is always all-or-nothing within a dashboard.

#### 6.4.7 Why no Sensitive flag

An earlier draft had a "Sensitive" flag that forced charts Private regardless of containers. Dropped because the actual user need — "funders see the chart, field staff see the chart, the data shown differs by audience" — is better served by row-level security + column masking on the underlying dataset (deferred to V2; see §15.2). For V1, Private floor + direct shares + warnings cover the safety story for accidental oversharing. RLS handles the audience-aware-data case in V2.

### 6.5 Public link sharing

Off by default for all resources. Editor can toggle on per resource. Public links are view-only and include resource ID with no sensitive identifiers.

### 6.6 Account Manager override

Account Manager can view/edit/delete any resource in the org regardless of visibility setting. This is org-level Admin power, used for governance and recovery (e.g., reassigning ownership when an Editor leaves).

---

## 7. Resource Taxonomy & Access Rules

### 7.1 The three access rules

These three rules apply to all resources, current and future:

1. **Every resource has its own audience.** Containers do not cascade access to children implicitly. A chart's effective audience = its visibility floor ∪ its direct share list, regardless of which dashboards it's embedded in.

2. **Embed and dashboard-share operations gate audience alignment.** Per §6.4, an editor can only embed a chart in a container with a broader audience by extending the chart's direct share list to match (with explicit consent). A dashboard's audience can only be broadened if all inner charts can be bulk-extended to match (or the dashboard share is cancelled).

3. **Direct shares stack additively, never subtractively.** Effective access = visibility floor ∪ union of all direct grants. Removing a direct grant subtracts only that grant; other paths to access (floor, other direct grants) remain.

### 7.2 Additional access primitives

- **Embedding control:** To embed chart X in dashboard Y, the embedder must have Edit on chart X. For a Private chart with no direct shares, only the owner (plus AM) can embed. This is the primary structural defense against accidental oversharing — other editors can't even see Private charts in their picker.
- **Embed-time warning when audience broadens:** See §6.4.1. If the chart's effective audience doesn't cover the container's audience, the system warns the editor at embed time and offers to extend the chart's direct share list to cover the gap — or cancel.
- **Dashboard-broadening warning:** See §6.4.2. If a dashboard's new audience exceeds the audience of any chart inside it, the system bulk-extends all such charts' share lists on consent — or cancels the dashboard share. No partial sharing.
- **References ≠ shares.** An alert referencing a metric, a report linking to a dashboard, a KPI used in a chart — none of these grant access to the referenced resource. Each resource is independently access-controlled.

### 7.3 Full resource taxonomy

| Resource | Type | Contains | Contained in | Individually shareable? | Default visibility floor | Access behavior |
|---|---|---|---|---|---|---|
| **Dashboard** | Content | Charts | — | Yes | Internal | Audience = floor ∪ direct shares. Embed/share warnings keep inner charts' audiences aligned. |
| **Chart** | Content | — | Dashboard, Report | Yes | Internal | Audience = floor ∪ direct shares. Independent of containers; warnings ensure container audiences are covered before embed/share. |
| **Report** | Content | Charts | — | Yes | Internal | Audience = floor ∪ direct shares. Same as Dashboard. |
| **Pipeline** | Infrastructure | — | Pipelines module | No (V1) | Module-grant only | Module-level grant only |
| **Transform (dbt)** | Infrastructure | — | Transforms module | No (V1) | Module-grant only | Module-level grant only |
| **Orchestration Flow** | Infrastructure | — | Orchestration module | No (V1) | Module-grant only | Module-level grant only |
| **Data Explorer** | Tool/UI | — | Data Explorer module | No | Module-grant only | Module-level grant only |
| **Alert** *(future)* | Reference | — | Alerts module | Yes | Private | References a chart/metric but doesn't inherit its access |
| **KPI** *(future)* | Reference | — | KPIs module | Module-level (V1), individual (V2) | Module-grant only | Definition is module-level; dashboards using it don't grant KPI access |
| **Metric** *(future)* | Reference | — | Metrics module | Module-level (V1), individual (V2) | Module-grant only | Same as KPI; tracked separately |
| **Dataset / Warehouse table** *(future)* | Data | — | Warehouse | Governed by RLS (V2) | RLS-managed | Chart access does NOT grant dataset access; row/column rules apply at query time |
| **Chat with Dashboards** *(future)* | UI feature | — | Dashboards module | Linked to dashboard | Internal | Available to anyone with view access to the dashboard |

### 7.4 Worked examples

- **KPI rendered in a shared dashboard:** James (Viewer) has view on the dashboard. He sees the KPI value/visualization inside the dashboard because the dashboard owner authorized that embed. He does NOT get access to the KPI as a standalone resource — can't open it in the Metrics module, can't use it in his own dashboards.

- **Beneficiary PII chart for field staff:** Priya creates a beneficiary detail chart and marks its floor **Private**. No one else can see it in the chart picker. She creates a "Field Operations" dashboard, shares it with the Field Staff group, and drags the chart in. Embed-time warning fires: *"This chart isn't visible to Field Staff group (15 people). Add Field Staff group to this chart's share list?"* She picks Yes. Chart floor stays Private; direct shares now include Field Staff group. Field staff see the chart inside the dashboard. Funders have no path to it because they're not on the Field Operations dashboard and not in the chart's share list.

- **Salary chart for leadership only:** Priya marks the salary chart's floor **Private**. She adds it to "Leadership Overview" (shared with Leadership group). Embed warning fires; she accepts → Leadership group added to the chart's share list. Later, she tries to drop the same chart into "Org Overview" (shared with All Viewers). Embed warning fires again: *"This chart isn't visible to All Viewers. Add All Viewers to this chart's share list?"* She picks Cancel. The salary chart stays restricted to Leadership group.

- **Dashboard audience broadened after embed:** Sarah (AM) decides the "Field Operations" dashboard should also be shared with the Funders group. The dashboard contains 10 charts, 3 of which currently aren't shared with Funders. On save, system warns: *"3 charts in this dashboard aren't shared with Funders group. Add Funders to all 3 charts' share lists?"* Sarah picks Cancel — funders don't belong on this dashboard. (If Sarah wanted to keep a subset private, she'd remove those charts from the dashboard first and re-share.)

- **Other editor tries to embed a Private chart:** Aanya (another Analyst) is building a compensation dashboard. The salary chart Priya created doesn't appear in her chart picker because its floor is Private and she isn't on the share list — she can't pull Priya's chart into her dashboard. *Limitation:* Aanya still has Analyst-level dataset access, so she could rebuild the chart from the underlying salary table. V1 protects against accidental oversharing by the creator and against external Viewers; protecting against another Editor reading the underlying data requires V2 dataset-level RLS + column masking. See §15.3 V1 Limitations.

- **Chart in two dashboards:** Chart X (floor = Internal, direct shares = []) is added to Dashboard A (shared with Field Staff group, Viewers). Embed warning fires; Priya accepts → Field Staff added to X's share list. Later X is added to Dashboard B (shared with Funders group, Viewers). Warning fires again; Priya accepts → Funders added to X's share list. X's effective audience is now: Internal staff + Field Staff + Funders. Removing X from Dashboard A doesn't subtract Field Staff from X's share list — they remain explicitly granted access. Priya cleans this up manually if she wants by editing X's share list directly.

---

## 8. User Groups

### 8.1 Group governance

- **Any Editor can create a group** (Analyst, Pipeline Manager, Account Manager)
- **Groups are org-wide and reusable** across resources
- **Any Editor can add existing org members** to any group
- **Group creator and Account Manager** can rename, delete, or remove members
- **Account Manager** can merge groups (V1 utility for cleaning sprawl)
- **Name-collision warning** on create — prevents three different "Field Staff" groups

### 8.2 Group sharing

- Resources can be shared with groups at View or Edit level
- Adding a member to a group grants them access to all resources shared with that group
- Removing a member revokes access (unless they have a direct grant)
- Deleting a group revokes all access granted through it

### 8.3 Deferred to V2

- **Restricted Groups** (AM-only membership management for sensitive groups like "Leadership")
- **Nested groups** (groups-within-groups)

---

## 9. Sharing & Invite Flow

### 9.1 The combined share modal

The dominant user flow — Editor shares a dashboard with a group of 30 — is collapsed into a single modal:

```
Share "Field Performance Dashboard"

┌─────────────────────────────────────────────────┐
│ Add people, groups, or paste emails             │
│ [field-staff@ngo.org, anjali@ngo.org, ...]      │
├─────────────────────────────────────────────────┤
│ Permission on this resource: [View ▼]           │
│                                                  │
│ Invite new users as: [Viewer ▼]                 │
│   (Options gated by your role — Sarah sees      │
│    Viewer/Analyst/Pipeline Manager/Account Manager) │
│                                                  │
│ Assign to group: [Field Staff ▼] [+ New group]  │
└─────────────────────────────────────────────────┘

✔ anjali@ngo.org — existing user, will be granted view access
⚠ xyz@new-partner.org — not on Dalgo
   → Will be invited as Viewer and added to Field Staff
   → [Remove this email]

[ Cancel ]                              [ Share ]
```

### 9.2 Behaviors

- **Matched emails:** existing users get the assigned permission immediately
- **Unmatched emails:** flagged with a warning; default to "invite at the modal's invite-role + add to selected group + apply the share on accept"
- **Pending state:** unmatched users appear in the share list and group list with a "pending" tag until they accept
- **Bulk paste:** comma- or newline-separated emails accepted in one paste
- **Group assignment:** assigning emails to a group (existing or newly created) is done in the same modal — no need to leave and create a group separately
- **Default permission on resource:** View; Editor can change to Edit before sending
- **Default invite role:** Viewer (the 95% case for resource sharing); inviter can pick any role at-or-below their own level from the modal picker
- **Permission scope:** Editors can grant up to their own level on the resource (Editor can grant View or Edit; cannot grant Admin since Admin is org-level only)

### 9.3 Invitation rules

**Invite-at-and-below-your-level** — applies wherever an invite is created (resource share modal or Settings > Users):

| Inviter | Can invite as |
|---|---|
| Account Manager | Account Manager, Pipeline Manager, Analyst, Viewer |
| Pipeline Manager | Pipeline Manager, Analyst, Viewer |
| Analyst | Analyst, Viewer |
| Viewer | Cannot invite |

**One unified invite model, two entry points:**

1. **Paste-to-share from a resource** (dominant flow). Role picker defaults to Viewer and is gated by inviter's level. Most pastes will keep the default; the AM doing bulk onboarding can flip it to Analyst once for the whole batch.
2. **Invite to platform** (from Settings, by Editors). Same role picker; no resource-share context; inviter optionally selects initial groups or resource grants.

The role-permission gating is identical in both entry points. No asymmetry.

### 9.4 Account Manager governance (AM-only)

- Change an existing user's role
- Deactivate / remove a user
- Force-edit or force-delete any resource (org admin override)
- Change org-level defaults (visibility threshold, etc.)

---

## 10. User Journeys

### 10.1 Sarah onboards a new field-staff team (10 users)

1. Sarah opens the "Field Performance" dashboard, clicks Share
2. She pastes 10 emails, picks View permission, leaves invite-role at default (Viewer)
3. She creates a new group "Field Staff – Q3" in the same modal
4. All 10 emails: unmatched. System will invite each as Viewer, add to the new group, apply the share on accept.
5. Sarah hits Share. **Dashboard-broadening warning fires** because the dashboard's new audience (Field Staff – Q3 group, Viewers) isn't currently covered by all charts inside. *"8 of the 10 charts in this dashboard aren't shared with Field Staff – Q3. Add Field Staff – Q3 to all 8 charts' share lists?"* Sarah picks Yes. All 8 charts now have direct grant to the new group.
6. Done. ~45 seconds.
7. Over the next week, as field staff accept invites, they automatically gain access to the shared dashboard and every chart inside it. Pending state visible to Sarah in the share list.

*Variant — one of the 10 is a new analyst:* Sarah opens a separate Share or a separate paste batch, flips the invite-role picker to Analyst, pastes that one email. Same flow.

### 10.2 Priya handles two sensitive charts among ten

1. Priya creates ten charts for the quarter. Eight are operational metrics — she leaves them at the default visibility floor **Internal**, empty direct share list.
2. Two contain sensitive data: a beneficiary detail table (PII) and a staff-salary-by-role chart. She sets both visibility floors to **Private**.
3. The Private charts disappear from every other editor's chart picker. Only Priya (and Sarah, the AM) can see they exist.
4. **Beneficiary chart →** Priya drags it into "Field Operations" (shared with Field Staff group, Viewers). Embed warning: *"This chart isn't visible to Field Staff group (15 people). Add Field Staff group to this chart's share list?"* She picks Yes. Chart floor stays Private; direct shares now include Field Staff group. Field staff see the chart inside the dashboard.
5. **Salary chart →** Priya drags it into "Leadership Overview" (shared with Leadership group, Viewers). Embed warning fires; she accepts → Leadership group added to chart's share list.
6. Two weeks later, Priya tries to also drop the salary chart into "Org Overview" (shared with All Viewers). Embed warning fires: *"This chart isn't visible to All Viewers. Add All Viewers to this chart's share list?"* She picks Cancel. Salary chart stays restricted to Leadership group.
7. The eight Internal-floor charts: no warnings on embed because they're already visible to all internal staff (and the dashboards default to Internal too). If any of those dashboards is later shared with Viewers, the dashboard-broadening warning fires for all 8 charts as a bulk extension.

### 10.3 James (funder) logs in

1. James accepts his invite, lands in Dalgo
2. Sees a "Shared with you" view — three dashboards explicitly shared with him via the "Funders" group
3. Sidebar shows only Dashboards, Charts, Reports, Settings > About
4. No access to pipelines, transforms, data explorer, or any other dashboard in the org

### 10.4 Priya invites a new analyst

1. Priya goes to Settings > Users, clicks Invite
2. Enters email, picks Analyst role
3. Optionally selects initial groups or resources (defaults to module-level Analyst grants)
4. Sends. New analyst lands with full content access on accept.

---

## 11. UI Surface

### 11.1 Share modal
Combined paste + group + invite flow (see §9.1). One permission picker (View/Edit) for the resource grant, one role picker for new-user invites (gated by inviter's level, defaults to Viewer). Surfaces pending state for unmatched emails.

### 11.2 Resource list pages (Dashboards, Charts, Reports)
- "Shared with you" section for Viewers
- 👥 icon for resources shared by/with you
- 🔒 icon for Private-floor resources
- Visibility badge showing the floor (Private / Internal / All Viewers / Public)
- Direct-share count shown on hover (e.g., "Private · shared with 2 groups")

### 11.3 Resource editor view
- "You have view-only access" banner when applicable
- Visibility-floor selector in resource settings: Private / Internal / All Viewers / Public link
- Direct shares panel (manage groups/users with explicit View or Edit access)

### 11.3a Embed-time warning modal
When an editor adds a chart to a container whose audience the chart doesn't fully cover:

```
⚠ Extend chart access

This chart isn't currently visible to all viewers of
"Field Operations Dashboard".

Missing audience:
  • Field Staff group (15 people, Viewers)

Adding this chart will add Field Staff group to the chart's
share list. The chart's visibility floor (Private) is unchanged.

[ Cancel ]                            [ Yes, share with group ]
```

### 11.3b Dashboard-broadening warning modal
When an editor changes a dashboard's audience to include groups/users that some inner charts aren't shared with:

```
⚠ Extend chart access

Your new share for "Field Performance Dashboard" includes
Field Staff – Q3 group, who aren't shared on 8 of the
10 charts in this dashboard.

[ Cancel share ]                  [ Yes, extend all 8 charts ]
```

Bulk-or-cancel only. To keep a specific chart out of the new share, the editor removes that chart from the dashboard first and retries the dashboard share.

### 11.4 Settings > Users
- User list with role, last active, status (active / pending / deactivated)
- Invite button (role options gated by inviter's level)
- Role change action (AM only)
- Deactivate action (AM only)

### 11.5 Settings > Groups
- Group list with member count, resources shared with
- Create group, add/remove members, rename, delete

### 11.6 Settings > Organization
- Org-level default visibility threshold (AM only)
- Other governance settings

### 11.7 Sidebar & route gating
- Sidebar items hidden (not grayed) when user lacks permission
- Direct URL to unauthorized page → redirect to first accessible page or "No Access" page
- "No Access" page shows org admin contact info

---

## 12. Migration Story

| Today | After V1 |
|---|---|
| Guest role (broken) | Renamed to Viewer; gets working view permissions on dashboards/charts |
| Existing Guest users | Become Viewers. Empty resource list on day 1 until shares are created. AM should triage and apply org-wide shares where intended. |
| Existing Analysts have pipeline write | Pipeline write removed. **Requires communication to implementation partners.** Grace period recommended. |
| Dashboards have sharing | Existing shares migrate 1:1 to new ResourceShare model |
| Reports have dashboard-style sharing | Existing shares migrate 1:1 |
| Charts have NO sharing today | Migrate to visibility floor = **Internal**, empty direct share list. Today's "Analyst+ can see all charts" behavior is preserved. |
| Dashboards already shared with Viewers | One-time migration: for every existing dashboard share to a Viewer (user or group), auto-extend that share to every chart in the dashboard (added to each chart's direct share list). Preserves current effective access; charts don't appear as locked tiles post-migration. |
| Default visibility | All new content resources start with floor = Internal, empty direct share list. Old resources keep current visibility post-migration. |
| Sidebar | Filtered by role-derived permissions |

---

## 13. Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Viewer users per active org | ~0 (role broken) | 5+ within 3 months of GA |
| External partners onboarded (funders/field staff) per org | Near zero | At least 1 per active org |
| Support tickets about "can't see dashboard" | Unknown | ↓80% |
| % of active orgs using resource-level sharing | 0% | 50% within 3 months |
| % of active orgs using groups | 0% | 30% within 3 months |
| Analyst-caused pipeline/transform breakages | Possible | Zero (permission removed) |
| Time to share a dashboard with 30 people | Manual / per-user | <60 seconds |

---

## 14. Technical Implications

### 14.1 DDP_backend (Django + Django Ninja)

| Change | Impact |
|---|---|
| Role permission seed data | Migration: Guest → Viewer rename + permission rewrite; Analyst pipeline/transform write removed |
| New models | `UserGroup`, `UserGroupMember`, `ResourceShare`, `OrgAccessSettings` |
| Resource model updates | Add `visibility_floor` enum on Dashboard, Chart, Report. `ResourceShare` carries direct grants (group or user × resource × View/Edit). |
| Visibility floor enum values | `private`, `internal`, `all_viewers`, `public_link` (no `inherit`) |
| Permission resolver | Effective audience = visibility floor ∪ direct shares. Implements §5.5 across direct + group + module + org grants. |
| Embed-time guardrail service | At chart embed → compute container's audience minus chart's effective audience. If non-empty, return the gap to frontend as warning payload. On Yes, insert ResourceShare records granting the gap-audience View access to the chart. |
| Dashboard-broadening guardrail service | At dashboard share-change → for the newly-added audience, scan inner charts; surface the set of charts not currently shared with that audience. On Yes, bulk-insert ResourceShare records for every chart in the set. On Cancel, abort the dashboard share. No partial state. |
| Share API endpoints | Group CRUD, share CRUD, paste-to-share, pending invite acceptance, bulk-extend-to-children for dashboard-broadening |
| Invitation flow | Pending ResourceShare records activate on invite accept |
| Redis permission cache | Invalidates on grant change, role change, group change, visibility floor change |
| Schema access | `has_schema_access()` remains a documented TODO (V2 RLS + column masking feature) |
| Hooks for V2 | `User.signup_origin` field; `ResourceShare` supports email-based pending records; `dataset_access_rules` stub for V2 RLS/column-masking work to attach to |

### 14.2 webapp_v2 (Next.js 15 + React 19)

| Change | Impact |
|---|---|
| Sidebar (`main-layout.tsx`) | Filter nav items via `useUserPermissions()` |
| Route middleware | Permission-based route guards |
| Share modal | New combined flow (paste + group + bulk invite + pending state) |
| Resource list pages | Visibility badges, Private indicator (🔒), "Shared with you" section for Viewers |
| Resource editor | View-only banner, visibility-floor selector (Private / Internal / All Viewers / Public link), direct-shares panel for adding/removing groups & users |
| Embed-time warning modal | Triggers when a chart's effective audience doesn't cover the container's audience; Yes adds the missing audience to chart's share list, Cancel aborts embed |
| Dashboard-broadening warning modal | Triggers when broadening a dashboard's share to an audience not covered by all inner charts; Yes bulk-extends all gap-charts, Cancel aborts the dashboard share. Bulk-only, no per-chart picker. |
| Settings > Users | Invite flow with role picker gated by inviter level; role/deactivate actions (AM only) |
| Settings > Groups | New page — group CRUD + membership |
| Settings > Organization | New section — default visibility threshold (AM only) |
| `PermissionGate` component | Conditional UI rendering wrapper |
| No Access page | New component |

### 14.3 Performance considerations

- `ResourceShare` indexed on (resource_type, resource_id), (shared_with_user), (shared_with_group), (status)
- Permission cache keyed by user × resource with bounded TTL
- List queries use a single resolved-access subquery rather than per-resource checks

---

## 15. Scope: V1 vs V2

### 15.1 In V1

- Role rename Guest → Viewer; fix Viewer permissions
- Tighten Analyst (remove pipeline/transform write)
- WHO × WHAT × WHERE model with View/Edit at resource layer + Admin at org layer
- Roles as templates with default grants
- Compulsory visibility floor (Private / Internal / All Viewers / Public link) for dashboards, charts, reports; default Internal; org-level threshold setting
- Direct share list on every content resource (groups + users)
- Embed-time warning modal when chart's effective audience doesn't cover container audience (offers to extend chart's direct share list)
- Dashboard-broadening warning modal with bulk-extend-or-cancel behavior — no partial sharing, no locked tiles ever
- Resource-level sharing for dashboards, charts, reports
- Embedding control (Edit-on-chart required to embed) — primary structural defense against accidental oversharing
- User groups — org-wide, any Editor can create
- Paste-to-share with bulk invite + group assignment in one modal
- Pending invite state visible
- Invite-at-and-below-your-level
- Permission-gated sidebar + route guards + No Access page
- Migration: existing dashboards/reports preserve shares; charts get floor = Internal; existing Viewer-shared dashboards bulk-extend chart direct shares one time

### 15.2 Deferred to V2

- **Row-Level Security + column masking on datasets** — the right answer for "funders and field staff see the same chart, different data." Single dashboard with audience-aware data. Powers the original "beneficiary PII without splitting dashboards" use case that the V1 Private + embed warning model handles imperfectly via dashboard splitting. `has_schema_access()` stays a TODO; `dataset_access_rules` stub lands in V1 for V2 to build on.
- **Email-domain auto-signup** — needs domain verification infra + conflict resolution; partial coverage given personal-email reality in Indian NGOs; design hook left in V1 via `User.signup_origin`
- **Restricted Groups** (AM-only membership) — wait for customer demand
- **Org-level "AM-only invitations" toggle** — wait for customer demand
- **Audit log** — real need, separate feature
- **Time-bound / expiring access**
- **Resource-level sharing on Pipelines / Transforms / Orchestration** — infra stays role/module-gated
- **Individual sharing for KPIs / Metrics** — module-level only in V1; resource-level when the Metrics module ships
- **Custom roles** beyond the four standard ones
- **Cross-org sharing**
- **"Manage" permission level at resource layer** — confirmed View/Edit is sufficient

### 15.3 V1 Limitations (Honest Caveats)

V1 ships a clear safety story for the dominant threat surface but does not solve everything. Documented limitations:

1. **Editor-to-Editor data privacy is not enforced.** Marking a chart Private prevents other Editors from pulling it into their dashboards (chart picker hides it; Edit-on-chart required to embed). It does *not* prevent another Analyst from opening Data Explorer, querying the underlying dataset, and rebuilding the chart. Any Analyst-or-above can read every dataset the org owns. This is acceptable in the typical Dalgo NGO context (1–5 editors who already share organizational trust) but is a real gap for orgs with role separation (e.g., program Analyst and HR Analyst should not see each other's data). V2 dataset-level RLS + column masking closes it.

2. **Audience-aware data on a single dashboard requires splitting in V1.** "Funders see the chart with names masked; field staff see names" cannot be done on one chart in V1. Pattern is to split into two dashboards with different audiences. V2 RLS + column masking removes the need to split.

3. **No audit trail.** V1 does not log who viewed what, who shared what, who broadened access. V2 Audit log addresses this.

4. **No row-level filtering.** "James (funder) sees only the rows for his region" is not supported in V1. V2 RLS.

5. **Warehouse table access is uncontrolled.** `has_schema_access()` is a documented TODO. Any authenticated user with platform-level dataset access can query any table the platform connects to. Mitigated today by the fact that only Editors have dataset access at all; V2 RLS makes this proper.

**Positioning guidance:** When introducing V1 to customers, frame as "safe to invite external partners and funders + accidental-oversharing prevention," not as "complete data privacy." The Editor-to-Editor case must be communicated honestly — particularly to orgs handling salary/HR data.

---

## 16. Open Implementation Questions

1. **Analyst permission tightening communication.** How and when do we notify existing Analyst users (especially implementation partners) that they're losing pipeline/transform write? Grace period? In-app banner + email?
2. **Existing Guest → Viewer transition.** Auto-share all currently-visible dashboards with affected users on day 1, or let the AM triage? Recommended: a 1-time bulk migration tool for the AM.
3. **Share notifications.** Email + in-app notification when a user is added to a share? Recommended V1.
4. **Pending invite expiry.** Default 30 days, configurable per org? Recommended.
5. **Performance at scale.** 50+ dashboards × 100+ users — confirm the resolved-access query holds up. Load test plan?
6. **Reports current sharing.** Confirm exact current behavior to map cleanly into the new ResourceShare model.
7. **Group ownership ambiguity.** Anyone with Edit can add members; only creator + AM can delete the group. Confirm this is the right line.
8. **Visibility floor on Reports.** Same model as dashboards (Private / Internal / All Viewers / Public link)? Yes — confirm.
9. **Private-chart adoption metric.** To know if "Internal-by-default" is the right call, track: (a) % of charts created with Private floor, (b) % of resources moved from Internal → Private within 7 days, (c) frequency of bulk-extend acceptances vs cancels on dashboard-broadening warnings. The last is the clearest signal of whether the default floor is right.
10. **RLS + column masking timeline.** V1 ships dashboard-splitting as the recommended pattern for "audience-aware data." If RLS slips far past V2, editors maintain duplicate dashboards indefinitely. Commit to a rough RLS sequencing target so this doesn't become permanent.
11. **Chart-share-list sprawl.** Charts can accumulate direct shares over time as dashboards get shared with new groups. Need a "Manage shares" UI on each chart that shows the full list cleanly, plus an org-level audit ("which groups can see this chart and via what path?"). Acceptable scope for V1?
12. **Bulk-broaden default.** When the dashboard-broadening warning fires for 8 charts, the default action button is "Yes, extend all 8 charts." Confirm this is the right default vs. defaulting to Cancel.

---

## 17. Appendix: Dalgo vs Other Platforms

| Capability | Dalgo V1 (this spec) | Google Docs / Notion | Looker / Tableau Cloud | Power BI |
|---|---|---|---|---|
| Granular resource sharing | ✅ Charts, Dashboards, Reports | ✅ Docs, Pages | ✅ Reports, Dashboards, Explores | ✅ Reports, Dashboards |
| Public link sharing (view-only) | ✅ | ✅ | ✅ | ✅ |
| Role-based platform access | ✅ AM, PM, Analyst, Viewer | ✅ Owner, Editor, Viewer | ✅ Admin, Developer, Viewer, Explorer | ✅ Workspace Admin, Member |
| View/Edit on resources | ✅ Per-resource | ✅ | ✅ | ✅ |
| Permission model | ✅ Visibility floor + direct share list + embed/share guardrails (no locked tiles) | ✅ Same shape | ✅ Same shape | ✅ Same shape |
| User invitation via email | ✅ Up to inviter's level | ✅ | ✅ Admins only | ✅ |
| Groups for sharing | ✅ V1 (org-wide, any Editor) | ✅ | ✅ | ✅ |
| Row-level access | ❌ V2 (RLS) | ❌ | ✅ | ✅ |
| Per-resource private + embed-time guardrail | ✅ V1 (Dalgo-specific affordance) | Partial | Partial | Partial |
| Row-level security / column masking | ❌ V2 | ❌ | ✅ | ✅ |
| Time-bound access | ❌ V2 | ✅ Optional | ✅ | ✅ |
| Audit logging | ❌ V2 | ✅ Enterprise | ✅ | ✅ Premium |
| Email-domain auto-signup | ❌ V2 | ✅ | Varies | ✅ |
| Onboarding flow for new users | ✅ Invite → Viewer default | ✅ Seamless | ✅ Admin-controlled | ✅ Microsoft account |

---

## 18. Implementation Order (Recommended)

```
Layer 1 — Roles & Permissions         → Ships first. Independent. Low risk.
Layer 2 — Navigation & Route Gating   → Frontend only. Parallels with Layer 3 backend.
Layer 3 — Groups, Direct Sharing, Visibility Floor + Warnings → Critical for Viewer flow to work as designed.
Layer 4 — RLS on Datasets             → Future. Separate spec.
```

Key dependency: Viewer role works as intended only after Layer 3 ships. Layer 1 alone leaves Viewers seeing all org dashboards — acceptable transitional state (Layer 1 fixes the broken permissions; Layer 3 adds the targeted-sharing surface that makes the role useful).

---

## 19. Engineering Notes

- Pradeep / Siddhanth: model in §5 maps directly onto the structure Siddhanth already drafted (`Experiments/dalgo-core/workdocs/access_control/spec.md`). Main changes from Siddhanth's draft:
  - Resource-level "Admin" tier removed (View/Edit only at resource layer)
  - Compulsory visibility floor on every content resource (Private / Internal / All Viewers / Public link) + additive direct share list. No "Inherit" concept. No "Sensitive" flag.
  - Effective audience = floor ∪ direct shares (audit-friendly: every grant is explicit)
  - Embed-time warning offers to extend the chart's direct share list when an embed would create a locked-tile situation
  - Dashboard-broadening warning is bulk-extend-or-cancel only — no partial sharing, no locked tiles ever
  - Combined share + group + invite modal called out as the dominant flow
  - Invitation rules clarified (invite at-and-below-your-level)
  - Org-level default visibility threshold added as a single setting
  - V2 RLS + column masking explicitly framed as the answer to "audience-aware data on a single dashboard"
