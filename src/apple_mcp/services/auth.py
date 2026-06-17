import logging

import aioimaplib  # type: ignore[import-untyped]
from pyicloud import PyiCloudService  # type: ignore[import-untyped]
from pyicloud.exceptions import PyiCloudFailedLoginException  # type: ignore[import-untyped]

from apple_mcp.config import ServerConfig
from apple_mcp.errors import AuthError, ServiceUnavailableError
from apple_mcp.services import ServiceStatus

logger = logging.getLogger("apple_mcp.services.auth")


class AuthService:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.pyicloud: PyiCloudService | None = None
        self.mail_clients: dict[str, aioimaplib.IMAP4_SSL] = {}

    async def authenticate(self) -> ServiceStatus:
        status = ServiceStatus()

        needs_icloud = self.config.enable_calendar or self.config.enable_reminders
        if needs_icloud:
            password = self.config.password_for("calendar") or self.config.password_for("reminders")
            if not password:
                status.errors["icloud"] = "No password configured for iCloud services"
            else:
                try:
                    self.pyicloud = PyiCloudService(self.config.apple_id, password)

                    if self.pyicloud.requires_2fa or self.pyicloud.requires_2sa:
                        raise AuthError(
                            "Two-factor authentication required. Use an app-specific password, "
                            "not your main Apple Account password. Generate one at "
                            "https://account.apple.com → Sign-In and Security → App-Specific Passwords."
                        )

                    if self.config.enable_calendar:
                        try:
                            cals = self.pyicloud.calendar.get_calendars()
                            status.calendar_ok = cals is not None
                        except Exception as exc:
                            status.errors["calendar"] = str(exc)

                    if self.config.enable_reminders:
                        try:
                            self.pyicloud.reminders.lists()
                            status.reminders_ok = True
                        except Exception as exc:
                            status.errors["reminders"] = str(exc)

                except PyiCloudFailedLoginException as exc:
                    raise AuthError(
                        "iCloud login failed. Check your email address and app-specific password. "
                        "Generate a new app-specific password at https://account.apple.com"
                    ) from exc
                except AuthError:
                    raise
                except Exception as exc:
                    msg = str(exc)
                    status.errors["icloud"] = msg
                    logger.warning("iCloud connection failed: %s", msg)

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
                    await imap.wait_hello_from_server()
                    await imap.login(account_config.email, password)
                    self.mail_clients[account_config.email] = imap
                except Exception as exc:
                    status.errors[f"mail.{account_config.email}"] = str(exc)
                    logger.warning("Mail login failed for %s: %s", account_config.email, exc)

            status.mail_ok = len(self.mail_clients) > 0

        if status.errors:
            logger.warning(
                "Auth service status: calendar=%s reminders=%s mail=%s errors=%s",
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

    def get_mail_client(self, email: str) -> aioimaplib.IMAP4_SSL:
        client = self.mail_clients.get(email)
        if client is None:
            raise ServiceUnavailableError(f"Mail account '{email}' is not connected")
        return client
