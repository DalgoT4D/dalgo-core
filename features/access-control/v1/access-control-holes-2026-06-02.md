# Dalgo Access Control — Risk Register & Comparator Analysis

**Date:** 2026-06-02
**Owner:** Product
**Purpose:** Stress-test the locked V2 access-control model (Spec A role system + Spec B resource sharing) against realistic Dalgo org shapes; surface where it fails, rank by severity, propose fixes; benchmark against comparable BI tools.
**Inputs:** `access-control-context-2026-06-02.md`, `access-control-spec-A-role-system-2026-06-02.md`, `access-control-spec-B-resource-sharing-2026-06-02.md`.
**For reviewers:** this is up for comment. Skim the TL;DR and the at-a-glance table, then drop inline comments on the specific risks (R1–R12) you want to weigh in on.

---

## TL;DR

We stress-tested the locked V2 model (Spec A roles + Spec B sharing) against real Dalgo org types and found **12 risks — 3 blocking, 5 serious, 4 watch.**

The model's *structure* is sound and in places ahead of comparable tools (ownership, additive grants, the no-locked-tile guardrails). The problem is **defaults and governance.** Two locked decisions cause most of the damage:

- **Factory "All users / Edit" floor** → invited funders/board members become editors who can re-share and publish content (R2).
- **PM→Admin** → external pipeline operators get org-wide god-mode over PII (R1).

Public-sharing-on-by-default (R6) and any-Analyst-can-edit-group-membership (R4) compound it, and there's no separate **data-access plane**, so "private" charts/metrics aren't actually private (R7).

**Five decisions close or shrink ~8 of the 12 risks:**

1. Factory floor default → **View**, not Edit (R2; also shrinks R6/R8/R9).
2. Public sharing **OFF** by default; toggle gated to owner/Admin (R6).
3. Group membership locked to **creator+Admin**; consider restricted groups (R4).
4. **Alert recipients** gated to people who can access the trigger source (R5).
5. Confirm **infra-ACL → Analyst** sequencing so operators stop needing Admin (R1).

## Risks at a glance

| ID | Risk | Severity | Orgs | One-line fix |
|---|---|---|---|---|
| R1 | Pipeline operators must be full Admins — no "operator, not governor" tier | 🔴 Blocking | B, C | Resource-scoped infra grants + View/Run/Edit/Manage verbs → Analyst |
| R2 | Factory "All users / Edit" makes external Members editors | 🔴 Blocking | A, C, D | Default floor = View |
| R3 | Spec A interim window shows Members all content | 🔴 Blocking | A, C, D | Hold external-Member onboarding until Spec B (or empty interim) |
| R4 | Any Analyst+ can mutate any group's membership | 🟠 Serious | C, E | Membership = creator+Admin; restricted groups |
| R5 | Alert trigger-context leaks values to unauthorized recipients | 🟠 Serious | C | Gate recipients to trigger-source access |
| R6 | Anyone can publish PII to a public URL (open default + global on) | 🟠 Serious | C | Public default OFF; toggle = owner/Admin |
| R7 | No data-access plane → "private" charts/metrics aren't private | 🟠 Serious | C, E | Treat data plane first-class; eval Superset RLS; position honestly |
| R8 | Access-request approver = any Edit-holder (rubber-stamp) | 🟠 Serious | A, C | Approval = owner + Admin |
| R9 | User hard-delete vs. owned resources undefined | 🟡 Watch | all | Reassign owned resources to oldest Admin on delete |
| R10 | Migration auto-extend explodes chart share lists | 🟡 Watch | D, E | Extend at group granularity; load-test |
| R11 | No RLS → funder/program separation needs duplicate dashboards | 🟡 Watch | D, E | Commit RLS target (Superset in-stack) |
| R12 | 30-day invite expiry is a hard platform constant | 🟡 Watch | field-heavy | Per-org override or one-click re-invite |

## Decisions needed from reviewers

Comment inline on the relevant risk. Open decisions:

- [ ] **R1** — infra-ACL sequencing + verb model (esp. a distinct **Run** permission) + interim posture for partner-operated orgs
- [ ] **R2** — flip factory floor default to View?
- [ ] **R3** — interim Member-visibility posture before Spec B ships
- [ ] **R4** — group membership = creator+Admin only? restricted groups in V1?
- [ ] **R5** — alert-recipient gating rule
- [ ] **R6** — public-sharing global defaults OFF + toggle gated to owner/Admin?
- [ ] **R7** — V1 data-privacy positioning + Superset RLS as the path?
- [ ] **R8** — access-request approver scope = owner + Admin?

---

## How to read this

Severity scale:

- 🔴 **Blocking** — breaks the core safety promise ("safe to invite external partners; PII not accidentally exposed") for a common org type. Should be resolved before GA.
- 🟠 **Serious** — a real data-leak or governance gap via a side channel; resolve in V1 or document loudly with a committed fix date.
- 🟡 **Watch** — real but lower-likelihood or lower-blast-radius; can ship with a known-limitation note.

Org archetypes referenced:

- **A — Tiny NGO:** 1 Admin (M&E lead) + a few program-staff Members + occasionally 1 funder.
- **B — Partner-operated NGO:** uses an external implementation partner to build/run pipelines (the partner serves several NGOs).
- **C — PII-heavy NGO:** beneficiary names, locations, health/GBV/child-welfare status, staff salary/HR data.
- **D — Funder/consortium NGO:** multiple funders, each should see only their program.
- **E — Multi-program NGO:** program teams that should be siloed from each other.

---

## Blocking

### R1 — No "operate infra without governing the org" role; pipeline operators must be full Admins
- **Orgs:** B, C
- **Failure:** Infra (Ingest/Transform/Warehouse/Pipelines/Orchestration) is the one place role still gates function, and only Admin can edit it (Analyst read-only, Member hidden). So anyone who runs pipelines must be Admin = effective owner of every resource, can view/edit/delete/re-share/transfer anything, and reads every warehouse table — including PII and salary. PM→Admin makes every existing pipeline operator an org governor. For an external implementation partner serving multiple NGOs, that's unaudited god-mode over each org's most sensitive data.
- **Why it's structural:** The old Pipeline Manager filled the "infra-operator, not governor" slot; collapsing PM→Admin removed the capability. Content decoupled role from function; infra did not.
- **Planned mitigation (per Product):** Build resource-level access control on the Data items (sources, transform, orchestrate, warehouse) — the same grant model as content — then push infra access down to the **Analyst** role. Once that lands, a pipeline operator can be an Analyst with infra grants, not an Admin. **This downgrades R1's residual risk because there is a committed path.**
- **Proposed infra model (informed by Fivetran / Airbyte / Hevo / dbt Cloud — see Appendix B):** scope infra grants to the **Source/connector**, **Transform project**, and **Orchestration pipeline** level (not a blanket infra flag), and use a **verb model richer than content's View/Edit** because infra has a *run* dimension: **View / Run / Edit / Manage**. An external implementation partner then becomes an **Analyst with Manage (or Run+Edit) grants on the specific pipelines/sources they operate** — they operate infra without being an org governor and without blanket access to PII content. This is precisely the "operator, not governor" tier R1 says is missing, and every comparator ships some version of it.
- **Residual risk until then:** During the window where PM→Admin is live but infra ACLs aren't, partner-operated orgs (B) run with external Admins. Note the cautionary parallel: Airbyte Cloud *Standard* lands every invited user as Workspace Admin with no differentiation — the same trap PM→Admin puts Dalgo in, and a widely-criticized one. Recommend: (a) sequence the infra-ACL work close behind Spec A/B rather than "V-next," and (b) interim guidance that external partners get Admin only where the org accepts it, else stay Analyst (read-only infra) and the org keeps pipeline ops in-house.
- **Decision needed:** Confirm infra-ACL sequencing, the verb model (esp. a distinct **Run** permission for orchestration), and interim posture for partner-operated orgs.

### R2 — Factory default "All users / Edit" inverts the safety story
- **Orgs:** A, C, D (any org inviting an external Member)
- **Failure:** Every new resource starts editable by all users, including external funders/board Members. Edit confers: re-share to anyone, toggle a public link, regenerate a Report snapshot. So an invited funder can edit your dashboard, re-share it onward, or publish it publicly — the opposite of "safe to invite externals." Safety depends on the owner remembering to narrow each sensitive resource to Private *before* building it; humans forget, and PII-heavy orgs (C) pay for it.
- **Proposed fix:** Change the factory default to **"All users / View"** (or "Analysts+ / Edit"). Keep the open-edit option available for orgs that want it, but don't ship it as the factory value. Editing and re-sharing by external Members should be opt-in, not default. *(Note: §5.2 now makes the org-default a full picker, so this is a one-value change, not a model change.)*
- **Decision needed:** Confirm factory default flips to View. (This single change also shrinks R6, R8, R9.)

### R3 — Spec A interim window leaks all content to Members
- **Orgs:** A, C, D
- **Failure:** Spec A makes Members see all content View-only, and Admins can onboard Members via Settings > Users in that window. So onboarding an external Member before Spec B ships exposes every PII and salary dashboard. "Communicate it's transitional" does not prevent the leak.
- **Proposed fix:** Either (a) hold external-Member onboarding until Spec B ships (explicit released-together guidance), or (b) in the interim, scope Member content visibility to nothing/empty rather than all (accept the "logged-in, see-nothing" cliff for the short window), or (c) compress the gap between Spec A and Spec B to near-zero for orgs with sensitive data.
- **Decision needed:** Pick the interim posture; if (a), state it as a hard rollout rule.

---

## Serious

### R4 — Groups are an unconsented access side-channel
- **Orgs:** C, E
- **Failure:** Groups are org-wide and any Analyst+ can create them *and edit any group's membership*. A resource owner shares the salary chart with the "Leadership" group, trusting its roster. Later any Analyst adds a person to "Leadership" → that person sees salary, with no involvement from the chart owner. This breaks the "every grant is explicit, owner controls the audience, auditable" promise — membership is mutated by third parties.
- **Proposed fix:** **Restricted groups** (admin-managed membership) for sensitive groups, or at minimum: only the group creator + Admin manage membership (Spec B §9 already says creator+Admin can manage — but "any Analyst+ can add existing members" in the carried-over model contradicts this; lock it to creator+Admin), and surface a "membership changed" signal to owners of resources shared with that group. Long-term: IdP/SSO-synced groups (industry norm).
- **Decision needed:** Confirm group-membership management is creator+Admin only, and whether restricted groups move into V1.

### R5 — Alerts are a data-exfiltration channel
- **Orgs:** C
- **Failure:** Alert recipients get "notifications with trigger context" but no resource access. The trigger context *is* the sensitive value (e.g., "District X beneficiary count = 412"). Any Analyst+ can create an alert and set arbitrary users/groups as recipients. So sensitive metric values can be piped to people with no access to the underlying KPI/metric — access control bypassed via notifications.
- **Proposed fix:** Either (a) recipients must already have View on the alert's trigger source (KPI/Metric), or (b) trigger context is scrubbed to "a threshold was crossed" (no value) for recipients without access, with the value visible only on click-through (which enforces access). Default to (a) for sensitive orgs.
- **Decision needed:** Confirm recipient-gating rule.

### R6 — Public links + default-on global + Edit-for-all = anyone can publish PII to the open web
- **Orgs:** C
- **Failure:** "Allow public sharing" defaults ON; under the factory floor everyone has Edit; Edit lets you toggle a public link. So in a default org, any user can expose a beneficiary dashboard at an anonymous URL. The only gate is an Admin proactively turning the global off.
- **Proposed fix:** Default the org global **OFF**; require **owner or Admin** (not generic Edit) to toggle a public link; add an explicit confirm step naming the resource's sensitivity. Largely neutralized if R2 (View default) also lands.
- **Decision needed:** Confirm public-sharing global defaults OFF and link-toggle requires owner/Admin.

### R7 — Single-plane model: "data access" isn't separable from "content access," so chart/metric privacy is partly illusory
- **Orgs:** C, E
- **Failure:** Two symptoms of the same root: (i) the documented Editor-to-Editor gap — any Analyst+ can rebuild a Private chart from the warehouse; (ii) a Private metric still computes inside any shared chart, so chart-viewers see its output regardless of the metric's floor ("references ≠ shares"). The model controls *content visibility* but not *data visibility*; they're treated as one plane. Every mature comparator separates these (see Appendix).
- **Proposed fix:** Model the **data plane** as first-class now even if enforcement (RLS/column masking) is deferred: keep the `dataset_access_rules` stub, and — critically — **stop implying that chart/metric floors deliver data privacy.** Position V1 honestly (Spec B §17.2 already does this; make sure the taxonomy doesn't oversell metric-level control). Since Dalgo runs on Superset, evaluate exposing **Superset's native row-level security** rather than building from scratch (see Appendix).
- **Decision needed:** Confirm V1 positioning and whether Superset RLS is the V-next path.

### R8 — Request-access approver = any Edit-holder → rubber-stamp under open default
- **Orgs:** A, C
- **Failure:** Approvers are owner + any Edit-holder + Admin. Under the factory-open floor, everyone has Edit, so everyone can approve access requests — access control becomes a rubber stamp by arbitrary Members. Even under stricter floors, "any Edit-holder approves" may include people the owner never intended as gatekeepers.
- **Proposed fix:** Approval = **owner + Admin** (+ explicitly designated delegates), not raw Edit. Shrinks automatically if R2 lands.
- **Decision needed:** Confirm approver scope (this was already flagged as Spec B open question §17.1.6).

---

## Watch

### R9 — User hard-delete vs. owned resources is undefined
- **Orgs:** all (staff turnover)
- **Failure:** Spec A ships hard delete of users; ownership is owner-bound. Deleting a departing staffer could orphan or cascade-delete their dashboards.
- **Proposed fix:** On user delete, reassign owned resources to the oldest active Admin (reuse the migration fallback rule) with a notice; never cascade-delete content on user delete.

### R10 — Migration auto-extend explodes chart share lists
- **Orgs:** D, E (many dashboards × large groups)
- **Failure:** The one-time auto-extend writes every consumer onto every inner chart's direct-share list. 20 dashboards × 10 charts × a 30-person group = thousands of rows on day one; "Manage shares" becomes unusable; permization/perf hit.
- **Proposed fix:** Extend at **group granularity** (add the group, not each member) so one row covers the group; load-test the resolver and the Manage-shares view against the largest existing org before migration.

### R11 — No RLS → funder/program separation requires dashboard duplication
- **Orgs:** D, E
- **Failure:** "Each funder sees only their program" or "program teams siloed on shared data" can't be done on one dashboard; editors maintain parallel duplicates. For funder-driven orgs (a large share of the base) this is ongoing toil.
- **Proposed fix:** Commit a rough RLS sequencing target (Superset RLS is in-stack). Until then, document the duplication pattern and size the editor burden.

### R12 — 30-day pending-invite expiry is a hard platform constant
- **Orgs:** field-heavy NGOs, low connectivity
- **Failure:** Field staff on personal emails with intermittent access may miss a fixed 31-day window; not per-org configurable.
- **Proposed fix:** Keep 30 days as default but consider per-org override, or a one-click re-invite from the pending list. Low priority.

---

## The throughline

The model decoupled **role from function on content** — clean and modern. But two choices let "function" leak back as "anyone can do anything," and one structural gap over-loads the Admin role:

1. **Open-edit default (R2)** + **generic-Edit-can-do-everything** (re-share, public-link, regenerate, approve) means the safety story depends on owner discipline rather than safe defaults. Cascades into R6, R8, and the public-PII risk.
2. **Public-sharing-on default (R6)** compounds #1.
3. **Loose group membership (R4)** and **side channels (R5 alerts, R7 data plane)** route access around the resource-grant model.
4. **Infra-only-Admin (R1)** over-loads Admin and forces external partners into god-mode — mitigated by the planned infra-ACL work.

**Highest-leverage moves for the review:** flip the factory default to **View** (R2), default public sharing **OFF** (R6), lock group membership to **creator+Admin** (R4), gate alert recipients (R5), and confirm the **infra-ACL-then-Analyst** sequencing (R1). Those five close or shrink roughly eight of the twelve items.

---

## Appendix A — How comparable tools handle roles, sharing & access

Benchmarked against the tools closest to Dalgo's job (self-service BI over a warehouse), with emphasis on **Superset**, since Dalgo's dashboard/chart layer runs on it.

### A.1 The universal pattern Dalgo is missing: two planes

Every mature comparator separates **content access** ("can you open this dashboard/folder") from **data access** ("can you see these rows/columns"):

| Tool | Content plane | Data plane |
|---|---|---|
| **Superset** | Dashboard/chart RBAC; Gamma users only see objects built on data sources they're granted | Per-role **dataset access** + **Row-Level Security (RLS)** filters per role — core, not paywalled |
| **Metabase** | **Collection** permissions: Curate / View / No-access, additive, most-permissive-wins | Separate **data permissions** (View-data / Blocked); **row & column security** (sandboxing) on Pro/Enterprise |
| **Looker** | **Folder** content access: View / Manage | **Model sets** (half the role) + **access filters / user attributes** for row-level — content and data are explicitly different halves |
| **Power BI** | **Workspace roles** (Admin/Member/Contributor/Viewer) + app audiences | **RLS roles** enforced independent of workspace access |

**Lesson for Dalgo:** Dalgo has a single plane (the floor + shares control content; data is "whatever the chart queries"). R7 and the Editor-rebuild gap are direct symptoms. Even with RLS deferred, treat the data plane as a first-class concept (the `dataset_access_rules` stub is the right instinct) and don't market content-floor as data-privacy. **Because Dalgo embeds Superset, Superset's RLS is already in the stack** — exposing it is likely cheaper than building bespoke, and it's the same mechanism Metabase/Looker/Power BI consider table-stakes.

### A.2 Default posture: everyone defaults to *restrictive*, never open-edit

- **Metabase:** the built-in "All Users" group trends to limited/Blocked data access; collections aren't world-editable by default.
- **Power BI:** Viewer is strict read-only; edit requires being added as Contributor/Member.
- **Looker:** best-practice guidance is to *secure folders* by default; viewers can't manage.
- **Superset:** Gamma (the consumer role) is read-only and can't even see data sources it wasn't granted.

**Lesson:** Dalgo's factory **"All users / Edit"** is an industry outlier. No comparable tool makes the consumer tier an editor by default. This is the strongest external support for flipping R2 to View.

### A.3 Viewer/consumer is a hard read-only role at the content layer

Comparators keep a genuinely read-only tier (Power BI Viewer, Superset Gamma, Metabase view-only, Looker viewer). Dalgo's decoupling (role doesn't cap function; a Member can hold Edit) is philosophically cleaner and *fine* — **but only if the default grant is View.** The decoupling isn't the problem; the open default weaponizes it.

### A.4 Groups & membership governance

- Comparators treat groups as the primary grant unit (good — Dalgo matches), but **membership is admin-controlled or IdP/SSO-synced**, not editable by any content editor.
- **Lesson:** Dalgo letting any Analyst+ mutate any group's membership (R4) is looser than every comparator. Restricted/admin-managed groups, or IdP-synced groups, are the norm.

### A.5 Public / embed sharing

- **Metabase:** public sharing is **admin-enabled and off by default**.
- **Power BI:** publish-to-web is admin-gated and explicitly discouraged for sensitive data.
- **Superset:** the Public role is deliberately narrow and opt-in.
- **Lesson:** Dalgo defaulting the public-sharing global **ON** (R6) diverges from all of them. Default OFF, gate the toggle to owner/Admin.

### A.6 Where Dalgo is doing *well* (keep these)

- **Ownership as first-class + Admin override** — matches Power BI workspace-admin and Looker manage semantics.
- **Additive grants, most-permissive-wins** — identical to Metabase's collection model.
- **Floor audience tiers (Private / Admins / Analysts+ / All)** — close cousin of Metabase's Curate/View/No-access and Looker's tiered folder access.
- **Hybrid inheritance + no-locked-tiles guardrails** — genuinely better than most. Superset and Metabase will happily render a dashboard with tiles the viewer can't see/query (blocked or broken tiles); Dalgo's embed-time + bulk-broaden warnings are a thoughtful affordance comparators lack. Worth keeping and even marketing.
- **Personal space gap (minor):** comparators give a personal/draft space (Looker personal folders, Metabase personal collections, Power BI "My workspace") so new content isn't instantly org-visible. Dalgo has none — everything lands on the floor. A personal/draft default would be a *safer* alternative to the open floor and is worth considering alongside R2.

### A.7 One-line scorecard

| Principle | Industry norm | Dalgo V2 | Verdict |
|---|---|---|---|
| Content ≠ data plane | Separated | Single plane | **Behind** (R7) — but stub exists |
| Row-level security | Standard (Superset RLS free) | Deferred | **Behind** (R11) — in-stack via Superset |
| Default grant for consumers | Read-only / restrictive | Edit (factory) | **Outlier** (R2) |
| Public sharing default | Off, admin-gated | On | **Outlier** (R6) |
| Group membership control | Admin/IdP-managed | Any Analyst+ | **Looser** (R4) |
| Ownership + admin override | Standard | First-class | **On par** |
| Additive, most-permissive | Standard | Yes | **On par** |
| No-locked-tile guardrails | Rare | Yes | **Ahead** |

**Net:** Dalgo's *structure* is competitive-to-better (ownership, additive grants, guardrails). Its *defaults and governance* (open-edit, public-on, loose groups) diverge from every mature comparator, and it lacks the second (data) plane those tools treat as table-stakes. The good news: each divergence has a well-trodden answer to borrow, and the data plane can likely ride on Superset's existing RLS.

---

## Appendix B — Infra access control: lessons from the ELT / transform tools

Appendix A benchmarked the **BI / sharing** side. This appendix benchmarks the **ingest / transform / orchestrate** side against the tools that do exactly that job — Fivetran, Airbyte, Hevo, dbt Cloud — to inform how Dalgo's Data section should be permissioned (directly feeds R1 and the planned infra-ACL work).

### B.1 What each tool does

| Tool | Grant scope (the "where") | Roles / tiers (the "what") | Notable mechanic |
|---|---|---|---|
| **Fivetran** | Three nested scopes: **Account → Destination → Connector** | Account Admin, Account Reviewer, **Connector Creator**, Destination Admin, **Destination Analyst**, **Connector Admin**; custom roles on Enterprise | Roles can be granted *per destination* or *per connector*, and to **Teams** (group as grant unit) — you can give someone admin over one connector and nothing else. |
| **Airbyte** | **Organization → Workspace** (a workspace groups sources + destinations + connections) | Org Admin/Reader; Workspace **Admin / Editor / Runner / Reader** | A dedicated **Runner** role: can *trigger syncs* but not edit connections. Workspace roles can only *elevate* above the org role, never restrict below it. Granular roles gated to Cloud Teams / Enterprise. |
| **Hevo** | Entity-level: **Pipeline**, Model, Destination, plus team | Team Admin, Team Collaborator, **Pipeline Admin** (create/edit/delete pipelines), **Pipeline Collaborator** (edit config, schedule, pause/restart, schema mapping — *not* create/delete), **Observer** (view only) | Clean **operator vs. governor** split: Collaborator runs and reconfigures; Admin creates/deletes. Observer is hard read-only and explicitly *cannot* see raw data, transformations, or models. |
| **dbt Cloud** | **Project** and **Environment** level | **License type** (Developer / Read-Only / IT) sits *above* **permission sets** (Developer, Project Creator, Stakeholder, Admin…) | **License type overrides role**: a Read-Only license can't perform admin actions even if assigned to an Admin group — a hard capability ceiling independent of the permission set. Environment-level permissions gate prod vs. dev. |

### B.2 The four patterns worth borrowing

1. **Scope grants to the infra resource, not a blanket flag.** All four scope access to a *grouping*: Fivetran destination/connector, Airbyte workspace, Hevo pipeline, dbt project/environment. **Dalgo should grant at the Source/connector, Transform-project, and Orchestration-pipeline level**, mirroring Spec B's content-resource model. This is exactly the "resource-level access control on data items" Product already plans — the comparators confirm it's the right shape.

2. **Add a "Run" verb — infra needs more than View/Edit.** Content has two verbs (View/Edit); infra has a third: *trigger/run* without *changing the definition*. Airbyte makes this a first-class **Runner** role; Hevo's Collaborator can "pause/restart" without create/delete. **Dalgo's infra ACL should model verbs `View / Run / Edit / Manage`**, where Run = re-sync/re-run/pause an existing pipeline, Edit = change config/schedule/transform code, Manage = create/delete + credentials. Orchestration especially needs Run separated from Edit (an operator who reruns failed jobs shouldn't need to edit pipeline definitions).

3. **Ship an explicit "operator, not governor" tier.** Hevo Collaborator, Airbyte Editor/Runner, dbt Developer, Fivetran Connector Admin all let someone *operate and reconfigure* infra without holding *account governance* (billing, users, org settings). This tier is exactly what R1 says Dalgo deleted by collapsing PM→Admin. **An implementation partner should be an Analyst granted Run/Edit/Manage on the specific pipelines they run — not an org Admin.**

4. **Consider a hard capability ceiling (dbt's license model).** dbt's Read-Only *license* overrides any group permission. The analogue: **Member should have a hard "no infra, ever" ceiling no grant can lift**, and Analyst's infra access should be *granted up* from a read-only floor rather than role-bumped wholesale. This keeps the role (ceiling) × grant (function) decoupling Dalgo already uses on content, applied cleanly to infra.

### B.3 The cautionary tale

**Airbyte Cloud Standard puts every invited user at Workspace Admin with no role differentiation** — granular RBAC is paywalled to Teams/Enterprise. This is the *same posture as PM→Admin*: everyone who touches infra is effectively an admin. It's a known pain point users complain about and upgrade to escape. It's evidence that "everyone-admin on infra" is a stopgap, not a destination — reinforcing that the infra-ACL work should be sequenced close behind Spec A/B, not parked in "V-next."

### B.4 Proposed Dalgo Data-section model (synthesis)

A concrete starting point for the infra-ACL spec, drawn from the above:

- **Resources:** Source/connector (Ingest), Transform project (dbt), Orchestration pipeline/flow, Warehouse connection.
- **Verbs:** `View` (config + logs + lineage) · `Run` (trigger/re-sync/pause/re-run) · `Edit` (config, schedule, transform code, schema mapping) · `Manage` (create/delete, credentials).
- **Defaults / ceilings:**
  - **Admin** — Manage everywhere (governance escape hatch). Unchanged.
  - **Analyst** — `View` by default (today's read-only floor), grantable up to Run / Edit / Manage on *specific* infra resources.
  - **Member** — hard no-infra ceiling; no grant can lift it.
- **Implementation partner** = Analyst + Manage/Run/Edit grants on the pipelines/sources they operate → operates infra, governs nothing, sees only the content they're granted. **Closes R1.**
- **Phasing:** Phase 1 (Spec A) keeps Analyst read-only on infra (already true) and accepts the PM→Admin interim. Phase 2 introduces the verb-based infra ACL and stops forcing operators into Admin. Sequence Phase 2 close behind, per B.3.

This mirrors the Spec B content model (own audience + grants + owner/Admin override) and adds the one thing content doesn't need — the **Run** verb — so the same mental model spans content and infra.

---

## Sources

- [Apache Superset — Security Configurations](https://superset.apache.org/admin-docs/security/)
- [Apache Superset — Row Level Security](https://superset.apache.org/developer-docs/api/row-level-security/)
- [Metabase — Permissions overview](https://www.metabase.com/docs/latest/permissions/start)
- [Metabase — Collection permissions](https://www.metabase.com/docs/latest/permissions/collections)
- [Metabase — Data permissions](https://www.metabase.com/docs/latest/permissions/data)
- [Metabase — Row and column security](https://www.metabase.com/docs/latest/permissions/row-and-column-security)
- [Looker — Access control and permission management](https://cloud.google.com/looker/docs/access-control-and-permission-management)
- [Looker — Secure your folders (content access)](https://docs.cloud.google.com/looker/docs/best-practices/how-to-secure-your-folders)
- [Power BI — Roles in workspaces](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-roles-new-workspaces)
- [Power BI — Give users access to workspaces](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-give-access-new-workspaces)
- [Fivetran — Role-Based Access Control](https://fivetran.com/docs/using-fivetran/fivetran-dashboard/account-settings/role-based-access-control)
- [Fivetran — RBAC Permission Matrix](https://beta.fivetran.com/docs/using-fivetran/fivetran-dashboard/account-management/role-based-access-control/troubleshooting/permission-matrix-tables)
- [Airbyte — Role-based access control (RBAC)](https://docs.airbyte.com/platform/access-management/rbac)
- [Airbyte — RBAC Role Mapping](https://docs.airbyte.com/platform/access-management/role-mapping)
- [Hevo — User Roles and Workspaces](https://docs.hevodata.com/getting-started/creating-your-hevo-account/roles-workspace/)
- [dbt Cloud — Enterprise permissions](https://docs.getdbt.com/docs/platform/manage-access/enterprise-permissions)
- [dbt Cloud — Users and licenses](https://docs.getdbt.com/docs/cloud/manage-access/seats-and-users)
