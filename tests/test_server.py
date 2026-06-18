import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from apple_mcp.services import ServiceStatus


class TestServerCreation:
    def test_server_creation(self, base_config):
        from apple_mcp.server import AppleMCPServer

        server = AppleMCPServer(base_config)
        assert server.config.apple_id == "test@icloud.com"
        assert server._services_ready is False

    @patch("apple_mcp.services.auth.AuthService")
    def test_init_services(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_status = MagicMock()
        mock_status.calendar_ok = True
        mock_status.reminders_ok = True
        mock_status.mail_ok = True
        mock_status.errors = {}
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            assert server._services_ready is True

        asyncio.run(run())


class TestMCPToolsRegistration:
    @patch("apple_mcp.services.auth.AuthService")
    def test_calendar_tools_registered(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_instance.pyicloud = MagicMock()
        mock_status = MagicMock()
        mock_status.calendar_ok = True
        mock_status.reminders_ok = True
        mock_status.mail_ok = True
        mock_status.errors = {}
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            assert "apple_calendar_list_calendars" in server._tool_handler
            assert "apple_reminders_list_lists" in server._tool_handler
            assert "apple_mail_search" in server._tool_handler

        asyncio.run(run())

    @patch("apple_mcp.services.auth.AuthService")
    def test_auth_tools_always_registered(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_status = ServiceStatus()
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            tool_names = [t.name for t in server._all_tools]
            assert "apple_auth_status" in tool_names
            assert "apple_auth_reconnect" in tool_names
            assert "apple_auth_submit_2fa" in tool_names

        asyncio.run(run())


class TestAuthStatusTool:
    @patch("apple_mcp.services.auth.AuthService")
    def test_auth_status_all_ok(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_status = ServiceStatus(calendar_ok=True, reminders_ok=True, mail_ok=True)
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            result = await server.handle_tool_call("apple_auth_status", {})
            data = json.loads(result[0].text)
            assert data["calendar"] == "ok"
            assert data["reminders"] == "ok"
            assert data["mail"] == "ok"

        asyncio.run(run())

    @patch("apple_mcp.services.auth.AuthService")
    def test_auth_status_degraded(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_status = ServiceStatus(calendar_ok=True, reminders_ok=False, mail_ok=True)
        mock_status.errors["reminders"] = "2FA required. A verification code has been sent."
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            result = await server.handle_tool_call("apple_auth_status", {})
            data = json.loads(result[0].text)
            assert data["calendar"] == "ok"
            assert data["reminders"] == "2fa_required"

        asyncio.run(run())

    def test_auth_status_disabled_service(self):
        from apple_mcp.config import ServerConfig
        from apple_mcp.server import AppleMCPServer

        config = ServerConfig(
            apple_id="test@icloud.com",
            app_specific_password="test",
            enable_reminders=False,
        )
        server = AppleMCPServer(config)
        status = server._auth_status_dict()
        assert status["reminders"] == "disabled"


class TestReconnect:
    @patch("apple_mcp.services.auth.AuthService")
    def test_reconnect_restores_services(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        failed_status = ServiceStatus(calendar_ok=False, reminders_ok=False, mail_ok=False)
        ok_status = ServiceStatus(calendar_ok=True, reminders_ok=True, mail_ok=True)
        ok_status.errors = {}
        mock_instance.authenticate = AsyncMock(side_effect=[failed_status, ok_status])
        mock_instance.pyicloud = MagicMock()
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            assert len(server._tool_handler) == 0

            result = await server.reconnect()
            assert result["calendar"] == "ok"

        asyncio.run(run())

    @patch("apple_mcp.services.auth.AuthService")
    def test_submit_2fa(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_status = ServiceStatus(calendar_ok=True, reminders_ok=True, mail_ok=True)
        mock_status.errors = {}
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_instance.pyicloud = MagicMock()
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            result = await server.handle_tool_call("apple_auth_submit_2fa", {"code": "123456"})
            data = json.loads(result[0].text)
            assert "calendar" in data

        asyncio.run(run())

    @patch("apple_mcp.services.auth.AuthService")
    def test_submit_2fa_missing_code(self, mock_auth_class, base_config):
        from apple_mcp.server import AppleMCPServer

        mock_instance = MagicMock()
        mock_status = ServiceStatus()
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            result = await server.handle_tool_call("apple_auth_submit_2fa", {})
            data = json.loads(result[0].text)
            assert "error" in data

        asyncio.run(run())
