# Apple MCP

Model Context Protocol server for Apple iCloud. Gives your AI agents access to your Calendar, Reminders, and Mail — filtered through a scope engine so they only see what you want them to see.

Supports stdio and HTTP transport. Works anywhere, not just macOS. 37 tools, zero stubs.

## What It Does

Connects your AI tools (Claude Desktop, Continue.dev, Cursor, or any MCP client) to your iCloud account. Three services, each independently toggleable:

- **Calendar** (12 tools) — list, create, update, delete events and calendars. Search by keyword, check availability, recurrence support.
- **Reminders** (15 tools) — full CRUD. Alarms, hashtags, URL attachments, recurrence rules, sync cursors.
- **Mail** (10 tools) — multi-account IMAP. Search, read, send, reply, move, flag, delete emails.

All access is gated through a **scope engine**. Configure which calendars, reminder lists, mail folders, and mail accounts are visible. Put a service in read-only mode if you only want your agent to see data, not change it.

## Quick Start

### Generate an App-Specific Password

You need an app-specific password, **not** your main Apple Account password.

1. Go to [account.apple.com](https://account.apple.com)
2. Sign in → Sign-In and Security → App-Specific Passwords
3. Click "Generate an app-specific password"
4. Name it "Apple MCP" so you know what it's for
5. Copy the password (format: `xxxx-xxxx-xxxx-xxxx`)

You can revoke this password at any time from the same page.

### Run with Docker

```bash
docker run -p 8080:8080 \
  -e APPLE_ID=you@icloud.com \
  -e APPLE_APP_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx \
  ghcr.io/thetaroot/apple-mcp:latest
```

### Run with pip

```bash
pip install apple-mcp
apple-mcp --transport http
```

Or stdio transport for local MCP clients:

```bash
apple-mcp --transport stdio
```

### Using with Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apple": {
      "command": "python",
      "args": ["-m", "apple_mcp", "--transport", "stdio"],
      "env": {
        "APPLE_ID": "you@icloud.com",
        "APPLE_APP_SPECIFIC_PASSWORD": "xxxx-xxxx-xxxx-xxxx",
        "APPLE_CALENDAR_NAMES": "Work",
        "APPLE_REMINDER_LISTS": "Work Tasks",
        "APPLE_MAIL_MODE": "read_only"
      }
    }
  }
}
```

### Using with Cursor or Continue.dev

Point your MCP client to the HTTP endpoint:

```json
{
  "mcpServers": {
    "apple": {
      "url": "http://localhost:8080/mcp",
      "headers": {}
    }
  }
}
```

The HTTP transport uses the standard MCP Streamable HTTP protocol (spec 2025-03-26).

## Configuration

All configuration via environment variables.

### Authentication (required)

| Variable | Description |
|----------|-------------|
| `APPLE_ID` | Your iCloud email address |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password (shared for all services) |

For better security, use per-service passwords instead:

| Variable | Description |
|----------|-------------|
| `APPLE_CALENDAR_PASSWORD` | Password for calendar only |
| `APPLE_REMINDERS_PASSWORD` | Password for reminders only |
| `APPLE_MAIL_PASSWORD` | Password for mail only |

### Service Toggles

| Variable | Default | Description |
|----------|---------|-------------|
| `APPLE_ENABLE_CALENDAR` | `true` | Enable calendar tools |
| `APPLE_ENABLE_REMINDERS` | `true` | Enable reminder tools |
| `APPLE_ENABLE_MAIL` | `true` | Enable mail tools |

### Calendar Scope

| Variable | Description |
|----------|-------------|
| `APPLE_CALENDAR_NAMES` | Comma-separated calendar names to allow |
| `APPLE_CALENDAR_EXCLUDE` | Comma-separated calendar names to block |
| `APPLE_CALENDAR_MODE` | `read_write` (default) or `read_only` |

### Reminder Scope

| Variable | Description |
|----------|-------------|
| `APPLE_REMINDER_LISTS` | Comma-separated list names to allow |
| `APPLE_REMINDER_EXCLUDE` | Comma-separated list names to block |
| `APPLE_REMINDER_MODE` | `read_write` or `read_only` |

### Mail Scope

| Variable | Description |
|----------|-------------|
| `APPLE_MAIL_FOLDERS` | Comma-separated folder names to allow |
| `APPLE_MAIL_EXCLUDE_FOLDERS` | Comma-separated folder names to block |
| `APPLE_MAIL_MODE` | `read_write` or `read_only` |

### External Mail Accounts

```bash
APPLE_MAIL_ACCOUNTS='[
  {"type": "icloud", "email": "you@icloud.com", "folders_allow": ["INBOX", "Sent"]},
  {"type": "external", "email": "luis@company.com", "imap_host": "mail.company.com",
   "imap_port": 993, "smtp_host": "mail.company.com", "smtp_port": 587,
   "password_env": "MAIL_PWD_WORK", "folders_allow": ["INBOX", "Sent"]}
]'
MAIL_PWD_WORK=your-external-mail-password
```

## Tools Reference

### Calendar — 12 tools

All functional, no stubs. Recurrence support via `recurrence` parameter (RRULE string). Change tracking via `get_changes` (ctag-based).

### Reminders — 15 tools

All functional, no stubs. Recurrence support: create, list, and delete recurrence rules. Sync cursor support via `get_changes`.

### Mail — 10 tools

All functional, no stubs. Reply support via SMTP with In-Reply-To headers. Full HTML body returned by `get`.

## Health Check

```bash
curl http://localhost:8080/health
# {"status":"ok","version":"1.1.0","tools_registered":37}
```

## Requirements

- Python 3.12 or later
- An Apple Account with two-factor authentication enabled
- An app-specific password (generated at account.apple.com)

## License

MIT
