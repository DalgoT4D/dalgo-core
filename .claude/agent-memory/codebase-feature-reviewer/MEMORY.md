# Dalgo Platform Code Review Memory

## Architecture Overview
- **DDP_backend**: Django REST API with Django Ninja at `/Users/siddhant/Documents/Dalgo/DDP_backend`
- **webapp_v2**: Next.js 15 + React 19 frontend at `/Users/siddhant/Documents/Dalgo/webapp_v2`
- **prefect-proxy**: FastAPI proxy for Prefect at `/Users/siddhant/Documents/Dalgo/prefect-proxy`
- **dalgo-ai-gen**: AI/ML repo at `/Users/siddhant/Documents/dalgo/dalgo-ai-gen` (mostly planning docs)

## Key Patterns
- Backend CLAUDE.md defines a comprehensive layer architecture (API -> Core -> Models)
- Backend uses `has_permission` decorator for RBAC
- Frontend uses SWR for data fetching, Zustand for auth, cookie-based JWT auth
- Prefect-proxy has no authentication -- relies on network-level security

## Auth & RBAC System (April 2026 Deep Review)
- **auth.py line 44**: bare `except:` swallows all exceptions as 404 (security issue)
- JWT middleware uses Redis with NO TTL on cache keys
- `orguser_role:{user_id}` -> `{orguser_id: role_id}` cached in Redis
- GUEST_ROLE referenced in: auth.py, orguserfunctions.py, 4 test files, 1 migration
- Frontend usePermissions reads from Zustand authStore synchronously (no API call)
- Frontend sidebar: NO permission gating, only feature flags + environment checks
- Frontend middleware.ts: CORS-only for /share/*, NO auth routing

## Seed Data Facts (verified April 2026)
- Guest (pk=5) DOES have can_view_dashboards(64) and can_view_charts(65) in seed data
- Duplicate PKs 213-216: Django loaddata last-wins = permission 59 replaces 58
- This means roles 1-4 get can_view_flags(59) but LOSE can_accept_tnc(58) via loaddata
- Analyst has 46 permissions including full dbt write, sync sources, orgtask management

## Chart Data Pipeline Architecture (March 2026)
- **Entry**: `charts_api.py` POST `/chart-data/` and GET `/{chart_id}/data/`
- **Flow**: API -> `generate_chart_data_and_config()` -> `charts_service.build_chart_query()` -> `AggQueryBuilder` -> `warehouse.execute()`
- **NO caching** on chart data queries
- **New warehouse client per request**
- **Reports still hit the warehouse**: Frozen configs store metadata only, NOT data

## File Locations
- Auth: `/DDP_backend/ddpui/auth.py`
- Role Models: `/DDP_backend/ddpui/models/role_based_access.py`
- Charts Service: `/DDP_backend/ddpui/core/charts/charts_service.py`
- Query Builder: `/DDP_backend/ddpui/core/datainsights/query_builder.py`
- Main Layout: `/webapp_v2/components/main-layout.tsx`
- usePermissions: `/webapp_v2/hooks/api/usePermissions.ts`
- Auth Store: `/webapp_v2/stores/authStore.ts`
- Migration Pattern: `/DDP_backend/ddpui/migrations/0137_update_landing_page_permissions.py`
