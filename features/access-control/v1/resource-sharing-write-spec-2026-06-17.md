# Resource Sharing — v1

**Scoped from**: access-control (Spec A role system + the resource-sharing work)
**Version**: v1
**Status**: Draft

## Scope for this iteration

### What's included
- Two-axis floor (audience × permission) on every content resource, with an org-wide default
- Additive direct shares to users and groups (View / Edit)
- Public-link sharing as a separate per-resource toggle, gated by an Admin global
- Hybrid inheritance with embed-time and dashboard-broadening guardrails (no locked tiles, ever)
- Groups (org-wide, reusable)
- Unified share modal (add people / groups / paste emails / invite), pending invites with 30-day expiry
- Request-access for authenticated users who hit a link they can't open
- Bulk (multi-select) sharing, floor change, and public-link toggle from resource lists
- Alerts with their own audience + recipient list
- Comments on Reports

### What's deferred to later versions
- **Row-level security & column masking on datasets** — the proper answer to "same dashboard, audience-aware data" (e.g. funders see masked names, field staff see names). Larger surface; v1 handles audience-aware data by splitting dashboards.
- **Dedicated chart-share-sprawl management UI** (per-chart "Manage shares" tab + org-level "who can see this, via what path" audit) — deferred; revisit when sprawl bites.
- **Audit log** of who viewed / shared / broadened — separate feature.
- **Time-bound / expiring access.**
- **Resource-level sharing on Data infrastructure** (ingest / transform / orchestrate / warehouse) — stays role-gated (Spec A); its own future feature.
- **Individual sharing for KPIs / Metrics** beyond what's defined here.
- **Restricted groups** (admin-managed membership), **custom roles**, **cross-org sharing**, **comments on anything other than Reports.**

---

## Problem Statement

A typical Dalgo NGO has a small editing team (1–5 staff) producing dashboards consumed by a much larger audience (30+ program staff, leadership, funders, field partners), and the data frequently contains beneficiary-level PII. Today there is no way to share one dashboard with one funder: a consumer either sees everything in the org or nothing. There is no baseline visibility control, no way to share with a team of 30 in one action, nothing to stop an editor accidentally exposing a PII chart on an all-staff dashboard, no safe way to expose a view-only dashboard externally, no way for someone handed a link to request access, and no way to adjust many resources at once.

This feature makes it safe to invite external partners and to share specific resources with specific people and groups — while keeping the dominant flow (one editor shares one dashboard with a group of 30) under a minute, and guaranteeing a viewer never lands on a dashboard with charts they can't see.

## Target Users

- **Admin** (e.g. M&E Lead) — owns the org's data setup, onboards staff, sets the org-wide sharing defaults, and governs all resources.
- **Analyst** (e.g. M&E Officer, implementation partner) — creates dashboards, charts, and reports and shares them with consumers and groups.
- **Member** (e.g. program staff, leadership, funder — often external) — consumes specific dashboards/reports shared with them; does not build content.

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
Entry: a resource page or a resource list. → Add people, groups, or pasted emails; choose the permission (View/Edit); optionally adjust the resource's floor or toggle a public link. → If the resource is a container (dashboard/report) whose audience now exceeds some inner charts', a **broadening warning** lists the affected charts by name; **default action is Cancel**. → On confirm, grants are applied; matched users get access immediately, unmatched emails become pending invites. Exit: share list shows everyone with access and pending invitees.
- Alternate: choosing "extend" on the warning adds the new audience to the listed charts.
- Error: an unmatched email that's malformed is flagged before send.

### Flow 2 — Set or narrow a resource's floor
Entry: resource settings. → Pick floor audience (Private / Admins only / Analysts+ / All users) × permission (View / Edit). → If the change **narrows** access and the resource has existing direct shares, a **warn + offer** appears: those direct shares will keep access — remove them too? → Apply with the chosen handling. Exit: new floor in effect; nothing silently revoked or silently retained.

### Flow 3 — Embed a chart into a container
Entry: editing a dashboard/report (requires Edit on the container) and picking a chart (requires at least View on the chart). → If the chart's audience already covers the container's, it embeds silently. → If not, an **embed warning** offers to extend the chart's audience to cover the container; doing so requires Edit on the chart. → Accept extends the chart's shares; Cancel aborts the embed. Exit: no viewer of the container can see a chart they lack access to.
- Alternate: an embedder with only View on the chart can't close a gap — they're prompted to request Edit or ask the owner.

### Flow 4 — Request access to a link
Entry: an authenticated user opens a resource link they don't have access to. → A request-access screen lets them request View or Edit with an optional note. → The request routes to the resource **owner**. → The owner approves (choosing the level, can downgrade Edit→View) or declines. Exit: on approve, a direct share is created and the requester notified; on decline, the requester is notified.
- Note: public-link (anonymous) viewers are out of this flow; if public sharing is off and a non-user opens a link, they're prompted to sign in or be invited.

### Flow 5 — Bulk share / adjust from a list
Entry: a resource list with multi-select. → Select N resources; choose Share, a floor change, or a public-link toggle. → The action applies to the resources the actor can edit; the rest are skipped with a clear count. → If the batch broadens dashboards past inner charts, **one aggregated broadening prompt** covers the whole selection (default Cancel); a narrowing floor change shows one aggregated warn+offer to remove direct shares. Exit: a summary of applied vs skipped.

### Flow 6 — Receive an alert
Entry: an alert fires; recipients get a notification with trigger context. → A recipient clicks through to the trigger source. → If they lack access, they land on the request-access screen (Flow 4). Exit: recipients with access see the resource; others can request it. Recipient status alone never grants access.

### Flow 7 — Comment on a report
Entry: viewing a report. → Anyone with View can read and add comments. → A report editor can moderate (hide/delete). Exit: discussion attached to the report. (Public-link viewers cannot comment.)

## User Stories

### Admin
- **As an Admin, I want to set the org-wide default visibility for new resources, so that new content starts at the posture my org expects.** Acceptance: the default uses the same audience × permission picker as a resource's floor; the factory default is "All users / View"; changing it does not retroactively change existing resources.
- **As an Admin, I want to control whether public links are allowed org-wide, so that sensitive orgs can switch them off.** Acceptance: when off, the public-link toggle is hidden on every resource.
- **As an Admin, I want governance access to any resource, so that I can recover or correct sharing when an owner is unavailable.** Acceptance: an Admin can view, edit, re-share, and grant access on any resource regardless of its floor.

### Analyst
- **As an Analyst, I want to share a dashboard with several groups at once (e.g. Field Staff and Funders), so that I don't repeat the flow per group.** Acceptance: multiple groups added in one action; if inner charts don't cover a group, the broadening warning names the affected charts before I confirm.
- **As an Analyst, I want to invite people who aren't on Dalgo yet while sharing, so that onboarding and sharing happen together.** Acceptance: unmatched emails are invited as Members, added to the chosen group, share applied on accept; shown as pending until then; invites expire after 30 days.
- **As an Analyst, I want to lock a sensitive chart down to Private, so that only I (and Admins) can see it even though the org default is open.** Acceptance: setting the floor to Private removes the all-users audience and hides the chart from other editors' pickers.
- **As an Analyst, I want to narrow a previously over-shared dashboard and be sure no leftover direct shares keep people in, so that "make it private" actually locks it down.** Acceptance: narrowing the floor prompts a warn + offer listing the direct shares that would otherwise persist, so I can remove them in the same step.
- **As an Analyst, I want to remove one group from a resource without affecting others, so that I can revoke selectively.** Acceptance: removing a direct share subtracts only that grant; floor and other shares remain.
- **As an Analyst, I want to bulk-share or bulk-lock several resources at once, so that batch setup is fast.** Acceptance: the action applies to resources I can edit and skips the rest with a count; one aggregated prompt handles broadening/narrowing across the selection.
- **As an Analyst, I want to embed a chart and be told exactly which charts will be newly exposed, so that I don't leak data by accident.** Acceptance: embed/broadening warnings name the affected charts; closing a gap requires Edit on the chart.
- **As an Analyst, I want to create a group once and reuse it, so that I'm not rebuilding audiences.** Acceptance: any Analyst+ can create a group; the creator (and Admins) manage its membership; a name-collision warning prevents duplicates.
- **As an Analyst, I want to configure an alert and choose its recipients, so that the right people are notified without gaining hidden access.** Acceptance: the alert has its own floor; recipients (users/groups) get notifications; recipient status grants no resource access.

### Member
- **As a Member, I want to see only the dashboards and reports shared with me, so that the product isn't cluttered with content I can't use.** Acceptance: a "Shared with you" view; no access to other resources or to the data-infrastructure area.
- **As a Member, I want to request access when I open a link I'm not on, so that I'm not stuck at a dead end.** Acceptance: a request-access screen for View/Edit with a note; the request routes to the owner.
- **As a Member (funder/leadership), I want a clean view of a specific dashboard, so that I can read it without navigating a full BI tool.** Acceptance: view access renders the dashboard and its charts inline; no edit affordances unless granted Edit.
- **As a Member on an alert recipient list, I want a useful notification and a clear way to request access if I click through to something I can't see.** Acceptance: clicking the link routes me to request-access when I lack access.

## UI Surface

- **Share modal** — add people / groups / pasted emails; per-resource permission picker; floor controls (audience × permission); public-link toggle (hidden if org disallows); invite-role picker (Member by default; only Admins pick Analyst/Admin); pending state for unmatched emails. States: empty, populated, pending, error (bad email).
- **Resource list pages** (Dashboards, Charts, Reports, Alerts) — floor/audience badge; 🔒 for Private; "Shared with you" section for Members; multi-select with bulk Share / floor / public-link and a skipped-count summary. States: empty, loading, populated.
- **Request-access screen** — shown on access-denied; request View/Edit + note; routes to the owner. States: form, submitted, decided (approved/declined).
- **Requests area** (in Manage shares / share modal) — pending access requests with approve (pick level) / decline.
- **Resource editor / settings** — two-axis floor selector; direct-shares panel (add/remove users & groups at View/Edit); public-link toggle; "Manage shares" view showing who has access and via which path; narrowing the floor triggers the warn-and-offer to remove direct shares.
- **Embed-time warning modal** — fires on embed when the chart doesn't cover the container; extend (needs Edit on chart) or cancel.
- **Dashboard-broadening warning modal** — lists affected charts by name; **default action Cancel**; extend-all or cancel (no per-chart picker); one aggregated prompt across a bulk selection.
- **Groups (Settings)** — list with member count and resources shared with; create / rename / delete / manage membership (creator + Admin); name-collision warning; list scoped by role.
- **Alerts** — configuration with the alert's own floor and a recipient list; notification links route to request-access for recipients without access.
- **Reports** — comments panel for viewers; moderation for report editors.

## Scope

### In (v1)
Everything under "What's included" above. Key product rules:
- **Floor**: audience ∈ {Private, Admins only, Analysts+, All users} × permission ∈ {View, Edit}; factory default **All users / View**; Admin always retains governance access.
- **Direct shares** are additive — effective access is the union of floor and all grants, at the most permissive level; removing one grant removes only that path; narrowing the floor never silently drops or keeps direct shares (warn + offer).
- **Inheritance**: viewing a container renders its contents inline only (no standalone access); editing a container edits its structure only (editing a contained resource needs Edit on it); references (alert→KPI/metric, chart→metric) never grant access to the referenced.
- **No locked tiles, ever** — a container's viewers can always see all its charts, or the broadening action fails (default Cancel).
- **Re-sharing** requires Edit on the resource; anyone with Edit (including a Member covered by an Edit floor) can re-share up to their own level.
- **Request-access** approver is the **owner** (single approver; Admins can still grant via governance).
- **Public links** are view-only, anonymous, no comments; gated by the Admin global.
- **Comments** are on Reports only; a Report is a point-in-time snapshot of one Dashboard.

### Out (deferred)
Everything under "What's deferred to later versions," each with its reason there. Notably, dataset-level data privacy (RLS/column masking) is out — so audience-aware data on a single dashboard is handled by splitting dashboards in v1, and the Editor-to-Editor case (an editor can rebuild a private chart from the warehouse) is a known v1 limitation to communicate honestly to orgs handling salary/HR data.

## Dependencies

- **Requires: Access-control role system (Spec A)** — the Admin / Analyst / Member roles, the ownership primitive (creator = owner, transferable, Admin = effective owner, owner-only delete), the consolidated Settings with org-default controls, and the invitation role-tier rules (anyone invites as Member; only Admins elevate). This feature makes those primitives functional for content.
- **Enables**: dataset-level row/column security (audience-aware data on one dashboard) in a later version; alert digests; an access audit view.

## Handoff Checklist

- [ ] Problem, target users, and success metrics agreed.
- [ ] User flows cover share, floor-narrow, embed, request-access, bulk, alerts, comments — including the key alternate/error paths.
- [ ] User stories per persona have user-visible acceptance criteria.
- [ ] UI surface enumerated with states; warning copy direction (named charts, Cancel default) captured.
- [ ] Scope boundaries explicit; every deferral has a reason.
- [ ] Dependencies named (Spec A role system).
- [ ] No unresolved product questions; defaults chosen and written in.
- [ ] Ready for `/engineering/plan-feature` to produce `plan.md` (data model, APIs, services live there — not here).
