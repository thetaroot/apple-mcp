# mypy: ignore-errors
import contextlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from caldav import Calendar, DAVClient
from caldav.elements import dav
from mcp.types import Tool

from apple_mcp.errors import ScopeError
from apple_mcp.services.scope import ScopeEngine

logger = logging.getLogger("apple_mcp.services.calendar")


class CalendarService:
    def __init__(self, caldav_client: Any, scope: ScopeEngine):
        self._client: Any = caldav_client
        self._scope = scope
        self._principal: Any = None
        self._calendars_cache: Any = None

    async def _get_calendars(self) -> list[Calendar]:
        if self._calendars_cache is not None:
            return self._calendars_cache
        if self._principal is None:
            self._principal = self._client.principal()
        cals = self._principal.calendars()
        if cals is None:
            cals = []
        self._calendars_cache = list(cals)
        return self._calendars_cache

    def _filter_visible(self, cals: list[Calendar]) -> list[Calendar]:
        return [c for c in cals if self._scope.calendar_visible(c.name)]

    def _find_calendar(self, name: str) -> Calendar:
        cals = self._get_calendars_sync()
        for c in cals:
            if c.name.lower() == name.lower() and self._scope.calendar_visible(c.name):
                return c
        raise ScopeError(f"Calendar '{name}' not found or not in scope")

    def _get_calendars_sync(self) -> list[Calendar]:
        if self._calendars_cache is not None:
            return self._calendars_cache
        if self._principal is None:
            self._principal = self._client.principal()
        cals = self._principal.calendars()
        self._calendars_cache = list(cals) if cals else []
        return self._calendars_cache

    def tools(self) -> list[Tool]:
        return [
            Tool(
                name="apple_calendar_list_calendars",
                description="List all visible calendars. Names are filtered by your scope configuration.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="apple_calendar_get_events",
                description="Get events from a calendar within a date range. Use period shortcuts or pass exact dates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string", "description": "Name of the calendar."},
                        "from_date": {"type": "string", "description": "Start date ISO format."},
                        "to_date": {"type": "string", "description": "End date ISO format."},
                        "period": {"type": "string", "enum": ["day", "week", "month"]},
                        "limit": {"type": "integer", "description": "Max events.", "default": 100},
                    },
                    "required": ["calendar_name"],
                },
            ),
            Tool(
                name="apple_calendar_get_event",
                description="Get full details of a single calendar event by its UID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string"},
                        "event_id": {"type": "string", "description": "The event UID."},
                    },
                    "required": ["calendar_name", "event_id"],
                },
            ),
            Tool(
                name="apple_calendar_create_event",
                description="Create a new event. Supports alarms, invitees, location, notes, and recurrence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string"},
                        "title": {"type": "string"},
                        "start_date": {"type": "string", "description": "ISO datetime."},
                        "end_date": {"type": "string", "description": "ISO datetime."},
                        "location": {"type": "string"},
                        "notes": {"type": "string"},
                        "all_day": {"type": "boolean", "default": False},
                        "invitees": {"type": "array", "items": {"type": "string"}},
                        "alarm_minutes_before": {"type": "integer"},
                        "recurrence": {"type": "string", "description": "RRULE string."},
                    },
                    "required": ["calendar_name", "title", "start_date", "end_date"],
                },
            ),
            Tool(
                name="apple_calendar_update_event",
                description="Update an event's fields. Only provide the fields you want to change.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string"},
                        "event_id": {"type": "string"},
                        "title": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "location": {"type": "string"},
                        "notes": {"type": "string"},
                        "recurrence": {"type": "string"},
                    },
                    "required": ["calendar_name", "event_id"],
                },
            ),
            Tool(
                name="apple_calendar_delete_event",
                description="Delete an event from a calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {"calendar_name": {"type": "string"}, "event_id": {"type": "string"}},
                    "required": ["calendar_name", "event_id"],
                },
            ),
            Tool(
                name="apple_calendar_search_events",
                description="Search events across all visible calendars by keyword.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term."},
                        "from_date": {"type": "string"},
                        "to_date": {"type": "string"},
                        "limit": {"type": "integer", "description": "Max results.", "default": 50},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="apple_calendar_add_calendar",
                description="Create a new calendar in your iCloud account.",
                inputSchema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "color": {"type": "string"}},
                    "required": ["title"],
                },
            ),
            Tool(
                name="apple_calendar_remove_calendar",
                description="Delete a calendar and all its events. Cannot be undone.",
                inputSchema={
                    "type": "object",
                    "properties": {"calendar_name": {"type": "string"}},
                    "required": ["calendar_name"],
                },
            ),
            Tool(
                name="apple_calendar_get_availability",
                description="Check which time slots are free or busy across your calendars.",
                inputSchema={
                    "type": "object",
                    "properties": {"from_date": {"type": "string"}, "to_date": {"type": "string"}},
                    "required": ["from_date", "to_date"],
                },
            ),
            Tool(
                name="apple_calendar_get_changes",
                description="Get a change tag (ctag) for each visible calendar. If it changes, events were modified.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="apple_calendar_get_calendar_info",
                description="Get detailed info about a calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {"calendar_name": {"type": "string"}},
                    "required": ["calendar_name"],
                },
            ),
        ]

    async def handle(self, name: str, arguments: dict) -> str:
        handlers = {
            "apple_calendar_list_calendars": self._list_calendars,
            "apple_calendar_get_events": self._get_events,
            "apple_calendar_get_event": self._get_event,
            "apple_calendar_create_event": self._create_event,
            "apple_calendar_update_event": self._update_event,
            "apple_calendar_delete_event": self._delete_event,
            "apple_calendar_search_events": self._search_events,
            "apple_calendar_add_calendar": self._add_calendar,
            "apple_calendar_remove_calendar": self._remove_calendar,
            "apple_calendar_get_availability": self._get_availability,
            "apple_calendar_get_changes": self._get_changes,
            "apple_calendar_get_calendar_info": self._get_calendar_info,
        }
        handler = handlers.get(name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = handler(arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except ScopeError as exc:
            return json.dumps({"error": str(exc), "type": "scope_error"})
        except Exception as exc:
            logger.exception("Calendar tool %s failed", name)
            return json.dumps({"error": str(exc), "type": "server_error"})

    def _list_calendars(self, _args: dict) -> list[dict]:
        cals = self._get_calendars_sync()
        result = []
        for c in cals:
            if not self._scope.calendar_visible(c.name):
                continue
            result.append(
                {
                    "name": c.name,
                    "url": str(c.url) if c.url else "",
                    "ctag": getattr(c, "get_property_value", lambda x: None)(dav.GetEtag()) or "",
                    "writable": self._scope.calendar_writable(c.name),
                }
            )
        return result

    def _get_events(self, args: dict) -> list[dict]:
        cal = self._find_calendar(args["calendar_name"])
        from_str = args.get("from_date", datetime.now(UTC).strftime("%Y-%m-%d"))
        to_str = args.get("to_date")
        period = args.get("period")
        limit = args.get("limit", 100)

        if period:
            from_dt = datetime.fromisoformat(from_str)
            to_dt = from_dt + {"day": timedelta(days=1), "week": timedelta(weeks=1), "month": timedelta(days=30)}.get(
                period, timedelta(days=30)
            )
        else:
            from_dt = datetime.fromisoformat(from_str)
            to_dt = datetime.fromisoformat(to_str) if to_str else from_dt + timedelta(days=30)

        try:
            events = cal.search(start=from_dt, end=to_dt, event=True, expand=True)
        except Exception:
            events = cal.date_search(start=from_dt, end=to_dt, expand=True)

        result = []
        for evt in events:
            if limit and len(result) >= limit:
                break
            try:
                result.append(
                    {
                        "uid": getattr(evt, "id", ""),
                        "title": getattr(evt, "summary", "") or "",
                        "start": str(getattr(evt, "dtstart", None)),
                        "end": str(getattr(evt, "dtend", None)),
                        "location": getattr(evt, "location", "") or "",
                    }
                )
            except Exception:
                continue
        return result

    def _get_event(self, args: dict) -> dict:
        cal = self._find_calendar(args["calendar_name"])
        evt = cal.event(args["event_id"])
        if evt is None:
            raise ScopeError(f"Event '{args['event_id']}' not found")
        return {
            "uid": evt.id,
            "title": getattr(evt, "summary", "") or "",
            "start": str(getattr(evt, "dtstart", None)),
            "end": str(getattr(evt, "dtend", None)),
            "location": getattr(evt, "location", "") or "",
            "notes": getattr(evt, "description", "") or "",
        }

    def _create_event(self, args: dict) -> dict:
        cal = self._find_calendar(args["calendar_name"])
        self._scope.guard_read_only("calendar", "create_event")

        from icalendar import Calendar as ICal
        from icalendar import Event as ICalEvent

        ievent = ICalEvent()
        ievent.add("summary", args["title"])
        start = datetime.fromisoformat(args["start_date"])
        end = datetime.fromisoformat(args["end_date"])
        ievent.add("dtstart", start)
        ievent.add("dtend", end)

        if args.get("location"):
            ievent.add("location", args["location"])
        if args.get("notes"):
            ievent.add("description", args["notes"])
        if args.get("recurrence"):
            ievent.add("rrule", {"freq": args["recurrence"]})

        if args.get("alarm_minutes_before") is not None:
            from icalendar import Alarm

            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", "Reminder")
            alarm.add("trigger", timedelta(minutes=-args["alarm_minutes_before"]))
            ievent.add_component(alarm)

        if args.get("invitees"):
            for email in args["invitees"]:
                ievent.add("attendee", f"mailto:{email}")

        ical = ICal()
        ical.add_component(ievent)
        saved = cal.save_event(ical.to_ical().decode("utf-8"))
        return {"status": "created", "uid": getattr(saved, "id", ""), "title": args["title"]}

    def _update_event(self, args: dict) -> dict:
        cal = self._find_calendar(args["calendar_name"])
        self._scope.guard_read_only("calendar", "update_event")
        evt = cal.event(args["event_id"])
        if evt is None:
            raise ScopeError(f"Event '{args['event_id']}' not found")

        with contextlib.suppress(Exception):
            evt.load()

        data = evt.data
        changed = False
        for key, field in [
            ("title", "summary"),
            ("start_date", "dtstart"),
            ("end_date", "dtend"),
            ("location", "location"),
            ("notes", "description"),
        ]:
            if key in args:
                data = self._replace_ical_prop(data, field, args[key])
                changed = True
        if changed:
            evt.data = data
            evt.save()
        return {"status": "updated", "uid": args["event_id"]}

    def _delete_event(self, args: dict) -> dict:
        cal = self._find_calendar(args["calendar_name"])
        self._scope.guard_read_only("calendar", "delete_event")
        evt = cal.event(args["event_id"])
        if evt is None:
            raise ScopeError(f"Event '{args['event_id']}' not found")
        evt.delete()
        return {"status": "deleted", "uid": args["event_id"]}

    def _search_events(self, args: dict) -> list[dict]:
        query = args["query"].lower()
        limit = args.get("limit", 50)
        now = datetime.now(UTC)
        from_dt = datetime.fromisoformat(args["from_date"]) if args.get("from_date") else now - timedelta(days=90)
        to_dt = datetime.fromisoformat(args["to_date"]) if args.get("to_date") else now + timedelta(days=90)

        results = []
        cals = self._get_calendars_sync()
        for cal in cals:
            if not self._scope.calendar_visible(cal.name):
                continue
            try:
                events = cal.search(start=from_dt, end=to_dt, event=True, expand=True)
            except Exception:
                continue
            for evt in events:
                title = (getattr(evt, "summary", "") or "").lower()
                location = (getattr(evt, "location", "") or "").lower()
                if query in title or query in location:
                    results.append(
                        {
                            "uid": getattr(evt, "id", ""),
                            "title": getattr(evt, "summary", ""),
                            "start": str(getattr(evt, "dtstart", None)),
                            "calendar": cal.name,
                        }
                    )
                    if len(results) >= limit:
                        return results
        return results

    def _add_calendar(self, args: dict) -> dict:
        self._scope.guard_read_only("calendar", "add_calendar")
        if self._principal is None:
            self._principal = self._client.principal()
        props = {}
        if args.get("color"):
            with contextlib.suppress(Exception):
                props["X-APPLE-CALENDAR-COLOR"] = args["color"]
        self._principal.make_calendar(name=args["title"], cal_id=args["title"].lower().replace(" ", "-"))
        self._calendars_cache = None
        return {"status": "created", "name": args["title"]}

    def _remove_calendar(self, args: dict) -> dict:
        self._scope.guard_read_only("calendar", "remove_calendar")
        cal = self._find_calendar(args["calendar_name"])
        cal.delete()
        self._calendars_cache = None
        return {"status": "deleted", "name": args["calendar_name"]}

    def _get_availability(self, args: dict) -> dict:
        from_dt = datetime.fromisoformat(args["from_date"])
        to_dt = datetime.fromisoformat(args["to_date"])
        busy = []
        cals = self._get_calendars_sync()
        for cal in cals:
            if not self._scope.calendar_visible(cal.name):
                continue
            try:
                events = cal.search(start=from_dt, end=to_dt, event=True, expand=True)
            except Exception:
                continue
            for evt in events:
                busy.append(
                    {
                        "start": str(getattr(evt, "dtstart", None)),
                        "end": str(getattr(evt, "dtend", None)),
                        "title": getattr(evt, "summary", ""),
                        "calendar": cal.name,
                    }
                )
        return {"busy_slots": busy}

    def _get_changes(self, _args: dict) -> dict:
        changes = {}
        cals = self._get_calendars_sync()
        for cal in cals:
            if not self._scope.calendar_visible(cal.name):
                continue
            ctag = getattr(cal, "get_property_value", lambda x: None)(dav.GetEtag())
            changes[cal.name] = {"ctag": ctag or ""}
        return {"calendars": changes}

    def _get_calendar_info(self, args: dict) -> dict:
        cal = self._find_calendar(args["calendar_name"])
        return {
            "name": cal.name,
            "url": str(cal.url) if cal.url else "",
            "ctag": getattr(cal, "get_property_value", lambda x: None)(dav.GetEtag()) or "",
        }

    @staticmethod
    def _replace_ical_prop(data: str, prop: str, value: str) -> str:
        import re

        pattern = rf"^{prop.upper()}[:;].*$"
        new_line = f"{prop.upper()}:{value}"
        lines = data.split("\r\n")
        replaced = False
        for i, line in enumerate(lines):
            if re.match(pattern, line, re.IGNORECASE):
                lines[i] = new_line
                replaced = True
                break
        if not replaced:
            lines.insert(1, new_line)
        return "\r\n".join(lines)
