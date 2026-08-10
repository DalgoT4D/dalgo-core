# Dalgo Security Audit — Run 1 (2026-08)

Security audit of the Dalgo **backend** (`DDP_backend`, Django/django-ninja) and **frontend**
(`webapp_v2`, Next.js 15), produced with the `security-audit` skill (6-phase, multi-agent:
recon → hunt → validate → report → structured output → independent verification).

> ⚠️ **Do not push this branch to a public remote.** These reports describe **unpatched**
> vulnerabilities in Dalgo (including the location of a leaked credential). Keep the branch
> local / private until the findings are remediated.

## Layout

- `DDP_backend/run-1/` — backend results
- `webapp_v2/run-1/` — frontend results

Each folder contains:
- `REPORT.md` — human-readable report: executive summary, findings table, per-finding attack +
  fix, hardening notes, killed leads, positive patterns
- `FINDINGS-DETAIL.md` — concrete data flows + exact HTTP requests for MEDIUM+ findings
- `findings.json` — schema-validated machine-readable findings (`confirmed`/`rejected`)
- `architecture.md` — Phase 1 recon map (trust model, input surfaces)

## Headline findings

| Sev | Finding | Repo |
|-----|---------|------|
| CRITICAL | Public dashboard link → read entire org warehouse (schema/table from request) | backend |
| CRITICAL | Unauthenticated stored XSS via ECharts tooltip on public share pages (no CSP) | cross-repo |
| HIGH | Deactivated users keep access + refresh tokens forever (`is_active` never checked) | backend |
| HIGH | GCP service-account private key in git history, reachable from `main` (rotate) | backend |
| HIGH | dbt path traversal → cross-tenant model overwrite + all-orgs `rmtree` | backend |
| HIGH | Full-read SSRF via org-logo URL; attacker-content file write via `sslrootcert` | backend |
| HIGH | DOM XSS in authenticated RangeChart tooltip | frontend |

See each `REPORT.md` for the full set (18 backend + 6 frontend confirmed) and the leads that were
investigated and **ruled out** (dead `text()` SQLi, no `git clone` RCE, dead `convert_github_url`).

This is **run 1**; audit coverage improves with additional runs.
