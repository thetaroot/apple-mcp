from dataclasses import dataclass, field


@dataclass
class ServiceStatus:
    calendar_ok: bool = False
    reminders_ok: bool = False
    mail_ok: bool = False
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def all_ok(self) -> bool:
        return self.calendar_ok and self.reminders_ok and self.mail_ok
