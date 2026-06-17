import json
import logging
import uuid
from typing import Any

from mcp.types import Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

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
                "serverInfo": {"name": "apple-mcp", "version": "1.0.0"},
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


def create_http_app(apple_mcp_server) -> Starlette:
    app = Starlette(
        routes=[
            Route("/mcp", _handle_request, methods=["POST", "DELETE"]),
        ]
    )
    app.state.server = apple_mcp_server
    return app
