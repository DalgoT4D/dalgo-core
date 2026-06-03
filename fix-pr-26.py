#!/usr/bin/env python3
"""
Fixes PR #26 (feat/token-aware-truncation) merge conflict in dalgo-mcp.

Usage:
    python3 fix-pr-26.py <github-token>

Token needs Contents: read+write for DalgoT4D/dalgo-mcp
Create at: https://github.com/settings/tokens/new (Fine-grained)
"""

import base64, json, sys, urllib.request

TOKEN = sys.argv[1] if len(sys.argv) > 1 else (print("Usage: python3 fix-pr-26.py <token>") or sys.exit(1))
BRANCH = "feat/token-aware-truncation"
OWNER, REPO = "DalgoT4D", "dalgo-mcp"


def api(method, path, body=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        method=method,
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


def push(path, content, message):
    sha = api("GET", f"contents/{path}?ref={BRANCH}")["sha"]
    result = api("PUT", f"contents/{path}", {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
        "branch": BRANCH,
    })
    print(f"  pushed {path} → {result['commit']['sha'][:8]}")


# ── src/dalgo_mcp/server.py ──────────────────────────────────────────────────
# Fix: add # noqa: E402 to the tools import line (trivial conflict)
SERVER_PY = '''\
import json
import logging
import time

from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from dalgo_mcp.config import config

logging.basicConfig(level=logging.DEBUG if config.debug else logging.INFO)
logger = logging.getLogger(__name__)

# Module-level start time for uptime tracking
_start_time = time.time()


class DebugRequestMiddleware(BaseHTTPMiddleware):
    """Logs method, path, headers, and body for every incoming request."""

    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        logger.debug(
            ">>> %s %s\\nHeaders: %s\\nBody: %s",
            request.method,
            request.url,
            dict(request.headers),
            body.decode("utf-8", errors="replace")[:2000] if body else "(empty)",
        )
        response = await call_next(request)
        logger.debug(
            "<<< %s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response


class ToolCallLoggingMiddleware(BaseHTTPMiddleware):
    """Log MCP tool calls with timing and success/failure status."""

    async def dispatch(self, request: Request, call_next):
        tool_name = None

        if request.method == "POST":
            try:
                body_bytes = await request.body()
                data = json.loads(body_bytes)
                if data.get("method") == "tools/call":
                    tool_name = data.get("params", {}).get("name")
            except Exception:
                pass

        t0 = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - t0) * 1000

        if tool_name:
            success = response.status_code < 400
            logger.info(
                "tool_call tool=%s duration_ms=%.1f success=%s status_code=%d",
                tool_name,
                duration_ms,
                success,
                response.status_code,
            )

        return response


def _create_app() -> FastMCP:
    """Create the FastMCP app with transport-appropriate settings."""
    if config.transport == "streamable-http":
        from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

        from dalgo_mcp.login import create_login_handlers
        from dalgo_mcp.oauth import DalgoOAuthProvider

        if config.public_url:
            server_url = config.public_url
        else:
            issuer_host = "localhost" if config.host == "0.0.0.0" else config.host
            server_url = f"http://{issuer_host}:{config.port}"
        oauth_provider = DalgoOAuthProvider(config.api_url)

        mcp = FastMCP(
            "Dalgo",
            instructions=(
                "Dalgo is an open-source ELT platform for NGOs and social-impact organizations. "
                "Use this server when the user asks about their data warehouse, data pipelines, "
                "dashboards, charts, reports, or data sources.\\n\\n"
                "Capabilities:\\n"
                "- Warehouse: browse schemas, tables, columns, and fetch row data\\n"
                "- Pipelines: list, create, trigger, and monitor Prefect orchestration pipelines\\n"
                "- Sources & Connections: manage Airbyte data sources and sync connections\\n"
                "- Dashboards & Charts: create, update, and query visualization dashboards and charts\\n"
                "- Reports: create point-in-time dashboard snapshots with date filtering\\n"
                "- Transforms: manage dbt workspace, run dbt, view the DAG, sync sources\\n"
                "- Notifications: view and manage user notifications\\n"
                "- Organization: view current user, org members, and feature flags\\n"
                "- Documentation: search and browse Dalgo product documentation"
            ),
            auth_server_provider=oauth_provider,
            auth=AuthSettings(
                issuer_url=server_url,
                resource_server_url=server_url,
                client_registration_options=ClientRegistrationOptions(
                    enabled=True,
                ),
            ),
            streamable_http_path="/",
            host=config.host,
            port=config.port,
            debug=True,
            log_level="DEBUG",
        )

        handle_login_get, handle_login_post = create_login_handlers(oauth_provider)

        @mcp.custom_route("/login", methods=["GET"])
        async def login_get(request):
            return await handle_login_get(request)

        @mcp.custom_route("/login", methods=["POST"])
        async def login_post(request):
            return await handle_login_post(request)

        @mcp.custom_route("/health", methods=["GET"])
        async def health(request):
            from starlette.responses import JSONResponse

            from dalgo_mcp.client import _token_clients

            return JSONResponse(
                {
                    "status": "ok",
                    "uptime_seconds": round(time.time() - _start_time, 1),
                    "active_token_clients": len(_token_clients),
                    "tool_count": len(mcp._tool_manager._tools),
                }
            )

        return mcp
    else:
        return FastMCP(
            "Dalgo",
            instructions=(
                "Dalgo is an open-source ELT platform for NGOs and social-impact organizations. "
                "Use this server when the user asks about their data warehouse, data pipelines, "
                "dashboards, charts, reports, or data sources.\\n\\n"
                "Capabilities:\\n"
                "- Warehouse: browse schemas, tables, columns, and fetch row data\\n"
                "- Pipelines: list, create, trigger, and monitor Prefect orchestration pipelines\\n"
                "- Sources & Connections: manage Airbyte data sources and sync connections\\n"
                "- Dashboards & Charts: create, update, and query visualization dashboards and charts\\n"
                "- Reports: create point-in-time dashboard snapshots with date filtering\\n"
                "- Transforms: manage dbt workspace, run dbt, view the DAG, sync sources\\n"
                "- Notifications: view and manage user notifications\\n"
                "- Organization: view current user, org members, and feature flags\\n"
                "- Documentation: search and browse Dalgo product documentation"
            ),
        )


app = _create_app()

# Register all tool modules
from dalgo_mcp.tools import (  # noqa: E402
    charts,
    connections,
    dashboards,
    docs,
    notifications,
    organization,
    pipelines,
    reports,
    sources,
    transforms,
    warehouse,
)

organization.register(app)
warehouse.register(app)
pipelines.register(app)
sources.register(app)
connections.register(app)
dashboards.register(app)
charts.register(app)
reports.register(app)
transforms.register(app)
notifications.register(app)
docs.register(app)


def main():
    config.validate()

    if config.debug and config.transport == "streamable-http":
        import anyio
        import uvicorn

        async def _run_debug_http():
            starlette_app = app.streamable_http_app()
            starlette_app.add_middleware(ToolCallLoggingMiddleware)
            starlette_app.add_middleware(DebugRequestMiddleware)
            server = uvicorn.Server(
                uvicorn.Config(
                    starlette_app,
                    host=app.settings.host,
                    port=app.settings.port,
                    log_level="trace",
                )
            )
            await server.serve()

        logger.info("Starting in DEBUG mode — all requests will be logged")
        anyio.run(_run_debug_http)
    elif config.transport == "streamable-http":
        import anyio
        import uvicorn

        async def _run_http():
            starlette_app = app.streamable_http_app()
            starlette_app.add_middleware(ToolCallLoggingMiddleware)
            server = uvicorn.Server(
                uvicorn.Config(
                    starlette_app,
                    host=app.settings.host,
                    port=app.settings.port,
                    log_level=app.settings.log_level.lower(),
                )
            )
            await server.serve()

        anyio.run(_run_http)
    else:
        app.run(transport=config.transport)


if __name__ == "__main__":
    main()
'''

# ── src/dalgo_mcp/tools/pipelines.py ────────────────────────────────────────
# Fix: use FlowRunId type (from main), keep extended docstring + truncation logic (from PR)
PIPELINES_PY = '''\
from mcp.server.fastmcp import FastMCP

from dalgo_mcp.client import format_response
from dalgo_mcp.context import adapt_context
from dalgo_mcp.params import DeploymentId, FlowRunId, Limit


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
        import json

        from dalgo_mcp.truncate import truncate_log_text

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

msg = "fix: resolve merge conflict — FlowRunId type + noqa comment"
print(f"Pushing to {BRANCH}...")
push("src/dalgo_mcp/server.py",            SERVER_PY,    msg)
push("src/dalgo_mcp/tools/pipelines.py",   PIPELINES_PY, msg)
print("Done — PR #26 should now show as conflict-free.")
