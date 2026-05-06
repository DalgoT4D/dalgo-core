# Access Control — Feature Spec

**Status**: Draft
**Source**: [High-level plan](../../dalgo-ai-gen references) + detailed planning docs (unified_access_control_rls_plan.md, groups_and_sharing_plan.md, access_control_ux_design.md)

---

## Problem Statement

Dalgo's current role-based access system is broken in multiple ways that directly impact NGO partners:

1. **Guest role can't view dashboards or charts** — the permissions `can_view_dashboards` and `can_view_charts` are missing from the Guest role entirely, making the role useless for its intended purpose.
2. **Analyst has full pipeline/dbt write access** — an M&E officer with "Analyst" role can modify data infrastructure, creating risk of accidental pipeline breakage.
3. **No per-resource sharing** — you either see ALL org dashboards or NONE. There's no way to share a specific dashboard with a specific user or team.
4. **No user groups** — every sharing action must target individual users. Can't organize "Field Staff" or "Partners" as a team.
5. **Sidebar not gated by role** — Viewers see Ingest/Transform/Orchestrate nav items they can't use, creating confusion.
6. **No route protection** — unauthorized pages are accessible via direct URL.
7. **`has_schema_access()` is a TODO** — any authenticated user can query any table in the warehouse (data exposure risk).

These gaps mean NGOs can't safely onboard external partners (funders, field staff, consultants) because there's no way to limit what they see.

---

## Target Users

| Persona | Role | Real-world example |
|---------|------|-------------------|
| **Sarah** (M&E Lead) | Account Manager | Manages the org's data team, onboards staff, oversees all programs |
| **Raj** (Data Engineer) | Pipeline Manager | Implementation partner who builds pipelines and transforms |
| **Priya** (M&E Officer) | Analyst | Creates dashboards/charts to track program outcomes |
| **James** (Program Staff / Funder) | Viewer | Checks specific dashboards regularly, doesn't create anything, may be external |

The most underserved persona today is **James (Viewer)** — NGOs cannot safely give him access because the platform shows him everything or nothing.

---

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Viewer users per org | ~0 (role is broken) | 3-5 per org |
| External partners onboarded | Near zero (unsafe to invite) | At least 1 per active org |
| Support tickets about "can't see dashboard" | Unknown | Reduce by 80% |
| % of orgs using resource-level sharing | 0% | 50% of active orgs within 3 months |
| Analyst users accidentally modifying pipelines | Possible (46 perms) | Impossible (22 perms) |

---

## User Stories

### Story 1: Viewer can access shared dashboards

**As a** Viewer (James), **I want** to log in and see only the dashboards shared with me, **so that** I can check program progress without being overwhelmed by data I don't need.

**Acceptance Criteria:**
- [ ] Viewer sees only dashboards explicitly shared with them (directly or via group membership)
- [ ] Charts within shared dashboards are automatically visible (chart inheritance)
- [ ] Viewer can interact with dashboard filters (date range, region, etc.)
- [ ] Viewer can download PDF exports of shared dashboards
- [ ] Viewer cannot create, edit, or delete any resource
- [ ] Viewer sees "Shared with you" as the organizing principle, not "All dashboards"
- [ ] If nothing is shared, Viewer sees an empty state with clear explanation

### Story 2: Analyst loses pipeline access

**As an** Account Manager (Sarah), **I want** Analysts to only access dashboards, charts, reports, and data explorer, **so that** they can't accidentally break pipelines or transforms.

**Acceptance Criteria:**
- [ ] Analyst role reduced from 46 to ~22 permissions
- [ ] Analyst cannot access Ingest, Transform, or Orchestrate modules
- [ ] Analyst retains full dashboard/chart/report CRUD
- [ ] Analyst retains Data Explorer access
- [ ] Analyst can invite users as Viewer only (not other roles)
- [ ] Existing Analyst users notified of permission changes

### Story 3: Share a dashboard with a group

**As an** Analyst (Priya), **I want** to share my "Program Outcomes" dashboard with the "Field Staff" group, **so that** all field team members can view it without me sharing individually with each person.

**Acceptance Criteria:**
- [ ] Can create a user group ("Field Staff") and add members
- [ ] Can share a dashboard with a group at view or edit permission level
- [ ] All group members immediately see the shared dashboard
- [ ] New members added to the group later automatically get access
- [ ] Removing a member from the group revokes their access
- [ ] Revoking group-level share removes access for all group members
- [ ] Charts within the dashboard are inherited (no need to share individually)

### Story 4: Paste-to-share with email addresses

**As an** Analyst (Priya), **I want** to paste multiple email addresses into the share modal, **so that** I can quickly share with people without navigating user lists.

**Acceptance Criteria:**
- [ ] Share modal accepts pasted comma/newline-separated emails
- [ ] Matched emails (existing org users) get immediate access
- [ ] Unmatched emails show option: "Not on Dalgo. [Invite as Viewer] [Remove]"
- [ ] Analyst can only invite as Viewer (role choice not shown)
- [ ] Account Manager can invite as any role
- [ ] Pending shares activate when invited user accepts and creates account
- [ ] Share modal shows groups in search alongside individual users

### Story 5: Sidebar reflects my permissions

**As a** Viewer (James), **I want** to only see nav items I can actually use, **so that** the interface isn't confusing with options I can't access.

**Acceptance Criteria:**
- [ ] Sidebar items hidden (not grayed out) when user lacks permission
- [ ] Viewer sees only: Dashboards, Charts, Reports, Settings > About
- [ ] Analyst sees only: Dashboards, Charts, Reports, Data Explorer, Settings > About
- [ ] Pipeline Manager sees all except Settings > Users and Settings > Billing
- [ ] Account Manager sees everything
- [ ] Direct URL to unauthorized page redirects to first accessible page
- [ ] "No Access" page displayed with org admin contact info when appropriate

### Story 6: Account Manager manages groups

**As an** Account Manager (Sarah), **I want** to create and manage user groups for my organization, **so that** I can organize users by team/function and share resources efficiently.

**Acceptance Criteria:**
- [ ] Can create groups with name and optional description
- [ ] Can add/remove members from any group
- [ ] Can see all groups in the org and their membership
- [ ] Groups are flat (no nesting, no groups-within-groups)
- [ ] Deleting a group revokes all shares granted through that group
- [ ] Pipeline Manager and Analyst can create and manage their own groups
- [ ] Viewer cannot create or manage groups

### Story 7: Chart inheritance from dashboard sharing

**As a** user with a shared dashboard, **I want** all charts within that dashboard to be automatically accessible to me, **so that** I don't need separate share permissions for each chart.

**Acceptance Criteria:**
- [ ] Sharing a dashboard automatically creates inherited share records for all contained charts
- [ ] Adding a new chart to a shared dashboard automatically shares it with existing share recipients
- [ ] Revoking dashboard share cascades to revoke inherited chart shares
- [ ] Inherited charts display "via [Dashboard Name]" indicator
- [ ] Directly shared charts are not affected by dashboard share revocation
- [ ] Chart permission level matches the dashboard permission level (view/edit)

---

## Scope

### In Scope (Full Vision)

**Layer 1 — Roles & Permissions:**
- Rename Guest to Viewer
- Fix Viewer permissions (add dashboard/chart view, remove infrastructure perms)
- Tighten Analyst permissions (remove pipeline/dbt/orchestration write)
- Add report-specific permissions (`can_view_reports`, `can_create_reports`, `can_share_reports`)
- Add `can_share_charts` permission
- Analyst invite constraint (Viewer only)

**Layer 2 — Frontend Navigation & Route Gating:**
- Permission-based sidebar filtering (hide unauthorized items)
- Route guards redirecting unauthorized users
- "No Access" page with admin contact info
- Permission-gated UI elements (buttons, actions)

**Layer 3 — User Groups & Resource-Level Sharing:**
- UserGroup and UserGroupMember models
- ResourceShare model (user/group/email sharing)
- Chart inheritance from dashboard shares
- Paste-to-share flow (matched + unmatched emails)
- Viewer scoping (only see shared resources)
- Share modal UX (groups, permissions, invite flow)
- Group management UI

### Out of Scope (Future)

- **Row-Level Security (RLS)** — controlling which data rows users see within charts. Depends on Layer 1 being finalized. Separate feature.
- **Nested user groups** — groups-within-groups. Intentionally excluded for simplicity.
- **"Manage" permission level** — only view/edit. Resource owner manages sharing.
- **Cross-org sharing** — sharing dashboards between different organizations.
- **Audit trail** — logging who shared what with whom and when.
- **Bulk role changes** — changing multiple users' roles at once.
- **Custom roles** — user-defined roles beyond the 4 standard ones.
- **API token-scoped access** — API keys with limited permissions.

---

## Technical Implications

### DDP_backend (Django + Django Ninja)

| Change | Impact |
|--------|--------|
| Role permission seed data | Migration to update Guest→Viewer permissions, strip Analyst perms |
| New models: `UserGroup`, `UserGroupMember`, `ResourceShare` | New migration, new API endpoints |
| Dashboard/Chart listing logic | Must filter by ResourceShare for Viewer role |
| `has_schema_access()` | Remains TODO until RLS phase (documented risk) |
| Share API endpoints | New endpoints for group CRUD, share CRUD, paste-to-share |
| Chart inheritance service | Triggered on dashboard save/share — syncs child chart shares |
| Invitation flow | Must handle pending ResourceShare activation on invite accept |
| Redis permission cache | Must invalidate when role permissions change |

### webapp_v2 (Next.js 15 + React 19)

| Change | Impact |
|--------|--------|
| Sidebar component (`main-layout.tsx`) | Filter nav items by `useUserPermissions()` |
| Route middleware | Add permission-based route guards |
| Share modal | Redesign: paste emails, group selector, permission dropdown |
| Dashboard/Chart list pages | Show sharing badges, "Shared with you" section for Viewers |
| Group management page | New page under Settings |
| No Access page | New page component |
| `PermissionGate` component | New wrapper for conditional UI rendering |

### Cross-cutting

| Concern | Approach |
|---------|----------|
| Migration safety | Existing Guest users become Viewers with fixed perms. Existing Analysts lose pipeline perms — requires communication to partners. |
| Backwards compatibility | Public sharing (token-based) continues to work unchanged |
| Performance | ResourceShare queries need indexing on (resource_type, resource_id) and (shared_with_user/group) |
| Data integrity | Chart inheritance requires triggers/signals on dashboard-chart relationship changes |

---

## Open Questions

1. **Analyst permission change communication** — How do we notify existing Analyst users that they'll lose pipeline/transform access? Do we provide a grace period?

2. **Existing Guest users with no shared dashboards** — After the rename to Viewer, these users will see empty dashboard lists until someone shares with them. How do we handle the transition? Auto-share all currently-visible dashboards?

3. **Group ownership** — Can only the group creator manage membership, or can any AM manage any group? Current plan says "own groups" for PM/Analyst, "any group" for AM.

4. **Share notifications** — Should users receive email/in-app notifications when a dashboard is shared with them? Or is this out of scope for v1?

5. **Pending share expiry** — If an invited user never accepts, do pending shares expire? After how long?

6. **Performance at scale** — For orgs with 50+ dashboards and 100+ users, will the ResourceShare query pattern (checking shares for each listing) be performant enough?

7. **Reports handling** — Reports currently reuse dashboard permissions. With new report-specific permissions, do existing reports need migration, or do we only enforce for new reports?

---

## Handoff Checklist

- [x] Problem clearly defined with specific broken behaviors
- [x] Target users identified with real personas
- [x] Success metrics defined and measurable
- [x] User stories have concrete acceptance criteria
- [x] Scope is clearly split: in-scope vs deferred
- [x] Technical implications cover both repos
- [x] Implementation layers defined with dependency order
- [ ] Open questions resolved (need team discussion)
- [x] Detailed planning docs available (unified plan, groups & sharing plan, UX design)
- [ ] Analyst permission reduction communicated to affected partners

---

## Implementation Order (Recommended)

```
Layer 1 (Roles & Permissions)  →  Ships first. Independent. Low risk.
Layer 2 (Nav & Route Gating)   →  Frontend only. Can parallel with Layer 3 backend.
Layer 3 (Groups & Sharing)     →  Critical for Viewer to work as designed.
Layer 4 (RLS)                  →  Future. Separate feature spec.
```

**Key dependency**: Viewer role only works as intended after Layer 3 ships. Until then, Viewers with fixed permissions will see all org dashboards (acceptable transitional state since they at least CAN view them after Layer 1 fix).

---

## Reference Documents

| Document | Contents |
|----------|----------|
| `unified_access_control_rls_plan.md` | Full permission audit (73 perms), role matrices, proposed changes, RLS design |
| `groups_and_sharing_plan.md` | Data models, access logic, chart inheritance, paste-to-share, API endpoints |
| `access_control_ux_design.md` | UX specs for all 7 features: invite flow, role mgmt, nav gating, share modal, viewer experience |
