from apple_mcp.config import ServerConfig, load_config


class TestServerConfig:
    def test_defaults(self):
        config = ServerConfig(apple_id="test@icloud.com", app_specific_password="pw")
        assert config.enable_calendar is True
        assert config.enable_reminders is True
        assert config.enable_mail is True
        assert config.calendar_mode == "read_write"
        assert config.calendar_names == []

    def test_password_fallback(self):
        config = ServerConfig(
            apple_id="test@icloud.com",
            app_specific_password="shared",
        )
        assert config.password_for("calendar") == "shared"
        assert config.password_for("reminders") == "shared"
        assert config.password_for("mail") == "shared"

    def test_per_service_password_override(self):
        config = ServerConfig(
            apple_id="test@icloud.com",
            app_specific_password="shared",
            calendar_password="cal-only",
            reminders_password="rem-only",
            mail_password="mail-only",
        )
        assert config.password_for("calendar") == "cal-only"
        assert config.password_for("reminders") == "rem-only"
        assert config.password_for("mail") == "mail-only"

    def test_repr_redacts_passwords(self):
        config = ServerConfig(apple_id="test@icloud.com", app_specific_password="secret123")
        rep = repr(config)
        assert "secret123" not in rep
        assert "***" in rep

    def test_default_mail_account(self):
        config = ServerConfig(
            apple_id="test@icloud.com",
            app_specific_password="pw",
            enable_mail=True,
        )
        assert len(config.mail_accounts) == 1
        assert config.mail_accounts[0].type == "icloud"
        assert config.mail_accounts[0].imap_host == "imap.mail.me.com"

    def test_no_mail_accounts_when_disabled(self):
        config = ServerConfig(
            apple_id="test@icloud.com",
            app_specific_password="pw",
            enable_mail=False,
        )
        assert len(config.mail_accounts) == 0

    def test_has_any_service(self):
        config = ServerConfig(apple_id="t@t.com", app_specific_password="p")
        assert config.has_any_service is True

        config = ServerConfig(
            apple_id="t@t.com",
            app_specific_password="p",
            enable_calendar=False,
            enable_reminders=False,
            enable_mail=False,
        )
        assert config.has_any_service is False

    def test_cookie_directory_default_empty(self):
        config = ServerConfig(apple_id="t@t.com", app_specific_password="p")
        assert config.cookie_directory == ""

    def test_cookie_directory_set(self):
        config = ServerConfig(apple_id="t@t.com", app_specific_password="p", cookie_directory="/data/pyicloud")
        assert config.cookie_directory == "/data/pyicloud"


class TestLoadConfig:
    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("APPLE_ID", "envtest@icloud.com")
        monkeypatch.setenv("APPLE_APP_SPECIFIC_PASSWORD", "envpw")
        monkeypatch.setenv("APPLE_ENABLE_CALENDAR", "false")
        monkeypatch.setenv("APPLE_CALENDAR_NAMES", "Work,Projects")

        config = load_config()
        assert config.apple_id == "envtest@icloud.com"
        assert config.app_specific_password == "envpw"
        assert config.enable_calendar is False
        assert config.calendar_names == ["Work", "Projects"]

    def test_load_with_cookie_directory(self, monkeypatch):
        monkeypatch.setenv("APPLE_ID", "t@t.com")
        monkeypatch.setenv("APPLE_APP_SPECIFIC_PASSWORD", "pw")
        monkeypatch.setenv("APPLE_COOKIE_DIRECTORY", "/data/pyicloud")

        config = load_config()
        assert config.cookie_directory == "/data/pyicloud"

    def test_load_with_external_mail(self, monkeypatch):
        monkeypatch.setenv("APPLE_ID", "t@t.com")
        monkeypatch.setenv("APPLE_APP_SPECIFIC_PASSWORD", "pw")
        monkeypatch.setenv(
            "APPLE_MAIL_ACCOUNTS",
            '[{"type":"external","email":"user@example.com","imap_host":"imap.example.com",'
            '"imap_port":993,"smtp_host":"smtp.example.com","smtp_port":587,"password_env":"EXTRA"}]',
        )

        config = load_config()
        assert len(config.mail_accounts) == 1
        assert config.mail_accounts[0].type == "external"
        assert config.mail_accounts[0].email == "user@example.com"
