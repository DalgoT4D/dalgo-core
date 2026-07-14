# Access Control — Design (v1)

**Status:** Ready for engineering
**Spec:** access-control-spec-A-role-system-2026-06-02.md
**Figma:** https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL
**Last updated:** 2026-06-04

## Screens

| Screen | Frame | Node ID | Figma link | Status |
|--------|-------|---------|------------|--------|
| Sidebar — Admin | S1a · Sidebar Admin | 21:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=21-2) | ✅ Ready |
| Sidebar — Analyst | S1b · Sidebar Analyst | 22:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=22-2) | ✅ Ready |
| Sidebar — Member | S1c · Sidebar Member | 23:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=23-2) | ✅ Ready |
| No Access Page | S2 · No Access Page | 24:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=24-2) | ✅ Ready |
| Settings IA | S3 · Settings IA | 25:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=25-2) | ✅ Ready |
| Settings > Users | S4 · Settings > Users | 27:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=27-2) | ✅ Ready |
| Invite User Modal | S5 · Invite User Modal | 28:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=28-2) | ✅ Ready |
| Data Section (Analyst read-only) | S7 · Data Section Analyst | 29:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=29-2) | ✅ Ready |
| Migration Changelog Modal | S8 · Migration Changelog | 31:2 | [View →](https://www.figma.com/design/viO3UsJicCOz3rwx4iocBL?node-id=31-2) | ✅ Ready |

## User Flows & Prototype

| Scenario | Starting frame | Key connections |
|----------|---------------|-----------------|
| Onboard a new team member | S4 · Settings > Users | Invite user CTA → S5 modal → success → back to S4 |
| Member hits a restricted URL | S1c · Sidebar Member | Direct-URL /ingest → S2 No Access → "Go to dashboards" CTA |
| Role comparison | S1a · Sidebar Admin | Side-by-side with S1b (Analyst) and S1c (Member) |

Prototype connections not yet wired — add manually in Figma or re-run after approval.

## Design Decisions

**Sidebar (S1a/b/c)**
- Three separate frames (one per role) — clearest for engineering reference
- Nav items hidden entirely when role cannot access (not greyed) — matches spec §5.3
- "Read only" badge next to Data and Pipelines in Analyst view
- Role chip in sidebar footer: Admin=brand-primary teal, Analyst/Member=grey
- Active item: 3px left border in brand-primary, brand-light background tint

**No Access Page (S2)**
- In-shell layout (sidebar + header visible) — user can navigate away immediately
- Header breadcrumb shows where they tried to go: "Data › Ingest"
- Admin contact card with email shown explicitly
- Single CTA: "Go to dashboards"

**Settings IA (S3)**
- Full-page takeover, sidebar still visible
- Left sub-nav (180px) within Settings: Warehouse, Appearance, Org defaults, Users, Groups
- Admin-only sections hidden entirely for Analyst/Member; only Groups visible
- Org defaults renders with inert controls, labelled as activating in next release

**Settings > Users (S4)**
- Inline role chip/dropdown — fastest for small NGO teams
- Pending invites in same table with amber "Pending" status chip
- Delete action in row action menu (⋯), not inline

**Invite User Modal (S5)**
- Single-step: Name, Email, Role dropdown with inline role descriptions
- CTA: "Send invite" — sends email immediately
- Duplicate email: inline error below Email field
- Success: toast, modal closes

**Data Section — Analyst read-only (S7)**
- All write actions absent (not greyed)
- "Read only" chip next to page title
- Applies uniformly to all Data sub-sections

**Migration Changelog (S8)**
- One modal, role-conditional copy (Admin variant shown)
- 3 bullets, role-specific CTA: "Go to Settings"
- One-time only

## Known Issues

- **S6 · Ownership Transfer not built** — needs a modal with user-search picker and a blocking transfer step in the delete-user flow. Add as a follow-up frame.
- Prototype connections not wired — add manually in Figma or re-run after designer approval.
- Frames are wireframe-quality — polish (icons, shadows, avatar images) should be refined in Figma before final engineering handoff.

## Figma

file_key: viO3UsJicCOz3rwx4iocBL
