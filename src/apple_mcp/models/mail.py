from datetime import datetime

from pydantic import BaseModel, Field


class MailAccountConfig(BaseModel):
    type: str = "icloud"
    email: str = ""
    imap_host: str = "imap.mail.me.com"
    imap_port: int = 993
    smtp_host: str = "smtp.mail.me.com"
    smtp_port: int = 587
    password_env: str = ""
    folders_allow: list[str] = Field(default_factory=lambda: ["INBOX", "Sent"])


class MailFolder(BaseModel):
    name: str = ""
    writable: bool = True


class MailMessage(BaseModel):
    uid: str = ""
    subject: str = ""
    from_: str = Field("", alias="from")
    to: str = ""
    date: datetime | None = None
    summary: str = ""


class MailMessageFull(BaseModel):
    uid: str = ""
    subject: str = ""
    from_: str = Field("", alias="from")
    to: str = ""
    cc: str = ""
    date: datetime | None = None
    body_text: str = ""
    body_html: bool = False
    attachments: list[dict] = Field(default_factory=list)
