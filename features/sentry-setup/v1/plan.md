# Sentry Setup v1 — Implementation Plan

**Status:** Draft v1
**Date:** 2026-05-08
**Spec:** [sentry_setup_plan.md](../../../dalgo-ai-gen/dalgo_mds/claude/planning/sentry_setup_plan.md)
**Research:** [research.md](./research.md)
**Domain map:** [docs/domain-map.md](../../../docs/domain-map.md)
**Branch:** `setup-sentry-tracking` (PR #258 in DalgoT4D/webapp_v2)

---

## 1. Overview

Harden the existing Sentry error-tracking setup in webapp_v2 by reducing quota waste, filtering noise, protecting against SSR crashes, enabling source-map uploads in CI/CD, and adding privacy safeguards for NGO user data. The Sentry SDK (v8.55.0) and core integration files already exist on branch `setup-sentry-tracking`; this plan covers configuration improvements only — no new dependencies or architectural changes.

**Services affected:**
- **webapp_v2** — All changes are in this repo (Sentry config files, Next.js config, env documentation)

**Not affected:** DDP_backend, prefect-proxy, dalgo-ai-gen

---

## 2. Blast Radius

Per `docs/domain-map.md`, section "What is intentionally NOT in this map":

> "Infrastructure (Redis, Postgres-for-app-state, S3) — belongs in architecture docs, not product impact analysis."

Sentry error tracking is infrastructure plumbing. It does not touch any product entities (Chart, Metric, KPI, Dashboard, ReportSnapshot, Pipeline, etc.). No domain-map traversal is required.

| Surface | Hop | Why affected | Status | Notes |
|---------|-----|-------------|--------|-------|
| *(none)* | — | Sentry is infrastructure, not a product entity | N/A | Per domain-map.md: infrastructure belongs in architecture docs, not product impact analysis |

**Confirmed:** No product entities are affected. No downstream surfaces are impacted. No user-facing behavior changes (error tracking is invisible to users). The only observable effect is improved error reports in the Sentry dashboard for the engineering team.

---

## 3. High-Level Design (HLD)

### 3.1 System Architecture: Sentry in Next.js

Sentry operates across three independent runtimes in the Next.js architecture. Each runtime has its own config file:

```
┌────────────────────────────────────────────────────────────────┐
│                         webapp_v2                              │
│                                                                │
│  ┌──────────────────┐  ┌───────────────────┐  ┌─────────────┐ │
│  │   Browser (CSR)  │  │  Node.js (SSR)    │  │    Edge     │ │
│  │                  │  │                    │  │  (Middleware)│ │
│  │  sentry.client   │  │  sentry.server     │  │  sentry.edge│ │
│  │  .config.ts      │  │  .config.ts        │  │  .config.ts │ │
│  │                  │  │       ↑             │  │             │ │
│  │  - React errors  │  │  instrumentation.ts │  │  - MW errors│ │
│  │  - User actions  │  │                    │  │             │ │
│  │  - Session replay│  │  - API route errors│  │             │ │
│  │  - Performance   │  │  - SSR errors      │  │             │ │
│  └────────┬─────────┘  └────────┬───────────┘  └──────┬──────┘ │
│           │                     │                      │        │
│           └─────────┬───────────┘──────────────────────┘        │
│                     │                                           │
│              ┌──────┴──────┐                                    │
│              │ tunnelRoute │  (POST /monitoring)                │
│              │ (Next.js    │  Proxies Sentry events             │
│              │  API route) │  Bypasses ad-blockers               │
│              └──────┬──────┘                                    │
└─────────────────────┼──────────────────────────────────────────┘
                      │ HTTPS
                      ▼
              ┌──────────────┐
              │  sentry.io   │
              │              │
              │  Events      │
              │  Traces      │
              │  Replays     │
              └──────────────┘
```

### 3.2 Build-Time Integration

```
next.config.ts
  └── withSentryConfig(nextConfig, sentryBuildOptions)
        ├── Webpack plugin injects Sentry into bundles
        ├── Source map upload (requires SENTRY_AUTH_TOKEN at build time)
        ├── hideSourceMaps: true (removes .map files from production output)
        └── tunnelRoute: "/monitoring" (proxy route for ad-blocker bypass)
```

### 3.3 Error Flow

```
Error occurs in any runtime
        │
        ▼
    Sentry SDK captures
        │
        ▼
    ignoreErrors filter ──── drops noise (ResizeObserver, ChunkLoad, etc.)
        │ (passes)
        ▼
    denyUrls filter ──── drops extension/third-party errors
        │ (passes)
        ▼
    beforeSend callback ──── scrubs PII (email patterns, org names)
        │ (returns event or null)
        ▼
    tunnelRoute proxy ──── bypasses ad-blockers on NGO networks
        │
        ▼
    sentry.io receives clean, filtered event
```

### 3.4 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **tracesSampleRate** | 0.2 (20%) | Balance between visibility and quota. ~20 NGO orgs with low traffic — 20% captures enough for performance monitoring |
| **tunnelRoute** | `/monitoring` | NGO offices commonly use ad-blockers or restrictive firewalls. Proxy ensures no silent event loss |
| **enabled flag** | `!!process.env.NEXT_PUBLIC_SENTRY_DSN` | Allows local development without Sentry by not setting DSN. Zero-config for developers |
| **beforeSend scope** | Email regex + breadcrumb scrub | Minimal but effective PII protection. maskAllText already handles replays |
| **ignoreErrors approach** | Regex patterns, not string matching | More resilient to minor wording changes in error messages across browser versions |

---

## 4. Low-Level Design (LLD)

### 4.1 Changes to `sentry.client.config.ts`

**Current state (inferred from spec):**
```typescript
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
});
```

**Target state:**
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,

  tracesSampleRate: 0.2,

  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  ignoreErrors: [
    /ResizeObserver loop/,
    /Non-Error promise rejection/,
    /Load failed/,
    /Failed to fetch/,
    /ChunkLoadError/,
    /NEXT_NOT_FOUND/,
    /AbortError/,
    /Network request failed/,
    /Loading chunk .* failed/,
  ],

  denyUrls: [
    /extensions\//i,
    /^chrome:\/\//i,
    /^chrome-extension:\/\//i,
    /^moz-extension:\/\//i,
    /^safari-extension:\/\//i,
  ],

  beforeSend(event) {
    // Scrub potential PII from error messages
    if (event.message) {
      event.message = event.message.replace(
        /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
        "[email]"
      );
    }
    // Scrub PII from breadcrumb messages
    if (event.breadcrumbs) {
      event.breadcrumbs = event.breadcrumbs.map((bc) => {
        if (bc.message) {
          bc.message = bc.message.replace(
            /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
            "[email]"
          );
        }
        return bc;
      });
    }
    return event;
  },
});
```

**Changes:**
1. Add `enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN`
2. Change `tracesSampleRate` from `1.0` to `0.2`
3. Add `ignoreErrors` array with 9 regex patterns
4. Add `denyUrls` array with 5 regex patterns
5. Add `beforeSend` callback for PII scrubbing

### 4.2 Changes to `sentry.server.config.ts`

**Target state:**
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.2,
  // Remove autoSessionTracking if present (server-side sessions are not meaningful)
});
```

**Changes:**
1. Add `enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN`
2. Change `tracesSampleRate` from `1.0` to `0.2`
3. Remove `autoSessionTracking` if present (LOW priority, harmless but wasteful)

### 4.3 Changes to `sentry.edge.config.ts`

**Target state:**
```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.2,
  // Remove autoSessionTracking if present
});
```

**Changes:** Same as server config.

### 4.4 Changes to `next.config.ts`

**Add tunnelRoute and verify sentryBuildOptions:**
```typescript
export default withSentryConfig(nextConfig, {
  // Existing options (keep as-is):
  org: "dalgo",
  project: "webapp-v2",
  silent: !process.env.CI,
  hideSourceMaps: true,
  disableLogger: true,

  // NEW: Add tunnelRoute for ad-blocker bypass
  tunnelRoute: "/monitoring",

  // Existing: source map upload (requires SENTRY_AUTH_TOKEN)
  // authToken is read from SENTRY_AUTH_TOKEN env var automatically
});
```

**Changes:**
1. Add `tunnelRoute: "/monitoring"`
2. Verify `hideSourceMaps: true` is set (should already be)
3. Verify `silent: !process.env.CI` for clean local builds

**Note on `window.location.origin` SSR risk (H3):** If any config file references `window.location.origin`, wrap it in a `typeof window !== 'undefined'` guard. The `tunnelRoute` approach uses a relative path (`/monitoring`) which avoids this issue entirely. Need to verify during implementation whether this reference exists in the current code.

### 4.5 Changes to `.env.example`

**Add documentation for Sentry environment variables:**
```bash
# Sentry Error Tracking
# DSN is public (write-only key) - safe to commit to .env.example
NEXT_PUBLIC_SENTRY_DSN=
# Auth token for source map uploads during build
# Required in CI/CD for readable stack traces in Sentry
# Generate at: https://sentry.io/settings/auth-tokens/
# Scopes needed: project:releases, org:read
SENTRY_AUTH_TOKEN=
```

### 4.6 No Changes Required

The following files are correct as-is and need no modifications:
- `instrumentation.ts` — correctly loads Sentry server config
- `app/global-error.tsx` — correctly wraps root layout with Sentry error boundary
- `components/pendo-script.tsx` — correctly calls `Sentry.setUser()` on auth

---

## 5. Security Review

### DSN Exposure
- **Status: Safe.** The Sentry DSN (`NEXT_PUBLIC_SENTRY_DSN`) is a write-only key. It can only send events to Sentry — it cannot read or delete anything. Exposing it in client-side JavaScript is the intended usage pattern per Sentry's documentation.
- The `NEXT_PUBLIC_` prefix correctly makes it available in the browser bundle.

### SENTRY_AUTH_TOKEN Handling
- **Status: Needs attention.** The auth token has write access to the Sentry project (source map uploads, release management). It must NEVER be exposed in client-side code.
- The token is read by `@sentry/nextjs` webpack plugin during build time only — it is not bundled into the application.
- **CI/CD requirement:** Must be set as a secret environment variable in Vercel / GitHub Actions. Must not be committed to `.env` or `.env.local`.
- **Local development:** Not needed. Source maps work locally without upload.

### PII Protection in Replays
- **Status: Already handled.** `maskAllText: true` and `blockAllMedia: true` are set in the replay integration config. This prevents NGO user data (names, org names, beneficiary data) from being captured in session replays.
- **Enhancement:** The `beforeSend` callback adds an additional layer by scrubbing email patterns from error messages and breadcrumbs.

### Source Map Hiding
- **Status: Already handled.** `hideSourceMaps: true` in `withSentryConfig()` removes `.map` files from the production build output. Source maps are uploaded to Sentry but not served to browsers.
- This prevents attackers from reverse-engineering the application's source code.

### tunnelRoute Security
- **Status: Safe.** The `/monitoring` tunnel route only proxies POST requests to `sentry.io`. It does not expose any server-side data. The Sentry SDK validates the envelope format before forwarding.

---

## 6. Testing Strategy

### Development Verification

For each change, verify in local development with Sentry enabled:

**6.1 — tracesSampleRate (H1)**
- Set `NEXT_PUBLIC_SENTRY_DSN` in `.env.local`
- Navigate through the app (5-10 page loads)
- Check Sentry Performance dashboard: expect ~20% of navigations to appear as transactions (not 100%)
- If testing is difficult at 0.2, temporarily set to 1.0 in dev only

**6.2 — ignoreErrors (H2)**
- Open browser console → manually trigger: `throw new Error("ResizeObserver loop completed with undelivered notifications")`
- Verify this error does NOT appear in Sentry
- Trigger a legitimate error (e.g., navigate to a broken route) → verify it DOES appear in Sentry

**6.3 — SSR safety (H3)**
- Run `npm run build` → verify no SSR crashes during build
- Run `npm run start` (production mode) → verify server starts cleanly
- Check server logs for `window is not defined` errors

**6.4 — Source maps (H4)**
- Set `SENTRY_AUTH_TOKEN` in local env
- Run `npm run build` → check build output for "Sentry source maps upload" success message
- If token is missing → build should complete with a warning (not an error)
- In Sentry, trigger an error → verify stack trace shows original TypeScript source, not minified JS

**6.5 — enabled flag (M1)**
- Remove `NEXT_PUBLIC_SENTRY_DSN` from `.env.local`
- Run the app → verify no Sentry network requests in browser DevTools (Network tab, filter `sentry`)
- Re-add DSN → verify Sentry events resume

**6.6 — denyUrls (M2)**
- Install a browser extension that throws errors → verify those errors do NOT appear in Sentry

**6.7 — tunnelRoute (M3)**
- After adding `tunnelRoute: "/monitoring"`, check browser DevTools Network tab
- Sentry events should POST to `/monitoring` (relative URL), not to `sentry.io` directly
- Verify events still arrive in Sentry dashboard

**6.8 — beforeSend (M4)**
- Trigger an error that includes an email address in the message: `throw new Error("Failed for user test@example.com")`
- Check Sentry → error message should show `"Failed for user [email]"`

### Staging Verification

After deploying to staging:
1. Verify Sentry receives events from the staging environment
2. Check source maps resolve correctly in Sentry stack traces
3. Verify tunnelRoute works end-to-end (events proxied through `/monitoring`)
4. Monitor Sentry quota usage for 24 hours — expect ~80% reduction in trace events vs. before

### Production Verification

After deploying to production:
1. Monitor Sentry error volume for 48 hours
2. Verify no new "missing source maps" errors in Sentry
3. Check that no PII appears in error messages or breadcrumbs
4. Verify session replay still works with existing privacy settings
5. Monitor quota usage over one week — compare to pre-change baseline

---

## 7. Milestones

All changes are in the `webapp_v2` repo on branch `setup-sentry-tracking`. The milestones are ordered by priority and can be committed as separate, reviewable changesets within the existing PR #258.

### Milestone 1: High-Priority Fixes (Quota + Noise + SSR Safety)

**Deliverable:** tracesSampleRate lowered to 0.2, ignoreErrors list added, SSR window.location.origin risk fixed, SENTRY_AUTH_TOKEN documented in .env.example.

**Services:** webapp_v2

**Key tasks:**
- [ ] In `sentry.client.config.ts`: change `tracesSampleRate` from `1.0` to `0.2`
- [ ] In `sentry.server.config.ts`: change `tracesSampleRate` from `1.0` to `0.2`
- [ ] In `sentry.edge.config.ts`: change `tracesSampleRate` from `1.0` to `0.2`
- [ ] In `sentry.client.config.ts`: add `ignoreErrors` array with 9 regex patterns (see LLD 4.1)
- [ ] Audit all three config files and `next.config.ts` for any `window.location.origin` references; guard with `typeof window !== 'undefined'` or remove
- [ ] In `.env.example`: add `SENTRY_AUTH_TOKEN` with documentation comment (see LLD 4.5)
- [ ] Verify `SENTRY_AUTH_TOKEN` is set in CI/CD (Vercel project settings or GitHub Actions secrets)

**Acceptance criteria:**
- `npm run build` succeeds without SSR errors
- Sentry receives events with 20% trace sampling
- ResizeObserver and ChunkLoadError events are filtered out
- Source map upload succeeds during CI build (check build logs)
- `.env.example` documents both `NEXT_PUBLIC_SENTRY_DSN` and `SENTRY_AUTH_TOKEN`

---

### Milestone 2: Medium-Priority Hardening (Privacy + Ad-Blocker Bypass + Disable Flag)

**Deliverable:** Sentry can be disabled via missing DSN, ad-blocker-proof event delivery via tunnelRoute, PII scrubbing via beforeSend, extension noise filtered via denyUrls.

**Services:** webapp_v2

**Key tasks:**
- [ ] In all three config files: add `enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN`
- [ ] In `sentry.client.config.ts`: add `denyUrls` array with 5 regex patterns (see LLD 4.1)
- [ ] In `sentry.client.config.ts`: add `beforeSend` callback for email regex scrubbing (see LLD 4.1)
- [ ] In `next.config.ts`: add `tunnelRoute: "/monitoring"` to `withSentryConfig()` options (see LLD 4.4)

**Acceptance criteria:**
- With DSN unset: no Sentry network requests in browser DevTools
- With DSN set: events POST to `/monitoring` (not directly to sentry.io)
- Error containing `test@example.com` appears as `[email]` in Sentry
- Browser extension errors do not appear in Sentry

---

### Milestone 3: Low-Priority Cleanup

**Deliverable:** Remove unnecessary server/edge config options.

**Services:** webapp_v2

**Key tasks:**
- [ ] In `sentry.server.config.ts`: remove `autoSessionTracking` if present
- [ ] In `sentry.edge.config.ts`: remove `autoSessionTracking` if present

**Acceptance criteria:**
- Server and edge Sentry configs contain only `dsn`, `enabled`, `tracesSampleRate`
- No behavior change (session tracking was already a no-op on server/edge)

---

## 8. Open Questions & Risks

### Open Questions

1. **window.location.origin reference (H3):** The spec flags an SSR risk from `window.location.origin`, but without reading the actual code, I cannot confirm which file contains this reference. During implementation, audit all three config files and `next.config.ts` for any `window` access. If found in the `tunnelRoute` setup, replacing with the relative path `/monitoring` eliminates the issue.

2. **SENTRY_AUTH_TOKEN in CI/CD:** Which CI/CD platform does webapp_v2 use? If Vercel, add as a project-level environment variable. If GitHub Actions, add as a repository secret. The implementer should confirm the deployment pipeline and add the token accordingly.

3. **Sentry project/org names:** The LLD assumes `org: "dalgo"` and `project: "webapp-v2"` in `withSentryConfig()`. These should be verified against the actual Sentry project settings. Incorrect values will cause source map upload to fail silently.

4. **tunnelRoute path collision:** The `/monitoring` path must not collide with any existing Next.js route. Verify by checking `app/monitoring/` does not exist. If it does, use an alternative like `/sentry-tunnel` or `/error-reporting`.

5. **Actual current code vs. spec description:** This plan is based on the spec's description of the current state, not a direct code read. The spec may have missed or mischaracterized certain configurations. The implementer should read each file before modifying it and adjust the plan if the actual state differs from what is described.

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| tracesSampleRate 0.2 may miss rare performance issues | Reduced visibility into infrequent slow routes | Monitor for 2 weeks; increase to 0.3 if needed. Future: implement `tracesSampler` for route-specific rates |
| ignoreErrors may be too aggressive | Legitimate errors that match patterns get silently dropped | Review Sentry dashboard weekly for first month; remove patterns that match real bugs |
| tunnelRoute adds server load | Extra server-side request proxying for every Sentry event | Negligible for ~20 NGO orgs with low traffic. Monitor Next.js server metrics |
| beforeSend email regex may cause false positives | Non-email strings matching the pattern get scrubbed | Regex is conservative; review first batch of scrubbed events in Sentry |
| SENTRY_AUTH_TOKEN rotation | Token expiry breaks source map uploads silently | Set calendar reminder to check token validity quarterly |
| Ad-hoc window.location.origin usage in other files | SSR crash not caught by this plan | Search entire codebase for `window.location` as part of Milestone 1 |

---

### Quality Checklist
- [x] `README.md` and `docs/domain-map.md` were read before research began
- [x] Blast Radius section confirms no product entities affected (infrastructure-only change)
- [x] No downstream surfaces impacted — confirmed per domain-map.md infrastructure exclusion
- [x] HLD covers all three Next.js runtimes and the build-time integration
- [x] LLD has concrete code changes per file with before/after states
- [x] Security review covers SENTRY_AUTH_TOKEN, DSN exposure, PII in replays, source map hiding, tunnelRoute
- [x] Milestones are independently shippable and ordered by priority (HIGH → MEDIUM → LOW)
- [x] Testing strategy covers dev, staging, and production verification per change
- [x] References existing codebase patterns from the spec

---

*Plan generated from [sentry_setup_plan.md](../../../dalgo-ai-gen/dalgo_mds/claude/planning/sentry_setup_plan.md), [codebase research](./research.md), and [domain map](../../../docs/domain-map.md).*
