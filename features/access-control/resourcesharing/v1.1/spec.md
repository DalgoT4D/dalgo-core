# Chart, KPI & Metric Sharing — v1.1 (Q0 partial reversal + grants for KPI/Metric)

**Status**: Draft — decided by Siddhant on 2026-07-16: *"we want chart to be independently shareable… it should follow this spec"*, then extended same day: *"we also need to share resource for chart, kpi and metrics similarly"*. Both reference the original Resource Sharing v1 draft (2026-06-17, pre-Q0).
**Parent feature**: `features/access-control/resourcesharing/` (shipped through the per-role permission model, 2026-07-16).

**Scope note (KPI/Metric):** this reverses the recorded "Metric/KPI: General-access only (no share modal)" decision. KPIs and Metrics are ALREADY registered shareable rtypes with working General access, list scoping, and request-access — only `grants=False` blocks direct shares. Enabling them is a registry flip + validation + UI mounting, far smaller than the chart work: no new columns, no migration, no inheritance/warning machinery (nothing embeds a KPI/metric — references never grant access, unchanged).

---

## 1. What changes

**Amendment Q0 (2026-07-07) decision #1 is REVERSED.** Charts stop "riding" their dashboards and become a first-class shareable resource, per the original spec's Flows 1, 3, and 5:

- Charts get **General access** (their own floor) and **direct shares** (users/groups, View/Edit), a share modal, request-access, list badges, and bulk actions.
- The **embed-time warning** returns (original Flow 3): embedding a chart whose audience doesn't cover the container warns; "extend" requires Edit on the chart; Cancel aborts. An embedder with only View can't close the gap — prompted to request Edit or ask the owner.
- The **dashboard-broadening warning** returns (original Flow 1): widening a dashboard's audience past its inner charts lists the affected charts **by name**, default button **Cancel**, extend-all or cancel (no per-chart picker).
- **Bulk** actions get the **one aggregated broadening prompt** across a selection (original Flow 5).
- **No locked tiles, ever** (original spec rule) — see §3 for how this is guaranteed.
- The two archived Figma frames (`Analyst-warning on adding charts.jpg`, `resource sharing- warning modal.jpg`) are UN-archived — they are the design reference for the two warnings. (Reverses decision D4.)

## 2. What does NOT change (Q0 decisions #2–#4 and later decisions stand)

| Kept rule | Why |
|---|---|
| **"General access", not "floor"** (Q0 #2) | shipped vocabulary, UI + API + code |
| **Member hard-capped at View** (Q0 #3) | the pasted original spec predates this; the amended rule won and is enforced everywhere. A Member never holds Edit on a chart either. |
| **Public global = kill switch** (Q0 #4) | shipped and tested |
| **Public links: Dashboards + Reports only** | charts do NOT get public links (assumption — flag to Siddhant; one-line change to reverse) |
| **Per-role General access (D1)** | the original spec's audience×permission picker no longer exists anywhere. Chart floors use the same per-role rows as every other resource: Analysts ∈ {No access, Can View, Can Edit}, Members ∈ {No access, Can View} (Member cap). Mapping from the old vocabulary: Private ≈ (none, none); Admins only ≈ (none, none) + admin governance; Analysts+ ≈ (level, none); All users ≈ (level, level). |
| **Metric/KPI individual sharing deferred** | the original spec defers it too. (Separate known hole: no UI exists to change a metric/KPI's General access post-creation — tracked as a follow-up, not part of this scope.) |

## 3. The inheritance model (how "no locked tiles" and chart privacy coexist)

**The rule:** a chart renders **inline** wherever its containing dashboard/report renders (as today — container view = inline content, no standalone access). The chart's own General access + grants govern **standalone** access: the Charts workshop list, the chart page/editor, and chart pickers.

**Example:** Priya sets the "Salary Breakdown" chart to Private (Analysts: No access, Members: No access). Other analysts no longer see it in the Charts list or the add-chart picker. It still renders inside the one HR dashboard it was already on — which is exactly why the warnings exist:

**The guardrails keep the two layers honest:**
- Embedding a private/narrow chart into a wider dashboard fires the **embed warning** ("this will expose Salary Breakdown to everyone who can see this dashboard — extend its access / cancel"). Extend raises the chart's levels/grants to cover the dashboard; it requires Edit on the chart.
- Widening a dashboard (raising its General access, adding grants, or enabling its public link) past any inner chart fires the **broadening warning**, naming the charts.
- **Why it matters:** without the warnings, "Private" would silently leak through embeds; without inline rendering, viewers would hit locked tiles. With both, a chart's stated audience and its real exposure only diverge after an explicit, named, Cancel-default confirmation.

## 4. Migration & defaults (behavior-preserving)

- **Existing charts** seed at `analyst_level=edit, member_level=none` — exactly today's effective behavior (all analysts see/edit all charts; members see them only inside shared containers). Nothing changes for anyone on migration day.
- **New charts** seed from the org defaults (Roles tab), like every other resource.
- **Chart editing** becomes resolver-gated (effective Edit on that chart) in addition to the existing `can_edit_charts` role slug — today's org-wide analyst editing continues because of the seed above, and narrows only when someone deliberately narrows a chart.
- Chart ownership: `created_by` = owner (transferable, same as other resources) — routes request-access approvals.

## 5. Out of scope (unchanged deferrals)

Everything the original spec defers: RLS/column masking, share-sprawl audit UI ("who can see this via what path"), audit log, expiring access, data-infrastructure sharing, restricted groups, custom roles, cross-org sharing, comments beyond Reports. The known v1 limitation stands: an editor with warehouse access can rebuild a Private chart's data — communicate honestly, not a bug.

## 6. Decisions (confirmed by Siddhant, 2026-07-16)

1. **No public links for charts** — Dashboards + Reports keep that exclusively. A chart is still publicly visible *inline* when its dashboard has a public link.
2. **Member chart grants are DEFERRED** — v1.1 chart sharing is Analyst/Admin-only. Granting a chart to a Member (directly, via a group, or via a Member-role email invite) is blocked with a clear message; `member_level` on charts is pinned to `none`. Members keep seeing charts inline inside shared dashboards/reports — unchanged.
3. **Existing charts migrate to `analyst_level=edit, member_level=none`** — behavior-preserving: nothing changes for anyone on migration day.

## 6b. KPI & Metric sharing (added 2026-07-16)

**The rule:** KPIs and Metrics become grant-capable exactly like dashboards — share modal on their pages/lists, direct user/group grants at View/Edit, email invites, request-access (already working) — under the same v1.1 consistency decisions:
- **Member grants deferred** (same as charts): grants are Analyst/Admin-only in v1.1; Members keep seeing KPIs/metrics via general access and inside shared dashboards. One consistent rule across all three new rtypes.
- **No public links** (their registry already says `public_link=False` — unchanged).
- **Owner-routed requests** already work (the approve path has always written metric/KPI grants — the resolver honors them today).

**Example:** Sarah (Admin) opens the "Monthly Beneficiaries" KPI and shares it with Priya (Analyst) at Edit — Priya can now retune the KPI without Sarah raising `analyst_level` for every analyst in the org.

**Why it matters:** today the ONLY way an individual gets a metric/KPI is to stumble on it, hit the request screen, and wait — admins cannot proactively share the org's core numbers.

**Also fixes an existing hole:** per-resource General access on KPIs/metrics currently has NO UI anywhere (set at creation, changeable only by API). v1.1 adds the multi-select bulk bar (share + General access) to the KPI and Metric list pages — same component the dashboards/reports/alerts lists use — giving it the same bulk/API-only home it has everywhere else after the modal's General-access removal.

## 7. Security findings folded into this work (from the v1.1 research)

- **Public chart leak (fix ships first, independently):** the public dashboard chart endpoints (`public_api.py:191,256`) check org but never that the chart is a tile on that public dashboard — any public link exposes every chart in the org anonymously. Milestone 0 closes this regardless of the rest.
- **Chart list is org-wide today:** `list_charts` has no per-resource scoping — per-chart privacy requires scoping it through the resolver (Milestone 1).
