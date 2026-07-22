# Platform Admin Portal — v1.1 (Domain-based entry)

**Parent:** `features/admin-portal/v1/spec.md` · **Status:** Draft
**Date:** 2026-07-21 · **Owner:** Veekshitha Nelluru (DMP 2026) · Issue #1254

> **What this is.** A change to **where the admin portal lives and how a Super Admin gets in** — moving it from `/admin` inside the NGO app onto its own hostname, `insights.dalgo.org`, with its own login. Nothing the portal *does* changes; v1's four features, screens, and endpoints are untouched.

---

## Scope

**In:** the portal's hostname; how a Super Admin arrives; removal of the in-app entry point; authenticating at the admin domain.

**Out:** everything the portal does (v1); any change to `@platform_admin_required` semantics or the org/user features.

---

## Problem

v1 put the portal at `/admin` inside the org-scoped NGO app, entered by a sidebar link. Team feedback: the Dalgo-ops surface should not be a route nested inside the customer-facing product. It should be a separate address, and entering it should be a deliberate act — not a side effect of already being signed into the NGO app.

---

## User Flow — enter the portal (v1.1)

```
Super Admin goes to insights.dalgo.org
  -> signs in at that domain
       (same credentials, same backend, same is_platform_admin check —
        a separate session from the NGO app, not a carried-over one)
  -> lands on /admin, admin sidebar (Home, Organizations, Notifications, Feature Flags)
  -> "Open Dalgo app" returns them to app.dalgo.org when they also work in an org
```

**Denied path:** a non–Super Admin who reaches insights is bounced to the app host in the UI and refused by the server with 403 on every `/api/v1/admin/*` call.

**Removed:** the "Admin Portal" sidebar link in the NGO app, and `/admin` on the app host (redirects to insights).

---

## Access model

| Layer | Where | Behavior |
|---|---|---|
| **Separate authentication** | insights.dalgo.org | The Super Admin signs in at this domain. The NGO-app session does not grant entry. |
| **AdminGuard** | Front end, all `/admin/*` | Checks `is_platform_admin`; bounces non-admins to the app host. UX only. |
| **API check** | Back end, every admin request | `@platform_admin_required` → 403. **Unchanged from v1 and still the only real wall.** |

> **The rule:** the domain split is topology, not authorization. A hostname is not an access check.
> **Why it matters:** the separate login must be enforced by the backend to mean anything. See plan §3.4 and §8 Q6 — the mechanism is not yet decided, and until it is, insights is exactly as protected as v1's `/admin`, no more.

---

## Acceptance criteria

- [ ] `insights.dalgo.org` serves the admin portal; `/` there resolves to `/admin`.
- [ ] A Super Admin with a live NGO-app session in the same browser is **still asked to sign in** at insights — no silent carry-over.
- [ ] Signing in at insights uses the same credentials and the same `is_platform_admin` check.
- [ ] The NGO app no longer shows an "Admin Portal" link; `/admin` on the app host redirects to insights.
- [ ] A dual-role admin can return to the NGO app via "Open Dalgo app" with org context intact.
- [ ] A non-admin reaching insights is bounced in the UI and 403'd by the server.
- [ ] Local/single-host development is unaffected (env unset ⇒ v1 behavior).

---

## Open

The enforcement mechanism for the separate login is unresolved — plan §8 Q6. It requires backend work; this is a **new requirement**, not a fix, since the session currently carries over by design (research §4).
