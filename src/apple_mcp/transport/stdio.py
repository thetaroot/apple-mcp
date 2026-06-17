import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server

logger = logging.getLogger("apple_mcp.transport.stdio")


async def run_stdio_server(mcp: Server) -> None:
    logger.info("Starting Apple MCP server (stdio transport)")
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())
