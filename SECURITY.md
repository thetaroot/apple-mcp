# Security

## Authentication Model

This server uses Apple **app-specific passwords**, not your primary Apple Account password.

An app-specific password:

- Is a separate, randomly generated credential you create at [account.apple.com](https://account.apple.com)
- Can be individually named (e.g. "MCP Calendar") and individually revoked
- Does **not** grant access to your Apple Account settings, payment methods, or Apple ID management
- Works only for iCloud services (Calendar, Reminders, Mail, Contacts, Drive, Notes)
- Is automatically revoked if you change your main Apple Account password
- You can create up to 25 of them

We recommend creating **separate app-specific passwords per service** for defense in depth. Use the per-service environment variables (`APPLE_CALENDAR_PASSWORD`, `APPLE_REMINDERS_PASSWORD`, `APPLE_MAIL_PASSWORD`) instead of the shared `APPLE_APP_SPECIFIC_PASSWORD`.

## What We Access and What We Don't

| Service | Protocols Used | What We Access |
|---------|---------------|----------------|
| Calendar | iCloud web API (via pyicloud) | Calendars you allow via scope config |
| Reminders | iCloud web API (via pyicloud) | Reminder lists you allow via scope config |
| Mail | IMAP + SMTP (standard protocols) | Folders and accounts you configure |

This code never touches your photos, files, contacts, notes, or device locations unless you explicitly enable those services (they are off by default).

You can verify this — the code is open source. Check `src/apple_mcp/services/`.

## Where Credentials Live

- Credentials are loaded from **environment variables only**
- They are **never** written to disk, log files, or any persistent storage by this server
- Passwords are redacted in all `repr()` output and log messages
- If you use this server with SwiftGate or another credential manager, that system is responsible for encrypting credentials at rest — this server only reads them from the environment

## Transport Security

- iCloud API calls use TLS 1.3 (enforced by the `requests` library that pyicloud uses)
- IMAP connections use SSL on port 993
- SMTP connections use STARTTLS on port 587
- The HTTP transport endpoint (`/mcp`) should only be exposed on internal networks — do not expose it directly to the internet without a reverse proxy and authentication

## Reporting Issues

If you find a security issue, please open a GitHub issue. For sensitive issues, email the address in the repository owner's profile.
