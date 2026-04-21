# Backend Code Templates

## Standard Module Structure

```
ddpui/
├── api/
│   └── {module}_api.py              # HTTP request/response handling
│
├── core/
│   └── {module}/                    # Feature module (all business logic here)
│       ├── __init__.py              # Keep empty (no re-exports or __all__)
│       ├── {module}_service.py      # Business logic and orchestration
│       ├── {module}_operations.py   # Domain operations (optional)
│       └── exceptions.py            # Custom exceptions for this feature
│
├── schemas/
│   └── {module}_schema.py           # Request/response validation (Pydantic)
│
├── models/
│   └── {module}.py                  # Database models (Django ORM)
│
└── utils/
    └── response_wrapper.py          # API response wrapper utility
```

**Note**: Models and schemas live in their own top-level folders (`models/` and `schemas/`), separate from `core/`. This keeps the codebase organized and avoids circular imports.

---

## API Structure Template

`ddpui/api/{module}_api.py`

```python
"""{Module} API endpoints"""

from typing import Optional, List
from ninja import Router
from ninja.errors import HttpError

from ddpui.auth import has_permission
from ddpui.models.org_user import OrgUser
from ddpui.utils.custom_logger import CustomLogger
from ddpui.utils.response_wrapper import api_response, ApiResponse

# Import from core module
from ddpui.core.{module}.{module}_service import {Module}Service
from ddpui.core.{module}.exceptions import (
    {Module}NotFoundError,
    {Module}ValidationError,
    {Module}PermissionError,
)

# Import schemas
from ddpui.schemas.{module}_schema import (
    {Module}Create,
    {Module}Update,
    {Module}Response,
    {Module}ListResponse,
)

logger = CustomLogger("ddpui.{module}_api")

{module}_router = Router()


@{module}_router.get("/", response=ApiResponse[{Module}ListResponse])
@has_permission(["can_view_{module}s"])
def list_{module}s(request, page: int = 1, page_size: int = 10):
    """List {module}s with pagination"""
    orguser: OrgUser = request.orguser

    {module}s, total = {Module}Service.list_{module}s(
        org=orguser.org,
        page=page,
        page_size=page_size,
    )

    return api_response(
        success=True,
        data={Module}ListResponse(
            data=[{Module}Response.from_model(m) for m in {module}s],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@{module}_router.get("/{{id}}/", response=ApiResponse[{Module}Response])
@has_permission(["can_view_{module}s"])
def get_{module}(request, id: int):
    """Get a specific {module}"""
    orguser: OrgUser = request.orguser

    try:
        {module} = {Module}Service.get_{module}(id, orguser.org)
        return api_response(
            success=True,
            data={Module}Response.from_model({module})
        )
    except {Module}NotFoundError as err:
        raise HttpError(404, str(err)) from err


@{module}_router.post("/", response=ApiResponse[{Module}Response])
@has_permission(["can_create_{module}s"])
def create_{module}(request, payload: {Module}Create):
    """Create a new {module}"""
    orguser: OrgUser = request.orguser

    try:
        # Schema validation happens automatically via Pydantic
        {module} = {Module}Service.create_{module}(payload, orguser)
        return api_response(
            success=True,
            data={Module}Response.from_model({module}),
            message="{Module} created successfully"
        )
    except {Module}ValidationError as err:
        raise HttpError(400, str(err)) from err
    except Exception as e:
        logger.error(f"Error creating {module}: {e}")
        raise HttpError(500, "Failed to create {module}") from e


@{module}_router.put("/{{id}}/", response=ApiResponse[{Module}Response])
@has_permission(["can_edit_{module}s"])
def update_{module}(request, id: int, payload: {Module}Update):
    """Update a {module}"""
    orguser: OrgUser = request.orguser

    try:
        {module} = {Module}Service.update_{module}(
            {module}_id=id,
            org=orguser.org,
            orguser=orguser,
            data=payload,
        )
        return api_response(
            success=True,
            data={Module}Response.from_model({module}),
            message="{Module} updated successfully"
        )
    except {Module}NotFoundError as err:
        raise HttpError(404, str(err)) from err
    except {Module}ValidationError as err:
        raise HttpError(400, str(err)) from err


@{module}_router.delete("/{{id}}/", response=ApiResponse)
@has_permission(["can_delete_{module}s"])
def delete_{module}(request, id: int):
    """Delete a {module}"""
    orguser: OrgUser = request.orguser

    try:
        {Module}Service.delete_{module}(id, orguser.org, orguser)
        return api_response(success=True, message="{Module} deleted successfully")
    except {Module}NotFoundError as err:
        raise HttpError(404, str(err)) from err
    except {Module}PermissionError as err:
        raise HttpError(403, str(err)) from err
```

---

## Service Template

`ddpui/core/{module}/{module}_service.py`

```python
"""{Module} service for business logic

This module encapsulates all {module}-related business logic,
separating it from the API layer for better testability and maintainability.
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass

from django.db.models import Q
from django.db import transaction

from ddpui.models.org import Org
from ddpui.models.org_user import OrgUser
from ddpui.utils.custom_logger import CustomLogger

# Import exceptions from same core module
from .exceptions import (
    {Module}NotFoundError,
    {Module}ValidationError,
    {Module}PermissionError,
)

# Import schemas from schemas folder
from ddpui.schemas.{module}_schema import {Module}Create, {Module}Update

# Import model from models folder
from ddpui.models.{module} import {Module}

logger = CustomLogger("ddpui.core.{module}")


class {Module}Service:
    """Service class for {module}-related operations"""

    @staticmethod
    def get_{module}({module}_id: int, org: Org) -> {Module}:
        """Get a {module} by ID for an organization.

        Args:
            {module}_id: The {module} ID
            org: The organization

        Returns:
            {Module} instance

        Raises:
            {Module}NotFoundError: If {module} doesn't exist or doesn't belong to org
        """
        try:
            return {Module}.objects.get(id={module}_id, org=org)
        except {Module}.DoesNotExist:
            raise {Module}NotFoundError({module}_id)

    @staticmethod
    def list_{module}s(
        org: Org,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> Tuple[List[{Module}], int]:
        """List {module}s for an organization with pagination and filtering.

        Args:
            org: The organization
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term

        Returns:
            Tuple of ({module}s list, total count)
        """
        query = Q(org=org)

        if search:
            query &= Q(title__icontains=search) | Q(description__icontains=search)

        queryset = {Module}.objects.filter(query).order_by("-updated_at")
        total = queryset.count()

        offset = (page - 1) * page_size
        {module}s = list(queryset[offset : offset + page_size])

        return {module}s, total

    @staticmethod
    def create_{module}(data: {Module}Create, orguser: OrgUser) -> {Module}:
        """Create a new {module}.

        Args:
            data: {Module} creation data (already validated by Pydantic)
            orguser: The user creating the {module}

        Returns:
            Created {Module} instance

        Raises:
            {Module}ValidationError: If {module} configuration is invalid
        """
        # Additional business logic validation
        {Module}Service._validate_business_rules(data, orguser.org)

        # Create {module}
        {module} = {Module}.objects.create(
            title=data.title,
            description=data.description,
            created_by=orguser,
            last_modified_by=orguser,
            org=orguser.org,
        )

        logger.info(f"Created {module} {{{module}.id}} for org {{{orguser.org.id}}}")
        return {module}

    @staticmethod
    def update_{module}(
        {module}_id: int,
        org: Org,
        orguser: OrgUser,
        data: {Module}Update,
    ) -> {Module}:
        """Update an existing {module}.

        Args:
            {module}_id: The {module} ID
            org: The organization
            orguser: The user making the update
            data: Update data (already validated by Pydantic)

        Returns:
            Updated {Module} instance

        Raises:
            {Module}NotFoundError: If {module} doesn't exist
            {Module}ValidationError: If updated configuration is invalid
        """
        {module} = {Module}Service.get_{module}({module}_id, org)

        # Apply updates only for provided fields
        if data.title is not None:
            {module}.title = data.title
        if data.description is not None:
            {module}.description = data.description

        {module}.last_modified_by = orguser
        {module}.save()

        logger.info(f"Updated {module} {{{module}.id}}")
        return {module}

    @staticmethod
    def delete_{module}({module}_id: int, org: Org, orguser: OrgUser) -> bool:
        """Delete a {module}.

        Args:
            {module}_id: The {module} ID
            org: The organization
            orguser: The user deleting the {module}

        Returns:
            True if deletion was successful

        Raises:
            {Module}NotFoundError: If {module} doesn't exist
            {Module}PermissionError: If user doesn't have permission
        """
        {module} = {Module}Service.get_{module}({module}_id, org)

        # Permission check (example: only creator can delete)
        if {module}.created_by != orguser:
            raise {Module}PermissionError("You can only delete {module}s you created.")

        {module}_title = {module}.title
        {module}.delete()

        logger.info(f"Deleted {module} '{{{module}_title}}' (id={{{module}_id}}) by {{{orguser.user.email}}}")
        return True

    @staticmethod
    def _validate_business_rules(data: {Module}Create, org: Org) -> None:
        """Validate business rules before creating {module}.

        This is where you add domain-specific validation that goes beyond
        schema validation.

        Raises:
            {Module}ValidationError: If validation fails
        """
        # Example: Check for duplicate titles
        if {Module}.objects.filter(org=org, title=data.title).exists():
            raise {Module}ValidationError(f"{Module} with title '{data.title}' already exists")
```

---

## Schema Structure Template

`ddpui/schemas/{module}_schema.py`

```python
"""{Module} schemas for request/response validation"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from ninja import Schema, Field


# =============================================================================
# Request Schemas
# =============================================================================

class {Module}Create(Schema):
    """Schema for creating a {module}"""
    title: str = Field(..., min_length=1, max_length=255, description="Title of the {module}")
    description: Optional[str] = Field(None, max_length=1000, description="Description")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Example {Module}",
                "description": "Example description",
            }
        }


class {Module}Update(Schema):
    """Schema for updating a {module} (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class {Module}ListQuery(Schema):
    """Schema for list query parameters"""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(None, description="Search term")


# =============================================================================
# Response Schemas
# =============================================================================

class {Module}Response(Schema):
    """Schema for {module} response"""
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model) -> "{Module}Response":
        """Create response from Django model instance"""
        return cls(
            id=model.id,
            title=model.title,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Example {Module}",
                "description": "Example description",
                "created_at": "2025-01-22T10:00:00Z",
                "updated_at": "2025-01-22T10:00:00Z",
            }
        }


class {Module}ListResponse(Schema):
    """Schema for paginated {module} list response"""
    data: List[{Module}Response]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


# =============================================================================
# Internal/Operation Schemas (for validating before external calls)
# =============================================================================

class {Module}DBTPayload(Schema):
    """Schema for validating payload before sending to DBT"""
    operation: str
    config: Dict[str, Any]

    class Config:
        extra = "forbid"  # Strict validation - no extra fields allowed
```

---

## Model Structure Template

`ddpui/models/{module}.py`

```python
"""{Module} model for Dalgo platform"""

from django.db import models
from ddpui.models.org import Org
from ddpui.models.org_user import OrgUser


class {Module}(models.Model):
    """{Module} configuration model"""

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Relationships
    org = models.ForeignKey(Org, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        OrgUser,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="{module}s_created"
    )
    last_modified_by = models.ForeignKey(
        OrgUser,
        on_delete=models.CASCADE,
        db_column="last_modified_by",
        null=True,
        related_name="{module}s_modified"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "{module}"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["org", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.id})"
```

---

## Exception Structure Template

`ddpui/core/{module}/exceptions.py`

```python
"""{Module} exceptions

Custom exceptions for {module} feature.
"""


class {Module}Error(Exception):
    """Base exception for {module} errors"""

    def __init__(self, message: str, error_code: str = "{MODULE}_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class {Module}NotFoundError({Module}Error):
    """Raised when {module} is not found"""

    def __init__(self, {module}_id: int):
        super().__init__(
            f"{Module} with id {{{module}_id}} not found",
            "{MODULE}_NOT_FOUND"
        )
        self.{module}_id = {module}_id


class {Module}ValidationError({Module}Error):
    """Raised when {module} validation fails"""

    def __init__(self, message: str):
        super().__init__(message, "{MODULE}_VALIDATION_ERROR")


class {Module}PermissionError({Module}Error):
    """Raised when user doesn't have permission"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "{MODULE}_PERMISSION_DENIED")


class {Module}ExternalServiceError({Module}Error):
    """Raised when external service (DBT, Airbyte) call fails"""

    def __init__(self, service: str, message: str):
        super().__init__(
            f"{service} error: {message}",
            "{MODULE}_EXTERNAL_ERROR"
        )
        self.service = service
```

### Exception Hierarchy and HTTP Mapping

```
{Module}Error (base)
  ├── {Module}NotFoundError      → 404 Not Found
  ├── {Module}ValidationError    → 400 Bad Request
  ├── {Module}PermissionError    → 403 Forbidden
  ├── {Module}ExternalServiceError → 502 Bad Gateway
  └── {Module}Error (generic)    → 500 Internal Server Error
```
