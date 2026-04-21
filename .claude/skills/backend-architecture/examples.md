# Backend Examples & Reference

## Schema Validation Before External Operations

When calling DBT, Airbyte, or any external service, **always validate using schemas first**:

```python
# GOOD: Validate before calling DBT
from ddpui.schemas.dbt_schema import DBTOperationPayload

class DBTService:
    @staticmethod
    def run_operation(payload: dict, org: Org) -> dict:
        # Validate using schema before hitting DBT
        validated_payload = DBTOperationPayload(**payload)

        # Now safe to call DBT
        result = dbt_client.run(validated_payload.dict())
        return result

# BAD: Calling DBT without validation
class DBTService:
    @staticmethod
    def run_operation(payload: dict, org: Org) -> dict:
        # Directly calling DBT without validation
        result = dbt_client.run(payload)  # Dangerous!
        return result
```

---

## Response Format

**Success Response:**
```json
{
    "success": true,
    "message": "Chart created successfully",
    "data": {
        "id": 1,
        "title": "Sales Overview",
        "created_at": "2025-01-22T10:00:00Z"
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "message": "Chart not found",
    "error_code": "CHART_NOT_FOUND"
}
```

**List Response:**
```json
{
    "success": true,
    "data": {
        "data": [...],
        "total": 100,
        "page": 1,
        "page_size": 10
    }
}
```

### Usage Examples

```python
# Simple success
return api_response(success=True, message="Operation completed")

# Success with data
return api_response(
    success=True,
    data=ChartResponse.from_model(chart),
    message="Chart created"
)

# List response
return api_response(
    success=True,
    data=ChartListResponse(
        data=[ChartResponse.from_model(c) for c in charts],
        total=total,
        page=page,
        page_size=page_size,
    )
)
```

---

## Request-Response Flow

```
1. Client Request
   ↓
2. API Layer (api/{module}_api.py)
   ├── Validate request (Pydantic schema - automatic)
   ├── Check permissions (@has_permission)
   ├── Extract orguser from request
   └── Call core service method
   ↓
3. Core Layer (core/{module}/{module}_service.py)
   ├── Business logic validation
   ├── Validate payloads before external calls (using schemas)
   ├── Transaction management
   ├── Call operations (if needed)
   ├── Database operations (via models)
   └── Return model instance
   ↓
4. Core Operations (core/{module}/{module}_operations.py) - Optional
   ├── Domain operations
   ├── External service calls (DBT, Airbyte)
   └── Data transformations
   ↓
5. Model Layer (models/{module}.py)
   └── Database operations
   ↓
6. Core Layer (return)
   └── Return model instance
   ↓
7. API Layer (serialize)
   ├── Convert model to response schema
   ├── Wrap with api_response()
   └── Return HTTP response
   ↓
8. Client Response
```

---

## Complete Example: Charts Module

### Module Structure

```
ddpui/
├── api/
│   └── charts_api.py                # HTTP request/response handling
├── core/
│   └── charts/
│       ├── __init__.py
│       ├── chart_service.py         # Business logic and orchestration
│       ├── chart_operations.py      # Query building, data transformation
│       ├── chart_validator.py       # Validation logic
│       ├── exceptions.py            # Chart-specific exceptions
│       └── echarts_config_generator.py  # ECharts configuration
├── schemas/
│   └── chart_schema.py              # All chart schemas
└── models/
    └── chart.py                     # Chart database model
```

### `core/charts/__init__.py`
```python
# Keep empty — all imports should use full paths like:
# from ddpui.core.charts.chart_service import ChartService
# Do NOT add re-exports or __all__ here.
```

### `exceptions.py`
```python
"""Chart exceptions"""


class ChartError(Exception):
    """Base exception for chart errors"""

    def __init__(self, message: str, error_code: str = "CHART_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ChartNotFoundError(ChartError):
    def __init__(self, chart_id: int):
        super().__init__(f"Chart with id {chart_id} not found", "CHART_NOT_FOUND")
        self.chart_id = chart_id


class ChartValidationError(ChartError):
    def __init__(self, message: str):
        super().__init__(message, "CHART_VALIDATION_ERROR")


class ChartPermissionError(ChartError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "CHART_PERMISSION_DENIED")
```

### `schemas/chart_schema.py`
```python
"""Chart schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from ninja import Schema, Field


class ChartCreate(Schema):
    title: str = Field(..., min_length=1, max_length=255)
    chart_type: str = Field(..., description="Type of chart (bar, line, pie, etc.)")
    schema_name: str = Field(..., description="Database schema name")
    table_name: str = Field(..., description="Database table name")
    description: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChartUpdate(Schema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None


class ChartResponse(Schema):
    id: int
    title: str
    chart_type: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, chart) -> "ChartResponse":
        return cls(
            id=chart.id,
            title=chart.title,
            chart_type=chart.chart_type,
            description=chart.description,
            created_at=chart.created_at,
            updated_at=chart.updated_at,
        )


class ChartListResponse(Schema):
    data: List[ChartResponse]
    total: int
    page: int
    page_size: int
```

### Example Flow: Creating a Chart

```python
# 1. Client sends POST /api/charts/
{
    "title": "Sales Overview",
    "chart_type": "bar",
    "schema_name": "public",
    "table_name": "sales"
}

# 2. API Layer (api/charts_api.py)
@charts_router.post("/", response=ApiResponse[ChartResponse])
@has_permission(["can_create_charts"])
def create_chart(request, payload: ChartCreate):
    orguser = request.orguser
    chart = ChartService.create_chart(payload, orguser)
    return api_response(
        success=True,
        data=ChartResponse.from_model(chart),
        message="Chart created successfully"
    )

# 3. Core Service Layer (core/charts/chart_service.py)
class ChartService:
    @staticmethod
    def create_chart(data: ChartCreate, orguser: OrgUser) -> Chart:
        ChartService._validate_business_rules(data, orguser.org)

        dbt_payload = ChartDBTPayload(
            operation="validate_table",
            schema=data.schema_name,
            table=data.table_name,
        )

        chart = Chart.objects.create(
            title=data.title,
            chart_type=data.chart_type,
            schema_name=data.schema_name,
            table_name=data.table_name,
            created_by=orguser,
            org=orguser.org,
        )
        return chart

# 4. Final Response
{
    "success": true,
    "message": "Chart created successfully",
    "data": {
        "id": 1,
        "title": "Sales Overview",
        "chart_type": "bar"
    }
}
```

### Exception Usage in API Layer

```python
from ddpui.core.{module}.exceptions import (
    {Module}NotFoundError,
    {Module}ValidationError,
    {Module}PermissionError,
    {Module}ExternalServiceError,
)

@{module}_router.get("/{{id}}/")
@has_permission(["can_view_{module}s"])
def get_{module}(request, id: int):
    try:
        {module} = {Module}Service.get_{module}(id, request.orguser.org)
        return api_response(success=True, data={Module}Response.from_model({module}))
    except {Module}NotFoundError as err:
        raise HttpError(404, str(err)) from err
    except {Module}ValidationError as err:
        raise HttpError(400, str(err)) from err
    except {Module}PermissionError as err:
        raise HttpError(403, str(err)) from err
    except {Module}ExternalServiceError as err:
        raise HttpError(502, str(err)) from err
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HttpError(500, "Internal server error") from e
```

---

## Key Changes from Previous Architecture

| Before | After |
|--------|-------|
| `services/{module}_service.py` | `core/{module}/{module}_service.py` |
| `schemas/{module}_schema.py` | `schemas/{module}_schema.py` (unchanged) |
| `models/{module}.py` | `models/{module}.py` (unchanged) |
| Exceptions in service file | `core/{module}/exceptions.py` |
| `model.to_json()` | `Schema.from_model(model)` |
| Direct response dict | `api_response()` wrapper |
| No validation before DBT | Schema validation required |
