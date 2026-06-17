import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


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
        mock_instance.authenticate = AsyncMock(return_value=mock_status)
        mock_auth_class.return_value = mock_instance

        async def run():
            server = AppleMCPServer(base_config)
            await server._init_services()
            assert "apple_calendar_list_calendars" in server._tool_handler
            assert "apple_reminders_list_lists" in server._tool_handler
            assert "apple_mail_search" in server._tool_handler

        asyncio.run(run())
