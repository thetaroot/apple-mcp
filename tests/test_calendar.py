import asyncio
import json

from apple_mcp.services.calendar import CalendarService
from apple_mcp.services.scope import ScopeEngine


class FakeCalendar:
    def __init__(self, title, guid, color=None):
        self.title = title
        self.guid = guid
        self.color = color


class FakeEvent:
    def __init__(self, guid, pguid, title, start_date, end_date, location="", all_day=False):
        self.guid = guid
        self.pguid = pguid
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.location = location
        self.description = ""
        self.all_day = all_day


class TestCalendarService:
    def test_tools_count(self, base_config, mock_pyicloud):
        scope = ScopeEngine(base_config)
        svc = CalendarService(mock_pyicloud, scope)
        tools = svc.tools()
        assert len(tools) == 12

    def test_list_calendars_filtered(self, scoped_config, mock_pyicloud):
        scope = ScopeEngine(scoped_config)
        svc = CalendarService(mock_pyicloud, scope)

        mock_pyicloud.calendar.get_calendars.return_value = [
            FakeCalendar("Work", "g1"),
            FakeCalendar("Personal", "g2"),
            FakeCalendar("SwiftGate Dev", "g3"),
        ]

        result = svc._list_calendars({})
        names = [c["name"] for c in result]
        assert "Work" in names
        assert "SwiftGate Dev" in names
        assert "Personal" not in names

    def test_list_calendars_writable_check(self, readonly_config, mock_pyicloud):
        scope = ScopeEngine(readonly_config)
        svc = CalendarService(mock_pyicloud, scope)

        mock_pyicloud.calendar.get_calendars.return_value = [
            FakeCalendar("Work", "g1"),
        ]

        result = svc._list_calendars({})
        assert len(result) == 1
        assert result[0]["writable"] is False

    def test_create_event_readonly_raises(self, readonly_config, mock_pyicloud):
        scope = ScopeEngine(readonly_config)
        svc = CalendarService(mock_pyicloud, scope)

        mock_pyicloud.calendar.get_calendars.return_value = [
            FakeCalendar("Work", "g1"),
        ]

        result = asyncio.run(svc.handle("apple_calendar_create_event", {
            "calendar_name": "Work",
            "title": "Test Event",
            "start_date": "2026-06-20T09:00:00",
            "end_date": "2026-06-20T10:00:00",
        }))
        parsed = json.loads(result)
        assert "error" in parsed or "scope_error" in parsed.get("type", "")

    def test_handle_unknown_tool(self, base_config, mock_pyicloud):
        scope = ScopeEngine(base_config)
        svc = CalendarService(mock_pyicloud, scope)
        result = asyncio.run(svc.handle("apple_calendar_unknown", {}))
        assert "unknown" in result.lower() or "Unknown" in result
