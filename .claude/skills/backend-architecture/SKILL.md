# Backend Architecture Skill

Use this skill when building new backend features, adding API endpoints, creating services, or working with Django models and Pydantic schemas in `DDP_backend/`.

## What's Here

- **`templates.md`** — Code templates for every layer: API endpoints, services, schemas, models, and exceptions. Copy and adapt these when creating new modules.
- **`examples.md`** — Concrete examples: a complete Charts module walkthrough, request-response flow diagrams, JSON response formats, and a migration reference table.

## Quick Reference

The backend follows a 4-layer architecture: **API -> Core -> Schema -> Model**

- API layer: `ddpui/api/{module}_api.py`
- Core layer: `ddpui/core/{module}/{module}_service.py` + `exceptions.py`
- Schema layer: `ddpui/schemas/{module}_schema.py`
- Model layer: `ddpui/models/{module}.py`

Rules and conventions are in `DDP_backend/.claude/CLAUDE.md` (always loaded).
