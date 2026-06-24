# KPI v1.1 — Number Formatting & Prefix/Suffix — Implementation Plan

**Status:** Draft v1
**Date:** 2026-06-24
**Parent version:** [`features/metrics_kpis/v1/spec.md`](../v1/spec.md) | [`features/metrics_kpis/v1/plan.md`](../v1/plan.md)
**Research:** [research.md](./research.md)
**Domain map:** [`docs/domain-map.md`](../../../docs/domain-map.md)

---

## 1. Overview

Add **number formatting + prefix/suffix** options to KPI config, mirroring the existing number-chart pattern. The same 4 fields the number chart already exposes (`numberFormat`, `decimalPlaces`, `numberPrefix`, `numberSuffix`) land on the KPI model under `extra_config.customizations`. The enhancement threads these through every KPI render surface — card, drawer, dashboard widget, frozen ReportSnapshot, and kpi_rag alert email body — and brings the backend formatter up to parity with the frontend so alert emails match on-screen rendering.

**Enhancement description (verbatim from user):**
> We actually need 2 things — Number formatting options and prefix/suffix options exactly same as the number chart.

**Services affected:**
- **DDP_backend** — KPI model + schema + new shared formatter module + alert rendering + report snapshot freeze
- **webapp_v2** — KPI form, KPI card, drawer, dashboard widget, snapshot viewer

**Not affected:** prefect-proxy.

---

## 2. Blast Radius

Derived from `docs/domain-map.md` traversal of KPI's consumers (1-hop and 2-hop). Every entry confirmed with the user.

| Surface | Hop | Why affected | Edge type | Status | Notes |
|---|---|---|---|---|---|
| **KPI card** (KPIs page) | 0 (direct) | Current value + target are now formatted | direct render | **In scope** | Swap `formatMetricValue` → `formatKPIValue` |
| **KPI detail drawer** | 0 (direct) | Header value + target | direct render | **In scope** | Same swap |
| **KPI dashboard widget** | 1 from KPI | KPI rendered inside dashboard via `KPIChartElement` | `compose` | **In scope** | Inherits via the same KPICard render path |
| **Dashboard** | 1 from KPI | Composes KPI widget | `compose` | **Auto-inherited** | No dashboard-builder changes — widget already exists |
| **ReportSnapshot** | 2 from KPI (via Dashboard) | Snapshot freezes KPI chart data into `frozen_chart_configs` | `snapshot-of` | **In scope** | Freeze `customizations` alongside data; historical snapshots render with frozen format |
| **Alert (kpi_rag)** | 1 from KPI | Email body renders `{{current_value}}` | `reference` | **In scope** | Swap token render to use `format_number_v2` + KPI customizations |
| **Share link (live Dashboard)** | 3 | Renders live KPI on shared dashboard | `embed` | **Auto-inherited** | Picks up format automatically |
| **Share link (Report)** | 3 | Renders frozen snapshot under share token | `embed` | **Auto-inherited** | Picks up frozen format |
| **Trendline axis labels** | — | Trendline Y-axis on card/drawer/widget/report | — | **Explicitly raw** | User-confirmed out of scope. Document in spec so QA doesn't file as bug |
| **Trendline tooltips** | — | Hover values on trendline | — | **Explicitly raw** | Same — user-confirmed raw |
| **Period-over-period delta** | — | "+230 since last month" text on card/drawer/timeline | — | **Explicitly raw** | User-confirmed out of scope |
| **Annotation snapshot values** | — | Value/RAG captured per annotation | — | **Explicitly raw** | User-confirmed out of scope |
| **Notification** | 3 from KPI (via Alert) | Alert delivery channel | `trigger` | **Not in delivery path** | Per domain map: alerts deliver directly via SMTP/Slack, not via Notification |

### Known v2 debt from this table

None — every in-scope surface ships in v1.1.

---

## 3. High-Level Design (HLD)

### 3.1 System interaction

```
┌──────────────────────────────────────────────────────────┐
│                       webapp_v2                          │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ KPI form   │  │ KPI card   │  │ Dashboard KPI      │ │
│  │ Step 2:    │  │ + Drawer   │  │ widget             │ │
│  │ <Number…   │  │            │  │                    │ │
│  │  Format    │  │ formatKPI- │  │ inherits via       │ │
│  │  Panel />  │  │ Value()    │  │ KPICard render     │ │
│  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘ │
│        │ persists       │ reads from        │            │
│        ▼ extra_config.  ▼ kpi.extra_config. ▼            │
│        customizations   customizations                   │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP
┌──────────────────────────┼───────────────────────────────┐
│                     DDP_backend                          │
│                          ▼                                │
│   POST /api/kpis/      PUT /api/kpis/{id}/               │
│       │                     │                             │
│       ▼                     ▼                             │
│   KPICreate            KPIUpdate                          │
│   .extra_config        .extra_config                      │
│       │                     │                             │
│       ▼                     ▼                             │
│   ┌──────────────────────────────────────┐               │
│   │  KPI model: extra_config JSONField   │               │
│   └────────────────┬─────────────────────┘               │
│                    │                                      │
│      ┌─────────────┼─────────────┐                       │
│      ▼             ▼             ▼                       │
│  ReportSnapshot  Alert         (future                   │
│  freeze:         render:       consumers)                │
│  copy into       format_       inherit shared            │
│  FrozenKpiConfig number_v2()   formatter                 │
│                                                          │
│   ┌─────────────────────────────────────────┐           │
│   │ NEW: core/charts/number_formatting.py   │           │
│   │      format_number_v2(value, type,      │           │
│   │      decimals, prefix, suffix) -> str   │           │
│   │      Uses babel for indian/european/    │           │
│   │      international locale grouping      │           │
│   └─────────────────────────────────────────┘           │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Data flow

**Render-time (frontend):**
1. KPI loaded with `extra_config.customizations` from the API
2. Card / drawer / widget call `formatKPIValue(value, customizations)` → `lib/formatters.ts`
3. `formatKPIValue` wraps `formatNumber()` + prepends `numberPrefix` + appends `numberSuffix`
4. `null`/`NaN` → returns `"No data"` with no prefix/suffix wrap

**Render-time (backend — alert email):**
1. Cron evaluator computes KPI value
2. Renders `{{current_value}}` using `format_number_v2(value, customizations.numberFormat, customizations.decimalPlaces, customizations.numberPrefix, customizations.numberSuffix)`
3. Mustache replaces token in template; email sent

**Snapshot freeze:**
1. User snapshots a dashboard with a KPI widget
2. `FrozenKpiConfig` is built per KPI in the dashboard
3. Snapshot copies `kpi.extra_config.customizations` into the frozen blob
4. At render time, snapshot viewer reads frozen `customizations` (NOT live KPI)

### 3.3 New / modified endpoints

No new endpoints. Existing endpoints extended:

| Method | Path | Change |
|---|---|---|
| `POST` | `/api/kpis/` | Accept `extra_config: Optional[Dict]` in `KPICreate` |
| `PUT` | `/api/kpis/{id}/` | Accept `extra_config: Optional[Dict]` in `KPIUpdate` |
| `GET` | `/api/kpis/{id}/` | Return `extra_config` in `KPISchema` |
| `GET` | `/api/kpis/` | Return `extra_config` in list |
| `GET` | `/api/kpis/summary/` | Return `extra_config` |

### 3.4 Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Storage** | `extra_config = JSONField(default=dict)` on KPI model, nested as `extra_config.customizations.{4 fields}` | Mirrors Chart exactly; extensible; no data migration |
| **Editability** | Editable post-create | Format is render-only; no data integrity risk. User-confirmed |
| **Frontend formatter reuse** | New `formatKPIValue(value, customizations)` wrapping existing `formatNumber()` | `formatNumber` already handles all 7 format types; KPI just needs prefix/suffix wrap + null guard |
| **ECharts mutation** | **None** — KPI value is React text, not ECharts `series[].detail` | `applyNumberChartFormatting()` is gauge-specific. KPI widget renders a line trendline + separate React text for current value |
| **Backend formatter** | New shared module `core/charts/number_formatting.py` with `format_number_v2`, uses `babel` for locale grouping | Cross-cutting (charts + alerts); babel produces output identical to browser `Intl.NumberFormat` |
| **Alert token swap** | Render `{{current_value}}` formatted in-place (no new token) | User-confirmed; existing kpi_rag templates start emitting formatted output |
| **Snapshot semantics** | Freeze `customizations` at snapshot time | Matches existing "frozen layout, live data" model; historical snapshots preserve display intent |
| **Snapshot back-compat** | Snapshots pre-v1.1 have no frozen customizations → fall back to no-formatting render | Matches what those snapshots showed before |
| **Parity test** | Shared `(value, format, decimals, prefix, suffix)` fixture; frontend Vitest + backend pytest assert byte-identical strings | Only way to keep FE/BE in sync over time |

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

**Modified:** `DDP_backend/ddpui/models/metric.py` — KPI class (~lines 84–129)

```python
class KPI(models.Model):
    # ... existing fields ...
    extra_config = models.JSONField(default=dict, blank=False, null=False)
    # ... existing fields ...
```

**Storage contract:** `extra_config` is **always a dict** at the DB layer — never `null`, never missing. `null=False` enforces it on the column; `default=dict` ensures every new row is created with `{}`.

**Migration:** `DDP_backend/ddpui/migrations/00XX_kpi_extra_config.py`
- `AddField` for `extra_config` with `default=dict`
- Django backfills every existing KPI row with `{}` when the migration runs — no separate data-migration step needed.
- After the migration, GET on a pre-v1.1 KPI returns `extra_config: {}` (i.e. `customizations` absent — frontend must check before reading).

### 4.2 API design — fully typed `extra_config`, no defaults

KPI has a single, stable customization shape (unlike `Chart.extra_config`, which varies per chart_type and stays a loose dict). So we type the whole tree at the API boundary AND make `extra_config` a **required** field on every request — the KPI form will always send it.

**`DDP_backend/ddpui/schemas/kpi_schema.py`:**

```python
from ddpui.schemas.chart_schemas.customizations import NumberChartCustomizations

class KPIExtraConfig(Schema):
    """Typed container for KPI.extra_config. `customizations` is optional inside."""
    customizations: Optional[NumberChartCustomizations] = None

class KPICreate(Schema):
    # ... existing fields ...
    extra_config: KPIExtraConfig                       # required, no default

class KPIUpdate(Schema):
    # ... existing fields ...
    extra_config: KPIExtraConfig                       # required, no default

class KPISchema(Schema):
    # ... existing fields ...
    extra_config: KPIExtraConfig                       # always present — DB guarantees {} via default=dict + null=False
```

**Contract enforced:**
- `extra_config` is **required on every Create/Update request** — the KPI form (being updated for this feature) always sends it, so this is fine. Older clients that omit it will get a 422 — surface in the v1.1 release note.
- `extra_config` on every **response** is always a populated object — never `null`, never missing. Backed by `null=False` + `default=dict` on the DB column and the migration backfill.
- `extra_config.customizations` is **optional** — frontend MUST check existence before reading `numberFormat` / `decimalPlaces` / etc. For pre-v1.1 KPIs (backfilled to `{}`), `customizations` will be absent.
- Unknown keys inside `extra_config` or `customizations` are rejected at the API boundary by Pydantic.

**Frontend mirror** (`webapp_v2/types/kpi.ts` or wherever KPI types live):

```typescript
type KPICustomizations = Pick<
  ChartCustomizations,
  'numberFormat' | 'decimalPlaces' | 'numberPrefix' | 'numberSuffix'
>;

type KPIExtraConfig = {
  customizations?: KPICustomizations;   // optional — MUST be checked
};

type KPI = {
  // ... existing fields ...
  extra_config: KPIExtraConfig;          // NOT optional — always present
};
```

**Validation rules** (enforced automatically by Pydantic via `NumberChartCustomizations`):
- `customizations.decimalPlaces` ∈ [0, 10]
- `customizations.numberFormat` ∈ existing `NumberFormat` literal (7 values)
- `customizations.numberPrefix` / `numberSuffix` — free-text strings, plain-text rendered (no XSS).

### 4.3 Backend logic

**New file:** `DDP_backend/ddpui/core/charts/number_formatting.py`

```python
from typing import Optional
from babel.numbers import format_decimal

def format_number_v2(
    value: Optional[float],
    format_type: str = "default",
    decimal_places: int = 0,
    prefix: str = "",
    suffix: str = "",
) -> str:
    """Format a numeric value for display.
    Mirrors webapp_v2/lib/formatters.ts:formatNumber + chart-formatting-utils prefix/suffix wrap.

    Returns "No data" for None/NaN — without prefix/suffix wrap.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "No data"

    if format_type == "percentage":
        formatted = f"{value:.{decimal_places}f}%"
    elif format_type == "currency":
        formatted = f"${value:,.{decimal_places}f}"
    elif format_type == "indian":
        formatted = format_decimal(value, locale="en_IN", format=f"#,##,##0.{'0' * decimal_places}")
    elif format_type == "european":
        formatted = format_decimal(value, locale="de_DE", format=f"#,##0.{'0' * decimal_places}")
    elif format_type == "international":
        formatted = format_decimal(value, locale="en_US", format=f"#,##0.{'0' * decimal_places}")
    elif format_type in ("adaptive_indian", "adaptive_international"):
        # Compact: 1.2K / 1.5M / 1.2L / 1.5Cr — port from frontend formatNumber
        # See research.md for frontend reference
        formatted = _format_adaptive(value, format_type, decimal_places)
    else:  # default
        if decimal_places > 0:
            formatted = f"{value:.{decimal_places}f}"
        else:
            formatted = str(int(value)) if value == int(value) else str(value)

    return f"{prefix}{formatted}{suffix}"
```

**Modified:** `DDP_backend/ddpui/core/charts/echarts_config_generator.py:89–112`
- `_format_number()` delegates to `number_formatting.format_number_v2`
- No behavior change for existing number chart consumers

**Modified:** `DDP_backend/ddpui/core/alerts/rendering.py:52` (or equivalent token-resolution site)
- For `kpi_rag` alerts, resolve `{{current_value}}` by calling `format_number_v2` with the KPI's `extra_config.customizations`
- KPI lookup already happens in this rendering path

**Modified:** Snapshot freeze code — grep `FrozenKpiConfig(` call sites in `DDP_backend/ddpui/core/`. At freeze time, copy `kpi.extra_config.get("customizations")` into the `FrozenKpiConfig.customizations` field.

**Modified:** `DDP_backend/ddpui/schemas/report_schema.py:59` — `FrozenKpiConfig`
- Add `customizations: Optional[Dict[str, Any]] = None`

**New dependency:** Add `babel` to `DDP_backend/pyproject.toml`.

### 4.4 Frontend components

**Modified:** `webapp_v2/components/charts/types/number/NumberChartCustomizations.tsx`
- **Extract** the number-format, decimals, prefix, suffix block into a reusable `<NumberFormatPanel value={…} onChange={…} />` component
- Co-locate in `webapp_v2/components/shared/NumberFormatPanel.tsx` or `webapp_v2/components/charts/shared/`
- `NumberChartCustomizations` re-imports the panel — no behavior change for number charts

**Modified:** `webapp_v2/components/kpis/kpi-form.tsx` (Step 2, around line 578 — after RAG/time-config, before tags)
- Insert `<NumberFormatPanel />` reading from `formData.extra_config?.customizations`, writing back to `formData.extra_config.customizations`

**Modified:** `webapp_v2/lib/formatters.ts`
- Add:
  ```ts
  export function formatKPIValue(
    value: number | null | undefined,
    customizations?: { numberFormat?: NumberFormat; decimalPlaces?: number; numberPrefix?: string; numberSuffix?: string },
  ): string {
    if (value == null || Number.isNaN(value)) return "No data";
    const formatted = formatNumber(value, {
      format: customizations?.numberFormat ?? "default",
      decimalPlaces: customizations?.decimalPlaces ?? 0,
    });
    return `${customizations?.numberPrefix ?? ""}${formatted}${customizations?.numberSuffix ?? ""}`;
  }
  ```

**Modified:** `webapp_v2/components/kpis/kpi-card.tsx`
- Line 281: `formatMetricValue(currentValue)` → `formatKPIValue(currentValue, kpi.extra_config?.customizations)`
- Line 285: target value renders via same swap

**Modified:** `webapp_v2/components/kpis/kpi-detail-drawer.tsx`
- Header current value + target render → `formatKPIValue(...)`

**Modified:** `webapp_v2/components/dashboard/kpi-chart-element.tsx`
- Verify the widget consumes value via `KPICard` (auto-inherits) OR directly — apply `formatKPIValue` if direct
- **No `applyNumberChartFormatting()` call** — see HLD § 3.4

**Modified:** ReportSnapshot KPI viewer (grep `frozen_chart_configs` consumers in `webapp_v2/`)
- Read `customizations` from the frozen blob, not the live KPI
- Pass to `formatKPIValue`

### 4.5 Integration points

- **`formatMetricValue` audit (M2 pre-work):** grep all call sites in `webapp_v2/` before swapping. Each site either gets the swap (KPI render contexts) or is explicitly documented as "stays raw" (CSV export, etc.).

---

## 5. Security Review

- **Auth & Authorization:** Existing `can_create_kpis`, `can_edit_kpis`, `can_view_kpis` permissions cover the new field — no new permission needed.
- **Input validation:** `extra_config.customizations` validated against `NumberChartCustomizations` Pydantic schema at API boundary. `decimalPlaces` bounded [0, 10]. `numberFormat` constrained to enum. `numberPrefix`/`numberSuffix` accept free-text strings.
- **XSS:** Prefix/suffix render in plain text via React (auto-escaped). Backend renders them into alert email bodies — email templates already escape HTML (verify with existing alert-rendering tests).
- **Multi-tenant access control:** `extra_config` is on the KPI row; same org-scoping as the rest of the KPI. No cross-tenant leak.
- **Injection risks:** No raw SQL involving customizations. Formatter takes typed inputs only.
- **External services:** None — formatting is local.
- **Rate limiting:** No new endpoints; existing throttling on `/api/kpis/` applies.

---

## 6. Testing Strategy

### Unit tests

**Backend (`DDP_backend/ddpui/tests/`):**
- `core/charts/test_number_formatting.py` (new) — every `(format_type × decimals × prefix × suffix × edge_case)` combination; ~30 cases. Edge cases: `None`, `0`, negative, very large, very small, `NaN`.
- `core/alerts/test_rendering.py` (extend) — `{{current_value}}` for a kpi_rag alert with KPI customizations emits formatted output; without customizations emits raw-equivalent default formatting.
- `api_tests/test_kpi_api.py` (extend) — POST + PUT round-trip `extra_config.customizations`; invalid `numberFormat` → 400; out-of-range `decimalPlaces` → 400.
- `core/services/test_report_service.py` (extend) — `FrozenKpiConfig` includes `customizations` at snapshot time; editing the KPI afterward does NOT mutate the snapshot.

**Frontend (`webapp_v2/`):**
- `lib/__tests__/formatters.test.ts` (extend) — `formatKPIValue` for each format, prefix/suffix combination, null guard.
- `components/kpis/__tests__/kpi-card.test.tsx` (extend) — KPI with no `extra_config` renders identically to v1 (snapshot test). KPI with each format renders expected string.
- `components/kpis/__tests__/kpi-form.test.tsx` (extend) — submitting the form persists `extra_config.customizations` in the API payload in the correct nested shape.

### Cross-stack parity test

Shared fixture file: `dalgo-core/tests/fixtures/number_format_parity.json` — ~12 representative tuples.
- Backend pytest reads the fixture, asserts `format_number_v2` matches expected string.
- Frontend Vitest reads the same fixture, asserts `formatKPIValue` matches expected string.
- CI fails if either diverges.

### Integration tests

- Playwright / Cypress: create a KPI with `format=indian`, `prefix=₹`, `decimals=0` → confirm card, drawer, and dashboard widget all show `₹1,23,456`.
- Snapshot E2E: create KPI → snapshot dashboard → edit KPI format → reload snapshot → snapshot still shows original format.

### Regression coverage (parent v1 must stay green)

- All existing `test_kpi_api.py`, `test_kpi_service.py`, `test_metric_api.py` tests pass without modification.
- A KPI row created via raw SQL with `extra_config={}` (simulating pre-migration state) renders correctly.
- All existing chart-formatting tests (`chart-formatting-utils.test.ts`, `echarts_config_generator` tests) pass.
- **Intentional behavior change in alert tests:** existing kpi_rag alert template tests need updated expectations because `{{current_value}}` now formats by default. Update test expectations explicitly.

### Specifically NOT tested (per scope)

- Trendline tooltip formatting (stays raw)
- Period-over-period delta formatting (stays raw)
- Annotation snapshot value formatting (stays raw)

Document these as "intentionally raw" in the spec so QA doesn't file them as bugs.

---

## 7. Milestones

Each milestone is independently shippable and reviewable as a single PR.

#### Milestone 1: Backend — schema, storage, parity formatter
- **Deliverable:** KPI model + API accept `extra_config.customizations`; new shared formatter module with babel; backend parity-fixture test passing.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Add `extra_config = JSONField(default=dict)` to KPI model
  - [ ] Migration `00XX_kpi_extra_config.py`
  - [ ] Extend `KPICreate`, `KPIUpdate`, `KPISchema` with typed `extra_config`
  - [ ] New `core/charts/number_formatting.py` with babel-backed `format_number_v2`
  - [ ] Delegate `echarts_config_generator._format_number` to new module
  - [ ] Add `babel` to `pyproject.toml`, update `uv.lock`
  - [ ] Backend unit tests + parity fixture
- **Acceptance:** POST `/api/kpis/` with `extra_config.customizations` round-trips; backend formatter produces correct output for all 7 format types; all existing chart tests still pass.

#### Milestone 2: Frontend — KPI form + card + drawer + dashboard widget
- **Deliverable:** UI surface where a user can set format options and see them on card, drawer, and dashboard widget.
- **Services:** webapp_v2
- **Key tasks:**
  - [ ] Extract `<NumberFormatPanel />` from `NumberChartCustomizations.tsx`
  - [ ] Insert panel in `kpi-form.tsx` Step 2
  - [ ] Add `formatKPIValue` to `lib/formatters.ts`
  - [ ] Swap call sites in `kpi-card.tsx`, `kpi-detail-drawer.tsx`
  - [ ] Verify dashboard widget renders correctly (no `applyNumberChartFormatting` call)
  - [ ] Vitest tests + frontend parity fixture
- **Acceptance:** Create a KPI with `format=indian`, `prefix=₹`, `decimals=0` → all three surfaces show `₹1,23,456`. A v1 KPI (no `extra_config`) renders identically to before.

#### Milestone 3: ReportSnapshot freeze + render
- **Deliverable:** Snapshots freeze the KPI format alongside data; historical snapshots render with the format active at snapshot time.
- **Services:** DDP_backend, webapp_v2
- **Key tasks:**
  - [ ] Extend `FrozenKpiConfig` with `customizations`
  - [ ] Snapshot freeze code copies `kpi.extra_config.customizations` at snapshot time
  - [ ] Snapshot viewer reads frozen `customizations` (not live KPI)
  - [ ] Backward-compat unit test: pre-v1.1 snapshots (no frozen customizations) render with no formatting
- **Acceptance:** Snapshot a dashboard with a formatted KPI; edit the KPI's format; reload snapshot → snapshot still shows the original format.

#### Milestone 4: Alert rendering — formatted `{{current_value}}`
- **Deliverable:** kpi_rag alert emails render the KPI value with prefix/suffix/format identical to the card.
- **Services:** DDP_backend
- **Key tasks:**
  - [ ] Update `core/alerts/rendering.py` to format `{{current_value}}` via `format_number_v2` + KPI customizations
  - [ ] Update existing alert-render tests with new expectations
  - [ ] Release note: existing kpi_rag templates now emit formatted output
- **Acceptance:** A kpi_rag alert linked to a formatted KPI sends an email body where the value matches the KPI card render byte-for-byte (via parity fixture).

---

## 8. Open risks

1. **kpi_rag alert template behavior change.** Existing templates with `{{current_value}}` will start emitting formatted output as soon as M4 ships. User-confirmed but worth a release note.
2. **`extra_config` is required on Create/Update.** The KPI form is being updated in M2 to always send it, so this is fine. But any external API consumer that POSTs to `/api/kpis/` without `extra_config` will get a 422 after v1.1 ships. Document in the release note alongside the alert behavior change.
3. **Babel dependency.** New explicit Python dep in DDP_backend. Document in `uv.lock`. Babel is widely used and stable.
4. **ReportSnapshot back-compat.** Pre-v1.1 snapshots have no frozen `customizations`. Render path must fall back to "no formatting" (same as a v1 KPI), matching what those snapshots showed before. Explicit unit test required.
5. **`formatMetricValue` audit.** Quick grep in `webapp_v2/` before M2 to find every call site — easy to miss one (mobile view, CSV export, PDF export if any). Each site either gets the swap or is documented as "stays raw."
6. **Compact formats (`adaptive_*`).** Frontend uses `formatNumber` with `Intl.NumberFormat` notation=compact; backend port via babel + manual logic. Highest divergence risk — keep the parity-fixture coverage broad here.

---

## Next Step

Draft v1 of the enhancement plan saved at `features/metrics_kpis/v1.1/plan.md`. Review and tell me what to revise — architecture, scope, milestones, anything. When ready, run `/engineering/execute-plan features/metrics_kpis/v1.1/plan.md` to implement.
