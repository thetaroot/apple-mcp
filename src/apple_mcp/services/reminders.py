import asyncio
import json
import logging
from datetime import datetime

from mcp.types import Tool
from pyicloud import PyiCloudService  # type: ignore[import-untyped]

from apple_mcp.errors import ScopeError, ServiceUnavailableError
from apple_mcp.services.scope import ScopeEngine

logger = logging.getLogger("apple_mcp.services.reminders")


class RemindersService:
    def __init__(self, pyicloud: PyiCloudService, scope: ScopeEngine):
        self._api = pyicloud
        self._scope = scope

    def tools(self) -> list[Tool]:
        return [
            Tool(
                name="apple_reminders_list_lists",
                description="List all visible reminder lists. Names are filtered by your scope configuration.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="apple_reminders_get_reminders",
                description="Get reminders from a list. Filter by completion status, due date, priority, or flagged.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_name": {"type": "string", "description": "Optional: scope to one list."},
                        "include_completed": {"type": "boolean", "default": False},
                        "due_before": {"type": "string", "description": "ISO date — reminders due before this."},
                        "due_after": {"type": "string", "description": "ISO date — reminders due after this."},
                        "priority": {"type": "integer", "description": "0=none, 1=high, 5=medium, 9=low."},
                        "flagged_only": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "description": "Max reminders to return.", "default": 200},
                    },
                },
            ),
            Tool(
                name="apple_reminders_get_reminder",
                description="Get full details of a single reminder by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="apple_reminders_create",
                description="Create a new reminder in a list. Set title, notes, due date, priority, and flag.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_name": {"type": "string", "description": "Target reminder list."},
                        "title": {"type": "string"},
                        "notes": {"type": "string"},
                        "due_date": {"type": "string", "description": "ISO datetime."},
                        "priority": {"type": "integer", "description": "0=none, 1=high, 5=medium, 9=low."},
                        "flagged": {"type": "boolean", "default": False},
                    },
                    "required": ["list_name", "title"],
                },
            ),
            Tool(
                name="apple_reminders_update",
                description="Update fields of an existing reminder. Only provide what you want to change.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                        "title": {"type": "string"},
                        "notes": {"type": "string"},
                        "due_date": {"type": "string"},
                        "priority": {"type": "integer"},
                        "flagged": {"type": "boolean"},
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="apple_reminders_complete",
                description="Mark a reminder as completed.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="apple_reminders_uncomplete",
                description="Re-open a completed reminder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="apple_reminders_delete",
                description="Delete a reminder permanently.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="apple_reminders_add_alarm",
                description="Add a time-based alarm to a reminder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                        "alarm_time": {"type": "string", "description": "ISO datetime for the alarm."},
                    },
                    "required": ["reminder_id", "alarm_time"],
                },
            ),
            Tool(
                name="apple_reminders_add_hashtag",
                description="Add a hashtag label to a reminder for organisation.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                        "tag": {"type": "string", "description": "Tag name without the # symbol."},
                    },
                    "required": ["reminder_id", "tag"],
                },
            ),
            Tool(
                name="apple_reminders_add_url",
                description="Attach a URL to a reminder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["reminder_id", "url"],
                },
            ),
            Tool(
                name="apple_reminders_get_changes",
                description="Get a sync cursor for tracking changes. Pass a previous cursor to see what was modified.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cursor": {
                            "type": "string",
                            "description": "Previous sync cursor. Omit on first call to get an initial cursor.",
                        },
                    },
                },
            ),
            Tool(
                name="apple_reminders_create_recurrence",
                description="Add a recurrence rule to a reminder (daily, weekly, monthly, yearly).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                        "frequency": {
                            "type": "string",
                            "enum": ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"],
                        },
                        "interval": {"type": "integer", "description": "Repeat every N units.", "default": 1},
                        "occurrence_count": {"type": "integer", "description": "Total occurrences.", "default": 0},
                    },
                    "required": ["reminder_id", "frequency"],
                },
            ),
            Tool(
                name="apple_reminders_get_recurrence_rules",
                description="Get all recurrence rules attached to a reminder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="apple_reminders_delete_recurrence",
                description="Delete a recurrence rule from a reminder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                        "rule_index": {"type": "integer", "description": "Index of the rule to delete (0-based)."},
                    },
                    "required": ["reminder_id", "rule_index"],
                },
            ),
        ]

    async def handle(self, name: str, arguments: dict) -> str:
        if self._api is None:
            raise ServiceUnavailableError("Reminders service not connected")

        handlers = {
            "apple_reminders_list_lists": self._list_lists,
            "apple_reminders_get_reminders": self._get_reminders,
            "apple_reminders_get_reminder": self._get_reminder,
            "apple_reminders_create": self._create,
            "apple_reminders_update": self._update,
            "apple_reminders_complete": self._complete,
            "apple_reminders_uncomplete": self._uncomplete,
            "apple_reminders_delete": self._delete,
            "apple_reminders_add_alarm": self._add_alarm,
            "apple_reminders_add_hashtag": self._add_hashtag,
            "apple_reminders_add_url": self._add_url,
            "apple_reminders_get_changes": self._get_changes,
            "apple_reminders_create_recurrence": self._create_recurrence,
            "apple_reminders_get_recurrence_rules": self._get_recurrence_rules,
            "apple_reminders_delete_recurrence": self._delete_recurrence,
        }

        handler = handlers.get(name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(handler, arguments),
                timeout=30.0,
            )
            return json.dumps(result, default=str, ensure_ascii=False)
        except TimeoutError:
            logger.error("Reminders tool %s timed out after 30s", name)
            return json.dumps({"error": f"Tool {name} timed out after 30s", "type": "timeout_error"})
        except ScopeError as exc:
            return json.dumps({"error": str(exc), "type": "scope_error"})
        except Exception as exc:
            logger.exception("Reminders tool %s failed", name)
            return json.dumps({"error": str(exc), "type": "server_error"})

    def _get_visible_lists(self) -> list:
        all_lists = self._api.reminders.lists()
        return [lst for lst in all_lists if self._scope.reminder_list_visible(getattr(lst, "title", ""))]

    def _find_list(self, name: str):
        for lst in self._get_visible_lists():
            if getattr(lst, "title", "").lower() == name.lower():
                return lst
        raise ScopeError(f"Reminder list '{name}' not found or not in scope")

    def _list_lists(self, _args: dict) -> list[dict]:
        return [
            {
                "id": getattr(lst, "id", ""),
                "title": getattr(lst, "title", ""),
                "color": getattr(lst, "color", None),
                "count": getattr(lst, "count", 0),
                "writable": self._scope.reminder_writable(getattr(lst, "title", "")),
            }
            for lst in self._get_visible_lists()
        ]

    def _get_reminders(self, args: dict) -> list[dict]:
        list_name = args.get("list_name")
        include_completed = args.get("include_completed", False)
        due_before = args.get("due_before")
        due_after = args.get("due_after")
        priority = args.get("priority")
        flagged_only = args.get("flagged_only", False)
        limit = args.get("limit", 200)

        if list_name:
            target_list = self._find_list(list_name)
            raw = self._api.reminders.reminders(list_id=target_list.id)
        else:
            raw = self._api.reminders.reminders()

        results = []
        for r in raw:
            if not include_completed and getattr(r, "completed", False):
                continue
            if priority is not None and getattr(r, "priority", 0) != priority:
                continue
            if flagged_only and not getattr(r, "flagged", False):
                continue

            due_date = getattr(r, "due_date", None)
            if due_before and due_date:
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date)
                if due_date > datetime.fromisoformat(due_before):
                    continue
            if due_after and due_date:
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date)
                if due_date < datetime.fromisoformat(due_after):
                    continue

            results.append(
                {
                    "id": getattr(r, "id", ""),
                    "title": getattr(r, "title", ""),
                    "notes": getattr(r, "desc", ""),
                    "completed": getattr(r, "completed", False),
                    "priority": getattr(r, "priority", 0),
                    "flagged": getattr(r, "flagged", False),
                    "due_date": str(due_date) if due_date else None,
                }
            )
            if len(results) >= limit:
                break
        return results

    def _get_reminder(self, args: dict) -> dict:
        r = self._api.reminders.get(args["reminder_id"])
        return {
            "id": getattr(r, "id", ""),
            "title": getattr(r, "title", ""),
            "notes": getattr(r, "desc", ""),
            "completed": getattr(r, "completed", False),
            "priority": getattr(r, "priority", 0),
            "flagged": getattr(r, "flagged", False),
            "due_date": str(getattr(r, "due_date", None)) if getattr(r, "due_date", None) else None,
        }

    def _create(self, args: dict) -> dict:
        lst = self._find_list(args["list_name"])
        if not self._scope.reminder_writable(args["list_name"]):
            raise ScopeError("Reminder list is read-only")
        self._scope.guard_read_only("reminders", "create")

        due_date = None
        if args.get("due_date"):
            due_date = datetime.fromisoformat(args["due_date"])

        created = self._api.reminders.create(
            list_id=lst.id,
            title=args["title"],
            desc=args.get("notes", ""),
            due_date=due_date,
            priority=args.get("priority", 0),
            flagged=args.get("flagged", False),
        )
        return {"status": "created", "id": created.id, "title": created.title}

    def _update(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "update")

        reminder = self._api.reminders.get(args["reminder_id"])
        if reminder is None:
            raise ScopeError(f"Reminder {args['reminder_id']} not found")

        changed = False
        if "title" in args:
            reminder.title = args["title"]
            changed = True
        if "notes" in args:
            reminder.desc = args["notes"]
            changed = True
        if "due_date" in args:
            reminder.due_date = datetime.fromisoformat(args["due_date"]) if args["due_date"] else None
            changed = True
        if "priority" in args:
            reminder.priority = args["priority"]
            changed = True
        if "flagged" in args:
            reminder.flagged = args["flagged"]
            changed = True

        if changed:
            self._api.reminders.update(reminder)
        return {"status": "updated", "id": args["reminder_id"]}

    def _complete(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "complete")
        reminder = self._api.reminders.get(args["reminder_id"])
        reminder.completed = True
        self._api.reminders.update(reminder)
        return {"status": "completed", "id": args["reminder_id"]}

    def _uncomplete(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "uncomplete")
        reminder = self._api.reminders.get(args["reminder_id"])
        reminder.completed = False
        self._api.reminders.update(reminder)
        return {"status": "uncompleted", "id": args["reminder_id"]}

    def _delete(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "delete")
        reminder = self._api.reminders.get(args["reminder_id"])
        self._api.reminders.delete(reminder)
        return {"status": "deleted", "id": args["reminder_id"]}

    def _add_alarm(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "add_alarm")
        reminder = self._api.reminders.get(args["reminder_id"])
        alarm_dt = datetime.fromisoformat(args["alarm_time"])
        reminder.due_date = alarm_dt
        self._api.reminders.update(reminder)
        return {"status": "alarm_added", "due_date": str(alarm_dt)}

    def _add_hashtag(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "add_hashtag")
        reminder = self._api.reminders.get(args["reminder_id"])
        self._api.reminders.create_hashtag(reminder, args["tag"])
        return {"status": "tag_added", "tag": args["tag"]}

    def _add_url(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "add_url")
        reminder = self._api.reminders.get(args["reminder_id"])
        self._api.reminders.create_url_attachment(reminder, url=args["url"])
        return {"status": "url_attached", "url": args["url"]}

    def _get_changes(self, args: dict) -> dict:
        cursor = args.get("cursor")
        if cursor:
            events = []
            for change in self._api.reminders.iter_changes(since=cursor):
                reminder_data = None
                if change.reminder is not None:
                    r = change.reminder
                    reminder_data = {
                        "id": getattr(r, "id", ""),
                        "title": getattr(r, "title", ""),
                        "completed": getattr(r, "completed", False),
                    }
                events.append(
                    {
                        "type": getattr(change, "type", "unknown"),
                        "reminder_id": getattr(change, "reminder_id", ""),
                        "reminder": reminder_data,
                    }
                )
            new_cursor = self._api.reminders.sync_cursor()
            return {"cursor": new_cursor, "events": events}
        else:
            cursor = self._api.reminders.sync_cursor()
            return {"cursor": cursor, "events": [], "note": "Cursor created. Save it and pass back to get changes."}

    def _create_recurrence(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "create_recurrence")
        from pyicloud.services.reminders.models import RecurrenceFrequency  # type: ignore[import-untyped]

        reminder = self._api.reminders.get(args["reminder_id"])
        freq = getattr(RecurrenceFrequency, args["frequency"], RecurrenceFrequency.DAILY)
        rule = self._api.reminders.create_recurrence_rule(
            reminder,
            frequency=freq,
            interval=args.get("interval", 1),
            occurrence_count=args.get("occurrence_count", 0),
        )
        return {"status": "recurrence_created", "rule_id": getattr(rule, "id", "")}

    def _get_recurrence_rules(self, args: dict) -> dict:
        reminder = self._api.reminders.get(args["reminder_id"])
        rules = []
        for rule in self._api.reminders.recurrence_rules_for(reminder):
            rules.append(
                {
                    "id": getattr(rule, "id", ""),
                    "frequency": str(getattr(rule, "frequency", "")),
                    "interval": getattr(rule, "interval", 1),
                    "occurrence_count": getattr(rule, "occurrence_count", 0),
                }
            )
        return {"recurrence_rules": rules}

    def _delete_recurrence(self, args: dict) -> dict:
        self._scope.guard_read_only("reminders", "delete_recurrence")
        reminder = self._api.reminders.get(args["reminder_id"])
        rules = self._api.reminders.recurrence_rules_for(reminder)
        rules_list = list(rules)
        idx = args["rule_index"]
        if idx < 0 or idx >= len(rules_list):
            raise ScopeError(f"Invalid rule_index {idx}: reminder has {len(rules_list)} rules")
        self._api.reminders.delete_recurrence_rule(reminder, rules_list[idx])
        return {"status": "recurrence_deleted", "rule_index": idx}
