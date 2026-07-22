# RBAC Screens — Gap Review and Plan (2026-07-15)

**What this is:** the 73 exported design screens in `RBAC screens/` compared, topic by topic,
against the built `feature/resource-sharing` branch (webapp `812513ab`, backend `faa98f60`).
Nine parallel review agents each took one topic. Their full reports live in `screens-review/`.

**How to read the labels:**
- **[MINOR]** — copy, icon, or layout tweak. Example: the modal's footer button says "Close" but the design says "CANCEL".
- **[MISSING]** — a designed thing we never built. Example: the "No people yet" empty state.
- **[DIFFERENT]** — we built it another way. Example: Owner sits in his own card instead of the first row of "People with access".
- **[DECISION]** — someone (you or the designer) has to choose before we can build.

---

## 1. Scoreboard

| Topic | Verdict | Report |
|---|---|---|
| Public sharing | ✅ Strong match — 2 copy nits | `screens-review/public-sharing.md` |
| Request access | ✅ Core loop matches — 2 gaps | `screens-review/request-access.md` |
| People tab | ✅ Table matches — 2 gaps | `screens-review/people-tab.md` |
| Share modal | 🟡 Mechanics match, fidelity gaps | `screens-review/share-modal.md` |
| Groups tab | 🟡 CRUD matches, flow gaps | `screens-review/groups-tab.md` |
| Ownership transfer | 🟡 Works, simpler than design | `screens-review/transfer-ownership.md` |
| Warnings + member view | 🔴 Remove-access confirm missing | `screens-review/warnings-member-view.md` |
| Bulk share | 🔴 Dialog never designed; ours diverges | `screens-review/bulk-share.md` |
| Roles tab | 🔴 Different data model (D1 confirmed) | `screens-review/roles-tab.md` |

---

## 2. What to do — three batches

### Batch 1 — Polish (small, no decisions needed, ~1 session)

Copy, icons, and layout tweaks. Each is a contained frontend change.

| # | Item | Where |
|---|---|---|
| P1 | Owner renders as the FIRST ROW inside "People with access", not a separate card | `share-modal.tsx` |
| P2 | Non-admin invite copy: locked sentence "New member will be invited as member" — no one-option dropdown | `share-modal-staging.tsx` |
| P3 | Footer button "Close" → "CANCEL" | `share-modal.tsx` |
| P4 | Input placeholder: "Type or paste emails…" in the empty input itself | `share-modal-staging.tsx` |
| P5 | Existing-access rows use "✕" remove icon, not a trash can (pairs with F2 below) | `share-modal.tsx` |
| P6 | Drop the Users icon before "People with access"; put the public-sharing icon in a circular badge | `share-modal.tsx` |
| P7 | Public card: label above copy-link button reads "Public sharing", ON-state copy explains what ON does | `share-modal.tsx` |
| P8 | Bulk selection bar: dismiss "✕" far left, "Select All" next to SHARE, button reads "SHARE" (caps), checkboxes appear on hover/selection only | dashboards list |
| P9 | Roles tab copy nits (Members description period; ON-vs-OFF phrasing of the public-sharing kill switch) | `AccessManagement.tsx` |

### Batch 2 — Designed features we haven't built (medium, no product decision)

| # | Item | Size | Notes |
|---|---|---|---|
| F1 | Empty states: People ("No people yet" + CTA + "Learn how roles and access work" link) and Groups (illustrated, heading, CTA, same link) | M | Design shows both; build has bare tables |
| F2 | Remove-access confirmation modal — "Remove access… cannot be undone", Cancel/Delete | S | Design mandates it in every frame; build deletes instantly on trash-click (a test pins the current behavior — update it) |
| F3 | Branded HTML invitation email (teal header, role + workspace, "Accept Invitation" button) | S | `send_html_message` already exists in `awsses.py`; invite path sends plain text |
| F4 | Groups: create-group modal adds members in the same step (today: create, then open drawer) | M | Design shows one modal doing both |
| F5 | Groups: per-member org-role badges (Admin/Analyst) in the member drawer; column sorting on the groups table | S | |
| F6 | Notifications page: inline Approve/Deny on access-request rows | M | Needs `request_id` in the notification payload (backend) + row actions (frontend); today deciding requires opening the share modal |

### Batch 3 — Blocked on a decision (see §3)

| # | Item | Blocked on |
|---|---|---|
| B1 | Roles tab: per-role defaults table ("Analysts → Can Edit, Members → Can View") + "Data & Pipeline access" column + SAVE/CANCEL | D1 |
| B2 | Ownership-transfer email (FYI now, or Accept/Deny consent flow) | D2 |
| B3 | Bulk-share dialog rework (staged rows + one SHARE, invite-role picker, free-email input) | D6 — dialog was never designed |
| B4 | Group create/add-member accepting brand-new emails with an invite-role warning | overlaps D1/D6 designs; backend `GroupMemberCreate` is orguser-only today |
| B5 | Email on access request / approval / decline | D7 |

---

## 3. Decisions

### For you (product calls)

| ID | Question | What the screens show | What's built | Recommendation |
|---|---|---|---|---|
| **D1** | Roles-tab data model | Per-role dropdowns: Admins locked "All access"; Analysts and Members EACH pick No access / View / Edit. Plus a read-only "Data & Pipeline access" column | One org-wide audience×level pair — "Analyst=Edit, Member=View" is impossible to store | Adopt the design's model: it's simpler to explain to NGO admins. Backend change: two per-role columns instead of the pair. ~1 milestone |
| **D2** | Transfer consent | Email to the new owner with Accept/Deny; old owner "can reclaim anytime" (copy is wrong — they only keep Edit) | Instant transfer, NO email at all | Ship an FYI email now (small, reuses Phase D transport); defer the consent flow |
| **D5** | Bulk-share email volume | — (not designed) | Sharing N dashboards with one existing teammate sends N separate "shared with you" emails | Batch to one digest email per person per bulk action |
| **D8** | Transfer recipient scope | Transfer only offered on people who already have access | Any org member pickable | Follow design — it prevents accidental transfers to strangers |
| **D9** | Delete user vs owned resources | The "Delete user" frames are actually per-resource remove-access; real account deletion isn't designed | Deleting an OrgUser does nothing about resources they own | Product call: block deletion until resources are transferred, or auto-transfer to the deleting admin |
| **D10** | Grant-level vs role on the dashboard toolbar | Member mocks show a full toolbar (can't validate) | Edit/Share/Delete gate on org role only, not the per-resource View/Edit grant | Verify with a live test; if a view-only grantee sees Edit, that's a real bug to fix |
| **D7** | Emails for request/approve/decline | Not designed | In-app notification only (deliberate scope note in `access_requests.py`; fields are schema-ready) | Keep in-app-only for v1; revisit with D5 |

### For the designer (missing or obsolete frames)

| ID | Ask |
|---|---|
| **D3** | Add the "General access" block to the share-modal frames — it's spec-mandated and built, but appears in none of the 12 modal screens |
| **D4** | Archive the two obsolete chart-extend-access warning frames (`Analyst-warning on adding charts.jpg`, `resource sharing- warning modal.jpg`) — that flow was deleted by the Q0 spec amendment |
| **D6** | Design the bulk-share dialog contents (only the selection bar exists), the group member-detail drawer, and the requester's post-approval screen |
| **D11** | Fix design-side bugs we already corrected in code: "PEOLPE" typo, "Delete User" copy on the delete-group modal, "can reclaim ownership anytime" transfer claim, ROLES/PERMISSIONS tab-name drift |

---

## 4. Suggested order

1. **Batch 1 (polish)** — one implementer+reviewer pass, all frontend.
2. **Batch 2 (F1–F6)** — F2/F3/F5 are quick wins; F1/F4/F6 are a normal session.
3. **Decide D1** — it's the biggest structural gap and blocks the Roles tab (B1).
4. **D2/D5/D8** — small backend follow-ups once decided.
5. Designer asks (D3/D4/D6/D11) can run in parallel with everything.
