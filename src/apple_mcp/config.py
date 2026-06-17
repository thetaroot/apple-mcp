import json
import os

from pydantic import BaseModel, Field


class MailAccountConfig(BaseModel):
    type: str = Field(default="icloud")
    email: str
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587
    password_env: str = ""
    folders_allow: list[str] = Field(default_factory=lambda: ["INBOX", "Sent"])


class ServerConfig(BaseModel):
    apple_id: str = Field(default="")
    app_specific_password: str = Field(default="")

    enable_calendar: bool = True
    enable_reminders: bool = True
    enable_mail: bool = True

    calendar_names: list[str] = Field(default_factory=list)
    calendar_exclude: list[str] = Field(default_factory=list)
    calendar_mode: str = "read_write"

    reminder_lists: list[str] = Field(default_factory=list)
    reminder_exclude: list[str] = Field(default_factory=list)
    reminder_mode: str = "read_write"

    mail_folders: list[str] = Field(default_factory=list)
    mail_exclude_folders: list[str] = Field(default_factory=list)
    mail_mode: str = "read_write"

    mail_accounts: list[MailAccountConfig] = Field(default_factory=list)

    calendar_password: str = Field(default="")
    reminders_password: str = Field(default="")
    mail_password: str = Field(default="")

    log_level: str = "INFO"

    def model_post_init(self, _context: object) -> None:
        if not self.calendar_password:
            self.calendar_password = self.app_specific_password
        if not self.reminders_password:
            self.reminders_password = self.app_specific_password
        if not self.mail_password:
            self.mail_password = self.app_specific_password

        valid_modes = {"read_write", "read_only"}
        for field_name in ("calendar_mode", "reminder_mode", "mail_mode"):
            value = getattr(self, field_name)
            if value not in valid_modes:
                raise ValueError(f"{field_name.upper()} must be 'read_write' or 'read_only', got '{value}'")

        if not self.mail_accounts and self.apple_id and self.enable_mail:
            self.mail_accounts = [
                MailAccountConfig(
                    type="icloud",
                    email=self.apple_id,
                    imap_host="imap.mail.me.com",
                    imap_port=993,
                    smtp_host="smtp.mail.me.com",
                    smtp_port=587,
                    password_env="APPLE_APP_SPECIFIC_PASSWORD",
                )
            ]

    def __repr__(self) -> str:
        safe = self.model_dump()
        for field in ("app_specific_password", "calendar_password", "reminders_password", "mail_password"):
            if safe.get(field):
                safe[field] = "***"
        return f"ServerConfig({json.dumps(safe)})"

    @property
    def has_any_service(self) -> bool:
        return self.enable_calendar or self.enable_reminders or self.enable_mail

    def password_for(self, service: str) -> str:
        mapping = {
            "calendar": self.calendar_password,
            "reminders": self.reminders_password,
            "mail": self.mail_password,
        }
        return mapping.get(service, self.app_specific_password)


def _parse_comma_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_config() -> ServerConfig:
    from dotenv import load_dotenv

    load_dotenv()

    mail_accounts_raw = os.getenv("APPLE_MAIL_ACCOUNTS")
    mail_accounts: list[MailAccountConfig] = []
    if mail_accounts_raw:
        try:
            raw = json.loads(mail_accounts_raw)
            mail_accounts = [MailAccountConfig(**item) for item in raw]
        except (json.JSONDecodeError, ValueError):
            pass

    return ServerConfig(
        apple_id=os.getenv("APPLE_ID", ""),
        app_specific_password=os.getenv("APPLE_APP_SPECIFIC_PASSWORD", ""),
        enable_calendar=os.getenv("APPLE_ENABLE_CALENDAR", "true").lower() == "true",
        enable_reminders=os.getenv("APPLE_ENABLE_REMINDERS", "true").lower() == "true",
        enable_mail=os.getenv("APPLE_ENABLE_MAIL", "true").lower() == "true",
        calendar_names=_parse_comma_list(os.getenv("APPLE_CALENDAR_NAMES")),
        calendar_exclude=_parse_comma_list(os.getenv("APPLE_CALENDAR_EXCLUDE")),
        calendar_mode=os.getenv("APPLE_CALENDAR_MODE", "read_write"),
        reminder_lists=_parse_comma_list(os.getenv("APPLE_REMINDER_LISTS")),
        reminder_exclude=_parse_comma_list(os.getenv("APPLE_REMINDER_EXCLUDE")),
        reminder_mode=os.getenv("APPLE_REMINDER_MODE", "read_write"),
        mail_folders=_parse_comma_list(os.getenv("APPLE_MAIL_FOLDERS")),
        mail_exclude_folders=_parse_comma_list(os.getenv("APPLE_MAIL_EXCLUDE_FOLDERS")),
        mail_mode=os.getenv("APPLE_MAIL_MODE", "read_write"),
        mail_accounts=mail_accounts,
        calendar_password=os.getenv("APPLE_CALENDAR_PASSWORD", ""),
        reminders_password=os.getenv("APPLE_REMINDERS_PASSWORD", ""),
        mail_password=os.getenv("APPLE_MAIL_PASSWORD", ""),
        log_level=os.getenv("APPLE_MCP_LOG_LEVEL", "INFO"),
    )
