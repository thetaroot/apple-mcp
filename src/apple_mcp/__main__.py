import argparse
import asyncio
import logging
import sys

from apple_mcp.__version__ import VERSION
from apple_mcp.config import load_config
from apple_mcp.server import AppleMCPServer

logger = logging.getLogger("apple_mcp")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apple MCP Server")
    parser.add_argument("--version", action="version", version=f"apple-mcp {VERSION}")
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default="http",
        help="Transport protocol (default: http)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument("--log-level", default="INFO", help="Log level (default: INFO)")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s [%(name)s] %(message)s",
    )

    config = load_config()

    if not config.apple_id:
        logger.error("APPLE_ID is required. Set it via environment variable.")
        sys.exit(1)

    server = AppleMCPServer(config)

    if args.transport == "http":
        asyncio.run(server.run_http(host=args.host, port=args.port))
    else:
        asyncio.run(server.run_stdio())


if __name__ == "__main__":
    main()
