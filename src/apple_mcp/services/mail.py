import json
import logging
from datetime import datetime
from typing import Any

from mailparser import MailParser  # type: ignore[import-untyped]
from mcp.types import Tool

from apple_mcp.errors import ScopeError, ServiceUnavailableError
from apple_mcp.services.scope import ScopeEngine

logger = logging.getLogger("apple_mcp.services.mail")


class MailService:
    def __init__(self, mail_clients: dict, scope: ScopeEngine):
        self._clients = mail_clients
        self._scope = scope

    def tools(self) -> list[Tool]:
        return [
            Tool(
                name="apple_mail_list_accounts",
                description="List all configured mail accounts that are connected and within scope.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="apple_mail_list_folders",
                description="List mail folders for an account. Folders are filtered by your scope configuration.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string", "description": "Email address of the account."},
                    },
                    "required": ["account"],
                },
            ),
            Tool(
                name="apple_mail_search",
                description="Search emails across accounts and folders by various criteria.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string", "description": "Optional: scope to one account."},
                        "folder": {"type": "string", "default": "INBOX"},
                        "query": {"type": "string", "description": "Free-text search term."},
                        "from": {"type": "string", "description": "Filter by sender address."},
                        "to": {"type": "string", "description": "Filter by recipient."},
                        "subject": {"type": "string"},
                        "since": {"type": "string", "description": "ISO date — messages since this date."},
                        "before": {"type": "string", "description": "ISO date — messages before this date."},
                        "limit": {"type": "integer", "default": 20, "description": "Max results to return."},
                    },
                    "required": ["account"],
                },
            ),
            Tool(
                name="apple_mail_get",
                description="Fetch a complete email message by UID. Returns headers, body, and attachment metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "folder": {"type": "string", "default": "INBOX"},
                        "uid": {"type": "string", "description": "Email UID from search results."},
                    },
                    "required": ["account", "uid"],
                },
            ),
            Tool(
                name="apple_mail_send",
                description="Send an email from one of your configured accounts. Supports plain text and HTML body.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string", "description": "Sender email address."},
                        "to": {"type": "string", "description": "Recipient. Multiple addresses: comma-separated."},
                        "cc": {"type": "string"},
                        "bcc": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string", "description": "Plain text body."},
                        "html": {"type": "string", "description": "Optional HTML body."},
                    },
                    "required": ["account", "to", "subject", "body"],
                },
            ),
            Tool(
                name="apple_mail_reply",
                description="Reply to an existing email. Optionally include all original recipients (reply-all).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "folder": {"type": "string", "default": "INBOX"},
                        "uid": {"type": "string", "description": "UID of the email to reply to."},
                        "body": {"type": "string"},
                        "reply_all": {"type": "boolean", "default": False},
                    },
                    "required": ["account", "uid", "body"],
                },
            ),
            Tool(
                name="apple_mail_move",
                description="Move an email to a different folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "uid": {"type": "string"},
                        "from_folder": {"type": "string", "default": "INBOX"},
                        "to_folder": {"type": "string"},
                    },
                    "required": ["account", "uid", "to_folder"],
                },
            ),
            Tool(
                name="apple_mail_flag",
                description="Flag or unflag an email.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "uid": {"type": "string"},
                        "folder": {"type": "string", "default": "INBOX"},
                        "flagged": {"type": "boolean", "default": True},
                    },
                    "required": ["account", "uid"],
                },
            ),
            Tool(
                name="apple_mail_mark_read",
                description="Mark an email as read or unread.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "uid": {"type": "string"},
                        "folder": {"type": "string", "default": "INBOX"},
                        "read": {"type": "boolean", "default": True},
                    },
                    "required": ["account", "uid"],
                },
            ),
            Tool(
                name="apple_mail_delete",
                description="Delete an email or move it to the Trash folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "uid": {"type": "string"},
                        "folder": {"type": "string", "default": "INBOX"},
                    },
                    "required": ["account", "uid"],
                },
            ),
        ]

    async def handle(self, name: str, arguments: dict) -> str:
        handlers = {
            "apple_mail_list_accounts": self._list_accounts,
            "apple_mail_list_folders": self._list_folders,
            "apple_mail_search": self._search,
            "apple_mail_get": self._get,
            "apple_mail_send": self._send,
            "apple_mail_reply": self._reply,
            "apple_mail_move": self._move,
            "apple_mail_flag": self._flag,
            "apple_mail_mark_read": self._mark_read,
            "apple_mail_delete": self._delete,
        }

        handler = handlers.get(name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            result = await handler(arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except ScopeError as exc:
            return json.dumps({"error": str(exc), "type": "scope_error"})
        except Exception as exc:
            logger.exception("Mail tool %s failed", name)
            return json.dumps({"error": str(exc), "type": "server_error"})

    def _get_client(self, account: str):
        client = self._clients.get(account)
        if client is None:
            raise ServiceUnavailableError(f"Mail account '{account}' is not connected")
        return client

    async def _select_folder(self, imap, folder: str) -> None:
        folder_name = f'"{folder}"' if " " in folder else folder
        result = await imap.select(folder_name)
        if result.result != "OK":
            raise ScopeError(f"Cannot access folder: {folder}")

    async def _list_accounts(self, _args: dict) -> list[dict]:
        return [
            {"email": email, "connected": True} for email in self._clients if self._scope.mail_account_visible(email)
        ]

    async def _list_folders(self, args: dict) -> list[dict]:
        imap = self._get_client(args["account"])
        result = await imap.list()
        folders = []
        for line in result.lines:
            if line is None:
                continue
            name = self._parse_folder_name(line)
            if not name:
                continue
            if not self._scope.mail_folder_visible(name):
                continue
            folders.append(
                {
                    "name": name,
                    "writable": self._scope.mail_writable(),
                }
            )
        return folders

    async def _search(self, args: dict) -> list[dict]:
        imap = self._get_client(args["account"])
        folder = args.get("folder", "INBOX")

        if not self._scope.mail_folder_visible(folder):
            raise ScopeError(f"Folder '{folder}' is outside your scope")

        await self._select_folder(imap, folder)

        criteria = self._build_search_criteria(args)
        result = await imap.uid("search", None, *criteria)

        uids = []
        if result.lines:
            for line in result.lines:
                parts = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
                for part in parts.split():
                    if part.isdigit():
                        uids.append(part)

        limit = args.get("limit", 20)
        uids = uids[-limit:]

        messages = []
        for uid in uids:
            fetch_result = await imap.uid("fetch", uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
            msg_info = self._parse_header_fetch(uid, fetch_result)
            if msg_info:
                messages.append(msg_info)

        return messages

    async def _get(self, args: dict) -> dict:
        imap = self._get_client(args["account"])
        folder = args.get("folder", "INBOX")
        await self._select_folder(imap, folder)

        fetch_result = await imap.uid("fetch", args["uid"], "(BODY.PEEK[])")
        raw = self._extract_body(fetch_result)
        if not raw:
            raise ServiceUnavailableError(f"Email {args['uid']} not found")

        parser = MailParser()
        parsed = parser.parse_from_bytes(raw.encode() if isinstance(raw, str) else raw)

        attachments = []
        for att in parsed.attachments:
            attachments.append(
                {
                    "filename": att.get("filename", "unnamed"),
                    "content_type": att.get("mail_content_type", "unknown"),
                    "size": len(att.get("payload", b"")),
                }
            )

        return {
            "uid": args["uid"],
            "from": parsed.from_,
            "to": parsed.to,
            "cc": parsed.cc,
            "subject": parsed.subject,
            "date": str(parsed.date) if parsed.date else None,
            "body_text": parsed.body,
            "body_html": bool(parsed.body_html),
            "attachments": attachments,
        }

    async def _send(self, args: dict) -> dict:
        if not self._scope.mail_writable():
            raise ScopeError("Mail is in read-only mode")

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["From"] = args["account"]
        msg["To"] = args["to"]
        msg["Subject"] = args["subject"]
        if args.get("cc"):
            msg["Cc"] = args["cc"]

        msg.attach(MIMEText(args["body"], "plain", "utf-8"))
        if args.get("html"):
            msg.attach(MIMEText(args["html"], "html", "utf-8"))

        recipients = [a.strip() for a in args["to"].split(",")]
        if args.get("cc"):
            recipients += [a.strip() for a in args["cc"].split(",")]

        import os

        smtp = aiosmtplib.SMTP(hostname="smtp.mail.me.com", port=587, use_tls=True)
        await smtp.connect()
        await smtp.login(args["account"], os.getenv("APPLE_APP_SPECIFIC_PASSWORD", ""))
        await smtp.send_message(msg)
        await smtp.quit()

        return {"status": "sent", "to": args["to"], "subject": args["subject"]}

    async def _reply(self, args: dict) -> dict:
        if not self._scope.mail_writable():
            raise ScopeError("Mail is in read-only mode")
        return {"status": "not_implemented", "note": "Reply support requires IMAP APPEND and more message parsing."}

    async def _move(self, args: dict) -> dict:
        if not self._scope.mail_writable():
            raise ScopeError("Mail is in read-only mode")
        imap = self._get_client(args["account"])
        from_folder = args.get("from_folder", "INBOX")
        to_folder = args["to_folder"]

        if not self._scope.mail_folder_visible(to_folder):
            raise ScopeError(f"Target folder '{to_folder}' is outside your scope")

        await self._select_folder(imap, from_folder)
        result = await imap.uid("copy", args["uid"], f'"{to_folder}"')
        if result.result == "OK":
            await imap.uid("store", args["uid"], "+FLAGS", "(\\Deleted)")
            await imap.expunge()
        return {"status": "moved", "uid": args["uid"], "to": to_folder}

    async def _flag(self, args: dict) -> dict:
        if not self._scope.mail_writable():
            raise ScopeError("Mail is in read-only mode")
        imap = self._get_client(args["account"])
        folder = args.get("folder", "INBOX")
        await self._select_folder(imap, folder)

        flag = "+FLAGS" if args.get("flagged", True) else "-FLAGS"
        await imap.uid("store", args["uid"], flag, "(\\Flagged)")
        return {"status": "flagged" if args.get("flagged", True) else "unflagged", "uid": args["uid"]}

    async def _mark_read(self, args: dict) -> dict:
        if not self._scope.mail_writable():
            raise ScopeError("Mail is in read-only mode")
        imap = self._get_client(args["account"])
        folder = args.get("folder", "INBOX")
        await self._select_folder(imap, folder)

        flag = "+FLAGS" if args.get("read", True) else "-FLAGS"
        await imap.uid("store", args["uid"], flag, "(\\Seen)")
        return {"status": "read" if args.get("read", True) else "unread", "uid": args["uid"]}

    async def _delete(self, args: dict) -> dict:
        if not self._scope.mail_writable():
            raise ScopeError("Mail is in read-only mode")
        imap = self._get_client(args["account"])
        folder = args.get("folder", "INBOX")
        await self._select_folder(imap, folder)

        await imap.uid("store", args["uid"], "+FLAGS", "(\\Deleted)")
        await imap.expunge()
        return {"status": "deleted", "uid": args["uid"]}

    def _build_search_criteria(self, args: dict) -> list:
        criteria = []

        if args.get("query"):
            criteria.extend(["TEXT", f'"{args["query"]}"'])
        if args.get("from"):
            criteria.extend(["FROM", f'"{args["from"]}"'])
        if args.get("to"):
            criteria.extend(["TO", f'"{args["to"]}"'])
        if args.get("subject"):
            criteria.extend(["SUBJECT", f'"{args["subject"]}"'])
        if args.get("since"):
            date_obj = datetime.fromisoformat(args["since"])
            criteria.extend(["SINCE", date_obj.strftime("%d-%b-%Y")])
        if args.get("before"):
            date_obj = datetime.fromisoformat(args["before"])
            criteria.extend(["BEFORE", date_obj.strftime("%d-%b-%Y")])

        return criteria if criteria else ["ALL"]

    def _parse_folder_name(self, line: bytes | str) -> str:
        raw = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
        parts = raw.split('"')
        if len(parts) >= 2:
            return parts[-2] if parts[-2] else (parts[-3] if len(parts) >= 4 else raw)
        return raw.strip()

    def _parse_header_fetch(self, uid: str, result) -> dict | None:
        try:
            raw = self._extract_body(result)
            if not raw:
                return None
            lines = raw.split("\n") if isinstance(raw, str) else raw.decode(errors="replace").split("\n")
            info: dict[str, Any] = {"uid": uid}
            for line in lines:
                line_lower = line.lower()
                if line_lower.startswith("from:"):
                    info["from"] = line[5:].strip()
                elif line_lower.startswith("to:"):
                    info["to"] = line[3:].strip()
                elif line_lower.startswith("subject:"):
                    info["subject"] = line[8:].strip()
                elif line_lower.startswith("date:"):
                    info["date"] = line[5:].strip()
            return info
        except Exception:
            return None

    def _extract_body(self, fetch_result) -> str | None:
        if hasattr(fetch_result, "lines"):
            for line in fetch_result.lines:
                if isinstance(line, (bytes, str)):
                    raw = line.decode(errors="replace") if isinstance(line, bytes) else line
                    if len(raw) > 50:
                        return raw
                elif isinstance(line, (list, tuple)):
                    for item in line:
                        if isinstance(item, bytes):
                            decoded = item.decode(errors="replace")
                            if len(decoded) > 50:
                                return decoded
        return None
