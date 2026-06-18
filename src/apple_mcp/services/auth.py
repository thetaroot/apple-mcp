import contextlib
import logging
from typing import Any

import aioimaplib  # type: ignore[import-untyped]
from caldav import DAVClient  # type: ignore[import-untyped]
from pyicloud import PyiCloudService  # type: ignore[import-untyped]
from pyicloud.exceptions import PyiCloudFailedLoginException  # type: ignore[import-untyped]

from apple_mcp.config import ServerConfig
from apple_mcp.services import ServiceStatus

logger = logging.getLogger("apple_mcp.services.auth")


class AuthService:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.caldav: Any = None
        self.pyicloud: PyiCloudService | None = None
        self.mail_clients: dict[str, aioimaplib.IMAP4_SSL] = {}

    async def authenticate(self) -> ServiceStatus:
        status = ServiceStatus()

        if self.config.enable_calendar:
            password = self.config.password_for("calendar")
            if not password:
                status.errors["calendar"] = "No password configured"
            else:
                try:
                    self.caldav = DAVClient(  # type: ignore[operator]
                        url="https://caldav.icloud.com",
                        username=self.config.apple_id,
                        password=password,
                    )
                    principal = self.caldav.principal()
                    cals = principal.calendars()
                    status.calendar_ok = cals is not None
                except Exception as exc:
                    status.errors["calendar"] = str(exc)
                    logger.warning("CalDAV auth failed: %s", exc)

        if self.config.enable_reminders:
            reminders_pw = self.config.icloud_password or self.config.password_for("reminders")
            if not reminders_pw:
                status.errors["reminders"] = (
                    "Reminders requires your Apple Account password (not app-specific). "
                    "Set APPLE_ICLOUD_PASSWORD or disable reminders."
                )
            else:
                try:
                    self.pyicloud = PyiCloudService(self.config.apple_id, reminders_pw)

                    if self.pyicloud.requires_2fa or self.pyicloud.requires_2sa:
                        status.errors["reminders"] = (
                            "2FA required for Reminders. Use an app-specific password for "
                            "Calendar and Mail, and your main password for Reminders."
                        )
                    else:
                        self.pyicloud.reminders.lists()
                        status.reminders_ok = True
                except PyiCloudFailedLoginException:
                    status.errors["reminders"] = (
                        "Reminders login failed. Check APPLE_ICLOUD_PASSWORD. "
                        "Reminders requires your main Apple Account password."
                    )
                except Exception as exc:
                    status.errors["reminders"] = str(exc)
                    logger.warning("pyicloud auth failed: %s", exc)

        if self.config.enable_mail:
            for account_config in self.config.mail_accounts:
                try:
                    password = self._resolve_password(account_config.password_env)
                    if not password:
                        status.errors[f"mail.{account_config.email}"] = f"No password for {account_config.email}"
                        continue
                    imap = aioimaplib.IMAP4_SSL(
                        host=account_config.imap_host,
                        port=account_config.imap_port,
                        timeout=15,
                    )
                    try:
                        await imap.wait_hello_from_server()
                        await imap.login(account_config.email, password)
                        self.mail_clients[account_config.email] = imap
                    except Exception:
                        with contextlib.suppress(Exception):
                            await imap.logout()
                        raise
                except Exception as exc:
                    status.errors[f"mail.{account_config.email}"] = str(exc)
            status.mail_ok = len(self.mail_clients) > 0

        if status.errors:
            logger.warning(
                "Auth status: calendar=%s reminders=%s mail=%s errors=%s",
                status.calendar_ok,
                status.reminders_ok,
                status.mail_ok,
                status.errors,
            )
        return status

    def _resolve_password(self, env_name: str) -> str:
        import os

        if not env_name:
            return ""
        pw = os.getenv(env_name, "")
        if pw:
            return pw
        return self.config.mail_password or self.config.app_specific_password
