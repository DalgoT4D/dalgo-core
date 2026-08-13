# Resource Sharing — Test Spec (by User Story)

Each section maps to one user story. Under each story:
- **Journey** — who does what, in one sentence
- **Backend tests** — Django unit/API tests (file reference + table of test cases); these are automated and run in CI
- **Frontend behavior** — manual QA checklist; a human verifies these in the browser before marking the story done

Test files:
- `ddpui/tests/core/test_access_control.py` — unit tests for the access engine (no HTTP)
- `ddpui/tests/api/test_access_api.py` — API integration tests (Django Ninja test client)
- `ddpui/tests/core/test_orguserfunctions.py` — invitation/acceptance tests

---

## Story 1: Admin sets org-wide permission floors

**Journey:** Admin opens Settings > Access > Roles tab and sets the default access level for Analysts and Members; the change takes effect immediately across all resources, and the UI prevents setting Members above Analysts.

**Backend test files:** `test_access_api.py`, `test_access_control.py`

### Backend tests

#### Floor hierarchy validation — `PUT /api/orgpreferences/`

| ID | Scenario | Payload | Expected |
|---|---|---|---|
| F01 | Valid: Member=View, Analyst=Edit | `{member: "view", analyst: "edit"}` | 200 |
| F02 | Valid: both No Access (equal) | `{member: "no_access", analyst: "no_access"}` | 200 |
| F03 | Valid: both View (equal) | `{member: "view", analyst: "view"}` | 200 |
| F04 | Valid: both Edit (equal) | `{member: "edit", analyst: "edit"}` | 200 |
| F05 | Invalid: Member=View, Analyst=No Access | `{member: "view", analyst: "no_access"}` | 400 |
| F06 | Invalid: Member=Edit, Analyst=View | `{member: "edit", analyst: "view"}` | 400 |
| F07 | Invalid: Member=Edit, Analyst=No Access | `{member: "edit", analyst: "no_access"}` | 400 |
| F08 | Non-Admin caller cannot change floors | Analyst caller, PUT | 403 |
| F09 | Non-Admin caller cannot see floor settings | Analyst caller, GET | 403 |

#### Floor applied to resource access — `get_user_access`

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| A01 | Analyst gets Edit on default Analyst floor | `prefs.default_analyst_level=edit`, no grant | `"edit"` |
| A02 | Member gets View on default Member floor | `prefs.default_member_level=view`, no grant | `"view"` |
| A03 | Member with No Access floor → invisible | `prefs.default_member_level=no_access` | `None` |
| A04 | Analyst with No Access floor → invisible | `prefs.default_analyst_level=no_access` | `None` |
| A05 | Admin always gets Edit regardless of floor | `prefs.default_analyst_level=no_access`, admin user | `"edit"` |
| A06 | Missing OrgPreferences row → defaults to View | no OrgPreferences row for org | `"view"` |
| A07 | Creator of resource always gets Edit | user == `resource.created_by`, floor=no_access | `"edit"` |
| A08 | Floor change is immediate | prefs updated to no_access after resource created | `None` on next call |
| Q04 | Floor change immediate for list endpoints | Members at View → No Access; call list endpoint | empty queryset |
| Q05 | Member empty state — no shares, no ownership | floor=No Access, no grants | all list endpoints return `[]` |

### Frontend behavior

**Page: Settings > Access > Roles tab**

| Scenario | Expected |
|---|---|
| Admin navigates to Settings > Access > Roles tab | Page loads; floor dropdowns and Allow Public Sharing toggle are visible and editable |
| Analyst navigates to Settings > Access > Roles tab | Page is not accessible — tab is hidden or route returns 403 |
| Member navigates to Settings > Access > Roles tab | Page is not accessible — tab is hidden or route returns 403 |
| Admin sets Member floor to Edit while Analyst floor is View (Member > Analyst) | Save button is disabled; validation message shown explaining the constraint |
| Admin sets valid floors (Member=View, Analyst=Edit) and saves | Success; dropdowns reflect saved values on page reload |
| Admin changes Member floor from View to No Access and reloads the dashboard list as a Member | Dashboard list is empty — floor change takes effect immediately |

---

## Story 2: Analyst shares a dashboard with a user or group

**Journey:** Analyst opens the share modal on a Dashboard, picks a colleague or group, sets permission to View or Edit, and clicks Share; the grant is active immediately and can be changed or revoked from the same modal.

**Backend test file:** `test_access_api.py`, `test_access_control.py`

### Backend tests

#### Adding a grant — `POST /api/access/{rtype}/{resource_id}/grants`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| G01 | Owner adds View grant for a user | owner | 201, grant created |
| G02 | Owner adds Edit grant for a user | owner | 201, grant created |
| G03 | Owner adds grant for a group | owner | 201, principal_type=group |
| G04 | Edit-holder (non-owner) adds grant — re-sharing allowed | edit-holder | 201 |
| G05 | View-holder cannot add grant | view-holder | 403 |
| G06 | No-access user cannot add grant | no-access | 403 |
| G07 | Resource belongs to different org | owner, cross-org resource_id | 404 |
| G08 | Resource does not exist | owner | 404 |
| G09 | Grant with access_level=no_access is rejected | owner | 400 |
| G10 | Duplicate grant for same user → updates existing row (upsert) | owner, user already has view | 200 |

#### Listing grants — `GET /api/access/{rtype}/{resource_id}/grants`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| G11 | Direct user grant shown with share_id | owner | share_id set, cascade_sources=[] |
| G15 | Pending invite appears in list with status=pending | owner | row with status=pending |
| G16 | View-holder cannot list grants | view-holder | 403 |

#### Updating a grant — `PATCH /api/access/{rtype}/{resource_id}/grants/{grant_id}`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| G17 | Owner updates View → Edit | owner | 200, level updated |
| G19 | Edit-holder updates grant | edit-holder | 200 |
| G20 | View-holder cannot update grant | view-holder | 403 |
| G21 | PATCH non-existent grant | owner | 404 |

#### Removing a grant — `DELETE /api/access/{rtype}/{resource_id}/grants/{grant_id}`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| G22 | Owner removes direct grant | owner | 200, grant gone |
| G24 | Edit-holder removes grant | edit-holder | 200 |
| G25 | View-holder cannot delete grant | view-holder | 403 |
| G26 | Delete non-existent grant | owner | 404 |

#### Grant combines with org floor (effective = max)

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| B01 | Edit grant on No Access floor → Edit | floor=no_access, user grant=edit | `"edit"` |
| B02 | Edit grant on View floor → Edit | floor=view, user grant=edit | `"edit"` |
| B03 | View grant on No Access floor → View | floor=no_access, user grant=view | `"view"` |
| B04 | View grant on Edit floor → Edit (floor wins; max) | floor=edit, user grant=view | `"edit"` |
| B05 | Group grant with No Access floor → Edit | floor=no_access, group grant=edit | `"edit"` |
| B06 | User in two groups (Edit + View on same resource) → max = Edit | group1=edit, group2=view | `"edit"` |
| B07 | User has View grant; group has Edit grant → max = Edit | user grant=view, group grant=edit | `"edit"` |
| B08 | `get_user_access_map` batch result matches per-call results | 3 resources, mixed grants | map values == per-call values |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User types a colleague's name in the share modal chip input | Autocomplete suggestions appear; selecting one adds a chip |
| User selects permission level from the dropdown next to a chip before clicking Share | Picker shows View / Edit options; selection reflected on chip |
| User clicks Remove on a grant row in the share modal | Grant row disappears; grantee loses access immediately |
| User shares and then re-opens the share modal | Grant list refreshes and shows the new grantee |

---

## Story 3: Shared dashboard — inner charts/KPIs automatically accessible

**Journey:** Analyst shares a Dashboard at Edit with the Field Staff group; Field Staff members can immediately open the dashboard and see all inner charts in their `/charts` list with Edit access — no separate chart sharing needed; when the share is removed, chart access disappears too.

**Backend test files:** `test_access_control.py`, `test_access_api.py`

### Backend tests

#### Access engine — cascade resolution

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| C01 | Edit dashboard share → user gets Edit on inner chart | cascade child row: rtype=chart, level=edit | `get_user_access(user, "chart", C) == "edit"` |
| C02 | View dashboard share → chart appears as view-only | cascade child row: level=view | `"view"` |
| C04 | Cascade Edit + permissive floor → max applies | cascade=edit, floor=view | `"edit"` |
| C05 | No Access floor + dashboard share → chart visible via cascade | floor=no_access, cascade child=view | `"view"` |
| C06 | Dashboard share deleted → child rows auto-deleted → chart invisible | delete parent ResourceShare; floor=no_access | `None` |
| C07 | KPI inside dashboard → cascade works same as chart | child row rtype=kpi | `get_user_access(user, "kpi", K) == "edit"` |
| C08 | Group dashboard share → cascade for group → chart accessible | group grant on dashboard | group member gets chart access |
| C09 | `accessible_filter` with cascade grant includes the chart | cascade child row only, no direct chart grant | chart in queryset |

#### Cascade rows are materialized at write time

| ID | Scenario | Action | Expected |
|---|---|---|---|
| H01 | Dashboard share created → child rows for all inner charts/KPIs | POST share on dashboard with 2 charts + 1 KPI | 3 child ResourceShare rows (rtype=chart/kpi, parent_id=share.id) |
| H02 | Dashboard share level updated → all child rows updated | PATCH View→Edit on parent share | all child rows.access_level = edit |
| H03 | Dashboard share deleted → child rows auto-deleted | DELETE parent share | 0 child rows remain |
| H04 | Chart added to dashboard tabs → cascade row created per existing share | PATCH dashboard tabs to add chart; existing share present | 1 new child row |
| H05 | Chart removed from dashboard tabs → cascade rows deleted | PATCH dashboard tabs to remove chart | cascade row deleted |
| H06 | Chart removed from dashboard; direct grant exists → direct grant survives | direct chart grant + cascade; remove from tabs | user retains access via direct grant |
| G18 | PATCH dashboard share level → cascade children reflect new level | owner, parent share | all child rows.access_level updated |
| G23 | Delete dashboard share → inner chart cascade rows auto-deleted | owner | chart inaccessible (floor=no_access) |

#### Grants list shows cascade context

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| G12 | Cascade-only user shown with share_id=None + cascade_sources | owner | share_id=None, cascade_sources=[{dashboard_id, title}] |
| G13 | Direct grant + cascade on same chart → one merged row at max level | owner | share_id set, cascade_sources=[...], access_level=max |
| G14 | Chart in two dashboards, sharing same user → two cascade sources listed | owner | cascade_sources has two entries |

#### Blocking direct changes on cascade-derived access

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| Q13 | PATCH directly on a cascade row is rejected | Dashboard D1 has Charts A and B; User X has Edit on D1 (cascade → Edit rows on A and B, parent_id set); caller calls PATCH on Chart A's cascade row id | 400 — cascade rows are read-only; must change via parent dashboard share |

### Frontend behavior

| Scenario | Expected |
|---|---|
| After sharing a dashboard with a user, shared user opens /charts | Inner charts of that dashboard appear in the list with the same access level |
| Owner opens Chart A share modal; User X's Edit came only from Dashboard D1 (no direct chart grant) | User X appears in the list at Edit — dropdown looks normal, no visual indicator that access is cascade-derived |
| Owner tries to change User X's level on Chart A (cascade-only, share_id=None) | Frontend intercepts — no API call made; message shown: "Access on this chart is inherited from Dashboard X — go there to change it" |

---

## Story 4: Chart in multiple dashboards — effective access is the max

**Journey:** Chart C is inside Dashboard A (shared at Edit) and Dashboard B (shared at View); the user's effective access on Chart C is Edit; when the Edit share on Dashboard A is removed, access drops to View (from Dashboard B).

**Backend test files:** `test_access_control.py`, `test_access_api.py`

### Backend tests

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| C03 | Chart in two dashboards (Edit + View) → effective Edit | two child rows for same chart: edit and view | `"edit"` (max) |
| H07 | Chart in two dashboards; one dashboard share deleted → still accessible via second | two dashboard shares; DELETE one parent | cascade from second dashboard remains |
| G14 | Grants list shows two cascade sources for same user on same chart | chart in two dashboards, shared user | cascade_sources has two entries |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User has Edit via Dashboard A and View via Dashboard B on Chart C; opens /charts | Chart C appears with effective access Edit |

---

## Story 5: Member with No Access floor gets an explicit share

**Journey:** The org floor for Members is No Access; Admin shares one Dashboard with Priya (a Member) at View; Priya can see that dashboard and its inner charts; all other Members still see nothing.

**Backend test file:** `test_access_control.py`

### Backend tests

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| B01 | Edit grant on No Access floor → Edit | floor=no_access, user grant=edit | `"edit"` |
| B03 | View grant on No Access floor → View | floor=no_access, user grant=view | `"view"` |
| E01 | No floor, no grants, no ownership → empty queryset | — | no resources |
| E02 | No floor, one direct grant → only that resource visible | one user grant | only granted resource + its cascade children (inner charts/KPIs) |
| E03 | No floor, owns resource → own resource returned | user is created_by | own resource visible |
| E07 | No floor, cascade grant → cascade-granted chart returned | child row rtype=chart | chart in queryset |
| Q11 | `accessible_filter` handles created_by=None (legacy row) without error | — | no exception |

### Frontend behavior

| Scenario | Expected |
|---|---|
| Member with No Access floor and no shares opens any list page | Page shows empty state — no resources listed |
| After receiving a View share on one dashboard, Member opens list pages | Only that dashboard (and its inner charts) appear |

---

## Story 6: Make a resource private

**Journey:** Analyst marks a Dashboard as Private; the org floor is bypassed — even Analysts who would normally have Edit via the floor can no longer see it unless they have an explicit share or are the owner/Admin; if a public link was active it is disabled automatically.

**Backend test files:** `test_access_control.py`, `test_access_api.py`

### Backend tests

#### Private resource behavior in access engine

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| D01 | Private + View floor → invisible (floor bypassed) | is_private=True, floor=view, no grant | `None` |
| D02 | Private + Edit floor → invisible | is_private=True, floor=edit, no grant | `None` |
| D03 | Private + direct Edit grant → Edit (grant still applies) | is_private=True, user grant=edit | `"edit"` |
| D04 | Private + direct View grant → View | is_private=True, user grant=view | `"view"` |
| D05 | Private + cascade Edit grant → Edit | is_private=True, cascade child row=edit | `"edit"` |
| D06 | Private + owner → Edit | is_private=True, user is created_by | `"edit"` |
| D07 | Private + Admin → Edit | is_private=True, admin user | `"edit"` |
| D08 | `accessible_filter`: private + floor only → excluded from queryset | is_private=True, floor=view | resource absent |
| D09 | `accessible_filter`: private + direct grant → included | is_private=True, user grant=view | resource present |
| D10 | `accessible_filter`: private + cascade grant → included | is_private=True, cascade child row | resource present |
| D11 | `accessible_filter`: private + owner → included | is_private=True, user is created_by | resource present |
| D12 | `get_user_access_map`: private, no grant → None | is_private=True, no grant, floor=view | `map[resource.pk] == None` |

#### Private toggle API — `PATCH /api/access/{rtype}/{resource_id}/private`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| I01 | Owner sets is_private=True | owner | 200, model.is_private=True |
| I02 | Enabling Private when public link is active → public link cleared | owner, is_public=True | 200; is_private=True, is_public=False, token=None |
| I03 | Disabling Private does not restore public link | owner | 200, is_private=False; public link remains off |
| I04 | Edit-holder can toggle Private | edit-holder | 200 |
| I05 | View-holder cannot toggle Private | view-holder | 403 |
| I06 | No-access user cannot toggle Private | no-access | 403 |
| I07 | Resource belongs to different org | owner, cross-org id | 404 |
| I08 | Resource does not exist | owner | 404 |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User enables Private toggle in share modal | Private toggle turns on; public link toggle becomes hidden |

---

## Story 7: Share via public link (Dashboard or Report)

**Journey:** Analyst turns on the public link toggle on a Dashboard; anyone with the link — including external funders not on Dalgo — can view the dashboard without logging in; the Admin can disable all public links org-wide with one toggle.

**Backend test file:** `test_access_api.py`

### Backend tests

| ID | Scenario | Expected |
|---|---|---|
| O01 | Dashboard public link enabled (org allow=True) → anonymous GET returns 200 | 200 |
| O02 | Dashboard public link disabled (resource toggle=off) → anonymous GET returns 403 | 403 |
| O03 | Org toggle turned off → all existing public link URLs return 403 immediately | 403 |
| O04 | Org toggle turned back on → tokens still valid; links work again | 200 |
| O05 | Private=True with active public link → link cleared → anonymous 403 | 403 |
| O06 | Private=False after public link cleared → public link NOT restored | link remains off |
| O07 | Authenticated user opens public-link URL → normal permission resolution applies | not anonymous bypass |
| O08 | Attempt to enable public link on a Chart → endpoint does not exist | 404 |
| O09 | Enable public link when org disallows it (allow_public_sharing=False) | 400 |
| Q03 | Public dashboard anonymous viewer sees inner charts even if chart floor=no_access | inner charts render |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User enables public link toggle in share modal | Toggle turns on; copy-link button appears with the public URL |
| Anonymous user opens the public link URL | Dashboard page renders without a login prompt |

---

## Story 8: Transfer ownership of a resource

**Journey:** M&E Lead (owner) picks "Transfer Ownership" from the share modal dropdown next to a senior Analyst's name; confirms the dialog; the Analyst becomes owner and the M&E Lead's access reverts to her org floor (or any direct share she holds).

**Backend test file:** `test_access_api.py`

`POST /api/access/{rtype}/{resource_id}/transfer-ownership` — body `{"to_orguser_id": int}`

### Backend tests

| ID | Scenario | Actor → Recipient | Expected |
|---|---|---|---|
| K01 | Owner transfers to Analyst (Edit floor) | owner → analyst | 200; resource.created_by = analyst |
| K02 | Owner transfers to Member with direct Edit share | owner → member with edit grant | 200 |
| K03 | Owner transfers to Member with View share only | owner → member, grant=view | 400 |
| K04 | Owner transfers to Member with No Access floor, no grants | owner → plain member | 400 |
| K05 | Admin initiates transfer | admin → analyst | 200 |
| K06 | Edit-holder (non-owner, non-admin) tries to transfer | edit-holder | 403 |
| K07 | View-holder tries to transfer | view-holder | 403 |
| K08 | Transfer to self | owner → self | 200 (no-op) |
| K09 | Transfer to user in different org | owner → cross-org user | 400 |
| K10 | After transfer — old owner had no direct share → access reverts to floor | old owner, no direct share | effective access = floor level |
| K11 | After transfer — old owner had direct Edit share → retains Edit | old owner, direct edit share exists | `"edit"` |

### Frontend behavior

| Scenario | Expected |
|---|---|
| Owner or Admin opens permission dropdown next to a grantee in the share modal | "Transfer Ownership" option is present in the dropdown |
| Non-owner Edit-holder opens permission dropdown next to a grantee | "Transfer Ownership" option is not present |
| Owner selects "Transfer Ownership" and clicks confirm in the dialog | Ownership transfers; share modal updates to show the new owner |

---

## Story 9: Member requests access to a resource they can't see

**Journey:** A program officer opens a dashboard link, has no access, sees the request-access screen (which displays the owner's name so the officer knows who will receive the request), selects View, adds a note, and submits; the owner gets the request in the share modal and approves at View; the officer now has a direct share and can open the dashboard.

**Backend test file:** `test_access_api.py`

### Backend tests

#### Submitting a request — `POST /api/access/{rtype}/{resource_id}/request-access`

| ID | Scenario | Requester state | Expected |
|---|---|---|---|
| L01 | User with no access requests View | user cannot currently see the resource (no floor access, no explicit share) | 201 — request created |
| L02 | User with no access requests Edit | same as above, requests a higher permission level | 201 — request created |
| L03 | User already has access (via floor) → rejected | floor=view | 409 |
| L04 | Duplicate pending request → rejected | existing pending for same user + resource | 409 |
| L05 | Resource does not exist — no request screen shown | any user; resource_id is invalid | 404 (frontend shows not-found page, never the request-access screen) |
| L06 | Resource in different org | any user | 404 |

#### Owner views pending requests — `GET /api/access/{rtype}/{resource_id}/request-access`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| L07 | Owner lists pending requests | owner | 200, list returned |
| L08 | Edit-holder (non-owner) lists requests | edit-holder | 200 |
| L09 | View-holder cannot list requests | view-holder | 403 |
| L10 | No pending requests | owner | 200, empty list |

#### Owner responds — `POST /api/access/{rtype}/{resource_id}/request-access/{req_id}/respond`

| ID | Scenario | Actor | Expected |
|---|---|---|---|
| L11 | Owner approves at requested level | owner, decision=approved | 200; grant created at requested level; request.status=approved; requester notified via email + in-app notification |
| L12 | Owner approves but downgrades (Edit request → grants View) | owner | 200; grant at View |
| L13 | Owner declines | owner, decision=declined | 200; no grant; request.status=declined; requester notified via email + in-app notification |
| L14 | Non-Edit-holder tries to respond | view-holder | 403 |
| L15 | Respond to non-existent request | owner | 404 |
| L16 | Respond to already-decided request | owner, request already approved | 400 or 409 |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User with no access opens a resource URL | No-access screen shown; owner's name is displayed; "Request Access" button is visible |
| User clicks "Request Access" | Modal opens with a level picker (View / Edit) and a note text field |
| User submits the request form | Button changes to "Request sent" confirmation state; form is no longer submittable |
| Owner opens the share modal for that resource | "Access Requests" section is visible listing pending requests |

---

## Story 10: Invite an external user via the share modal

**Journey:** Analyst types xyz@funder.org in the share modal — not in the system; the modal flags it as external; on Share, an invite email goes out; the funder accepts, joins Dalgo as a Member, and immediately gains View on the dashboard and its inner charts.

**Backend test files:** `test_orguserfunctions.py`, `test_access_control.py`, `test_access_api.py`

### Backend tests

| ID | File | Scenario | Expected |
|---|---|---|---|
| M01 | `test_orguserfunctions.py` | Pending ResourceShare (invitation_id set) — user accepts invite | principal_type=user, principal_id=new_orguser.id, invitation=None |
| M02 | `test_orguserfunctions.py` | Pending OrgUserGroupMember (invitation_id set) — user accepts | orguser=new_orguser, invitation=None |
| M03 | `test_access_control.py` | After promotion — user has effective access to shared resource | `get_user_access` returns granted level |
| M04 | `test_access_api.py` | Invite not yet accepted — list_grants shows status=pending | row with status=pending visible |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User types an email not in the system into the share modal chip input | Modal flags the chip as external / pending invite |
| User clicks Share with an external email chip | Invite email is sent; grants list shows that entry with status "pending" |

---

## Story 11: Downgrading Edit on a dashboard — cascade removal warning

**Journey:** Analyst removes or downgrades Edit on a dashboard share; the share modal shows a static generic confirmation before applying — no API call, no per-chart computation.

No backend tests. Frontend behavior only:

### Frontend behavior

| Scenario | Expected |
|---|---|
| User removes Edit share on a dashboard | Confirmation dialog shown: *"Removing or downgrading access on this dashboard will also affect access on its inner charts and KPIs. Continue?"* |
| User downgrades Edit → View on a dashboard share | Same dialog shown |
| User removes a View share on a dashboard | Same dialog shown (any removal or downgrade on a dashboard triggers the warning) |
| User confirms dialog | Change applied |
| User cancels dialog | No change applied |

---

## Story 12: Group management and group-derived access

**Journey:** Analyst creates "Field Staff" group, adds 8 members, shares a Dashboard with the group at Edit; all 8 members get Edit immediately; adding or removing a member from the group changes their access without touching the share.

**Backend test files:** `test_access_control.py`, `test_access_api.py`

### Backend tests

#### Group grants and effective access

| ID | Scenario | Setup | Expected |
|---|---|---|---|
| B05 | User in group with Edit grant + No Access floor → Edit | floor=no_access, group grant=edit | `"edit"` |
| B06 | User in two groups (Edit + View on same resource) → max | group1=edit, group2=view | `"edit"` |
| C08 | Group dashboard share → cascade for group → chart accessible for group members | group grant on dashboard | group member gets chart access |
| G03 | Owner adds grant for a group | owner | 201, principal_type=group |

#### Group management authorization

| ID | Scenario | Expected |
|---|---|---|
| Q06 | Member cannot create a group | 403 on group create endpoint |
| Q07 | Non-creator/non-Admin Analyst cannot edit another Analyst's group | 403 |
| Q08 | Group visibility by role — Analyst sees own + member-of groups; Member sees only their own | list filtered per spec |

### Frontend behavior

| Scenario | Expected |
|---|---|
| Analyst opens group management UI | Create / edit / delete dialogs are accessible |
| Member opens group management UI | Create group option is not present |

---

## Story 13: Bulk share from resource lists

**Journey:** Analyst selects 5 dashboards in the list, clicks "Share", adds the Field Staff group at View; 3 dashboards where the Analyst has Edit get shared; 2 are skipped with a count shown: "Shared 3 of 5 — 2 skipped: you don't have Edit on those."

**Backend test file:** `test_access_api.py`

### Backend tests

| ID | Scenario | Expected |
|---|---|---|
| Q09 | Actor has Edit on 3 of 5 selected resources → 3 succeed, 2 skipped; response includes skip count | 3 grants created; skip count = 2 |

### Frontend behavior

| Scenario | Expected |
|---|---|
| User selects multiple resources in a list page and clicks Share | Share modal opens pre-loaded with the selected resources |
| Bulk share completes with some resources skipped | Result banner shows "Shared X of Y — Z skipped: you don't have Edit on those" |

---

## Story 14: Resource or group deleted — orphan cleanup

**Journey:** Analyst deletes a Dashboard; all ResourceShare rows, AccessRequest rows, and cascade child rows for that dashboard are removed automatically; no orphaned grants remain in the database.

**Backend test file:** `test_access_api.py`

### Backend tests

| ID | Scenario | Expected |
|---|---|---|
| N01 | Dashboard deleted → all ResourceShare rows for that dashboard deleted | no orphan rows |
| N02 | Chart deleted → all ResourceShare rows for that chart deleted | no orphan rows |
| N03 | Report deleted → ResourceShare rows + AccessRequest rows deleted | no orphan rows |
| N04 | KPI deleted → ResourceShare rows deleted | no orphan rows |
| N05 | Group deleted → ResourceShare rows where principal_type=group deleted | no orphan rows |
| N06 | Group member removed → member loses group-derived access on next call | `get_user_access` returns floor, not group level |

---

## Story 15: Comments on Reports

**Journey:** Priya has View on a Report; she reads and adds comments; the report owner (Edit-holder) can delete or hide any comment for moderation; anonymous public-link viewers cannot comment.

**Backend test file:** `test_access_api.py`

### Backend tests

| ID | Scenario | Expected |
|---|---|---|
| P01 | View-holder adds comment on Report | 201 |
| P02 | View-holder reads comments | 200 |
| P03 | Edit-holder deletes another user's comment (moderation) | 200 |
| P04 | View-holder cannot delete another user's comment | 403 |
| P05 | Public-link (anonymous) viewer tries to comment | 401/403 |
| P06 | No-access user tries to read or write comments | 403 |

### Frontend behavior

| Scenario | Expected |
|---|---|
| View-holder opens a Report | Comment box is visible and submittable |
| Anonymous user opens Report via public link | Comment box is absent |

---

## Story 16: Edge cases and explicit rule enforcement

**Journey:** Targeted tests for spec rules that could easily be missed or misimplemented.

**Backend test files:** `test_access_control.py`, `test_access_api.py`

### Backend tests

| ID | Rule | Scenario | Expected |
|---|---|---|---|
| Q01 | Edit cascade does not confer delete | Cascade-Edit user calls DELETE on chart | 403 (only owner/Admin can delete) |
| Q02 | Derived Edit (cascade only) confers re-share rights | Cascade-Edit user calls POST grants on chart | 201 |
| E04 | Floor=View → all non-private resources returned | multiple resources, none private | all returned |
| E05 | Floor=View, one private → private excluded | one resource is_private=True | private excluded |
| E06 | Admin → all resources returned including private | admin user | all returned |
| Q11 | `accessible_filter` handles created_by=None (legacy row) without error | — | no exception |

### Frontend behavior

| Scenario | Expected |
|---|---|
| Owner opens Chart A share modal, sees User X at Edit (cascade-only, share_id=None), tries to change to View | No API call; message shown naming the source dashboard(s): "Access is inherited from Dashboard X — go there to change it" |
| User X has direct View on Chart A + inherited Edit from Dashboard D1 (effective=Edit, share_id set, cascade_sources=[D1]); owner tries to change to View | Blocked — cascade from D1 is still at Edit so downgrading the direct grant wouldn't lower the effective level; message: "User X also has Edit via Dashboard D1 — go there to change it first" |
