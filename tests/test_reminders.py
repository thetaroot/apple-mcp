import pytest

from apple_mcp.errors import ScopeError
from apple_mcp.services.reminders import RemindersService
from apple_mcp.services.scope import ScopeEngine


class FakeReminderList:
    def __init__(self, id, title, color=None, count=0):
        self.id = id
        self.title = title
        self.color = color
        self.count = count


class FakeReminder:
    def __init__(self, id, title, completed=False, priority=0, flagged=False, due_date=None, desc=""):
        self.id = id
        self.title = title
        self.completed = completed
        self.priority = priority
        self.flagged = flagged
        self.due_date = due_date
        self.desc = desc


class TestRemindersService:
    def test_tools_count(self, base_config, mock_pyicloud):
        scope = ScopeEngine(base_config)
        svc = RemindersService(mock_pyicloud, scope)
        tools = svc.tools()
        assert len(tools) == 15

    def test_list_lists_filtered(self, scoped_config, mock_pyicloud):
        scope = ScopeEngine(scoped_config)
        svc = RemindersService(mock_pyicloud, scope)

        mock_pyicloud.reminders.lists.return_value = [
            FakeReminderList("l1", "Work Tasks"),
            FakeReminderList("l2", "Shopping"),
            FakeReminderList("l3", "Personal"),
        ]

        result = svc._list_lists({})
        names = [lst["title"] for lst in result]
        assert "Work Tasks" in names
        assert "Shopping" not in names

    def test_list_lists_empty_allows_all(self, base_config, mock_pyicloud):
        scope = ScopeEngine(base_config)
        svc = RemindersService(mock_pyicloud, scope)

        mock_pyicloud.reminders.lists.return_value = [
            FakeReminderList("l1", "Anything"),
            FakeReminderList("l2", "Everything"),
        ]

        result = svc._list_lists({})
        assert len(result) == 2

    def test_get_reminders_excludes_completed(self, base_config, mock_pyicloud):
        scope = ScopeEngine(base_config)
        svc = RemindersService(mock_pyicloud, scope)

        mock_pyicloud.reminders.lists.return_value = [
            FakeReminderList("l1", "Work"),
        ]
        mock_pyicloud.reminders.reminders.return_value = [
            FakeReminder("r1", "Task 1", completed=False),
            FakeReminder("r2", "Task 2", completed=True),
            FakeReminder("r3", "Task 3", completed=False),
        ]

        result = svc._get_reminders({})
        assert len(result) == 2
        titles = [r["title"] for r in result]
        assert "Task 1" in titles
        assert "Task 2" not in titles

    def test_find_list_not_in_scope(self, scoped_config, mock_pyicloud):
        scope = ScopeEngine(scoped_config)
        svc = RemindersService(mock_pyicloud, scope)

        mock_pyicloud.reminders.lists.return_value = [
            FakeReminderList("l1", "Work Tasks"),
        ]

        with pytest.raises(ScopeError):
            svc._find_list("Shopping")
