from datetime import datetime

from pydantic import BaseModel


class ReminderList(BaseModel):
    id: str = ""
    title: str = ""
    color: str | None = None
    count: int = 0
    writable: bool = True


class Reminder(BaseModel):
    id: str = ""
    title: str = ""
    notes: str = ""
    completed: bool = False
    priority: int = 0
    flagged: bool = False
    due_date: datetime | None = None
    list_id: str = ""


class ReminderCreate(BaseModel):
    list_name: str
    title: str
    notes: str = ""
    due_date: datetime | None = None
    priority: int = 0
    flagged: bool = False


class ReminderUpdate(BaseModel):
    reminder_id: str
    title: str | None = None
    notes: str | None = None
    due_date: datetime | None = None
    priority: int | None = None
    flagged: bool | None = None
