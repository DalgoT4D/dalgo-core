# Dalgo Access Control — Spec B: Resource Sharing

**Status:** Draft for review (Design feedback pending before circulation)
**Owner:** Product
**Engineering:** Engineering (model + delivery)
**Design:** Design (share modal + resource-page UI — primary input gate for this spec)
**Reviewers:** Engineering, Leadership
**Date:** 2026-06-02
**Depends on:** Spec A — Role System. Spec A ships first; Spec B builds on its role tiers, ownership primitive, and Settings IA.
**Replaces:** The sharing / visibility / inheritance portions of the superseded rebuilt spec (`workdocs/access_control/access-control-v2-spec-rebuilt copy.md`). Do not build to that spec.

---

## 1. Overview

Spec A fixed the foundation — three roles, sidebar gating, ownership, and the principle that role does not cap function on content. Spec B builds the layer that makes that principle real: **how View and Edit access to content resources is granted, inherited, and shared.**

The model has three parts that stack:

1. A **two-axis floor** on every content resource — a baseline *audience* (minimum role) and *permission* (View or Edit) — set by an org-wide default and overridable per resource by the owner.
2. **Direct shares** — additive grants to specific users or groups at View or Edit, on top of the floor.
3. A **hybrid inheritance model** — viewing a container renders its contents inline, but never grants standalone or edit access to those contents; embed-time and dashboard-broadening guardrails keep a container's audience and its contents' audiences aligned so a viewer never hits a locked tile.

Public-link sharing is a separate per-resource toggle, gated by an Admin global. Groups, the share modal, alerts, and comments-on-Reports round out the surface.

This spec is longer and has more design surface than Spec A. It should go to Design for review before circulating to Engineering and Leadership.

---

## 2. Goals & Non-goals

### 2.1 Goals

1. Make it safe to share a single dashboard with an external funder or field team without exposing the rest of the org's data.
2. Give every content resource a clear, auditable effective audience: floor ∪ direct shares.
3. Keep the dominant flow — one editor shares one dashboard with a group of 30 — under a minute.
4. Guarantee **no locked tiles, ever**: a viewer of a dashboard can see every chart in it, or the broadening action fails.
5. Scale cleanly to alerts, KPIs, and metrics without re-architecting.
6. Provide groups so sharing with 30+ consumers doesn't require per-person operations.

### 2.2 Non-goals (deferred beyond V1)

Row-level security and column masking on datasets (the proper answer to "same dashboard, audience-aware data" — explicitly deferred; see §17), audit log, time-bound/expiring access, resource-level sharing on Data infrastructure (Ingest/Transform/Warehouse/Pipelines/Orchestration stay role-gated per Spec A), individual sharing for KPIs/Metrics beyond what's defined here, custom roles, cross-org sharing, comments on anything other than Reports.

---

## 3. Problem Statement

With Spec A shipped, content function is grant-driven — but no grant model exists yet. The gaps Spec B closes:

1. **No per-resource sharing.** A user either sees content (interim View-all from Spec A) or, once this ships, nothing targeted. There's no way to share one dashboard with one funder.
2. **No baseline visibility control.** No notion of "this resource is visible to all internal staff" vs. "owner only."
3. **No groups.** Sharing with 30 people is 30 actions.
4. **No protection against accidental oversharing.** An editor can drop a PII chart onto an all-staff dashboard with nothing stopping the leak.
5. **No public-link control.** No safe, governed way to expose a view-only dashboard outside the org.
6. **Alerts, comments unscoped.** No model for who configures an alert, who receives it, or who can comment.
7. **No way to request access.** A user handed a resource link but lacking access hits a dead end instead of asking the owner for it.
8. **No bulk operations.** Sharing or adjusting many resources means repeating the same action one resource at a time.

---

## 4. Dependency on Spec A

Spec B assumes the following from Spec A and does not redefine them:

| From Spec A | How Spec B uses it |
|---|---|
| Three roles (Admin / Analyst / Member) | Floor audience tiers are expressed as minimum roles; invite tiers gated per Spec A §9. |
| Role decoupled from function | View/Edit grants in this spec work identically for any role. A Member with Edit can edit and re-share. |
| Ownership (`owner` column, owner-only delete, Admin = effective owner, transfer) | Owner sets the floor and manages shares; Admin overrides everywhere; only owner/Admin deletes. |
| Settings > Org defaults (controls rendered, inert in Spec A) | Spec B consumes `default_visibility_floor` and `allow_public_sharing`. |
| Invitation role-tier rules (anyone invites as Member; only Admin elevates) | The share modal's invite path enforces these. |
| Sharing capability = Edit on resource | Re-sharing in the share modal requires an Edit grant. |

---

## 5. The Sharing Model

### 5.1 Two-axis floor

Every content resource (Report, Dashboard, Chart, KPI, Alert) carries a compulsory **floor** with two independent axes:

```
Floor audience:    [ Private  /  Admins only  /  Analysts+  /  All users ]   (minimum role)
Floor permission:  [ View  /  Edit ]
```

- **Audience** sets the minimum role that gets the floor grant:
  - **Private** — owner only (plus Admin via governance override).
  - **Admins only** — all Admins.
  - **Analysts+** — all Analysts and Admins.
  - **All users** — every authenticated user in the org, including Members.
- **Permission** sets what that audience can do at the floor level: **View** or **Edit**.

Strictness ordering of the audience axis (most → least restrictive): `Private < Admins only < Analysts+ < All users`. This ordering powers the guardrails in §8.

**Admin is always implicit in any floor.** Even at floor = Private, Admins retain governance access (§4, Spec A ownership). The override is governance, not silent broadening — guardrails still fire for Admins.

### 5.2 Org-default floor

The Admin sets the org-wide default that new resources inherit at creation (Settings > Org defaults, rendered in Spec A, consumed here). **The org-default uses the same two-axis picker as the per-resource floor** — the Admin chooses any audience tier × permission, not a fixed list of presets. This keeps the default consistent with the per-resource control and lets a stricter org default to, say, "Analysts+ / View" rather than being forced to start fully open.

| Axis | Options | Factory default |
|---|---|---|
| Audience | Private / Admins only / Analysts+ / All users | **All users** |
| Permission | View / Edit (N/A when audience = Private) | **Edit** |

The UI can surface common combinations as one-click shortcuts: "Everything private" (Private), "Viewable to all" (All users / View), "Editable to all" (All users / Edit — factory default), "Internal only" (Analysts+ / View).

The default only sets the *starting* floor for new resources. Owners override per resource via the same two dropdowns at any time. Changing the org-default does not retroactively change existing resources.

> **Design/Leadership note:** the factory default ("All users, Edit") is maximally open — any user, including a Member, can edit any new resource until an owner narrows it. Because the default is now a full picker, an org wanting a safer posture can ship-configure it to "Analysts+ / View" in a single setting. The factory value still follows the "start open, let orgs lock down" philosophy; §19 shows where owners must narrow it (PII, salary).

### 5.3 Direct shares (additive)

On top of the floor, the owner — or anyone with an Edit grant — can add specific **users or groups** at **View** or **Edit**.

- Direct shares **stack additively**. Effective access = floor ∪ all direct grants, at the most permissive level any path confers.
- Removing a direct share subtracts **only that grant**. The floor and all other direct grants remain. (E.g., removing the Funders group from a chart doesn't affect the Field Staff group's grant or the floor.)
- A direct share can only raise access, never lower it below the floor. To restrict below the floor, the owner lowers the floor audience.

### 5.4 Effective access resolution

```
EffectiveAccess(user, resource) =
    max permission across:
      - Floor, if user's role ≥ floor audience minimum
      - Direct grants to the user on this resource
      - Direct grants to any group the user belongs to on this resource
      - Admin effective-owner override (always Edit + delete)
If none match → no access.
```

Permission is the **max** across all matching paths (View < Edit). Audience (who can see at all) is the **union** of all paths.

### 5.5 Public-link sharing

A separate per-resource toggle, distinct from the floor:

- Visible on a resource only if the Admin global **"allow public sharing"** is on (defaulted on, set in Settings > Org defaults).
- Public links are **view-only, anonymous, no comments.** No authentication required.
- Toggling a public link on/off is available to the owner or anyone with Edit.
- Public-link access is independent of the floor and direct shares — it's an additional, anonymous view path, not an audience tier.

---

## 6. Resource Taxonomy

| Resource | Role in model | Contains | Used by / embedded in | Individually shareable? |
|---|---|---|---|---|
| **Report** | Snapshot container | One Dashboard (point-in-time snapshot) | — | Yes |
| **Dashboard** | Container | Charts, KPIs | Reports | Yes |
| **Chart** | Leaf content | References a Metric + Dataset | Dashboards | Yes |
| **KPI** | Leaf content (chart using a metric) | References a Metric + Dataset | Dashboards | Yes |
| **Metric** | Computation / definition | References a Dataset | Charts, KPIs | Yes (forward-looking) |
| **Alert** | Standalone | References a KPI or Metric as trigger source | — | Yes (own audience) |
| **Dataset** | Data | — | Referenced by Metrics/Charts/KPIs | No — governed by role (Spec A) today; RLS in future |

- **Report = a snapshot of exactly one Dashboard** at a point in time. This is now explicit (was implicit before). Edit on a Report means: regenerate the snapshot, edit the executive summary, and moderate comments — *not* edit the underlying dashboard or its charts.
- KPIs and Metrics are forward-looking — the features are in development, so defining their sharing now avoids a rewrite later.
- Datasets are not individually shareable in V1; any-Analyst-and-above has read access to warehouse tables (Spec A). The Editor-to-Editor data-rebuild gap this leaves open is documented as a V1 limitation (§17).

---

## 7. Hybrid Inheritance Model

### 7.1 Three access rules (apply to all content resources)

1. **Every resource has its own audience.** A chart's effective audience = its floor ∪ its direct shares, regardless of which dashboards embed it. Containers do not implicitly cascade access.
2. **View on a container = inline render of contained resources only.** No standalone module access. A user with View on a Dashboard sees the charts render inside it, but those charts do **not** appear in that user's `/charts` list and can't be opened standalone.
3. **Edit on a container = edit container structure only.** Editing a *contained* resource still requires an explicit Edit grant on that resource. Edit on a Dashboard lets you add/remove embeds and change layout; it does not let you edit the charts inside.

### 7.2 Inheritance table

| Granted | Inline render | Standalone module entry (`/charts`, `/kpis`, `/metrics`) | Edit container structure | Edit contained resource |
|---|---|---|---|---|
| **View on Report** (snapshot of one Dashboard) | Yes | No | — | — |
| **Edit on Report** | Yes | No | Yes — regenerate snapshot, edit executive summary, moderate comments | No |
| **View on Dashboard** | Charts + KPIs render | No | — | — |
| **Edit on Dashboard** | Yes | No | Yes — add/remove embeds, layout | No |
| **Direct View on Chart** | Yes | Yes — appears in `/charts` for that user | — | — |
| **Direct Edit on Chart** | Yes | Yes | — | Yes |

The distinction: access via a **container** is inline-only; access via a **direct grant on the leaf** unlocks standalone use and (at Edit) editing.

### 7.3 References ≠ shares

A reference from one resource to another never grants access to the referenced resource:

- Alert → KPI / Metric (trigger source — alerts fire on a KPI or a metric, not a chart directly)
- Chart → Metric (a metric is a computation used in the chart)
- KPI → Metric
- Metric → Dataset

Each resource is independently access-controlled. Receiving an alert does not grant access to the KPI or metric it watches; using a metric in a chart does not grant the chart's viewers access to that metric as a standalone resource.

---

## 8. Embed-time & Dashboard-broadening Guardrails

Two warnings keep container audiences and contained-resource audiences aligned, so **no viewer ever sees a dashboard with charts they can't access (no locked tiles, ever).**

### 8.1 Embed-time warning (per chart)

Fires when an editor adds a chart to a container whose effective audience is **broader** than the chart's effective audience.

> *"This chart isn't visible to some viewers of 'Field Operations Dashboard' (Field Staff group, 15 people). Add Field Staff group to this chart's share list?"*

- **Yes** → the missing audience is added to the **chart's direct share list** (View). The chart's floor is unchanged. Effective audience now covers the container. *(Available only to an editor with Edit on the chart — extending a chart's audience is a re-share; see §8.3.)*
- **Cancel** → the embed is aborted; the chart's floor and shares stay as they were.

The chart's floor audience is never bumped by this flow — only its direct share list extends.

### 8.2 Dashboard-broadening warning (bulk)

Fires when an editor broadens a dashboard's audience (floor or direct share) to include principals that some inner charts aren't shared with.

> *"7 of the 10 charts in this dashboard aren't shared with Funders group. Extend all 7?"*

- **Yes** → the new audience is bulk-added to every gap-chart's direct share list. The dashboard share proceeds.
- **Cancel** → the dashboard share is aborted.

**Bulk-or-cancel only. No per-chart picker.** To exclude a specific chart, the editor removes it from the dashboard first, then re-shares.

### 8.3 No locked tiles; what it takes to embed

- **No locked tiles, ever.** Either every dashboard viewer can see every chart in it, or the broadening action doesn't go through.
- **Embedding a chart requires View on the chart + Edit on the dashboard.** Adding an embed is a container-structure edit, so you need Edit on the dashboard; you need at least View on the chart to see and select it. You do **not** need Edit on the chart to embed it.
- **Closing an audience gap requires Edit on the chart.** If the chart's effective audience already covers the dashboard's, the embed is harmless and proceeds with no prompt. If there's a gap, the embed-time warning (§8.1) offers to extend the chart's share list — but extending a chart's audience is a re-share, which requires **Edit on the chart**. An embedder with only View on the chart cannot close the gap: the embed is blocked with a prompt to request Edit (§10.5) or ask the owner.
- **The oversharing defense is preserved where it matters.** A Private chart with no shares isn't visible to other editors at all, so they can't select it to embed. A broadly-visible chart can be embedded freely by anyone who can see it — but only into audiences it already covers, unless they hold Edit to widen it.
- Admins trigger the same warnings — the override is governance access, not silent broadening.

---

## 9. Groups

- **Org-wide and reusable** across resources.
- **Any Analyst+ can create a group.** (Members cannot create groups.)
- **Creator can rename, delete, and manage membership.** Admin overrides on all groups.
- **Group-list visibility is scoped by role** (per Spec A Settings IA): an **Admin** sees all org groups; an **Analyst** sees groups they created or belong to; a **Member** sees only groups they belong to. A group's member roster is visible to anyone who can see the group.
- **Name-collision warning on create** — prevents three different "Field Staff" groups.
- Sharing a resource with a group grants every current member the resource's shared permission; adding a member later grants access to everything the group is shared on; removing a member revokes access gained via the group (unless they hold a direct grant); deleting a group revokes all access it conferred.

---

## 10. Share Modal & Invite Flow

### 10.1 The unified modal

The dominant flow — share one resource with people and/or a group, inviting non-users as needed — collapses into one modal, used identically wherever sharing starts (resource page, list view).

```
Share "Field Performance Dashboard"

┌─────────────────────────────────────────────────────────┐
│ Add people, groups, or paste emails                       │
│ [field-staff@ngo.org, anjali@ngo.org, ...]                │
├─────────────────────────────────────────────────────────┤
│ Permission on this resource:   [ View ▼ ]                 │
│ Assign to group:               [ Field Staff ▼ ] [+ New]  │
│ Invite new users as:           [ Member ▼ ]               │
│   (Only Admins can pick Analyst / Admin)                  │
├─────────────────────────────────────────────────────────┤
│ Floor:  Audience [ Analysts+ ▼ ]   Permission [ View ▼ ]  │
│ 🔗 Public link:  [ Off ]   (hidden if org disallows)      │
└─────────────────────────────────────────────────────────┘

✔ anjali@ngo.org — existing user, will be granted View
⚠ xyz@new-partner.org — not on Dalgo → invited as Member, added to Field Staff
                                       [Remove]

[ Cancel ]                                          [ Share ]
```

### 10.2 Behaviors

- **Matched emails** → existing users get the chosen permission immediately.
- **Unmatched emails** → flagged; default to "invite at the modal's invite-role + add to the selected group + apply the share on accept." Appear as **pending** in the share list until accepted.
- **Bulk paste** → comma- or newline-separated emails in one paste.
- **Group assignment in-modal** → assign to an existing group or create one without leaving the modal.
- **Default resource permission** = View; switchable to Edit by anyone with Edit.
- **Default invite role** = Member. Only Admins can switch the invite-role picker to Analyst/Admin (Spec A §9).
- **Re-sharing requires Edit** on the resource; a re-sharer can grant up to their own permission level (View grant-holders can't share).

### 10.3 Invitation rules & re-sharing (per Spec A §9)

- **Anyone can invite as Member** via the share modal — this is the path Analysts use to bring in consumers (their Settings > Users page is hidden).
- **Only Admins can invite as Analyst/Admin**, in the share modal or Settings > Users.
- **Re-sharing** is gated by an Edit grant on the resource, not by role. A Member with Edit can re-share up to Edit; a View-only holder cannot share.

### 10.4 Pending invites & expiry

- Pending invitees appear in the share list and group lists with a **pending** tag until they accept.
- On acceptance, all pending grants (resource shares + group membership) activate.
- **Pending invites expire after 30 days** — a **Dalgo platform-wide constant**, not configurable per org. Expired invites drop from share/group lists and must be re-sent.

### 10.5 Request access

Resource links get shared informally — pasted into chat, email, a deck. When an **authenticated** user opens a resource link they don't have access to, instead of a dead end they see a **request-access** screen:

- They can **request View or Edit**, with an optional note.
- The request routes to the resource **owner and anyone with Edit on it** (all of whom can already share) plus **Admins** — as a notification and an entry in a **Requests** area of the share modal / Manage shares view.
- An approver picks the level to grant (can downgrade an Edit request to View) → a **direct share** is created and the requester notified. Decline notifies the requester.
- Granting resource access **never changes the requester's platform role** — it only adds a resource grant (role changes remain Admin-only, Spec A §9).
- **Public-link viewers are out of scope** (anonymous). If public sharing is off and a non-user opens a link, they're prompted to sign in or be invited.
- Pending access requests expire on the same **30-day** platform constant (§10.4).

### 10.6 Bulk sharing from resource lists

**Every resource list across the platform** (Dashboards, Charts, Reports, Alerts) supports **multi-select**: tick N resources, hit **Share**, and the same modal applies the chosen grants / floor / public-link toggle to all selected resources at once.

- **Same guardrails per resource** — bulk-sharing dashboards that contain gap-charts surfaces the broadening warning (aggregated across the selection where possible), bulk-or-cancel.
- **Re-share gating still holds per resource** — a bulk action applies only to resources the actor has Edit on; the rest are skipped with a clear count (*"Shared 8 of 10 — 2 skipped: you don't have Edit on those"*).
- Multi-select also supports **bulk floor change** and **bulk public-link toggle**, under the same Edit gating.

---

## 11. Alerts (V1 governance)

- **An alert's trigger source is a KPI or a Metric** (a metric is a computation used in charts) — not a chart directly.
- **Created by Analyst+** — Admins anywhere; Analysts on resources they have access to. Members do not create alerts.
- **The Alert resource has its own floor + direct shares** (same two-axis model) governing who can view/edit the alert *configuration*.
- **Recipient list** uses the same direct-share primitive (users + groups). Recipients get notifications with trigger context.
- **Recipient status grants no resource access.** Receiving an alert does not grant access to the KPI or metric it watches (references ≠ shares, §7.3).

---

## 12. Comments (V1 — Reports only)

- **Reports only.** Dashboards, Charts, KPIs, Metrics, and Alerts have no comments in V1.
- Anyone with **View on a Report** can read and add comments.
- **Edit on a Report** includes comment moderation (delete/hide).
- Public-link viewers cannot comment (anonymous, view-only).

---

## 13. UI Surface

- **Share modal** (§10.1) — paste + group + invite + per-resource permission + floor controls + public-link toggle; pending state; invite-role picker gated per Spec A.
- **Resource list pages** (Dashboards, Charts, Reports, Alerts) — floor/audience badge; 🔒 for Private-floor; direct-share count on hover; "Shared with you" section for Members; resource-level **filter on the chart list** to manage share sprawl (per feedback log); **multi-select checkboxes + bulk Share / floor / public-link actions** with a per-resource Edit-gated skipped-count summary (§10.6).
- **Request-access screen** — shown when an authenticated user opens a resource they lack access to; request View/Edit with a note; routes to owner / Edit-holders / Admin (§10.5).
- **Requests area** (in Manage shares / share modal) — pending access requests with approve (pick the level) / decline.
- **Resource editor / settings** — two-axis floor selector (audience + permission); direct-shares panel (add/remove users & groups at View/Edit); public-link toggle; "Manage shares" view showing the full grant list and the path each principal has access by.
- **Embed-time warning modal** (§8.1) — fires on embed; Yes extends chart's share list, Cancel aborts.
- **Dashboard-broadening warning modal** (§8.2) — bulk-extend-or-cancel only.
- **Groups** (Settings) — list with member count + resources shared with; create/rename/delete/membership; name-collision warning. Scoped per role (Spec A).
- **Alerts** — config page with floor + recipient list.
- **Reports** — comments panel for View+; moderation for Edit.

---

## 14. Migration

| Today | After Spec B |
|---|---|
| Dashboards/Reports have current sharing | Existing shares migrate 1:1 into the new floor + direct-share model. |
| Charts have no sharing | Charts get floor = the org-default (factory: All users / Edit, unless Admin changed it pre-migration); empty direct-share list. Preserves today's "everyone can see charts" behavior. |
| Interim Member "sees all content" (Spec A window) | **Narrows** to floor ∪ direct grants. Members now see only what the floor admits + what's shared with them. This narrowing is expected; communicate before launch (Spec A §12). |
| Dashboards already shared with Members (consumers) | **One-time auto-extend:** for every existing dashboard share to a consumer, auto-add that consumer to each inner chart's direct share list, so no chart appears as a locked tile post-launch. |
| Public links | Existing public links preserved; gated going forward by the org "allow public sharing" toggle (default on). |
| Org default floor | Set to factory default ("All users, Edit") unless the Admin chose otherwise; existing resources keep their migrated floors. |

The one-time auto-extend is the migration's critical step — without it, Members who could previously see a dashboard would hit locked tiles when chart-level audiences come into force.

---

## 15. Technical Implications

### 15.1 DDP_backend (Django + Django Ninja)

| Change | Impact |
|---|---|
| Floor model | Add `floor_audience` enum (`private`/`admins`/`analysts_plus`/`all_users`) + `floor_permission` enum (`view`/`edit`) on every content resource. No legacy single-tier `visibility_floor` enum (drop the Iter-3 enum). |
| Direct shares | `ResourceShare` (resource_type, resource_id, principal_type user|group, principal_id, permission view|edit, status active|pending, created_by, created_at). |
| Org defaults | Read `default_visibility_floor` + `allow_public_sharing` (stored in Spec A). |
| Public link | Per-resource `public_link_enabled` + token; gated by org toggle. |
| Permission resolver | Implements §5.4 — max permission across floor + user + group + Admin override. Audience = union. |
| Embed-time guardrail service | On embed, compute container audience minus chart effective audience; return gap to frontend; on Yes, insert View `ResourceShare` for the gap principals on the chart. |
| Dashboard-broadening guardrail service | On dashboard share-change, scan inner charts for gap; return set; on Yes, bulk-insert shares; on Cancel, abort. No partial state. |
| Groups | `UserGroup`, `UserGroupMember`; CRUD scoped per Spec A roles; name-collision check. |
| Alerts | Alert carries floor + direct shares + recipient list (reuse `ResourceShare` with a recipient flag). |
| Comments | `ReportComment` (report_id, author, body, created_at); read/add for View+, moderate for Edit. |
| Pending invites | `ResourceShare`/group rows with `status=pending` + email; activate on accept; **30-day expiry job** (platform constant). |
| Access requests | `AccessRequest` (resource, requester, requested_permission, note, status, decided_by, decided_at); notify owner + Edit-holders + Admins; on approve insert a `ResourceShare`; 30-day expiry. |
| Bulk share | Batch endpoint applying shares / floor / public-link to a set of resource IDs; per-resource Edit check; returns applied/skipped counts; reuses the guardrail services per resource. |
| Migration | 1:1 share migration; chart floor backfill to org-default; one-time auto-extend for existing consumer-shared dashboards. |
| Redis cache | Invalidate on grant/floor/group/public-link change. |
| V-next hooks | `dataset_access_rules` stub for future RLS/column-masking; KPI/Metric share rows ready when modules ship. |

### 15.2 webapp_v2 (Next.js 15 + React 19)

| Change | Impact |
|---|---|
| Share modal | Combined paste + group + invite + floor + public-link; pending state; invite-role gated per Spec A. |
| Resource list pages | Floor/audience badge, 🔒 indicator, "Shared with you" for Members, chart-list share filter, **multi-select + bulk Share/floor/public-link** with skipped-count summary. |
| Request access | Access-denied → request screen (request View/Edit + note); **Requests** area in Manage shares (approve with level / decline). |
| Resource editor | Two-axis floor selector, direct-shares panel, public-link toggle, "Manage shares" path view. |
| Embed-time warning modal | Gap detection on embed; extend-or-cancel. |
| Dashboard-broadening warning modal | Bulk-extend-or-cancel only. |
| Groups (Settings) | CRUD + membership + name-collision; role-scoped. |
| Alerts | Floor + recipient list UI. |
| Reports | Comments panel + moderation. |

### 15.3 Performance

- `ResourceShare` indexed on (resource_type, resource_id), (principal), (status).
- Permission cache keyed user × resource, bounded TTL.
- List queries use one resolved-access subquery, not per-resource checks.

---

## 16. Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Members (consumers) per active org | ~0 (role broken pre-V1) | 5+ within 3 months of GA |
| External partners (funders/field staff) onboarded per org | ~0 | ≥1 per active org |
| "Can't see dashboard" support tickets | Unknown | ↓80% |
| Active orgs using resource-level sharing | 0% | 50% within 3 months |
| Active orgs using groups | 0% | 30% within 3 months |
| Time to share a dashboard with 30 people | Manual / per-user | <60 seconds |
| Bulk-extend acceptances vs. cancels on broadening warning | n/a | Track — the clearest signal of whether the factory-open default floor is right |

---

## 17. Open Questions & V1 Limitations

### 17.1 Open questions

1. **Factory-open floor ("All users, Edit").** Confirm with Leadership this is the right default given it lets any Member edit new resources until narrowed. Worked examples (§19) argue it's safe for the trusted-editor reality but needs owner discipline on sensitive resources.
2. **Chart-share-list sprawl.** Charts accumulate direct shares as dashboards are shared with new groups. The plan: a "Manage shares" tab per chart + an org-level audit view ("who can see this chart, via what path"). Confirm scope for V1.
3. **Bulk-broaden default button.** When the warning fires for N charts, is the default action "Extend all N" or "Cancel"? Recommend Cancel-as-default to make broadening deliberate.
4. **Floor permission = Edit interaction with re-sharing.** If floor permission is Edit and audience is All users, every user can re-share. Confirm this is intended at the open default, or cap re-sharing to Analyst+ even when floor grants Edit.
5. **Design review** on the share modal and resource-page UI is the gating dependency before circulation.
6. **Access-request approvers** — spec'd as owner + any Edit-holder + Admin (Edit already implies the ability to share). Confirm, or restrict approval to owner + Admin only.
7. **Bulk-broadening UX** — when a multi-select bulk share spans many dashboards with gap-charts, confirm whether warnings aggregate into one prompt or step per resource.

### 17.2 V1 limitations (honest caveats)

1. **Editor-to-Editor data privacy is not enforced.** A Private chart is hidden from other editors' pickers, but any Analyst+ can rebuild it from the underlying dataset (full warehouse read). Acceptable for the typical 1–5 trusted-editor org; a real gap for orgs with internal role separation (program vs. HR). Closed by future dataset RLS + column masking.
2. **Audience-aware data on one dashboard requires splitting in V1.** "Funders see masked names; field staff see names" can't be done on one chart — split into two dashboards. RLS removes this need later.
3. **No audit trail** of who viewed/shared/broadened. Separate future feature.
4. **No row-level filtering** ("this funder sees only their region's rows"). Future RLS.

**Positioning:** introduce V1 as *"safe to invite external partners + accidental-oversharing prevention,"* not *"complete data privacy."* The Editor-to-Editor case must be communicated honestly to orgs handling salary/HR data.

---

## 18. Implementation Order

```
1. Floor model + permission resolver (two-axis) + org-default consumption   → backend
2. Direct shares + ResourceShare + Manage-shares UI                         → backend + frontend
3. Groups CRUD + membership + name-collision                                → backend + frontend
4. Share modal (paste + group + invite + pending + 30-day expiry)           → frontend + backend
5. Embed-time + dashboard-broadening guardrails (+ no-locked-tiles)         → backend + frontend
6. Public-link toggle (gated by org global)                                 → backend + frontend
7. Alerts (floor + recipient list)                                          → backend + frontend
8. Comments on Reports                                                      → backend + frontend
9. Request-access flow + Requests area                                      → backend + frontend
10. Multi-select bulk sharing across resource lists                          → frontend + backend
11. Migration (1:1 shares + chart floor backfill + one-time auto-extend)     → backend
```

Steps 1–5 are the core viewer flow and must land together for the Member experience to work. Public links, alerts, and comments can follow within the same release.

---

## 19. Worked Examples (NGO scenarios)

These double as the concrete scenarios to walk leadership/architecture through when defending the floor + guardrails model.

**A. Beneficiary PII chart for field staff (default-open is *not* enough — owner must narrow).**
An M&E Officer creates a beneficiary-detail chart. Under the factory default it starts at "All users, Edit" — wrong for PII. She sets its **floor to Private**. It disappears from every other editor's picker. She creates a "Field Operations" dashboard shared with the Field Staff group and drags the chart in. Embed-time warning fires: *"This chart isn't visible to Field Staff (15 people). Add them to the chart's share list?"* → Yes. Chart floor stays Private; Field Staff added as a direct View share. Field staff see it inside the dashboard; funders, who aren't on that dashboard or the chart's share list, have no path. **This is the canonical case for the embed warning preventing accidental leakage.**

**B. Salary chart for leadership only (broadening warning blocks the leak).**
The officer marks a salary-by-role chart's **floor Private**, adds it to "Leadership Overview" (Leadership group) — embed warning, accept → Leadership added. Weeks later she tries to drop the same chart onto "Org Overview" (audience: All users). Embed warning fires: *"This chart isn't visible to All users. Add All users to the chart's share list?"* → **Cancel.** The salary chart stays restricted to Leadership. **This is the case to show when leadership questions whether default-open is dangerous — the guardrail is the safety net.**

**C. Sharing a clean operational dashboard with 30 funders (the happy path, <60s).**
An operational dashboard with no sensitive charts (all at the open floor) is shared with a new "Funders" group of 30 pasted emails. Non-users are invited as Members, added to the group, share applied on accept. Broadening warning fires only if any inner chart is narrower than All users — here none are, so it sails through. ~45 seconds.

**D. Chart in two dashboards (additive shares, explicit and auditable).**
A chart (floor Analysts+) is added to Dashboard A (Field Staff) — warning, accept → Field Staff added. Later added to Dashboard B (Funders) — warning, accept → Funders added. Effective audience = Analysts+ ∪ Field Staff ∪ Funders. Removing the chart from Dashboard A does **not** subtract Field Staff; the owner cleans that up manually via Manage shares if desired. Every grant is explicit and auditable.

---

## 20. Boundary Handshake with Spec A

- **Spec A** defines roles, the role each invite produces, role-driven capability (sidebar + Data infra), ownership, and Settings IA. **Spec B** defines the per-resource View/Edit model — independent of role.
- **Ownership** is a Spec A primitive; Spec B exercises it (floor-setting, owner-only delete, transfer, Admin override).
- **Settings > Org defaults** render in Spec A (inert there); Spec B consumes `default_visibility_floor` + `allow_public_sharing`.
- **Invitation role-tier rules** are defined in Spec A §9 (anyone invites as Member; only Admin elevates); Spec B's share modal enforces them.
- **Sharing capability = Edit on resource** (Spec A policy); Spec B makes it functional in the share modal and guardrails.
