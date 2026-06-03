#!/usr/bin/env python3
"""
Run this on any machine with Python 3 and internet access.

Usage:
    python3 fix-pr-conflicts.py <your-github-token>

Your token needs: repo write access to DalgoT4D/dalgo-mcp
Create one at: https://github.com/settings/tokens → Fine-grained → dalgo-mcp → Contents: read+write
"""

import base64
import json
import sys
import urllib.request

if len(sys.argv) < 2:
    print("Usage: python3 fix-pr-conflicts.py <github-token>")
    sys.exit(1)

TOKEN = sys.argv[1]
OWNER = "DalgoT4D"
REPO  = "dalgo-mcp"


def api(method, path, body=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")
        raise


def push_file(branch, path, content, message):
    current = api("GET", f"contents/{path}?ref={branch}")
    sha = current["sha"]
    encoded = base64.b64encode(content.encode()).decode()
    result = api("PUT", f"contents/{path}", {
        "message": message,
        "content": encoded,
        "sha": sha,
        "branch": branch,
    })
    print(f"  ✓ {path} → {result['commit']['sha'][:8]}")


# ── PR #22: fix/pii-masking-chart-data ──────────────────────────────────────
print("\nPR #22 — fix/pii-masking-chart-data")
CHARTS_PII = '''\
import json

from mcp.server.fastmcp import FastMCP

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import ChartId
from dalgo_mcp.pii import mask_pii_in_rows


def register(app: FastMCP):

    @app.tool()
    async def dalgo_list_charts() -> str:
        """List all charts in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/charts/")
        return format_response(resp)

    @app.tool()
    async def dalgo_get_chart(chart_id: ChartId) -> str:
        """Get details of a specific chart.

        Args:
            chart_id: The chart ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/charts/{chart_id}/")
        return format_response(resp)

    @app.tool()
    async def dalgo_create_chart(chart_data: dict) -> str:
        """Create a new chart.

        Args:
            chart_data: Chart configuration dict with title, SQL query, chart type, and dashboard assignment.
        """
        client = await adapt_context()
        resp = await client.post("/api/charts/", json=chart_data)
        return format_response(resp)

    @app.tool()
    async def dalgo_update_chart(chart_id: ChartId, chart_data: dict) -> str:
        """Update an existing chart.

        Args:
            chart_data: Updated chart configuration dict.
        """
        client = await adapt_context()
        resp = await client.put(f"/api/charts/{chart_id}/", json=chart_data)
        return format_response(resp)

    @app.tool()
    async def dalgo_delete_chart(chart_id: ChartId) -> str:
        """Delete a chart.

        Args:
            chart_id: The chart ID.
        """
        client = await adapt_context()
        resp = await client.delete(f"/api/charts/{chart_id}/")
        return format_response(resp)

    @app.tool()
    async def dalgo_get_chart_data(chart_id: ChartId) -> str:
        """Execute a chart\'s query and return the resulting data.
        PII columns (name, email, phone, address, etc.) are automatically masked.

        Args:
            chart_id: The chart ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/charts/{chart_id}/data/")
        if resp.status_code < 400:
            try:
                body = resp.json()
                if isinstance(body, list):
                    return json.dumps(mask_pii_in_rows(body), indent=2, default=str)
                if isinstance(body, dict):
                    for key in ("data", "rows", "results"):
                        if key in body and isinstance(body[key], list):
                            body[key] = mask_pii_in_rows(body[key])
                            return json.dumps(body, indent=2, default=str)
            except Exception:
                pass
        return format_response(resp)
'''
push_file("fix/pii-masking-chart-data", "src/dalgo_mcp/tools/charts.py", CHARTS_PII,
          "fix: resolve conflict — add mask_pii_in_rows import alongside adapt_context")


# ── PR #26: feat/token-aware-truncation ──────────────────────────────────────
print("\nPR #26 — feat/token-aware-truncation")
PIPELINES_TRUNC = '''\
import json

from mcp.server.fastmcp import FastMCP

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import DeploymentId, FlowRunId, Limit
from dalgo_mcp.truncate import truncate_log_text


def register(app: FastMCP):

    @app.tool()
    async def dalgo_list_pipelines() -> str:
        """List all orchestration pipelines (Prefect deployments) in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/prefect/v1/flows/")
        return format_response(resp)

    @app.tool()
    async def dalgo_get_pipeline(deployment_id: DeploymentId) -> str:
        """Get details of a specific pipeline by its deployment ID.

        Args:
            deployment_id: The Prefect deployment ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/prefect/v1/flows/{deployment_id}")
        return format_response(resp)

    @app.tool()
    async def dalgo_create_pipeline(pipeline_data: dict) -> str:
        """Create a new orchestration pipeline.

        Args:
            pipeline_data: Pipeline configuration dict with connection_id, cron schedule, and transform settings.
        """
        client = await adapt_context()
        resp = await client.post("/api/prefect/v1/flows/", json=pipeline_data)
        return format_response(resp)

    @app.tool()
    async def dalgo_update_pipeline(deployment_id: DeploymentId, pipeline_data: dict) -> str:
        """Update an existing pipeline\'s configuration.

        Args:
            pipeline_data: Updated pipeline configuration dict.
        """
        client = await adapt_context()
        resp = await client.put(f"/api/prefect/v1/flows/{deployment_id}", json=pipeline_data)
        return format_response(resp)

    @app.tool()
    async def dalgo_delete_pipeline(deployment_id: DeploymentId) -> str:
        """Delete a pipeline by its deployment ID.

        Args:
            deployment_id: The Prefect deployment ID.
        """
        client = await adapt_context()
        resp = await client.delete(f"/api/prefect/v1/flows/{deployment_id}")
        return format_response(resp)

    @app.tool()
    async def dalgo_trigger_pipeline_run(deployment_id: DeploymentId) -> str:
        """Trigger an immediate run of a pipeline.

        Args:
            deployment_id: The Prefect deployment ID.
        """
        client = await adapt_context()
        resp = await client.post(f"/api/prefect/v1/flows/{deployment_id}/flow_run/")
        return format_response(resp)

    @app.tool()
    async def dalgo_get_pipeline_run_history(deployment_id: DeploymentId, limit: Limit = 10) -> str:
        """Get the run history for a specific pipeline.

        Args:
            deployment_id: The Prefect deployment ID.
            limit: Maximum number of runs to return (default 10).
        """
        client = await adapt_context()
        resp = await client.get(
            f"/api/prefect/v1/flows/{deployment_id}/flow_runs/history",
            params={"limit": limit},
        )
        return format_response(resp)

    @app.tool()
    async def dalgo_get_flow_run(flow_run_id: FlowRunId) -> str:
        """Get details of a specific flow run.

        Args:
            flow_run_id: The Prefect flow run ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/prefect/flow_runs/{flow_run_id}")
        return format_response(resp)

    @app.tool()
    async def dalgo_get_flow_run_logs(flow_run_id: FlowRunId) -> str:
        """Get logs for a specific flow run. Large logs are truncated to avoid context overflow —
        the response includes metadata showing how many lines were omitted.

        Args:
            flow_run_id: The Prefect flow run ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/prefect/flow_runs/{flow_run_id}/logs")

        if resp.status_code < 400:
            try:
                data = resp.json()
                if isinstance(data, str):
                    result = truncate_log_text(data)
                    return json.dumps(result, indent=2)
                elif isinstance(data, list):
                    text = "\\n".join(str(line) for line in data)
                    result = truncate_log_text(text)
                    return json.dumps(result, indent=2)
                elif isinstance(data, dict) and "logs" in data:
                    result = truncate_log_text(str(data["logs"]))
                    data["logs"] = result["content"]
                    data["_meta"] = result["_meta"]
                    return json.dumps(data, indent=2, default=str)
            except Exception:
                pass
        return format_response(resp)
'''
push_file("feat/token-aware-truncation", "src/dalgo_mcp/tools/pipelines.py", PIPELINES_TRUNC,
          "fix: resolve conflict — use adapt_context + typed params, add truncate imports")


# ── PR #29: feat/safety-annotations ──────────────────────────────────────────
print("\nPR #29 — feat/safety-annotations")

CHARTS_ANN = '''\
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import ChartId


def register(app: FastMCP):

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_charts() -> str:
        """List all charts in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/charts/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_chart(chart_id: ChartId) -> str:
        """Get details of a specific chart.

        Args:
            chart_id: The chart ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/charts/{chart_id}/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
    async def dalgo_create_chart(chart_data: dict) -> str:
        """Create a new chart.

        Args:
            chart_data: Chart configuration dict with title, SQL query, chart type, and dashboard assignment.
        """
        client = await adapt_context()
        resp = await client.post("/api/charts/", json=chart_data)
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True))
    async def dalgo_update_chart(chart_id: ChartId, chart_data: dict) -> str:
        """Update an existing chart.

        Args:
            chart_data: Updated chart configuration dict.
        """
        client = await adapt_context()
        resp = await client.put(f"/api/charts/{chart_id}/", json=chart_data)
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
    async def dalgo_delete_chart(chart_id: ChartId) -> str:
        """Delete a chart.

        Args:
            chart_id: The chart ID.
        """
        client = await adapt_context()
        resp = await client.delete(f"/api/charts/{chart_id}/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_chart_data(chart_id: ChartId) -> str:
        """Execute a chart\'s query and return the resulting data.

        Args:
            chart_id: The chart ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/charts/{chart_id}/data/")
        return format_response(resp)
'''

CONNECTIONS_ANN = '''\
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import ConnectionId


def register(app: FastMCP):

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_connections() -> str:
        """List all Airbyte connections (source-to-destination syncs) in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/airbyte/v1/connections")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_connection(connection_id: ConnectionId) -> str:
        """Get details of a specific Airbyte connection.

        Args:
            connection_id: The Airbyte connection ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/airbyte/v1/connections/{connection_id}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_sync_history(connection_id: ConnectionId) -> str:
        """Get sync run history for an Airbyte connection.

        Args:
            connection_id: The Airbyte connection ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/airbyte/v1/connections/{connection_id}/sync/history")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_connection_catalog(connection_id: ConnectionId) -> str:
        """Get the stream catalog for an Airbyte connection (selected streams and sync modes).

        Args:
            connection_id: The Airbyte connection ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/airbyte/v1/connections/{connection_id}/catalog")
        return format_response(resp)
'''

DASHBOARDS_ANN = '''\
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import DashboardId


def register(app: FastMCP):

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_dashboards() -> str:
        """List all dashboards in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/dashboards/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_dashboard(dashboard_id: DashboardId) -> str:
        """Get details of a specific dashboard including its charts.

        Args:
            dashboard_id: The dashboard ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/dashboards/{dashboard_id}/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
    async def dalgo_create_dashboard(dashboard_data: dict) -> str:
        """Create a new dashboard.

        Args:
            dashboard_data: Dashboard configuration dict with title and optional description.
        """
        client = await adapt_context()
        resp = await client.post("/api/dashboards/", json=dashboard_data)
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True))
    async def dalgo_update_dashboard(dashboard_id: DashboardId, dashboard_data: dict) -> str:
        """Update an existing dashboard.

        Args:
            dashboard_data: Updated dashboard configuration dict.
        """
        client = await adapt_context()
        resp = await client.put(f"/api/dashboards/{dashboard_id}/", json=dashboard_data)
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
    async def dalgo_delete_dashboard(dashboard_id: DashboardId) -> str:
        """Delete a dashboard.

        Args:
            dashboard_id: The dashboard ID.
        """
        client = await adapt_context()
        resp = await client.delete(f"/api/dashboards/{dashboard_id}/")
        return format_response(resp)
'''

PIPELINES_ANN = '''\
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import DeploymentId, FlowRunId, Limit


def register(app: FastMCP):

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_pipelines() -> str:
        """List all orchestration pipelines (Prefect deployments) in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/prefect/v1/flows/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_pipeline(deployment_id: DeploymentId) -> str:
        """Get details of a specific pipeline by its deployment ID.

        Args:
            deployment_id: The Prefect deployment ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/prefect/v1/flows/{deployment_id}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
    async def dalgo_create_pipeline(pipeline_data: dict) -> str:
        """Create a new orchestration pipeline.

        Args:
            pipeline_data: Pipeline configuration dict with connection_id, cron schedule, and transform settings.
        """
        client = await adapt_context()
        resp = await client.post("/api/prefect/v1/flows/", json=pipeline_data)
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True))
    async def dalgo_update_pipeline(deployment_id: DeploymentId, pipeline_data: dict) -> str:
        """Update an existing pipeline\'s configuration.

        Args:
            pipeline_data: Updated pipeline configuration dict.
        """
        client = await adapt_context()
        resp = await client.put(f"/api/prefect/v1/flows/{deployment_id}", json=pipeline_data)
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
    async def dalgo_delete_pipeline(deployment_id: DeploymentId) -> str:
        """Delete a pipeline by its deployment ID.

        Args:
            deployment_id: The Prefect deployment ID.
        """
        client = await adapt_context()
        resp = await client.delete(f"/api/prefect/v1/flows/{deployment_id}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
    async def dalgo_trigger_pipeline_run(deployment_id: DeploymentId) -> str:
        """Trigger an immediate run of a pipeline.

        Args:
            deployment_id: The Prefect deployment ID.
        """
        client = await adapt_context()
        resp = await client.post(f"/api/prefect/v1/flows/{deployment_id}/flow_run/")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_pipeline_run_history(deployment_id: DeploymentId, limit: Limit = 10) -> str:
        """Get the run history for a specific pipeline.

        Args:
            deployment_id: The Prefect deployment ID.
            limit: Maximum number of runs to return (default 10).
        """
        client = await adapt_context()
        resp = await client.get(
            f"/api/prefect/v1/flows/{deployment_id}/flow_runs/history",
            params={"limit": limit},
        )
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_flow_run(flow_run_id: FlowRunId) -> str:
        """Get details of a specific flow run.

        Args:
            flow_run_id: The Prefect flow run ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/prefect/flow_runs/{flow_run_id}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_flow_run_logs(flow_run_id: FlowRunId) -> str:
        """Get logs for a specific flow run.

        Args:
            flow_run_id: The Prefect flow run ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/prefect/flow_runs/{flow_run_id}/logs")
        return format_response(resp)
'''

SOURCES_ANN = '''\
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import SourceId


def register(app: FastMCP):

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_sources() -> str:
        """List all configured data sources (Airbyte sources) in the organization."""
        client = await adapt_context()
        resp = await client.get("/api/airbyte/sources")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_source(source_id: SourceId) -> str:
        """Get details of a specific data source.

        Args:
            source_id: The Airbyte source ID.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/airbyte/sources/{source_id}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_source_definitions() -> str:
        """List all available Airbyte source definitions (connector types)."""
        client = await adapt_context()
        resp = await client.get("/api/airbyte/source_definitions")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False))
    async def dalgo_delete_source(source_id: SourceId) -> str:
        """Delete a data source.

        Args:
            source_id: The Airbyte source ID.
        """
        client = await adapt_context()
        resp = await client.delete(f"/api/airbyte/sources/{source_id}")
        return format_response(resp)
'''

WAREHOUSE_ANN = '''\
import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import Limit, Offset, SchemaName, TableName
from dalgo_mcp.pii import mask_pii_in_rows


def register(app: FastMCP):

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_schemas() -> str:
        """List all schemas in the connected data warehouse."""
        client = await adapt_context()
        resp = await client.get("/api/warehouse/schemas")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_list_tables(schema_name: str) -> str:
        """List all tables in a specific warehouse schema.

        Args:
            schema_name: Name of the schema to list tables from.
        """
        client = await adapt_context()
        resp = await client.get(f"/api/warehouse/tables/{schema_name}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_table_columns(schema: SchemaName, table: TableName) -> str:
        """Get column names and types for a specific warehouse table."""
        client = await adapt_context()
        resp = await client.get(f"/api/warehouse/table_columns/{schema}/{table}")
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_table_data(schema: SchemaName, table: TableName, limit: Limit = 10, offset: Offset = 0) -> str:
        """Fetch rows from a warehouse table. Defaults to 10 rows to avoid context overflow.
        PII columns (name, email, phone, address, etc.) are automatically masked.
        """
        client = await adapt_context()
        resp = await client.get(
            f"/api/warehouse/table_data/{schema}/{table}",
            params={"limit": limit, "offset": offset},
        )
        if resp.status_code < 400:
            try:
                rows = resp.json()
                if isinstance(rows, list):
                    return json.dumps(mask_pii_in_rows(rows), indent=2, default=str)
            except Exception:
                pass
        return format_response(resp)

    @app.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def dalgo_get_table_row_count(schema: SchemaName, table: TableName) -> str:
        """Get the total row count of a warehouse table."""
        client = await adapt_context()
        resp = await client.get(f"/api/warehouse/table_count/{schema}/{table}")
        return format_response(resp)
'''

branch = "feat/safety-annotations"
msg = "fix: resolve conflicts — merge ToolAnnotations with typed params from adapt_context refactor"
push_file(branch, "src/dalgo_mcp/tools/charts.py",       CHARTS_ANN,      msg)
push_file(branch, "src/dalgo_mcp/tools/connections.py",   CONNECTIONS_ANN, msg)
push_file(branch, "src/dalgo_mcp/tools/dashboards.py",    DASHBOARDS_ANN,  msg)
push_file(branch, "src/dalgo_mcp/tools/pipelines.py",     PIPELINES_ANN,   msg)
push_file(branch, "src/dalgo_mcp/tools/sources.py",       SOURCES_ANN,     msg)
push_file(branch, "src/dalgo_mcp/tools/warehouse.py",     WAREHOUSE_ANN,   msg)

print("\nDone. All 3 PRs should now show as conflict-free on GitHub.")
