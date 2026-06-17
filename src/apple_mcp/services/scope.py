import logging

from apple_mcp.config import ServerConfig
from apple_mcp.errors import ScopeError

logger = logging.getLogger("apple_mcp.services.scope")


class ScopeEngine:
    def __init__(self, config: ServerConfig):
        self.config = config

    def _match_name(self, name: str, allowlist: list[str], blocklist: list[str]) -> bool:
        name_lower = name.lower()

        for blocked in blocklist:
            if blocked.lower() in name_lower:
                return False

        if not allowlist:
            return True

        for allowed in allowlist:  # noqa: SIM110
            if allowed.lower() in name_lower:
                return True

        return False

    def calendar_visible(self, name: str) -> bool:
        return self._match_name(name, self.config.calendar_names, self.config.calendar_exclude)

    def calendar_writable(self, name: str) -> bool:
        if not self.calendar_visible(name):
            return False
        return self.config.calendar_mode == "read_write"

    def reminder_list_visible(self, name: str) -> bool:
        return self._match_name(name, self.config.reminder_lists, self.config.reminder_exclude)

    def reminder_writable(self, name: str) -> bool:
        if not self.reminder_list_visible(name):
            return False
        return self.config.reminder_mode == "read_write"

    def mail_folder_visible(self, folder_name: str) -> bool:
        return self._match_name(folder_name, self.config.mail_folders, self.config.mail_exclude_folders)

    def mail_writable(self) -> bool:
        return self.config.mail_mode == "read_write"

    def mail_account_visible(self, email: str) -> bool:
        configured_emails = [a.email for a in self.config.mail_accounts]
        if not configured_emails:
            return True
        return email in configured_emails

    def guard_read_only(self, service: str, operation: str) -> None:
        modes = {
            "calendar": self.config.calendar_mode,
            "reminders": self.config.reminder_mode,
            "mail": self.config.mail_mode,
        }
        mode = modes.get(service, "read_write")
        if mode == "read_only":
            raise ScopeError(f"{service} is in read-only mode — {operation} not allowed")
