import asyncio
import inspect
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from apple_mcp.config import ServerConfig

logger = logging.getLogger("apple_mcp.server")

_AUTH_TOOLS = [
    Tool(
        name="apple_auth_status",
        description=(
            "Check authentication status for all Apple services. "
            "Returns per-service status: ok, auth_failed, 2fa_required, or disabled."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="apple_auth_reconnect",
        description=(
            "Re-authenticate all Apple services without restarting. "
            "Use this when auth has expired. If 2FA is required, the response will indicate so."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="apple_auth_submit_2fa",
        description=(
            "Submit a 2FA verification code to complete Apple authentication. "
            "Use this after apple_auth_reconnect returns '2fa_required'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The 6-digit 2FA code from your trusted device."},
            },
            "required": ["code"],
        },
    ),
]


class AppleMCPServer:
    def __init__(self, config: ServerConfig, *, server_name: str = "apple-mcp"):
        self.config = config
        self._mcp = Server(server_name)
        self._services_ready = False
        self._tool_handler: dict[str, Any] = {}
        self._all_tools: list[Tool] = []
        self._auth_ready = asyncio.Event()
        self._auth_status: Any = None
        self._reconnect_lock = asyncio.Lock()

    @property
    def mcp(self) -> Server:
        return self._mcp

    def _auth_status_dict(self) -> dict[str, str]:
        diag: dict[str, str] = {}
        for svc_name in ("calendar", "reminders", "mail"):
            enabled = getattr(self.config, f"enable_{svc_name}", False)
            if not enabled:
                diag[svc_name] = "disabled"
            elif self._auth_status and getattr(self._auth_status, f"{svc_name}_ok", False):
                diag[svc_name] = "ok"
            elif self._auth_status and svc_name in self._auth_status.errors:
                err = str(self._auth_status.errors[svc_name])
                if "2FA" in err or "2fa" in err:
                    if "invalid" in err.lower() or "validation failed" in err.lower():
                        diag[svc_name] = "2fa_invalid"
                    else:
                        diag[svc_name] = "2fa_required"
                elif "password" in err.lower() or "login failed" in err.lower():
                    diag[svc_name] = "auth_failed"
                else:
                    diag[svc_name] = err
            else:
                diag[svc_name] = "unavailable"
        return diag

    def _rebuild_services(self, auth: Any, status: Any) -> None:
        from apple_mcp.services.scope import ScopeEngine

        self._auth_status = status
        scope = ScopeEngine(self.config)

        new_handlers: dict[str, Any] = {}
        new_tools: list[Tool] = list(_AUTH_TOOLS)

        calendar_service = None
        reminders_service = None
        mail_service = None

        if status and self.config.enable_calendar and status.calendar_ok:
            from apple_mcp.services.calendar import CalendarService

            calendar_service = CalendarService(auth.caldav, scope)

        if status and self.config.enable_reminders and status.reminders_ok:
            from apple_mcp.services.reminders import RemindersService

            reminders_service = RemindersService(auth.pyicloud, scope)

        if status and self.config.enable_mail and status.mail_ok:
            from apple_mcp.services.mail import MailService

            mail_service = MailService(auth.mail_clients, scope)

        for svc in [calendar_service, reminders_service, mail_service]:
            if svc is None:
                continue
            for tool in svc.tools():
                new_tools.append(tool)
                new_handlers[tool.name] = svc

        new_tools.append(
            Tool(
                name="_sg_auth_status",
                description=json.dumps(self._auth_status_dict()),
                inputSchema={"type": "object", "properties": {}},
            )
        )

        self._all_tools = new_tools
        self._tool_handler = new_handlers

    async def reconnect(self, twofa_code: str | None = None) -> dict[str, str]:
        async with self._reconnect_lock:
            from apple_mcp.services.auth import AuthService

            if twofa_code:
                self.config.twofa_code = twofa_code

            auth = AuthService(self.config)
            try:
                status = await auth.authenticate()
            except Exception as exc:
                logger.warning("Reconnect auth failed: %s", exc)
                status = None

            self._rebuild_services(auth, status)

            if twofa_code:
                self.config.twofa_code = ""

            return self._auth_status_dict()

    async def _init_services(self) -> None:
        if self._services_ready:
            return

        from apple_mcp.services.auth import AuthService

        auth = AuthService(self.config)
        try:
            status = await auth.authenticate()
        except Exception as exc:
            logger.warning("Auth failed, services will be unavailable: %s", exc)
            status = None

        self._rebuild_services(auth, status)

        @self._mcp.list_tools()
        async def list_tools() -> list[Tool]:
            await self._auth_ready.wait()
            return self._all_tools

        @self._mcp.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            await self._auth_ready.wait()
            return await self.handle_tool_call(name, arguments)

        self._services_ready = True
        self._auth_ready.set()

    async def handle_tool_call(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "apple_auth_status":
            return [TextContent(type="text", text=json.dumps(self._auth_status_dict()))]

        if name == "apple_auth_reconnect":
            result = await self.reconnect()
            return [TextContent(type="text", text=json.dumps(result))]

        if name == "apple_auth_submit_2fa":
            code = arguments.get("code", "")
            if not code:
                return [TextContent(type="text", text=json.dumps({"error": "2FA code is required"}))]
            result = await self.reconnect(twofa_code=code)
            return [TextContent(type="text", text=json.dumps(result))]

        handler = self._tool_handler.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = handler.handle(name, arguments)
            if inspect.iscoroutine(result):
                result = await result
            return [TextContent(type="text", text=result)]
        except Exception as exc:
            return [TextContent(type="text", text=str(exc))]

    async def run_stdio(self) -> None:
        await self._init_services()
        from apple_mcp.transport.stdio import run_stdio_server

        await run_stdio_server(self._mcp)

    async def run_http(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        from apple_mcp.transport.http import create_http_app

        app = create_http_app(self)
        import uvicorn

        svr = uvicorn.Config(app, host=host, port=port, log_level=self.config.log_level.lower())

        async def _init_bg() -> None:
            await self._init_services()

        asyncio.ensure_future(_init_bg())
        await uvicorn.Server(svr).serve()
