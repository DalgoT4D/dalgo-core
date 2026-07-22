# Design Alignment — Resource Sharing UI vs Figma

**Date**: 2026-07-14
**Figma source**: [Dalgo 2.0 → "Rbac - access control" page](https://www.figma.com/design/grz6hMemfrBGfHfJuhBCTu/Dalgo-2.0?node-id=939-823) — 76 frames (admin 50, analyst 15, member 11)
**Build compared**: branch `feature/resource-sharing` (webapp `0ca351e5`)
**How this was produced**: the Figma MCP seat hit its monthly call cap after 1 metadata pull + 2 screenshots. The metadata pull captured the **complete layer tree (every text label) for all 76 frames**, so the comparison below is content-accurate. Visual detail (spacing, color, iconography) is confirmed only for the 2 downloaded screens; re-verify visuals once Figma access is restored (`figma/admin/*.png` has the 2 we have).

**What "design" means here**: the Figma frames predate the Q0 spec amendment (2026-07-07) in places. Where design and the amended spec conflict, the spec wins and the design frame is marked **obsolete** rather than a build gap.

---

## The headline gaps (read this if nothing else)

1. **Settings IA**: design has ONE "Access" page with `PEOPLE | GROUPS | ROLES` tabs. Build has THREE sidebar pages (User Management, Groups, Access Management).
2. **Share modal input model**: design has ONE Google-Drive-style search box ("Search for people, group or add emails") with typeahead mixing users + groups + emails, staged rows, and a single **SHARE** commit button. Build has three separate pickers (org member / invite by email / group) that each apply immediately, with no footer button.
3. **Roles tab**: design shows a per-role "Default permissions" matrix (Admins / Analysts / Members × Data access / Resource access) with editable dropdowns. Build has no such screen — org defaults are two pickers (audience + level) on Access Management.
4. **Invite-role picker**: design has "Invite new users as [Member ▾]" (Analyst/Admin options) inline in the share modal. Build hardcodes Member with a hint (sanctioned deviation — design now confirms the picker was intended).
5. **Ownership transfer consent**: design sends an email with **Accept / Deny** — transfer needs the new owner's consent. Build transfers instantly. Product decision needed.

---

## Flow-by-flow comparison

### 1. Settings information architecture

**Design** (frames `1335:2070` users, `1184:3242` group — screenshots on disk): one sidebar entry **Settings → Access**, heading "Access — Manage users and set organization level permission defaults", tabs **PEOPLE | GROUPS | ROLES**. Invite User / Create Group buttons live top-right of the same page and swap with the active tab.

**Build**: three separate pages/sidebar links — `/settings/user-management`, `/settings/groups`, `/settings/access-management` — each with its own heading and button.

**Gap**: structural. Everything built is present, just split across three pages.
**Action**: consolidate into one `/settings/access` page with 3 tabs; keep old routes as redirects. Medium effort — the three existing page bodies become tab panels almost as-is.

### 2. People tab (user management)

| Column | Design | Build |
|---|---|---|
| Email (with icon, sort, filter) | ✅ | ✅ (sort/filter, no icon) |
| Role (sort, filter) | ✅ | ✅ |
| **Created By** (avatar + email) | ✅ | ❌ missing |
| Actions (kebab menu) | ✅ | ✅ (icon buttons, not kebab) |

**Action**: add Created By column (backend already stores inviter on Invitation; needs to surface in org-users DTO — small backend addition), switch actions to kebab. Small.

### 3. Groups tab

| Element | Design | Build |
|---|---|---|
| Group Name + people icon | ✅ | ✅ (name is a link) |
| Members as **avatar stack "+12"** | ✅ | ❌ plain count |
| Created By (avatar + email) | ✅ | ❌ missing |
| Created date | ✅ | ❌ missing |
| "Organization" scope tag on rows | ✅ | ❌ missing |
| Shared-with count | ❌ not in design | ✅ built (keep — it's useful) |

**Action**: add avatar stack, Created By, Created columns (API already returns `created_by`; add `created_at` to DTO if absent). Small-medium.

### 4. Roles tab / default permissions ⚠️ product decision

**Design** (frames `2156:5277` + 3 variants): a "Default permissions" table — "Sets what each role can do across all resources on the platform":

| Role | Data & Pipeline access | Resources access |
|---|---|---|
| Admins — "Run the organisation…" | All access | All access 🔒 |
| Analysts — "Build and maintain dashboards…" | View only | Can Edit ▾ |
| Members — "Work with the shared dashboards…" | No access | Can View ▾ |

Plus the **Allow public sharing** toggle on the same tab. The 4 frame variants are the dropdown states (Analyst view/edit × Member view/no-access).

**Build**: Access Management page = kill switch + two pickers (default audience: Restricted/Admins/Analysts+/Everyone × default level: Viewer/Editor).

**Gap**: same underlying setting (the org-wide default General access), two very different mental models. The design's two dropdowns (Analyst level, Member level) map onto audience×level only partially — e.g. "Analyst Can Edit + Member Can View" is not expressible as one audience×level pair (that's "Analysts+ = Edit AND everyone = View", which the backend's single `(audience, level)` default cannot store).
**Action**: do NOT build the matrix yet. Take to product/design: either (a) design adopts audience×level (spec's model), or (b) backend gains a second default row. Until decided, restyle the existing pickers into the tab layout with the role descriptions as helper text.

### 5. Share modal — core layout ⚠️ biggest UI rework

**Design** (frames `1184:5110`, `1253:4357`, `2112:3845`, scrollable variants):
- Title: `Share "Untitled Dashboard"` with X.
- **One search input**: "Search for people, group or add emails". Typeahead dropdown mixes org users (with role tag: Admin/Analyst/Member), groups (tag: Group), and free emails.
- Selected entries become **staged rows** under the input: icon · email/name · role tag · permission pill (View ▾) · remove ✕. Nothing is applied yet.
- **People with access**: rows with icon · email · role tag · permission pill (Owner locked / View ▾ / Edit ▾).
- **Public sharing** card: icon, "Public sharing / Anyone with the link can view", toggle — inline above footer.
- Footer: **SHARE** button — commits all staged rows in one action.

**Build**: separate "Add a person" (two sub-tabs) + "Add a group" pickers, each adds immediately; owner row + transfer at top; general access section; public section; no staging, no SHARE footer.

**Gap**: interaction model (staged batch vs immediate), input unification, visual layout.
**Action**: rework ShareModal people section into unified-search + staged-rows + SHARE commit. The `POST /grants` API already accepts one grant per call — the SHARE button just fires the batch (same shape the bulk-email path already uses). Large frontend task, no backend change. Keep the narrowing-confirm and capability-flag logic intact.

### 6. Share modal — General access section ⚠️ flag to designer

**Design**: no per-resource General-access (audience × level) picker appears in ANY share-modal frame.
**Build**: has it — and the **spec mandates it** (Flow 2, warn-and-offer on narrowing; verified working in sandbox browser today).
**Action**: keep the build (spec wins). Ask design to add a "General access" block to the modal frames so the visual language matches the rest.

### 7. Invite new users from the modal

**Design** (frame `1184:5984`): unmatched email gets an inline notice — "xyzabcmail@.com isn't on Dalgo yet. Assign new invites role before sharing the resource." with **Invite new users as [Member ▾]** (options: Member/Analyst/Admin) — then SHARE.
**Build**: chips + "they'll join as Members" hint; role hardcoded to Member.
**Action**: add the role dropdown, Admin-only for Analyst/Admin options (spec §invite rules). Backend upsert already exists; share-path invite call needs a `role` param (it was deliberately deferred as "additive later" — this is that later). Small-medium, both sides.

### 8. Access requests

**Design**: (a) full-page request screen (frame `1184:6222`): "Request access to this file", "You can view the 'Resource' once your request is approved", "You're logged in as xyz@…". (b) In-modal banner (frame `1184:5173`): "priya@ngo.org wants to edit — Deny / Approve". (c) Multiple: "2 users are requesting access" (frame `1353:14586`). (d) Admin notification with APPROVE action (frame `1352:14575`).

**Build**: RequestAccessScreen on 403 (with View/Edit choice + note — richer than design), in-modal Approve/Decline rows ✅, notification with deep link (no inline APPROVE button).

**Gap**: mostly copy/layout polish; collapse count line ("2 users are requesting access") if >1; notification inline-approve is a nice-to-have (our notification system may not support action buttons).
**Action**: copy alignment + count header. Small. Skip notification inline-approve unless the notification component already supports actions.

### 9. Ownership transfer ⚠️ product decision

**Design** (frame `1184:6198` + email `2112:3952`): confirm dialog — "Ownership for the dashboard transfers to ⟨Anjali⟩, they can now delete or transfer it. You still have Edit access, you can reclaim ownership anytime." Then an **email to the new owner with Accept / Deny** — consent-based transfer.
**Build**: instant transfer on confirm; old owner keeps Edit (matches the "you still have Edit" copy); no consent step; no email. Also: "reclaim anytime" is not literally true in the build (old owner can't transfer back without being owner/admin).
**Action**: product decision — instant (build, spec-consistent) vs consent (design). If instant stays: fix the design copy ("reclaim anytime" overpromises) and optionally send an FYI email. Defer the Accept/Deny flow unless product wants it.

### 10. Bulk share (select all)

**Design** (frame `1992:2488`): checkbox column, bar with "8 selected · Select All · SHARE".
**Build**: checkbox column, bar with true cross-page count + "N on other pages" + Share / General access / Public link actions + 100-cap.
**Gap**: build is a superset; styling of the bar differs.
**Action**: restyle bar to design (count left, actions right); keep the extra actions. Small.

### 11. Public toggle

**Design** (frames `1426:2063/2115`): "Public sharing / Anyone with the link can view" card with toggle inside the modal.
**Build**: same section, plus copy-link button and kill-switch awareness (verified live today).
**Action**: cosmetic alignment only (card style, icon). Small.

### 12. Delete viewer (remove access)

**Design** (frames `1184:5756/5858/5960`): removal happens from the People-with-access row (pill dropdown → remove), list re-renders.
**Build**: same interaction (✕ per row).
**Action**: none beyond modal restyle in flow 5.

### 13. Warning modal — chart extend — **obsolete, do not build**

**Design** (frame `1251:3305`): "7 of the 10 charts in this dashboard aren't shared with Funders group. Extend all 7" — a per-chart sharing warning.
**Spec Q0 amendment explicitly deleted this flow** (charts are not independently shareable; they ride with the dashboard). Ignore this frame; tell design to archive it.

### 14. Emails (4 designed templates)

| Email | Design frame | Build |
|---|---|---|
| "[Inviter] has invited you to join Dalgo" + Accept Invitation | `1383:14859` | ✅ invitation email exists (invite flow) — copy check needed |
| "You've been added to the [Group] group" | `1383:15004` | ❌ no email on group add |
| "[Granter] shared a [Resource Type] with you" + View | `1383:15149` | ❌ in-app notification only |
| "[Granter] shared ownership…" + Accept/Deny | `2112:3952` | ❌ (depends on flow-9 decision) |

**Action**: add the shared-with-you and group-added emails (backend templates + calls at grant/membership creation — the notification hooks already exist at both sites). Medium, backend-only. Ownership email waits on flow 9.

---

## The plan

### Phase A — quick wins (copy, columns, styling) — ~1 short session
1. People tab: Created By column + kebab actions.
2. Groups tab: avatar stack, Created By, Created columns.
3. Bulk bar restyle; public-sharing card restyle; request-access copy + "N users are requesting access" header.
4. Transfer-confirm copy truthfulness (drop "reclaim anytime" phrasing until product decides flow 9).

### Phase B — settings consolidation — ~1 session
5. One `/settings/access` page, tabs PEOPLE | GROUPS | ROLES; existing three pages become panels; old routes redirect; sidebar shrinks to one entry. Roles tab = restyled kill switch + default pickers with role-description helper text (interim until the flow-4 decision).

### Phase C — share modal rework — the big one, ~1–2 sessions
6. Unified search input (users + groups + emails in one typeahead, role/Group tags).
7. Staged rows with permission pills + single SHARE commit (batch the existing POSTs).
8. Invite-role dropdown for unknown emails (Admin sees Analyst/Admin options) — small backend param.
9. Keep: owner row/transfer, General access block (spec-mandated), narrowing confirm, kill-switch behavior, capability flags.

### Phase D — emails — backend only, ~1 session
10. "Resource shared with you" + "Added to group" email templates and send calls.

### Product/design decisions to close first (blockers only for the flows they own)
- **D1 (flow 4)**: Roles-matrix vs audience×level for org defaults — blocks final Roles-tab UI.
- **D2 (flow 9)**: consent-based ownership transfer vs instant — blocks ownership email.
- **D3 (flow 6)**: designer adds General-access block to modal frames (build keeps it either way).
- **D4 (flow 13)**: archive the obsolete chart-extend warning frame.

### Verify
- Re-pull the 74 missing frame screenshots when Figma access is restored (token or Dev seat) and spot-check Phases A–C against the real visuals before calling alignment done.
