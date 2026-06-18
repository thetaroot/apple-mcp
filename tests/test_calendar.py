import asyncio
import json
from unittest.mock import MagicMock

from apple_mcp.services.calendar import CalendarService
from apple_mcp.services.scope import ScopeEngine


class FakeCalendar:
    def __init__(self, name, url="http://cal.example.com", ctag="ctag1"):
        self.name = name
        self.url = url
        self._ctag = ctag

    def get_property_value(self, prop):
        return self._ctag

    def search(self, **kwargs):
        return []

    def date_search(self, **kwargs):
        return []


class TestCalendarService:
    def _make_caldav(self, calendars=None):
        client = MagicMock()
        principal = MagicMock()
        principal.calendars.return_value = calendars or []
        client.principal.return_value = principal
        return client

    def test_tools_count(self, base_config, mock_caldav):
        scope = ScopeEngine(base_config)
        svc = CalendarService(mock_caldav, scope)
        tools = svc.tools()
        assert len(tools) == 12

    def test_list_calendars_filtered(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        client = self._make_caldav(
            [
                FakeCalendar("Work", ctag="ct1"),
                FakeCalendar("Personal", ctag="ct2"),
                FakeCalendar("SwiftGate Dev", ctag="ct3"),
            ]
        )
        svc = CalendarService(client, scope)
        result = svc._list_calendars({})
        names = [c["name"] for c in result]
        assert "Work" in names
        assert "SwiftGate Dev" in names
        assert "Personal" not in names

    def test_list_calendars_writable_check(self, readonly_config):
        scope = ScopeEngine(readonly_config)
        client = self._make_caldav([FakeCalendar("Work")])
        svc = CalendarService(client, scope)
        result = svc._list_calendars({})
        assert len(result) == 1
        assert result[0]["writable"] is False

    def test_create_event_readonly_raises(self, readonly_config):
        scope = ScopeEngine(readonly_config)
        client = self._make_caldav([FakeCalendar("Work")])
        svc = CalendarService(client, scope)
        result = asyncio.run(
            svc.handle(
                "apple_calendar_create_event",
                {
                    "calendar_name": "Work",
                    "title": "Test",
                    "start_date": "2026-06-20T09:00:00",
                    "end_date": "2026-06-20T10:00:00",
                },
            )
        )
        parsed = json.loads(result)
        assert "error" in parsed or "scope_error" in parsed.get("type", "")

    def test_handle_unknown_tool(self, base_config, mock_caldav):
        scope = ScopeEngine(base_config)
        svc = CalendarService(mock_caldav, scope)
        result = asyncio.run(svc.handle("apple_calendar_unknown", {}))
        assert "unknown" in result.lower() or "Unknown" in result
