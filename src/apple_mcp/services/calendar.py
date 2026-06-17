import json
import logging
from datetime import UTC, datetime, timedelta

from mcp.types import Tool
from pyicloud import PyiCloudService
from pyicloud.services.calendar import CalendarObject, EventObject

from apple_mcp.errors import ScopeError, ServiceUnavailableError
from apple_mcp.services.scope import ScopeEngine

logger = logging.getLogger("apple_mcp.services.calendar")


class CalendarService:
    def __init__(self, pyicloud: PyiCloudService, scope: ScopeEngine):
        self._api = pyicloud
        self._scope = scope

    def tools(self) -> list[Tool]:
        return [
            Tool(
                name="apple_calendar_list_calendars",
                description="List all visible calendars. Names are filtered by your scope configuration.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="apple_calendar_get_events",
                description="Get events from a calendar within a date range. Use period shortcuts or pass exact dates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {
                            "type": "string",
                            "description": "Name of the calendar to read from.",
                        },
                        "from_date": {
                            "type": "string",
                            "description": "Start date in ISO format (YYYY-MM-DD). Defaults to today.",
                        },
                        "to_date": {
                            "type": "string",
                            "description": "End date in ISO format (YYYY-MM-DD).",
                        },
                        "period": {
                            "type": "string",
                            "enum": ["day", "week", "month"],
                            "description": "Shortcut: show events for this period starting from from_date.",
                        },
                    },
                    "required": ["calendar_name"],
                },
            ),
            Tool(
                name="apple_calendar_get_event",
                description="Get full details of a single calendar event by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string", "description": "Calendar that contains the event."},
                        "event_id": {"type": "string", "description": "The event GUID."},
                    },
                    "required": ["calendar_name", "event_id"],
                },
            ),
            Tool(
                name="apple_calendar_create_event",
                description="Create a new event on a calendar. Supports alarms, invitees, location, and notes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string", "description": "Target calendar."},
                        "title": {"type": "string"},
                        "start_date": {"type": "string", "description": "ISO datetime string."},
                        "end_date": {"type": "string", "description": "ISO datetime string."},
                        "location": {"type": "string"},
                        "notes": {"type": "string"},
                        "all_day": {"type": "boolean", "default": False},
                        "invitees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Email addresses to invite.",
                        },
                        "alarm_minutes_before": {
                            "type": "integer",
                            "description": "Minutes before event to trigger alarm.",
                        },
                    },
                    "required": ["calendar_name", "title", "start_date", "end_date"],
                },
            ),
            Tool(
                name="apple_calendar_update_event",
                description="Update fields of an existing event. Only provide the fields you want to change.",
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
                    },
                    "required": ["calendar_name", "event_id"],
                },
            ),
            Tool(
                name="apple_calendar_delete_event",
                description="Delete an event from a calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string"},
                        "event_id": {"type": "string"},
                    },
                    "required": ["calendar_name", "event_id"],
                },
            ),
            Tool(
                name="apple_calendar_search_events",
                description="Search events across all visible calendars by keyword.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term — matches title, location, and notes."},
                        "from_date": {"type": "string"},
                        "to_date": {"type": "string"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="apple_calendar_add_calendar",
                description="Create a new calendar in your iCloud account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "color": {"type": "string", "description": "Hex color like #FF0000."},
                    },
                    "required": ["title"],
                },
            ),
            Tool(
                name="apple_calendar_remove_calendar",
                description="Delete a calendar and all its events. Cannot be undone.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string"},
                    },
                    "required": ["calendar_name"],
                },
            ),
            Tool(
                name="apple_calendar_get_availability",
                description="Check which time slots are free or busy across your calendars.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_date": {"type": "string", "description": "ISO datetime."},
                        "to_date": {"type": "string", "description": "ISO datetime."},
                    },
                    "required": ["from_date", "to_date"],
                },
            ),
            Tool(
                name="apple_calendar_get_changes",
                description="Get a sync token for incremental calendar change tracking.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="apple_calendar_share_calendar",
                description="Share a calendar with someone by email address.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_name": {"type": "string"},
                        "email": {"type": "string", "description": "Email of the person to share with."},
                    },
                    "required": ["calendar_name", "email"],
                },
            ),
        ]

    async def handle(self, name: str, arguments: dict) -> str:
        if self._api is None:
            raise ServiceUnavailableError("Calendar service not connected")

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
            "apple_calendar_share_calendar": self._share_calendar,
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

    def _get_calendar_by_name(self, name: str) -> CalendarObject:
        if not self._scope.calendar_visible(name):
            raise ScopeError(f"Calendar '{name}' is outside your configured scope")
        cals = self._api.calendar.get_calendars(as_objs=True)
        for cal in cals:
            if cal.title and cal.title.lower() == name.lower():
                return cal
        raise ScopeError(f"Calendar '{name}' not found")

    def _list_calendars(self, _args: dict) -> list[dict]:
        cals = self._api.calendar.get_calendars(as_objs=True)
        visible = []
        for cal in cals:
            name = getattr(cal, "title", "") or getattr(cal, "name", "")
            if not self._scope.calendar_visible(name):
                continue
            visible.append({
                "name": name,
                "guid": getattr(cal, "guid", ""),
                "color": getattr(cal, "color", None),
                "writable": self._scope.calendar_writable(name),
            })
        return visible

    def _get_events(self, args: dict) -> list[dict]:
        cal = self._get_calendar_by_name(args["calendar_name"])
        from_str = args.get("from_date", datetime.now(UTC).strftime("%Y-%m-%d"))
        to_str = args.get("to_date")
        period = args.get("period")

        if period:
            from_dt = datetime.fromisoformat(from_str)
            if period == "day":
                to_dt = from_dt + timedelta(days=1)
            elif period == "week":
                to_dt = from_dt + timedelta(weeks=1)
            else:
                to_dt = from_dt + timedelta(days=30)
        else:
            from_dt = datetime.fromisoformat(from_str)
            to_dt = datetime.fromisoformat(to_str) if to_str else from_dt + timedelta(days=30)

        events = self._api.calendar.get_events(
            from_dt=from_dt, to_dt=to_dt, as_objs=True
        )
        result = []
        for evt in events:
            if evt.pguid != cal.guid:
                continue
            result.append({
                "guid": evt.guid,
                "title": evt.title,
                "start": str(evt.start_date) if evt.start_date else None,
                "end": str(evt.end_date) if evt.end_date else None,
                "all_day": evt.all_day,
                "location": evt.location,
            })
        return result

    def _get_event(self, args: dict) -> dict:
        cal = self._get_calendar_by_name(args["calendar_name"])
        detail = self._api.calendar.get_event_detail(
            pguid=cal.guid, guid=args["event_id"]
        )
        return {
            "guid": getattr(detail, "guid", ""),
            "title": getattr(detail, "title", ""),
            "start": str(getattr(detail, "start_date", "")),
            "end": str(getattr(detail, "end_date", "")),
            "location": getattr(detail, "location", ""),
            "notes": getattr(detail, "description", ""),
            "all_day": getattr(detail, "all_day", False),
        }

    def _create_event(self, args: dict) -> dict:
        cal = self._get_calendar_by_name(args["calendar_name"])
        if not self._scope.calendar_writable(args["calendar_name"]):
            raise ScopeError("Calendar is read-only — cannot create events")

        self._scope.guard_read_only("calendar", "create_event")

        event = EventObject(
            pguid=cal.guid,
            title=args["title"],
            start_date=datetime.fromisoformat(args["start_date"]),
            end_date=datetime.fromisoformat(args["end_date"]),
            location=args.get("location", ""),
            all_day=args.get("all_day", False),
        )

        if args.get("invitees"):
            event.add_invitees(args["invitees"])
        if args.get("alarm_minutes_before") is not None:
            event.add_alarm_before(minutes=args["alarm_minutes_before"])

        self._api.calendar.add_event(event)
        return {"status": "created", "guid": event.guid, "title": event.title}

    def _update_event(self, args: dict) -> dict:
        cal = self._get_calendar_by_name(args["calendar_name"])
        if not self._scope.calendar_writable(args["calendar_name"]):
            raise ScopeError("Calendar is read-only — cannot update events")
        self._scope.guard_read_only("calendar", "update_event")

        detail = self._api.calendar.get_event_detail(pguid=cal.guid, guid=args["event_id"])

        if "title" in args:
            detail.title = args["title"]
        if "start_date" in args:
            detail.start_date = datetime.fromisoformat(args["start_date"])
        if "end_date" in args:
            detail.end_date = datetime.fromisoformat(args["end_date"])
        if "location" in args:
            detail.location = args["location"]
        if "notes" in args:
            detail.description = args["notes"]

        self._api.calendar.add_event(detail)
        return {"status": "updated", "guid": args["event_id"]}

    def _delete_event(self, args: dict) -> dict:
        cal = self._get_calendar_by_name(args["calendar_name"])
        if not self._scope.calendar_writable(args["calendar_name"]):
            raise ScopeError("Calendar is read-only — cannot delete events")
        self._scope.guard_read_only("calendar", "delete_event")

        detail = self._api.calendar.get_event_detail(pguid=cal.guid, guid=args["event_id"])
        self._api.calendar.remove_event(detail)
        return {"status": "deleted", "guid": args["event_id"]}

    def _search_events(self, args: dict) -> list[dict]:
        query = args["query"].lower()
        now = datetime.now(UTC)
        from_dt = (
            datetime.fromisoformat(args["from_date"])
            if args.get("from_date")
            else now - timedelta(days=90)
        )
        to_dt = (
            datetime.fromisoformat(args["to_date"])
            if args.get("to_date")
            else now + timedelta(days=90)
        )

        results = []
        cals = self._api.calendar.get_calendars(as_objs=True)
        for cal in cals:
            name = getattr(cal, "title", "") or getattr(cal, "name", "")
            if not self._scope.calendar_visible(name):
                continue
            events = self._api.calendar.get_events(from_dt=from_dt, to_dt=to_dt, as_objs=True)
            for evt in events:
                if evt.pguid != cal.guid:
                    continue
                haystack = f"{evt.title or ''} {evt.location or ''} {getattr(evt, 'description', '') or ''}".lower()
                if query in haystack:
                    results.append({
                        "guid": evt.guid,
                        "title": evt.title,
                        "start": str(evt.start_date),
                        "calendar": name,
                    })
        return results

    def _add_calendar(self, args: dict) -> dict:
        self._scope.guard_read_only("calendar", "add_calendar")
        cal = CalendarObject(title=args["title"])
        if args.get("color"):
            cal.color = args["color"]
        self._api.calendar.add_calendar(cal)
        return {"status": "created", "name": args["title"], "guid": cal.guid}

    def _remove_calendar(self, args: dict) -> dict:
        self._scope.guard_read_only("calendar", "remove_calendar")
        cal = self._get_calendar_by_name(args["calendar_name"])
        if not self._scope.calendar_writable(args["calendar_name"]):
            raise ScopeError("Calendar is read-only")
        self._api.calendar.remove_calendar(cal.guid)
        return {"status": "deleted", "name": args["calendar_name"]}

    def _get_availability(self, args: dict) -> dict:
        from_dt = datetime.fromisoformat(args["from_date"])
        to_dt = datetime.fromisoformat(args["to_date"])
        busy = []

        cals = self._api.calendar.get_calendars(as_objs=True)
        for cal in cals:
            name = getattr(cal, "title", "")
            if not self._scope.calendar_visible(name):
                continue
            events = self._api.calendar.get_events(from_dt=from_dt, to_dt=to_dt, as_objs=True)
            for evt in events:
                if evt.pguid != cal.guid:
                    continue
                busy.append({
                    "start": str(evt.start_date),
                    "end": str(evt.end_date),
                    "title": evt.title,
                    "calendar": name,
                })
        return {"busy_slots": busy}

    def _get_changes(self, _args: dict) -> dict:
        calendars = self._list_calendars({})
        return {
            "calendars": calendars,
            "note": "Sync cursor not yet available. Re-fetch events to detect changes.",
        }

    def _share_calendar(self, args: dict) -> dict:
        self._get_calendar_by_name(args["calendar_name"])
        self._scope.guard_read_only("calendar", "share_calendar")
        return {
            "status": "not_implemented",
            "message":             f"Sharing calendars via iCloud API is limited. Share '{args['calendar_name']}' "
            f"with {args['email']} through the Calendar app instead.",
        }
