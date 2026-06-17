from datetime import datetime

from pydantic import BaseModel, Field


class Calendar(BaseModel):
    name: str = ""
    guid: str = ""
    color: str | None = None
    writable: bool = True


class CalendarEvent(BaseModel):
    guid: str = ""
    title: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    location: str = ""
    notes: str = ""
    all_day: bool = False
    calendar_name: str = ""


class EventCreate(BaseModel):
    calendar_name: str
    title: str
    start_date: datetime
    end_date: datetime
    location: str = ""
    notes: str = ""
    all_day: bool = False
    invitees: list[str] = Field(default_factory=list)
    alarm_minutes_before: int | None = None


class EventUpdate(BaseModel):
    calendar_name: str
    event_id: str
    title: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    location: str | None = None
    notes: str | None = None
