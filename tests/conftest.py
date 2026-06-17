from unittest.mock import MagicMock

import pytest

from apple_mcp.config import ServerConfig


@pytest.fixture
def base_config() -> ServerConfig:
    return ServerConfig(
        apple_id="test@icloud.com",
        app_specific_password="test-password",
        enable_calendar=True,
        enable_reminders=True,
        enable_mail=True,
    )


@pytest.fixture
def scoped_config() -> ServerConfig:
    return ServerConfig(
        apple_id="test@icloud.com",
        app_specific_password="test-password",
        enable_calendar=True,
        enable_reminders=True,
        enable_mail=True,
        calendar_names=["Work", "SwiftGate"],
        calendar_exclude=["Personal"],
        reminder_lists=["Work Tasks"],
        reminder_exclude=["Shopping"],
        mail_folders=["INBOX", "Sent"],
        mail_exclude_folders=["Spam"],
    )


@pytest.fixture
def readonly_config() -> ServerConfig:
    return ServerConfig(
        apple_id="test@icloud.com",
        app_specific_password="test-password",
        enable_calendar=True,
        enable_reminders=True,
        enable_mail=True,
        calendar_mode="read_only",
        reminder_mode="read_only",
        mail_mode="read_only",
    )


@pytest.fixture
def mock_pyicloud():
    cloud = MagicMock()
    cloud.authenticate.return_value = None
    return cloud
