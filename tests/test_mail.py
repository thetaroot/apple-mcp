import json
from unittest.mock import AsyncMock

import pytest

from apple_mcp.services.mail import MailService
from apple_mcp.services.scope import ScopeEngine


class FakeIMAPResult:
    def __init__(self, result="OK", lines=None):
        self.result = result
        self.lines = lines or []


class TestMailService:
    @pytest.fixture
    def mail_clients(self):
        imap = AsyncMock()
        imap.select.return_value = FakeIMAPResult("OK")
        imap.list.return_value = FakeIMAPResult(
            "OK",
            [
                b'(\\HasNoChildren) "/" "INBOX"',
                b'(\\HasNoChildren) "/" "Sent"',
                b'(\\HasNoChildren) "/" "Spam"',
            ],
        )
        return {"test@icloud.com": imap}

    @pytest.fixture
    def scoped_mail(self, scoped_config, mail_clients):
        scope = ScopeEngine(scoped_config)
        return MailService(mail_clients, scope)

    def test_tools_count(self, base_config, mail_clients):
        scope = ScopeEngine(base_config)
        svc = MailService(mail_clients, scope)
        tools = svc.tools()
        assert len(tools) == 10

    @pytest.mark.asyncio
    async def test_list_accounts(self, scoped_mail):
        result = await scoped_mail._list_accounts({})
        assert len(result) == 1
        assert result[0]["email"] == "test@icloud.com"

    @pytest.mark.asyncio
    async def test_list_folders_filtered(self, scoped_config, mail_clients):
        scope = ScopeEngine(scoped_config)
        svc = MailService(mail_clients, scope)

        imap = mail_clients["test@icloud.com"]
        imap.list.return_value = FakeIMAPResult(
            "OK",
            [
                b'(\\HasNoChildren) "/" "INBOX"',
                b'(\\HasNoChildren) "/" "Sent"',
                b'(\\HasNoChildren) "/" "Spam"',
                b'(\\HasNoChildren) "/" "Archive"',
            ],
        )

        result = await svc._list_folders({"account": "test@icloud.com"})
        names = [f["name"] for f in result]
        assert "INBOX" in names
        assert "Sent" in names
        assert "Spam" not in names

    @pytest.mark.asyncio
    async def test_read_only_blocks_send(self, readonly_config, mail_clients):
        scope = ScopeEngine(readonly_config)
        svc = MailService(mail_clients, scope)

        result = await svc.handle(
            "apple_mail_send",
            {
                "account": "test@icloud.com",
                "to": "someone@test.com",
                "subject": "Test",
                "body": "Hello",
            },
        )

        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_folder_not_visible(self, scoped_mail):
        result = await scoped_mail.handle(
            "apple_mail_search",
            {
                "account": "test@icloud.com",
                "folder": "Spam",
            },
        )
        parsed = json.loads(result)
        assert "error" in parsed
