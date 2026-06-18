import json
import logging
import uuid
from typing import Any

from mcp.types import Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from apple_mcp.__version__ import VERSION

logger = logging.getLogger("apple_mcp.transport.http")

MCP_SESSION_HEADER = "Mcp-Session-Id"


async def _handle_request(request: Request) -> Response:
    session_id = request.headers.get(MCP_SESSION_HEADER, str(uuid.uuid4()))
    server = request.app.state.server

    if request.method == "DELETE":
        return Response(status_code=200)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")

    rpc_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "apple-mcp", "version": VERSION},
            }
        elif method == "tools/list":
            result = {"tools": _serialize_tools(server._all_tools)}
        elif method == "tools/call":
            content = await server.handle_tool_call(
                params.get("name", ""),
                params.get("arguments", {}),
            )
            result = {  # type: ignore[misc]
                "content": [{"type": c.type, "text": c.text} if hasattr(c, "text") else c for c in content]
            }
        elif method == "notifications/initialized":
            return Response(status_code=202)
        else:
            error = {"code": -32601, "message": f"Method not found: {method}"}
    except Exception as exc:
        logger.error("Error handling %s: %s", method, exc)
        error = {"code": -32603, "message": str(exc)}

    response_body: dict[str, Any] = {"jsonrpc": "2.0", "id": rpc_id}
    if error:
        response_body["error"] = error
    if result is not None:
        response_body["result"] = result

    return JSONResponse(response_body, headers={MCP_SESSION_HEADER: session_id})


def _serialize_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
        }
        for t in tools
    ]


async def _handle_health(request: Request) -> JSONResponse:
    server = request.app.state.server
    tool_count = len(server._tool_handler)

    services: dict[str, str] = {}
    for svc_name in ("calendar", "reminders", "mail"):
        enabled = getattr(server.config, f"enable_{svc_name}", False)
        if not enabled:
            services[svc_name] = "disabled"
        elif server._auth_status and getattr(server._auth_status, f"{svc_name}_ok", False):
            services[svc_name] = "ok"
        elif server._auth_status and svc_name in server._auth_status.errors:
            err = server._auth_status.errors[svc_name]
            if "2FA" in str(err) or "2fa" in str(err):
                services[svc_name] = "2fa_required"
            else:
                services[svc_name] = "auth_failed"
        else:
            services[svc_name] = "unavailable"

    any_ok = any(v == "ok" for v in services.values())
    all_disabled = all(v == "disabled" for v in services.values())

    overall = "ok" if any_ok or all_disabled else "degraded"

    body = {
        "status": overall,
        "version": VERSION,
        "tools_registered": tool_count,
        "services": services,
    }

    if server._auth_status and server._auth_status.errors:
        body["errors"] = server._auth_status.errors

    return JSONResponse(body, status_code=200 if overall == "ok" else 503)


def create_http_app(apple_mcp_server) -> Starlette:
    app = Starlette(
        routes=[
            Route("/mcp", _handle_request, methods=["POST", "DELETE"]),
            Route("/health", _handle_health, methods=["GET"]),
        ]
    )
    app.state.server = apple_mcp_server
    return app
