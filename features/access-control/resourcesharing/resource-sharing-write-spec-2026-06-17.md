# Resource Sharing — v1

**Scoped from**: access-control (Spec A role system + the resource-sharing work)
**Version**: v1.1 — **amended 2026-07-07** (Q0: incorporates the 2026-07-02 product decisions; see Amendment note)
**Status**: Draft, amended

> **Amendment note (Q0, applied 2026-07-07).** Four decisions from the 2026-07-02 review are now folded into this text:
> 1. **Charts are not independently shareable.** Dashboards are the sharing unit; a chart is visible wherever its dashboards are visible. This deleted the embed-time and dashboard-broadening warning flows and the per-chart floor.
> 2. **"Floor" is renamed "General access"** (Google Drive vocabulary) in UI, API, and code.
> 3. **A Member is hard-capped at View** — a Member can never hold Edit, and therefore never re-shares (Spec A's shipped rule wins over this spec's earlier re-share sentence).
> 4. **The public-sharing global is a kill switch** — turning it off hides the toggles *and* stops existing public links from rendering.
>
> The original 2026-06-17 text is in git history. [Spec B](./access-control-spec-B-resource-sharing-2026-06-02.md) (the long-form vision doc) is *not* amended — read it as historical context only.

## Scope for this iteration

### What's included
- **General access** (audience × permission) on every shareable resource, with an org-wide default
- **Dashboards as the sharing unit** — charts ride along with their dashboards automatically; no per-chart sharing, no warning modals, no chart/dashboard permission mismatches possible
- Additive direct shares to users and groups (View / Edit)
- Public-link sharing as a separate per-resource toggle (Dashboards + Reports), gated by an Admin global that acts as a **kill switch**
- Groups (org-wide, reusable)
- Unified share modal (add people / groups / paste emails / invite), pending invites with 30-day expiry
- Request-access for authenticated users who hit a link they can't open
- Bulk (multi-select) sharing, General-access change, and public-link toggle from resource lists
- Alerts with their own General access + recipient list
- Comments on Reports

### What's deferred to later versions
- **Row-level security & column masking on datasets** — the proper answer to "same dashboard, audience-aware data" (e.g. funders see masked names, field staff see names). Larger surface; v1 handles audience-aware data by splitting dashboards. *(Layer 3 in the access-model roadmap.)*
- **Chart-level data privacy** — keeping a chart's *data* from specific viewers is dataset access (Layer 2 dataset grants), not content sharing. In v1, keeping a chart from an audience = don't put it on their dashboard.
- **Audit log** of who viewed / shared / broadened — separate feature.
- **Time-bound / expiring access.**
- **Resource-level sharing on Data infrastructure** (ingest / transform / orchestrate / warehouse) — stays role-gated (Spec A); its own future feature *(Layer 2)*.
- **Individual sharing for KPIs / Metrics** beyond what's defined here.
- **Audience grants** — a per-resource rule like "Analysts+ can Edit this one dashboard" on top of its General access. The grants table's shape supports them (open principal model), but v1 creates and honors only **user** and **group** grants; wanting "everyone views, analysts edit" is served by a group in v1. Enabling audience grants later is additive (no schema change). *(Deferred 2026-07-08.)*
- **Restricted groups** (admin-managed membership), **custom roles**, **cross-org sharing**, **comments on anything other than Reports.**

---

## Problem Statement

A typical Dalgo NGO has a small editing team (1–5 staff) producing dashboards consumed by a much larger audience (30+ program staff, leadership, funders, field partners), and the data frequently contains beneficiary-level PII. Today there is no way to share one dashboard with one funder: a consumer either sees everything in the org or nothing. There is no baseline visibility control, no way to share with a team of 30 in one action, no safe way to expose a view-only dashboard externally, no way for someone handed a link to request access, and no way to adjust many resources at once.

This feature makes it safe to invite external partners and to share specific resources with specific people and groups — while keeping the dominant flow (one editor shares one dashboard with a group of 30) under a minute. Because the dashboard is the sharing unit, a viewer by construction never lands on a dashboard with charts they can't see. Protecting the *data* behind a chart from specific viewers (PII columns, restricted tables) is dataset access — Layer 2, deferred.

## Target Users

- **Admin** (e.g. M&E Lead) — owns the org's data setup, onboards staff, sets the org-wide sharing defaults, and governs all resources.
- **Analyst** (e.g. M&E Officer, implementation partner) — creates dashboards, charts, and reports and shares them with consumers and groups.
- **Member** (e.g. program staff, leadership, funder — often external) — consumes specific dashboards/reports shared with them; does not build content. **Always view-only** — a Member never holds Edit.

Org shape to design for: 1–5 editors and 30+ consumers; PII common in the data.

## Success Metrics

- Members (consumers) active per org: **5+ within 3 months** of GA (from ~0 today).
- External partners (funders / field staff) onboarded: **≥1 per active org** (from ~0).
- "Can't see the dashboard" support tickets: **down ~80%**.
- Active orgs using resource-level sharing: **50% within 3 months**.
- Active orgs using groups: **30% within 3 months**.
- Time to share a dashboard with 30 people: **under 60 seconds**.

## User Flows

Persona-agnostic end-to-end paths. Each: entry → steps → exit, with key alternate/error paths.

### Flow 1 — Share a resource
Entry: a resource page or a resource list. → Add people, groups, or pasted emails; choose the permission (View/Edit); optionally adjust the resource's General access or toggle a public link. → On confirm, grants are applied; matched users get access immediately, unmatched emails become pending invites. Exit: share list shows everyone with access and pending invitees.
- Every chart on a shared dashboard is visible to that dashboard's audience automatically — there is nothing extra to confirm.
- Error: an unmatched email that's malformed is flagged before send.

### Flow 2 — Set or narrow a resource's General access
Entry: resource settings / share modal. → Pick audience (Private / Admins only / Analysts+ / All users) × permission (View / Edit). → If the change **narrows** access and the resource has existing direct shares, a **warn + offer** appears: those direct shares will keep access — remove them too? → Apply with the chosen handling. Exit: new General access in effect; nothing silently revoked or silently retained.

### Flow 3 — Embed a chart into a dashboard or report
Entry: editing a dashboard/report (requires Edit on the container). → Pick any org chart and embed it. → The chart renders for whoever can view the container, automatically. Exit: the container's viewers see all its charts, always.
- There are no embed-time access checks or warnings: putting a chart on a dashboard *is* publishing it to that dashboard's audience. To keep a chart from an audience, don't put it on their dashboard.

### Flow 4 — Request access to a link
Entry: an authenticated user opens a resource link they don't have access to. → A request-access screen lets them request View or Edit with an optional note. → The request routes to the resource **owner**. → The owner approves (choosing the level, can downgrade Edit→View) or declines. Exit: on approve, a direct share is created and the requester notified; on decline, the requester is notified.
- Note: public-link (anonymous) viewers are out of this flow; if public sharing is off and a non-user opens a link, they're prompted to sign in or be invited.

### Flow 5 — Bulk share / adjust from a list
Entry: a resource list with multi-select. → Select N resources; choose Share, a General-access change, or a public-link toggle. → The action applies to the resources the actor can edit; the rest are skipped with a clear count. → A narrowing General-access change shows **one aggregated warn+offer** to remove direct shares across the whole selection. Exit: a summary of applied vs skipped.

### Flow 6 — Receive an alert
Entry: an alert fires; recipients get a notification with trigger context. → A recipient clicks through to the trigger source. → If they lack access, they land on the request-access screen (Flow 4). Exit: recipients with access see the resource; others can request it. Recipient status alone never grants access.

### Flow 7 — Comment on a report
Entry: viewing a report. → Anyone with View can read and add comments. → A report editor can moderate (hide/delete). Exit: discussion attached to the report. (Public-link viewers cannot comment.)

## User Stories

### Admin
- **As an Admin, I want to set the org-wide default visibility for new resources, so that new content starts at the posture my org expects.** Acceptance: the default uses the same audience × permission picker as a resource's General access; the factory default is "All users / View"; changing it does not retroactively change existing resources.
- **As an Admin, I want to control whether public links are allowed org-wide, so that sensitive orgs can switch them off.** Acceptance: when off, the public-link toggle is hidden on every resource **and existing public links stop rendering** (kill switch — flipping it off closes today's open links, not just tomorrow's).
- **As an Admin, I want governance access to any resource, so that I can recover or correct sharing when an owner is unavailable.** Acceptance: an Admin can view, edit, re-share, and grant access on any resource regardless of its General access.

### Analyst
- **As an Analyst, I want to share a dashboard with several groups at once (e.g. Field Staff and Funders), so that I don't repeat the flow per group.** Acceptance: multiple groups added in one action; every chart on the dashboard is visible to those groups automatically.
- **As an Analyst, I want to invite people who aren't on Dalgo yet while sharing, so that onboarding and sharing happen together.** Acceptance: unmatched emails are invited as Members, added to the chosen group, share applied on accept; shown as pending until then; invites expire after 30 days.
- **As an Analyst, I want a dashboard I haven't shared to stay invisible to consumers, so that work-in-progress and sensitive content don't leak.** Acceptance: a Private dashboard is visible only to its owner and Admins; a chart appears to consumers only through dashboards they can view — Members have no standalone charts area.
- **As an Analyst, I want to narrow a previously over-shared dashboard and be sure no leftover direct shares keep people in, so that "make it private" actually locks it down.** Acceptance: narrowing General access prompts a warn + offer listing the direct shares that would otherwise persist, so I can remove them in the same step.
- **As an Analyst, I want to remove one group from a resource without affecting others, so that I can revoke selectively.** Acceptance: removing a direct share subtracts only that grant; General access and other shares remain.
- **As an Analyst, I want to bulk-share or bulk-lock several resources at once, so that batch setup is fast.** Acceptance: the action applies to resources I can edit and skips the rest with a count; one aggregated prompt handles narrowing across the selection.
- **As an Analyst, I want to create a group once and reuse it, so that I'm not rebuilding audiences.** Acceptance: any Analyst+ can create a group; the creator (and Admins) manage its membership; a name-collision warning prevents duplicates.
- **As an Analyst, I want to configure an alert and choose its recipients, so that the right people are notified without gaining hidden access.** Acceptance: the alert has its own General access; recipients (users/groups) get notifications; recipient status grants no resource access.

### Member
- **As a Member, I want to see only the dashboards and reports shared with me, so that the product isn't cluttered with content I can't use.** Acceptance: a "Shared with you" view; no access to other resources, to standalone charts, or to the data-infrastructure area.
- **As a Member, I want to request access when I open a link I'm not on, so that I'm not stuck at a dead end.** Acceptance: a request-access screen for View/Edit with a note; the request routes to the owner.
- **As a Member (funder/leadership), I want a clean view of a specific dashboard, so that I can read it without navigating a full BI tool.** Acceptance: view access renders the dashboard and its charts inline; no edit affordances — a Member is always view-only.
- **As a Member on an alert recipient list, I want a useful notification and a clear way to request access if I click through to something I can't see.** Acceptance: clicking the link routes me to request-access when I lack access.

## UI Surface

- **Share modal** — add people / groups / pasted emails; per-resource permission picker; **General access** controls (audience × permission); public-link toggle (hidden if org disallows); invite-role picker (Member by default; only Admins pick Analyst/Admin); pending state for unmatched emails. States: empty, populated, pending, error (bad email).
- **Resource list pages** (Dashboards, Reports, Alerts) — General-access badge; 🔒 for Private; "Shared with you" section for Members; multi-select with bulk Share / General access / public-link and a skipped-count summary. States: empty, loading, populated. *(The Charts list is not a sharing surface: it stays as-is for Analyst+ and is hidden for Members.)*
- **Request-access screen** — shown on access-denied; request View/Edit + note; routes to the owner. States: form, submitted, decided (approved/declined).
- **Requests area** (in the share modal) — pending access requests with approve (pick level) / decline.
- **Resource editor / settings** — General-access selector; direct-shares panel (add/remove users & groups at View/Edit); public-link toggle; "who has access and via which path" view; narrowing triggers the warn-and-offer to remove direct shares.
- **Groups (Settings)** — list with member count and resources shared with; create / rename / delete / manage membership (creator + Admin); name-collision warning; list scoped by role.
- **Alerts** — configuration with the alert's own General access and a recipient list; notification links route to request-access for recipients without access.
- **Reports** — comments panel for viewers; moderation for report editors.

## Scope

### In (v1)
Everything under "What's included" above. Key product rules:
- **General access**: audience ∈ {Private, Admins only, Analysts+, All users} × permission ∈ {View, Edit}; factory default **All users / View**; Admin always retains governance access.
- **Direct shares** are additive — effective access is the union of General access and all grants, at the most permissive level; removing one grant removes only that path; narrowing General access never silently drops or keeps direct shares (warn + offer).
- **Dashboards are the sharing unit**: a chart is visible exactly where its dashboards are visible; viewing a container renders its contents inline only (no standalone access); editing a container edits its structure only (editing a contained resource needs Edit on it); references (alert→KPI/metric, chart→metric) never grant access to the referenced.
- **Member cap**: a Member's effective access never exceeds View, regardless of grants or General access level. Members therefore never re-share.
- **Re-sharing** requires Edit on the resource; anyone with Edit can re-share up to their own effective level.
- **Request-access** approver is the **owner** (single approver; Admins can still grant via governance).
- **Public links** are view-only, anonymous, no comments; gated by the Admin global, which is a **kill switch** (off = existing links stop rendering).
- **Comments** are on Reports only; a Report is a point-in-time snapshot of one Dashboard.

### Out (deferred)
Everything under "What's deferred to later versions," each with its reason there. Notably, dataset-level data privacy (RLS/column masking) is out — so audience-aware data on a single dashboard is handled by splitting dashboards in v1, and the Editor-to-Editor case (an editor can rebuild a private chart's data from the warehouse) is a known v1 limitation to communicate honestly to orgs handling salary/HR data.

## Dependencies

- **Requires: Access-control role system (Spec A)** — the Admin / Analyst / Member roles, the ownership primitive (creator = owner, transferable, Admin = effective owner, owner-only delete), the consolidated Settings with org-default controls, and the invitation role-tier rules (non-Admins invite as Member only; only Admins elevate). This feature makes those primitives functional for content.
- **Enables**: dataset-level access (Layer 2) and row/column security (Layer 3 — audience-aware data on one dashboard); alert digests; an access audit view.

## Handoff Checklist

- [x] Problem, target users, and success metrics agreed.
- [x] User flows cover share, narrow, embed, request-access, bulk, alerts, comments — including the key alternate/error paths.
- [x] User stories per persona have user-visible acceptance criteria.
- [x] UI surface enumerated with states.
- [x] Scope boundaries explicit; every deferral has a reason.
- [x] Dependencies named (Spec A role system).
- [x] No unresolved product questions; defaults chosen and written in (Q0 amendment applied 2026-07-07).
- [x] Ready for `/engineering/plan-feature` → `plan.md` exists ([plan.md](./plan.md)).
