# Changelog

## 1.1.0 — Enterprise Launch

All tools fully implemented. Zero stubs. Production ready.

### New Features
- `apple_calendar_get_calendar_info` replaces `apple_calendar_share_calendar` (pyicloud has no share API)
- `apple_calendar_get_changes` properly implemented via iCloud ctag change tracking
- `apple_reminders_get_changes` properly implemented via sync_cursor + iter_changes
- `apple_mail_reply` implemented via SMTP with In-Reply-To headers
- Calendar events now support `recurrence` parameter (RRULE string)
- Reminders: three new tools — `create_recurrence`, `get_recurrence_rules`, `delete_recurrence`
- `limit` parameter on all list/search tools for pagination
- `apple_mail_get` now returns full HTML body
- Health check endpoint at `GET /health`
- Graceful shutdown with IMAP logout and pyicloud session cleanup
- `apple-mcp --version` CLI flag
- Retry logic on all network calls (3 attempts with backoff)
- Email address validation in mail account config

### Fixes
- `_add_alarm` now sets due_date (removed broken location-trigger call)
- `_send` uses account-specific SMTP config instead of hardcoded iCloud host
- Invalid mode values (`readonly`, `READ_ONLY`) now raise `ValueError`
- IMAP connections cleaned up on auth failure
- Batch IMAP FETCH replaces N+1 per-UID fetches
- `str(None)` no longer produces literal `"None"` string in output
- Redundant read-only checks removed from calendar operations
- Dead code removed (`auth.py.get_mail_client`)
- Dockerfile handles zero, one, or multiple wheel files
- Version strings read from `__version__` instead of hardcoded

## 1.0.0 — First Release

Initial release of the Apple MCP server.

- Calendar support: 12 tools via pyicloud (iCloud web API)
- Reminders support: 12 tools via pyicloud
- Mail support: 10 tools via IMAP/SMTP, multi-account
- Scope engine for fine-grained access control per service
- Streamable HTTP transport (MCP spec 2025-03-26)
- Stdio transport for local MCP clients
- Docker image with health checks
- Full test suite
