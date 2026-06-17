# Apple MCP

Model Context Protocol server for Apple iCloud. Gives your AI agents access to your Calendar, Reminders, and Mail — filtered through a scope engine so they only see what you want them to see.

Supports stdio and HTTP transport. Works anywhere, not just macOS.

## What It Does

Connects your AI tools (Claude Desktop, Continue.dev, Cursor, or any MCP client) to your iCloud account. Three services, each independently toggleable:

- **Calendar** — list, create, update, delete events and calendars. Search by keyword, check availability.
- **Reminders** — full CRUD. Alarms, hashtags, URL attachments. Filter by list, date, priority.
- **Mail** — multi-account IMAP. Search, read, send, move, flag, delete emails.

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

Or if you want stdio transport for local MCP clients:

```bash
apple-mcp --transport stdio
```

### Docker Compose

```yaml
services:
  apple-mcp:
    image: ghcr.io/thetaroot/apple-mcp:latest
    ports:
      - "8080:8080"
    environment:
      - APPLE_ID=you@icloud.com
      - APPLE_APP_SPECIFIC_PASSWORD=${APPLE_APP_SPECIFIC_PASSWORD}
      - APPLE_CALENDAR_NAMES=Work,Projects
      - APPLE_REMINDER_LISTS=Work Tasks
      - APPLE_MAIL_FOLDERS=INBOX,Sent,Work
```

## Configuration

All configuration is done through environment variables.

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

Per-service passwords override the shared one.

### Service Toggles

| Variable | Default | Description |
|----------|---------|-------------|
| `APPLE_ENABLE_CALENDAR` | `true` | Enable calendar tools |
| `APPLE_ENABLE_REMINDERS` | `true` | Enable reminder tools |
| `APPLE_ENABLE_MAIL` | `true` | Enable mail tools |

### Calendar Scope

| Variable | Description |
|----------|-------------|
| `APPLE_CALENDAR_NAMES` | Comma-separated calendar names to allow. Empty = all allowed. |
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

The iCloud mail account is connected automatically from `APPLE_ID`. To add other accounts (like your work email configured in Apple Mail), provide them as a JSON array:

```bash
APPLE_MAIL_ACCOUNTS='[
  {
    "type": "external",
    "email": "luis@company.com",
    "imap_host": "mail.company.com",
    "imap_port": 993,
    "smtp_host": "mail.company.com",
    "smtp_port": 587,
    "password_env": "MAIL_PWD_WORK",
    "folders_allow": ["INBOX", "Sent"]
  }
]'
```

Each external account needs its own password environment variable. Set it alongside the other vars:

```bash
MAIL_PWD_WORK=your-external-mail-password
```

When `APPLE_MAIL_ACCOUNTS` is set, the default iCloud account is **not** auto-added — you need to include it in the array if you want both:

```json
[
  {"type": "icloud", "email": "you@icloud.com", "folders_allow": ["INBOX", "Sent"]},
  {"type": "external", "email": "luis@company.com", "imap_host": "...", "password_env": "MAIL_PWD_WORK"}
]
```

## Using with Claude Desktop

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
        "APPLE_REMINDER_LISTS": "Work Tasks"
      }
    }
  }
}
```

## How the Scope Engine Works

The scope engine runs between your Apple data and the AI agent. It filters everything before the agent sees it.

An example: you have these calendars in iCloud:

- Work
- Personal
- Family
- SwiftGate

You set `APPLE_CALENDAR_NAMES=Work,SwiftGate`.

The agent only sees Work and SwiftGate. It cannot list, search, create, or modify events on Personal or Family — those calendars do not exist from the agent's perspective.

Same logic applies to reminder lists and mail folders. Combined with `read_only` mode, you can give your agents exactly the access level you're comfortable with.

## Tools Reference

### Calendar — 12 tools

| Tool | What it does |
|------|-------------|
| `apple_calendar_list_calendars` | List visible calendars |
| `apple_calendar_get_events` | Get events in a date range or period |
| `apple_calendar_get_event` | Get a single event by ID |
| `apple_calendar_create_event` | Create an event with alarms and invitees |
| `apple_calendar_update_event` | Update event fields |
| `apple_calendar_delete_event` | Delete an event |
| `apple_calendar_search_events` | Search across calendars by keyword |
| `apple_calendar_add_calendar` | Create a new calendar |
| `apple_calendar_remove_calendar` | Delete a calendar |
| `apple_calendar_get_availability` | Check free/busy time slots |
| `apple_calendar_get_changes` | Sync token for change tracking |
| `apple_calendar_share_calendar` | Share a calendar |

### Reminders — 12 tools

| Tool | What it does |
|------|-------------|
| `apple_reminders_list_lists` | List visible reminder lists |
| `apple_reminders_get_reminders` | Get reminders with filters |
| `apple_reminders_get_reminder` | Get a single reminder by ID |
| `apple_reminders_create` | Create a new reminder |
| `apple_reminders_update` | Update reminder fields |
| `apple_reminders_complete` | Mark as done |
| `apple_reminders_uncomplete` | Re-open a completed reminder |
| `apple_reminders_delete` | Delete permanently |
| `apple_reminders_add_alarm` | Add a time alarm |
| `apple_reminders_add_hashtag` | Add a hashtag label |
| `apple_reminders_add_url` | Attach a URL |
| `apple_reminders_get_changes` | Sync token for change tracking |

### Mail — 10 tools

| Tool | What it does |
|------|-------------|
| `apple_mail_list_accounts` | List connected mail accounts |
| `apple_mail_list_folders` | List visible folders |
| `apple_mail_search` | Search emails by criteria |
| `apple_mail_get` | Fetch a complete email |
| `apple_mail_send` | Send an email |
| `apple_mail_reply` | Reply to an email |
| `apple_mail_move` | Move to another folder |
| `apple_mail_flag` | Flag or unflag |
| `apple_mail_mark_read` | Mark read or unread |
| `apple_mail_delete` | Delete an email |

## Requirements

- Python 3.12 or later
- An Apple Account with two-factor authentication enabled
- An app-specific password (generated at account.apple.com)

## License

MIT
