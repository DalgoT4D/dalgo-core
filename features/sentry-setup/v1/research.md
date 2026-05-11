# Sentry Setup v1 — Research Notes

**Date:** 2026-05-08
**Purpose:** Codebase analysis and Sentry SDK best-practices research to inform the implementation plan.

---

## 1. Current State (from spec: sentry_setup_plan.md)

### SDK Version
- @sentry/nextjs v8.55.0 installed in webapp_v2

### Existing Config Files
| File | Purpose | Status |
|------|---------|--------|
| `sentry.client.config.ts` | Browser-side Sentry initialization | Exists, needs tuning |
| `sentry.server.config.ts` | Node.js server runtime initialization | Exists, needs tuning |
| `sentry.edge.config.ts` | Edge runtime initialization | Exists, needs tuning |
| `instrumentation.ts` | Next.js instrumentation hook (loads Sentry server config) | Exists, correct |
| `app/global-error.tsx` | Root error boundary with Sentry reporting | Exists, correct |
| `next.config.ts` | Next.js config with `withSentryConfig()` wrapper | Exists, needs review |
| `components/pendo-script.tsx` | Contains `Sentry.setUser()` call on auth | Exists, correct |
| `.env.example` | Environment variable documentation | Needs SENTRY_AUTH_TOKEN entry |
| `package.json` | Sentry dependency | v8.55.0 |

### What's Already Correct (per spec)
- Session replay rates (0.1 production, 1.0 dev) — appropriate for low-traffic NGO platform
- Privacy defaults (`maskAllText: true`, `blockAllMedia: true`) — correct for NGO data
- Source maps configured in `withSentryConfig()` — `hideSourceMaps: true` set
- `global-error.tsx` wraps root layout with Sentry error boundary
- `instrumentation.ts` properly loads Sentry in Node.js runtime
- `Sentry.setUser()` called on authentication in `pendo-script.tsx`

---

## 2. Issues Identified by Spec (Grouped by Priority)

### HIGH Priority

**H1 — tracesSampleRate too high (1.0)**
- Current: `tracesSampleRate: 1.0` in all three config files (client, server, edge)
- Problem: 100% trace sampling sends every transaction to Sentry. For a production NGO platform, this is excessive and will burn through Sentry quota quickly.
- Recommendation: Lower to `0.2` (20%) for production. This captures enough transactions for performance monitoring without quota waste.
- Reference: Sentry docs recommend 0.1-0.3 for production apps.

**H2 — No ignoreErrors list**
- Current: No `ignoreErrors` configured in client config
- Problem: Browser noise (ResizeObserver, extensions, network failures) creates alert fatigue and wastes Sentry event quota.
- Recommendation: Add standard ignoreErrors list covering:
  - `ResizeObserver loop` (Chrome-specific, harmless)
  - `Non-Error promise rejection` (browser extensions)
  - `Load failed` / `Failed to fetch` (network issues on slow NGO connections)
  - `ChunkLoadError` (Next.js chunk loading failures on slow networks)
  - `NEXT_NOT_FOUND` (expected 404s from Next.js)

**H3 — window.location.origin SSR risk**
- Current: `tunnelRoute` or DSN configuration may reference `window.location.origin`
- Problem: `window` is undefined during server-side rendering. This would crash the server runtime.
- Recommendation: Guard with `typeof window !== 'undefined'` check, or remove the reference entirely since `tunnelRoute` handles this via relative paths.

**H4 — Missing SENTRY_AUTH_TOKEN for source maps**
- Current: `withSentryConfig()` has source map upload enabled, but `SENTRY_AUTH_TOKEN` is not documented in `.env.example`
- Problem: Source map upload silently fails in CI/CD without the auth token. Production errors show minified stack traces, making debugging painful.
- Recommendation: Add `SENTRY_AUTH_TOKEN` to `.env.example` with documentation. Verify it's set in deployment environment.

### MEDIUM Priority

**M1 — No `enabled` flag**
- Current: Sentry always initializes regardless of environment
- Recommendation: Add `enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN` to all three configs. Allows disabling Sentry in local development by not setting the DSN.

**M2 — No `denyUrls`**
- Current: All error URLs are captured
- Recommendation: Add `denyUrls` to filter out errors from browser extensions, CDNs, and third-party scripts that Dalgo cannot fix.

**M3 — No `tunnelRoute` for ad-blocker bypass**
- Current: Sentry events sent directly to sentry.io
- Problem: Ad-blockers and corporate firewalls (common in NGO office networks) block requests to sentry.io, causing silent error-reporting gaps.
- Recommendation: Add `tunnelRoute: "/monitoring"` to `withSentryConfig()`. This proxies Sentry events through the Next.js server, bypassing ad-blockers.

**M4 — No `beforeSend` callback**
- Current: All errors sent as-is to Sentry
- Recommendation: Add `beforeSend` to scrub potential PII (email addresses, org names) from error messages and breadcrumbs. Important for NGO data privacy.

### LOW Priority

**L1 — autoSessionTracking in server/edge configs**
- Current: `autoSessionTracking` may be set to `true` in server/edge configs
- Problem: Session tracking is a browser-side concept. It's harmless but wasteful in server/edge runtimes.
- Recommendation: Remove from server and edge configs.

### Future (Not in v1)

- `tracesSampler` function for route-specific sampling rates
- `thirdPartyErrorFilterIntegration` to filter errors from third-party scripts
- `allowUrls` to explicitly whitelist Dalgo's own domains
- Route-specific `error.tsx` boundaries for high-traffic pages (dashboards, charts)

---

## 3. Next.js + Sentry Architecture

### Three Runtimes in Next.js

Next.js runs code in three distinct runtimes, each needing separate Sentry initialization:

```
Browser (Client)              Node.js (Server)              Edge
─────────────────            ──────────────────            ──────────────
sentry.client.config.ts      sentry.server.config.ts       sentry.edge.config.ts
                              ↑ loaded by
                              instrumentation.ts

Errors:                       Errors:                       Errors:
- React render errors         - API route errors             - Middleware errors
- Event handler errors        - Server Component errors      - Edge API errors
- Unhandled rejections        - Data fetching errors
- Network errors

Error Boundaries:
- app/global-error.tsx (root)
- app/{route}/error.tsx (per-route, optional)
```

### How Sentry Integrates with Next.js Build

```
next.config.ts
  └── withSentryConfig(nextConfig, sentryBuildOptions)
        ├── Wraps webpack config to inject Sentry
        ├── Uploads source maps during build (needs SENTRY_AUTH_TOKEN)
        ├── Hides source maps in production (hideSourceMaps: true)
        └── Sets up tunnelRoute proxy (if configured)
```

### Data Flow

```
Error occurs → Sentry.captureException() → beforeSend filter → tunnelRoute proxy → sentry.io
                                             ↓
                                        ignoreErrors / denyUrls filter
                                        (drops noise before sending)
```

---

## 4. Sentry SDK v8 Best Practices (External Research)

### Source Maps
- SENTRY_AUTH_TOKEN must be set as environment variable during build time
- Token needs `project:releases` and `org:read` scopes
- `hideSourceMaps: true` in `withSentryConfig()` prevents serving source maps to browsers
- Source maps are uploaded and then deleted from the build output

### Quota Management
- tracesSampleRate of 0.1-0.3 is recommended for production
- replaysSessionSampleRate of 0.1 is standard (Dalgo already uses this)
- ignoreErrors + denyUrls reduce noise events by 30-50% in typical setups
- tunnelRoute prevents event loss from ad-blockers (estimated 10-30% of events blocked otherwise)

### Privacy (NGO-relevant)
- `maskAllText: true` in replay config prevents PII capture in session replays
- `blockAllMedia: true` prevents image/video capture
- `beforeSend` can scrub additional PII from error payloads
- Sentry DSN is safe to expose publicly (it's a write-only key, limited to sending events)

### Common ignoreErrors for Next.js
```typescript
[
  /ResizeObserver loop/,
  /Non-Error promise rejection/,
  /Load failed/,
  /Failed to fetch/,
  /ChunkLoadError/,
  /NEXT_NOT_FOUND/,
  /AbortError/,
  /Network request failed/,
  /Loading chunk .* failed/,
]
```

### Common denyUrls
```typescript
[
  /extensions\//i,
  /^chrome:\/\//i,
  /^chrome-extension:\/\//i,
  /^moz-extension:\/\//i,
  /^safari-extension:\/\//i,
  /googletagmanager\.com/,
  /facebook\.net/,
  /graph\.facebook\.com/,
]
```

---

## 5. Impact Assessment

### Sentry Quota Impact
- Reducing tracesSampleRate from 1.0 to 0.2 reduces trace events by 80%
- Adding ignoreErrors + denyUrls reduces error events by estimated 30-50%
- Adding tunnelRoute increases captured events by estimated 10-30% (events previously blocked by ad-blockers now get through)
- Net effect: significant quota savings while improving signal quality

### CI/CD Impact
- SENTRY_AUTH_TOKEN needs to be added as a secret in CI/CD (Vercel, GitHub Actions, etc.)
- Build will log warnings if token is missing but will not fail (source map upload is non-blocking)
- No changes to deployment pipeline structure — only env var additions

### Performance Impact
- Lowering tracesSampleRate reduces client-side overhead slightly
- tunnelRoute adds one Next.js API route but handles minimal traffic
- beforeSend adds negligible per-error processing overhead
- Net effect: neutral to slightly positive
