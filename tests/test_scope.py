import pytest

from apple_mcp.errors import ScopeError
from apple_mcp.services.scope import ScopeEngine


class TestCalendarScope:
    def test_allowlist_match(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        assert scope.calendar_visible("Work") is True
        assert scope.calendar_visible("SwiftGate") is True
        assert scope.calendar_visible("Personal") is False
        assert scope.calendar_visible("Random") is False

    def test_blocklist_overrides_allowlist(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        assert scope.calendar_visible("Personal") is False

    def test_no_filter_allows_all(self, base_config):
        scope = ScopeEngine(base_config)
        assert scope.calendar_visible("Anything") is True
        assert scope.calendar_visible("Personal Stuff") is True

    def test_case_insensitive(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        assert scope.calendar_visible("work") is True
        assert scope.calendar_visible("WORK") is True

    def test_partial_match(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        assert scope.calendar_visible("Work Projects") is True

    def test_read_only_blocks_writes(self, readonly_config):
        scope = ScopeEngine(readonly_config)
        assert scope.calendar_visible("Work") is True
        assert scope.calendar_writable("Work") is False


class TestRemindersScope:
    def test_allowlist(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        assert scope.reminder_list_visible("Work Tasks") is True
        assert scope.reminder_list_visible("Shopping") is False

    def test_read_only(self, readonly_config):
        scope = ScopeEngine(readonly_config)
        assert scope.reminder_writable("Any List") is False


class TestMailScope:
    def test_folder_visible(self, scoped_config):
        scope = ScopeEngine(scoped_config)
        assert scope.mail_folder_visible("INBOX") is True
        assert scope.mail_folder_visible("Sent") is True
        assert scope.mail_folder_visible("Spam") is False
        assert scope.mail_folder_visible("Archive") is False

    def test_no_filter_allows_all_folders(self, base_config):
        scope = ScopeEngine(base_config)
        assert scope.mail_folder_visible("Anything") is True

    def test_read_only_blocks_send(self, readonly_config):
        scope = ScopeEngine(readonly_config)
        assert scope.mail_writable() is False


class TestGuardReadOnly:
    def test_raises_scope_error(self, readonly_config):
        scope = ScopeEngine(readonly_config)
        with pytest.raises(ScopeError):
            scope.guard_read_only("calendar", "create_event")

    def test_passes_for_read_write(self, base_config):
        scope = ScopeEngine(base_config)
        scope.guard_read_only("calendar", "create_event")
