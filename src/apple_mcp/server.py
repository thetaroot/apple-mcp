import inspect
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from apple_mcp.config import ServerConfig


class AppleMCPServer:
    def __init__(self, config: ServerConfig, *, server_name: str = "apple-mcp"):
        self.config = config
        self._mcp = Server(server_name)
        self._services_ready = False
        self._tool_handler: dict[str, Any] = {}
        self._all_tools: list[Tool] = []

    @property
    def mcp(self) -> Server:
        return self._mcp

    async def _init_services(self) -> None:
        if self._services_ready:
            return

        from apple_mcp.services.auth import AuthService
        from apple_mcp.services.scope import ScopeEngine

        auth = AuthService(self.config)
        try:
            status = await auth.authenticate()
        except Exception as exc:
            import logging
            logger = logging.getLogger("apple_mcp.server")
            logger.warning("Auth failed, services will be unavailable: %s", exc)
            status = None

        scope = ScopeEngine(self.config)

        calendar_service = None
        reminders_service = None
        mail_service = None

        if status and self.config.enable_calendar and status.calendar_ok:
            from apple_mcp.services.calendar import CalendarService

            calendar_service = CalendarService(auth.pyicloud, scope)

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
                self._all_tools.append(tool)
                self._tool_handler[tool.name] = svc

        @self._mcp.list_tools()
        async def list_tools() -> list[Tool]:
            return self._all_tools

        @self._mcp.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            return await self.handle_tool_call(name, arguments)

        self._services_ready = True

    async def handle_tool_call(self, name: str, arguments: dict) -> list[TextContent]:
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
        await self._init_services()
        from apple_mcp.transport.http import create_http_app

        app = create_http_app(self)
        import uvicorn

        svr = uvicorn.Config(app, host=host, port=port, log_level=self.config.log_level.lower())
        await uvicorn.Server(svr).serve()
