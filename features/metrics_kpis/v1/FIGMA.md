# FIGMA.md — Metrics & KPI Feature Extension

> Extends `~/Dalgo/FIGMA.md`. Read that file first, then this one.
> This file only contains things specific to the Metrics & KPI feature.

---

## 1. Screens in This Feature

All screens are 1440 × 900px. This feature's screens start at x=76600.

| Screen | Frame name | x |
|--------|-----------|---|
| Nav IA comparison | Nav IA v2 | 76600 |
| Metrics Library — with data | S1v3-MetricsLibrary | 77500 |
| Metrics Library — empty state | S1v3-Empty | 79100 |
| Create Metric dialog | S2-CreateMetric | 80700 |
| KPI Page — card grid | S3-KPIPage | 82300 |
| KPI Page — empty state | S3-Empty | 83900 |
| Create KPI wizard (4 steps) | S4-CreateKPI | 85500 |
| KPI Detail drawer | S5-KPIDetail | 87100 |
| MetricsSelector tab (chart builder) | S6-MetricsSelector | 88700 |
| KPI Dashboard widget | S7-DashboardChart | 90300 |
| Component Selector modal (+ KPI tab) | S8-ComponentSelector | 91900 |
| Edit Metric dialog | S9-EditMetric | 93500 |
| Blast Radius warning | S10-BlastRadius | 95100 |
| Delete Blocked | S11-DeleteBlocked | 96700 |

---

## 2. Dalgo Nav — Metrics Entry Point

Metrics is a **sub-item under DATA**, after Quality. It has a NEW badge on first release.

```
  DATA  ▾
    ·  Overview
    ·  Ingest
    ·  Transform
    ·  Orchestrate
    ·  Explore
    ·  Quality
    ·  Metrics  [NEW]   ← active when on any Metrics or KPI screen
```

---

## 3. Metrics Library Table (S1)

### Column spec (exact widths, exact order)

| Column | Width | Content |
|--------|-------|---------|
| Name | 220px | Name 13 SemiBold + description 11 Regular `C.mu` (truncated) |
| Mode | 80px | Simple or SQL badge |
| Data Source | 160px | `schema.table` — 12 Regular |
| Definition | 190px | Code-style bg (`C.su`), expression truncated |
| Current Value | 100px | 14 SemiBold `C.fg` |
| Used By | 120px | "3 charts · 1 KPI" — 12 Regular `C.mu` |
| Last Updated | 110px | "2d ago" — 12 Regular `C.mu` |
| Actions | 48px | `⋮` icon button |

### Mode Badges

| Mode | bg | text + border | size |
|------|----|--------------|------|
| Simple | `C.gb` | `C.gn` | 52 × 20, r=10 |
| SQL | `C.nb` | `C.nf` | 36 × 20, r=10 |

---

## 4. RAG Status Badges (KPI screens)

Always show label text + colour. Never colour alone.

| State | Label | bg | text + border |
|-------|-------|----|--------------|
| On Track | "On Track" | `C.gb` | `C.gn` |
| At Risk | "At Risk" | `C.ab` | `C.am` |
| Off Track | "Off Track" | `C.rb` | `C.rd` |
| No Target | "No Target" | `C.su` | `C.mu` · `C.bd` |
| Stale | "Stale Data" | `C.nb` | `C.nf` |

---

## 5. Create / Edit Metric — Dialog Modal

- Component: dialog (not drawer)
- Width: 480px, radius 12px, bg white, shadow via 1px `C.bd` border
- Padding: 24px header, 24px body, 16px footer
- Footer: border-top 1px `C.bd`, right-aligned Cancel + primary button
- Mode toggle (Simple / SQL) at top of form — two-segment control
- Simple mode: dataset picker → column picker → aggregation picker
- SQL mode: full-width code editor area (`C.su` bg, monospace-style)
- Live preview panel on right (shows current computed value)

---

## 6. KPI Page (S3) — Card Grid

- Route feel: `/kpis` (separate from `/metrics`)
- Layout: responsive card grid, 3 columns at 1440px
- Each KPI card shows: name, RAG badge, current value (large), target, % change, sparkline, last updated

---

## 7. Create KPI — 4-Step Wizard Dialog

- Component: dialog modal (not drawer), width 560px
- Step 1: Pick a Metric (search + select from library)
- Step 2: Set target, direction (↑ higher is better / ↓ lower is better), RAG thresholds
- Step 3: Trend config (time grain, window, comparison period)
- Step 4: Tags + name + summary — confirm

---

## 8. KPI Detail — Right Drawer / Sheet

- Component: sheet, slides in from right
- Width: 600px
- Sticky header: KPI name + RAG badge + ⋮ menu
- Sections (scrollable): Current value → Trend chart → Target info → Annotations timeline
- Annotations: each entry has period, value snapshot, comment/beneficiary quote, author, timestamp
- "Add Entry" button opens inline form at top of timeline

---

## 9. Feature-Specific Session Checklist

- [ ] Read `~/Dalgo/FIGMA.md` first
- [ ] Read this file
- [ ] Check canvas position map above — next free slot starts at x=98300
- [ ] Cross-check against `spec.md` and `design.md` in the v1 folder
- [ ] Metrics sub-item is always the active nav state for all screens in this feature

---

*Feature: Metrics & KPI v1 · Figma file: `lSXpuOg6n0qXXwvMjOfU7G` · Updated: 2026-05-06*
