# Design Review — Resource Sharing v1.2 "Capability Actions" (Layer 3b)

Reviewed: `features/access-control/resourcesharing/v1.2/plan.md` (§1, §2, §4, §9) against
the as-built code on `.dalgo-worktrees/resource-sharing/DDP_backend` and the parent plan
§9/§10 and the 2026-07-20 architecture review (H2, M5). All code claims below were
verified by reading the actual files, not the plan's description of them.

## Verdict

**The design is sound and I would build it — but the plan's sweep inventory is
incomplete relative to its own success criterion, and two of its selling points
("one lookup answers what can X do", "new level = one row") are oversold.** The core
moves are right at this scale: verbs not verb×rtype atoms, meaning in code / facts in
DB, resolver untouched, containment instead of rank integers, behavior-preserving
M1–M3 with a golden-matrix pin, M4 as a separate product-gated PR. The A-vs-B
comparison in §1 is honest and its two decisive rows (atom meaning, add-rtype cost)
are genuinely decisive. What needs fixing before execution is bookkeeping, not
architecture: five level-comparison sites the blast radius misses (one of which —
comment moderation — has no verb in the 7-verb vocabulary), an overclaimed §2.5
sentence about Member owners, and three hidden sequencing couplings with the
architecture-review fixes that the plan declares independent.

Ground-truthing results, for the record:

| plan claim | verdict |
|---|---|
| ~15 scattered comparison sites | **Confirmed** (~15–16: gates ×3, resolver cap, coverage:129, sharing_actions 352/386/539/960, access_requests:325, comment_service:302, access_api:228, 4 member write-blocks) |
| gates already rtype-generic | **Confirmed** (`gates.py` takes `rtype`, `_NOUN_BY_RTYPE`) |
| Member grant-cap buried in resolver | **Confirmed** (`access_resolver.py:174-175`) |
| `PERMISSION_RANK` used for re-share cap ×2 in sharing_actions | **Confirmed** (386, 960) — **but a third external site exists**: `access_requests.py:325` |
| slug AND capability composition at endpoints | **Confirmed** (`@has_permission` decorator + gate calls; e.g. `dashboard_native_api.py`) |
| Members lack `can_edit_*`/`can_share_*`/`can_delete_*` slugs | **Confirmed** (seeds 001–003) — this matters more than the plan admits, see F2/F9 |

---

## Findings (ranked)

### HIGH

**F1. The blast radius contradicts the plan's own invariant grep — five straggler
sites, one with no verb to map to.**
§8 says: after M3, `grep -rn '== "edit"\|PERMISSION_RANK'` outside the resolver must
return zero, enforced by an invariant test. But §3's blast radius declares
`access_requests.py` ("no change — levels pass through as data") and `coverage.py`
("no change") untouched, and never mentions `access_api.py` or
`core/reports/comment_service.py` at all. The grep as written will hit:

- `access_requests.py:325` — `PERMISSION_RANK` compares granted-vs-requested level in
  `approve_access_request` (the downgrade-only rule). This is exactly the ordering
  math M3 claims to kill; under the design it should become containment
  (`grantable ⊆ requested`'s action-set), or be documented as a sanctioned exception.
- `access_api.py:228` — bulk share eligibility does a raw
  `effective_permission(...) != "edit"`. This is a RESHARE check living outside the
  gates; it must become `can(..., RESHARE)` or it's a second source of meaning.
- `comment_service.py:302` — comment moderation on report snapshots is
  `effective_permission(...) == "edit"`. **There is no COMMENT/MODERATE verb among the
  7.** The sweep will force a silent policy decision ("moderators must hold MODIFY"?)
  that the plan never surfaces. Either map it to MODIFY explicitly and say so, or add
  a verb — but decide it in the plan, not mid-sweep.
- `sharing_actions.py:539` — extend-charts requires `== "edit"` per chart (this is a
  MODIFY? RESHARE? judgment call — extending is granting on the chart, so arguably
  RESHARE) and `:352` builds a permission label string.
- `coverage.py:129` — `permission == "edit"` on raw grant rows feeding
  `viewer_can_edit`. Reading a grant-row *fact* is arguably fine (it's not
  interpreting a level's meaning), but the grep can't tell the difference; the "add
  one comment" mitigation in §3 won't make the invariant test pass.

*Fix:* before M2, produce the complete site inventory with a per-site verb decision
(including the comment-moderation verb), update §3, and either scope the grep to
exclude sanctioned fact-reads or convert them. This is a half-day of work that
prevents the exact "two sources of meaning" failure the plan exists to end.

### MEDIUM

**F2. `effective_capabilities()` is Layer-3 truth, not whole-system truth — and §2.5
overclaims for Member owners.**
Worked example 1 sells the dictionary as "the answer is one lookup, for support staff
too". It isn't: the real answer is always slug AND capability. Verified against seeds:
Members hold no `can_edit_*`, `can_delete_*`, or `can_share_*` slugs, so a Member
owner's `OWNER_EXTRA` DELETE and TRANSFER capabilities are **dead at every slug-gated
door** — §2.5's "a Member owner without the slug still governs their own resource" is
true only for DECIDE_REQUESTS (the single OR-composed row) — not for delete or
transfer. A support engineer reading only the dictionary will give wrong answers for
Members. "What can X do" is now level AND role AND ownership AND slug — the dictionary
makes three of those legible and is silent about the fourth.
*Fix:* correct the §2.5 sentence; state in `capabilities.py`'s docstring that its
output is the Layer-3 half of an AND; optionally add a debug/introspection helper that
intersects with the viewer's slugs for support use. Do not try to fold slugs into the
dictionary — the separation itself is right (see Keep list).

**F3. "New level = one row" is marketing.**
A real `view_no_export` level touches: the dictionary row, the `AccessLevel`/
`GeneralLevel` model enums (write-path validation — `access_requests.py:323` checks
`GeneralLevel.values`), API schema, the share-modal dropdown and webapp `level ===`
mirrors, `grantable_levels` ordering, and docs. Still enormously better than a
15-site audit — the *gates* genuinely don't change, which is the point — but the plan
should ship the honest "new level checklist" so the first person to add one doesn't
discover the enum skew in production (a level in the dict but not the enum is
unwritable; in the enum but not the dict is a stored word that 500s every gate via
KeyError — the worst skew, because it passes write validation and fails at read time).

**F4. The golden matrix protects the dictionary, not the pairing.**
The matrix (role × level × action) will catch policy edits and the M4 diff — real
value, especially as the M4 review artifact. It structurally **cannot** catch the two
likelier drift modes: (a) an endpoint gating with the wrong verb (export endpoint
checking READ instead of EXPORT — invariant test only checks "every Action referenced
by ≥1 gate", i.e. existence, not correct pairing), and (b) rtype-conditional behavior
that lives in the resolver outside the matrix (`member_sharing=False` exclusion,
chart inline-render exception). The §2.5 pairing table is prose; nothing enforces it.
*Fix:* keep the matrix; check the pairing table in as a reviewed doc; rely on the
existing per-endpoint gate tests (which the no-rewrite rule in §6 already pins) as the
pairing enforcement, and say so explicitly. Accept the residual risk — at 6 rtypes ×
~7 endpoint classes this is reviewable by eye.

**F5. "Nothing here blocks or is blocked by" the review fixes — not quite. Three
hidden orderings.**
(a) The tier-2 naming sweep (`ResourceShare`→`ResourceGrant`, `.permission`→`.level`,
edit-migrations-in-place) must land **before** the review's H1 unique-constraint
migration — otherwise the constraint is written against the old names and the rename
window (§9.4) effectively closes, or churns. (b) M1's golden baseline is "the matrix
generated on the pre-refactor code" — if anyone fixes H2 independently while v1.2 is
in flight (it's #2 on the review's priority list), the baseline moves under M1–M3 and
the zero-diff contract breaks. The plan implicitly assumes an H2 freeze but never
states it. (c) M4 and the review's H3 fix (request-flow Member bypass on metric/kpi)
edit the same member-block sites in `sharing_actions.py`/`access_requests.py`; H3 is
*not* fixed by M4 (MEMBER_NEVER subtracts MODIFY/RESHARE; H3 is about READ grants
arriving through the side door). Do them in one coordinated pass or accept conflicts.
*Fix:* one paragraph in §7 declaring: naming sweep → H1 constraints → v1.2 M1–M3 →
M4+H2+H3 as one product conversation. Costs nothing, prevents the plan's
"independence" claim from being read as license to parallelize the wrong things.

### LOW

**F6. KeyError-as-500 is a defensible fail-closed, but be loud on purpose.**
An unknown stored level 500s *every* gate on that resource, including view — a
resource-bricking failure mode. Since write paths validate against the enum, garbage
requires DB tampering or the F3 enum-skew; low probability. Prefer an explicit
`raise LookupError(f"unknown access level {level!r} — LEVEL_CAPABILITIES and the
Level enum have diverged")` over a bare `[level]` so the on-call engineer gets the
diagnosis in the traceback. Do not silently deny — that hides the data bug. The
frozenset concern is a non-issue: `caps |= OWNER_EXTRA` rebinds (frozensets are
immutable); the pseudocode in §4.1 is safe as written.

**F7. Don't mint a fourth ownership implementation.**
There are already three: `access_resolver._is_owner`, `ownership.is_owner`, and
`ownership.can_delete_resource` (documented mirrors). `effective_capabilities`'s
`is_owner_or_admin` must be composed from `ownership.py`'s helpers, not re-derived.
Also note ownership is now computed twice per request (resolver step 2, then the
capability layer) — it's attribute reads, zero queries, fine — but it's the strongest
argument O4 (below) has; worth one code comment acknowledging the duplication is
deliberate.

**F8. DECIDE_REQUESTS (and TRANSFER, DELETE) never vary by level — the dictionary
hosts three constants.** As verbs they buy: a name, a test row, the Member-owner OR
door, and the option to someday put DELETE into "edit". That's enough to keep them —
7 verbs is not too many — but recognize DECIDE_REQUESTS is really an ownership
prerogative wearing an action costume, and the request-approval endpoint's
slug-OR-owner composition is the single irregularity in the otherwise-uniform AND
table. It predates this plan (as-built §9.5 behavior); document it as deliberate
rather than letting it look like an accident.

**F9. M4's real blast radius is smaller than its framing — use that.**
Because Members already lack every `can_edit_*`/`can_share_*` slug, MEMBER_NEVER
changes almost no door outcomes: a floor-edit Member already can't reach PUT
endpoints. M4's user-visible effect is *truth-in-UI and truth-in-email* — the share
modal stops displaying Member "Edit" grants the resolver never honors, and the
approval notification stops promising edit that never arrives (the H2 laundering).
Present it to product that way: "we're making the UI stop lying", not "we're removing
Member edit" — the sign-off gets easier and the prod-data query (§8's mitigation,
keep it) covers the residual risk of an org actually leaning on `member_level=edit`
via some non-slug-gated surface (comment moderation is one such surface — F1's verb
decision interacts here). Bundling M4 into this plan is **correct**: the dictionary
is precisely the mechanism that makes the H2 fix a one-line visible subtraction
instead of four scattered clamps, and the M4-as-separate-PR + matrix-diff-as-review
structure is the right containment. The sign-off gate is sufficient.

---

## The options, honestly priced at 20-NGO / 3-role / 2-level scale

| # | option | cost | what it buys here | when it becomes the right answer |
|---|---|---|---|---|
| O1 | Do nothing — keep string comparisons, fix H2 with 4 write-site clamps | ~1 day (the clamps) | Stops the shipped lie; zero refactor risk | If sharing were *done* — no third level, no new rtypes, team fully loaded elsewhere. The roadmap (v1.1→v1.2 cadence, the PII "view-no-export" ask, a Forms rtype) says it isn't. |
| O2 | The planned code dictionary (this plan) | ~1–2 wks incl. tests; +½ day for F1's inventory | One written meaning; H2-class bugs become structurally impossible; third level ≈ cheap; policy changes are reviewable diffs; zero schema/query/UX cost | **Now** — the moment a third level or continued Layer-3 evolution is plausible, which it demonstrably is. |
| O3 | DB-stored level→action bundles | O2 + tables, seeds, migration, cache invalidation, per-org divergence support burden | Per-org custom levels — which nobody has asked for | When an NGO actually demands a custom level. The plan's documented exit (dict → loader behind unchanged `can()`) reaches this from O2 without prepaying. Correctly rejected. |
| O4 | Resolver returns capability sets directly (collapse 3a/3b) | ≈ O2 effort, but touches resolver + every caller + API shape | Removes the level indirection and the double ownership check (F7) | Never cleanly: levels are *stored facts* (grants, floors) and *API-visible words* — the resolver's level output feeds `accessible_filter` SQL and webapp responses. Collapsing forces level words back out at every edge anyway and violates "resolver untouched", the plan's cheapest safety property. O4 is O2 with worse seams. |
| O5 | Policy engine (oso / casbin / OPA) | Weeks; a DSL nobody else on a small team reads; ops surface; opaque denials for non-technical users | Expressiveness this product has no use for — 3 fixed roles, 2 levels, 7 verbs fit in 20 lines | At orders of magnitude more tenants with per-customer contractual policies. The review already said "not Zanzibar"; same verdict, same reason. |
| O6 | Minimal: centralize constants + Level enum + H2 clamps, no `can()` rewiring | ~2 days | The documentation win, typo-proofing, the H2 fix | If team bandwidth collapses mid-quarter. But it leaves meaning *enforcement* scattered — the next H2 is still possible, the third level is still surgery. It's the fallback, not the plan. |

**Recommendation: O2, amended.** Execute this plan after (a) completing F1's site
inventory with per-site verb decisions (especially comment moderation), (b) fixing
the §2.5 Member-owner sentence and the "one lookup" framing (F2), and (c) writing the
F5 sequencing paragraph. Reasoning: the marginal cost of O2 over the O6 fallback is
roughly a week, and it buys the only property that compounds — *one place where
"edit" means something* — right before the two events that will test it (the M4
policy change and the PII third-level ask). Every heavier option (O3, O5) prepays for
scale this product may never see and is reachable later from O2; every lighter option
(O1, O6) leaves the H2 bug-class alive. The plan's own A-vs-B analysis already did
the hard thinking correctly; this review mostly tightens its edges.

---

## Keep list — do not second-guess these

- **Verbs as atoms, not Layer-2 slugs (design B).** The two decisive arguments hold
  under scrutiny: slug-atoms genuinely lie about scope inside a one-resource grant,
  and rtype-as-parameter makes new resource types free. The comparison table is fair
  to design A.
- **Resolver untouched, dictionary layered on top.** The as-built system's
  load-bearing property (one resolver, verified by the prior review) survives intact;
  M1–M3 risk is bounded by it.
- **Meaning in code, facts in DB.** Grants keep storing one word; policy ships with
  deploys, unit-testable, zero queries, use-time interpretation (§2.4's "meaning
  borrowed at use time" — a real win: policy changes retro-apply with no row
  migrations).
- **Containment replacing PERMISSION_RANK.** Set-inclusion is the correct ordering
  for capability bundles and slots future levels with no rank arithmetic.
- **The behavior-preservation contract** — M1–M3 observationally identical *including
  today's incoherences*, no test rewrites allowed, byte-identical 403 strings. This is
  the discipline that makes a security-surface refactor shippable.
- **M4 as its own PR with the matrix diff as the review centerpiece**, gated on
  explicit product sign-off, with the prod-data query first.
- **Owner as capability-addition, not a third level.** The resolver's binary output is
  API-visible; an "owner" level would leak into responses and grant rows can't store
  it. Addition with the Member-exemption ordering (`if owner … elif member`) is
  correct.
- **The naming law (§9) and the tier-2 rename window.** `effective_permission()`
  returning a level is a genuine standing lie; `resource_share.permission` likewise.
  Doing the schema rename only while migrations are prod-unseen is the right
  cost call — but it forces F5(a)'s ordering, so treat the window as closing.
- **Not building O3/O5.** Documented exits instead of prepaid generality.
