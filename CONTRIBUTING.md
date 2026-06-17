# Contributing

Thanks for helping out.

## Setup

```bash
git clone git@github.com:thetaroot/apple-mcp.git
cd apple-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest -v
```

## Code Style

```bash
ruff check src/ tests/
ruff format src/ tests/
mypy src/apple_mcp
```

All three must pass before a PR can be merged.

## Project Layout

```
src/apple_mcp/
├── server.py           Main server class, tool registration
├── config.py           Environment variable parsing, validation
├── errors.py           Exception hierarchy
├── transport/
│   ├── http.py         Streamable HTTP transport (POST /mcp)
│   └── stdio.py        Stdio transport (for Claude Desktop etc.)
├── services/
│   ├── auth.py         iCloud + IMAP authentication
│   ├── scope.py        Access control engine
│   ├── calendar.py     Calendar tools (12)
│   ├── reminders.py    Reminder tools (12)
│   └── mail.py         Mail tools (10)
└── models/
    ├── calendar.py     Calendar event models
    ├── reminders.py    Reminder models
    └── mail.py         Mail message models
```

## Adding a New Service

1. Create a service class in `src/apple_mcp/services/` with `tools()` and `handle()` methods
2. Register it in `AppleMCPServer._init_services()` in `server.py`
3. Add relevant scope checks to `ScopeEngine` in `scope.py`
4. Add environment variables to `ServerConfig` in `config.py`
5. Add tests in `tests/`
6. Update the README tool list

## Adding a New Tool

1. Add a `Tool(...)` entry to your service's `tools()` method
2. Add a handler method to the service
3. Wire it up in the `handlers` dict in `handle()`
4. Add a test
