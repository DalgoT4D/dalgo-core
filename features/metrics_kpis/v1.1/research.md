# KPI v1.1 — Research

**Date:** 2026-06-24
**Plan:** [plan.md](./plan.md)

This document captures the codebase findings backing the v1.1 plan. The enhancement mirrors the **number chart's** existing formatting pattern onto the **KPI** model and its render surfaces.

---

## 1. Number chart formatting — reference pattern

### Frontend config UI

**Component:** `webapp_v2/components/charts/types/number/NumberChartCustomizations.tsx` (lines 1–107)

Form fields exposed:
- `numberSize` (radio: small / medium / large) — lines 29–45
- `subtitle` (text input) — lines 49–60
- `numberFormat` (via `NumberFormatSection`) — lines 67–74
- `decimalPlaces` (integer, 0–10) — lines 67–74
- `numberPrefix` (text input) — lines 82–91
- `numberSuffix` (text input) — lines 94–103

**Fields KPI v1.1 inherits:** `numberFormat`, `decimalPlaces`, `numberPrefix`, `numberSuffix`. (No `numberSize` — KPI has its own card layout. No `subtitle` — KPI already has name/description.)

### Frontend customizations type

`webapp_v2/lib/chart-formatting-utils.ts` (lines 18–30):

```typescript
export interface ChartCustomizations {
  numberFormat?: NumberFormat;
  decimalPlaces?: number;
  numberPrefix?: string;
  numberSuffix?: string;
  // ... other chart-specific fields
}
```

This is the exact shape we lift onto KPI under `extra_config.customizations`.

### Frontend render-time formatter

**Function:** `formatNumber()` in `webapp_v2/lib/formatters.ts` (lines 135–230)

Signature:
```typescript
export function formatNumber(value: number, options: FormatOptions | NumberFormat): string
```

Supported formats:
```typescript
type NumberFormat = 'default' | 'percentage' | 'currency'
  | 'indian' | 'international' | 'european'
  | 'adaptive_international' | 'adaptive_indian';
```

**Library under the hood:** native `Number.toLocaleString()` (Intl.NumberFormat) with locale variants — `en-US`, `en-IN`, `de-DE`. No external dependency on the frontend.

### Frontend prefix/suffix application

`webapp_v2/lib/chart-formatting-utils.ts` (lines 213–233) — `applyNumberChartFormatting()`:

```typescript
const formatter = (value: number) => {
  const formatted = formatNumber(value, {
    format: numFormat,
    decimalPlaces: customizations.decimalPlaces,
  });
  return `${prefix}${formatted}${suffix}`;
};
```

**Critical:** This function mutates `config.series[0].detail.formatter` — which is a **gauge-specific** ECharts slot. The KPI widget renders a **line trendline + separate React text** for the current value — it has no `series[0].detail`. **KPI must NOT call `applyNumberChartFormatting()`**. Instead, KPI's current value (and target) are rendered as React text via `formatMetricValue()` in `kpi-card.tsx:281,285` — swap with `formatKPIValue()` at those sites.

### Backend customizations schema

`DDP_backend/ddpui/schemas/chart_schemas/customizations.py` (lines 121–132):

```python
class NumberChartCustomizations(BaseModel):
    """`extra_config.customizations` for chart_type='number'."""
    numberSize: Optional[Literal["small", "medium", "large"]] = None
    subtitle: Optional[str] = None
    numberFormat: Optional[NumberFormat] = None
    decimalPlaces: Optional[int] = Field(default=None, ge=0, le=10)
    numberPrefix: Optional[str] = None
    numberSuffix: Optional[str] = None
```

Shared `NumberFormat` Literal type — `customizations.py` (lines 8–17).

KPI v1.1 reuses this schema as the typed nested validator inside `KPICreate.extra_config` / `KPIUpdate.extra_config` / `KPISchema.extra_config`.

### Backend formatter (current)

`DDP_backend/ddpui/core/charts/echarts_config_generator.py` (lines 89–112) — `EChartsConfigGenerator._format_number`:

```python
@staticmethod
def _format_number(
    value: float, format_type: str, decimal_places: int, prefix: str = "", suffix: str = ""
) -> str:
    """Format number based on type, decimal places, prefix and suffix"""
    if format_type == "percentage":
        formatted = f"{value:.{decimal_places}f}%"
    elif format_type == "currency":
        formatted = f"${value:,.{decimal_places}f}"
    else:  # default
        if decimal_places > 0:
            formatted = f"{value:.{decimal_places}f}"
        else:
            formatted = str(int(value)) if value == int(value) else str(value)

    if prefix or suffix:
        return f"{prefix}{formatted}{suffix}"
    return formatted
```

**Parity gap with frontend:** Only handles `default`, `percentage`, `currency`. **Does NOT handle** `indian`, `european`, `international`, `adaptive_*`. Per v1.1 plan, we extract this into a new `core/charts/number_formatting.py` and upgrade it with `babel` to match the frontend's 7-format set.

### Backend endpoint touchpoints (Chart, today)

`DDP_backend/ddpui/api/charts_api.py`:
- `POST /create_chart` (line 1093) — `payload: ChartCreate` → stores `extra_config`
- `PUT /update_chart` (line 1148) — `payload: ChartUpdate` → updates `extra_config`

`ChartCreate` / `ChartUpdate` at `DDP_backend/ddpui/schemas/chart_schema.py` (lines 18–39). Both accept `extra_config: dict`.

---

## 2. KPI current state — where v1.1 plugs in

### KPI Django model

`DDP_backend/ddpui/models/metric.py` (lines 84–129):

Current fields (no formatting yet):
```
id, metric (FK), name, target_value, direction,
green_threshold_pct, amber_threshold_pct,
time_grain, time_dimension_column, metric_type_tag,
program_tags (JSONField), annotations (JSONField),
display_order, org (FK), created_by, last_modified_by
```

**v1.1 adds:** `extra_config = models.JSONField(default=dict, blank=True)`.

### KPI Pydantic schemas

`DDP_backend/ddpui/schemas/kpi_schema.py` (lines 13–62):
- `KPICreate` — accepts all KPI creation fields
- `KPIUpdate` — same, all Optional
- `KPISchema` — response shape

**v1.1 adds:** `extra_config: Optional[Dict[str, Any]] = None` (Create / Update), `extra_config: Dict = {}` (Schema response default).

### KPI frontend form

`webapp_v2/components/kpis/kpi-form.tsx` (lines 1–649):
- Step 1: Metric picker + Name + Target + Direction (lines 335–428)
- Step 2: RAG thresholds + Time config (lines 431–626)

**v1.1 adds:** `<NumberFormatPanel />` in Step 2, near line 578 (between RAG/time-config and Program Tags).

### KPI render components

| Component | Path | Where formatting plugs in |
|---|---|---|
| Card (KPIs page) | `webapp_v2/components/kpis/kpi-card.tsx` | Lines 281, 285 — currently call `formatMetricValue(currentValue)` and target render. Swap to `formatKPIValue(value, kpi.extra_config?.customizations)` |
| Detail drawer | `webapp_v2/components/kpis/kpi-detail-drawer.tsx` | Header current value + target — same swap |
| Dashboard widget | `webapp_v2/components/dashboard/kpi-chart-element.tsx` (line 31 consumes `echartsConfig` from `useKPIData`) | Verify it inherits via `KPICard` render path. **No `applyNumberChartFormatting` call** (gauge-specific) |

### Today's formatter

`webapp_v2/lib/formatters.ts` — `formatMetricValue()` (line 18 referenced by `kpi-card.tsx`). v1.1 replaces this call with a new `formatKPIValue(value, customizations)` that wraps `formatNumber()` + prefix/suffix + null guard.

---

## 3. ReportSnapshot — how KPI data is frozen

Per `docs/domain-map.md`, KPI chart data is already frozen into `Report.frozen_chart_configs` keyed by chart_id at snapshot time. **The format config needs to ride along inside that frozen JSON.**

`DDP_backend/ddpui/schemas/report_schema.py` (line 59) — `FrozenKpiConfig` is a strict Pydantic model. Extra fields don't silently pass through. v1.1 explicitly adds:

```python
class FrozenKpiConfig(BaseModel):
    # ... existing frozen fields ...
    customizations: Optional[Dict[str, Any]] = None
```

The snapshot freeze code (grep `FrozenKpiConfig(` in `DDP_backend/ddpui/core/`) copies `kpi.extra_config.get("customizations")` at snapshot time. Snapshots taken before v1.1 ship with `customizations=None` → renderer falls back to "no formatting" (same as a v1 KPI).

---

## 4. Alert — `kpi_rag` render path

Per `docs/domain-map.md`:
- `kpi_rag` alert has FK to KPI (`on_delete=CASCADE`)
- Message rendered via Mustache template
- Alert evaluates on a cron schedule (NOT pipeline events)

Current token resolution in `DDP_backend/ddpui/core/alerts/rendering.py` (line 52):
- `{{current_value}}` resolves via `str(v)` — emits raw scalar
- Existing templates assume raw: `tests/core/alerts/test_rendering.py:21` asserts `"value is 42"`

**v1.1 changes this in-place:** `{{current_value}}` now calls `format_number_v2` with the KPI's `extra_config.customizations`. **Behavior change** (user-confirmed): existing kpi_rag templates start emitting formatted output. Release note required.

---

## 5. Tests — existing patterns to mirror

**Number chart formatting tests:**
- Frontend: `webapp_v2/lib/__tests__/chart-formatting-utils.test.ts` — tests `applyNumberChartFormatting()` and `formatNumber()`
- Backend: `DDP_backend/ddpui/tests/api_tests/test_charts_api.py` (line 326)

**KPI test files to extend:**
- `DDP_backend/ddpui/tests/api_tests/test_kpi_api.py`
- `DDP_backend/ddpui/tests/services/test_kpi_service.py`
- `webapp_v2/components/kpis/__tests__/` (card logic + types)

**New test files:**
- `DDP_backend/ddpui/tests/core/charts/test_number_formatting.py` (new)
- `webapp_v2/lib/__tests__/formatters.test.ts` (extend)
- Shared parity fixture at `dalgo-core/tests/fixtures/number_format_parity.json` (new)

---

## 6. Reuse summary

| Need | Reuse from | Location |
|---|---|---|
| Frontend formatter | `formatNumber()` | `webapp_v2/lib/formatters.ts:135–230` |
| Frontend customizations TS type | `ChartCustomizations` interface | `webapp_v2/lib/chart-formatting-utils.ts:18–30` |
| Backend customizations schema | `NumberChartCustomizations` Pydantic | `DDP_backend/ddpui/schemas/chart_schemas/customizations.py:121–132` |
| Backend `NumberFormat` literal | shared Literal type | `DDP_backend/ddpui/schemas/chart_schemas/customizations.py:8–17` |
| Backend formatter (current) | `_format_number()` (to be extended) | `DDP_backend/ddpui/core/charts/echarts_config_generator.py:89–112` |
| Form-panel UI (to extract) | sub-block of `NumberChartCustomizations.tsx` | `webapp_v2/components/charts/types/number/NumberChartCustomizations.tsx:1–107` |

---

## 7. Non-reuse — things we deliberately DON'T mirror

| Why | Pattern |
|---|---|
| Gauge-specific | `applyNumberChartFormatting()` mutates `series[0].detail.formatter` — KPI widget has no gauge series. KPI uses React text + line trendline. |
| Backend formatter parity gap | Current `_format_number` only supports 3 formats. v1.1 ships a new `format_number_v2` (in a new shared module) with babel-backed locale support to match the frontend's 7 formats. The old method delegates to the new one for back-compat. |
| `numberSize` and `subtitle` | Chart-specific. KPI has its own card layout and name/description fields. |

---

## 8. Domain-map references

- **KPI entity** (`docs/domain-map.md`): `verified` confidence. Consumed by Dashboard (compose), ReportSnapshot (2-hop via Dashboard), Alert (reference).
- **ReportSnapshot** (`docs/domain-map.md`): "frozen layout, live data" — KPI chart data is frozen into `frozen_chart_configs` at snapshot time. v1.1 adds customizations to that frozen blob.
- **Alert** (`docs/domain-map.md`): `kpi_rag` type uses FK to KPI; cron-scheduled evaluation; direct email/Slack delivery (NOT via Notification entity).
