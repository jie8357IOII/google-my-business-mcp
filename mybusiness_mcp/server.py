"""Entry point for the Google Business Profile MCP server."""

from __future__ import annotations

import asyncio
import sys
import traceback

import mcp.server
import mcp.server.stdio
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions

from . import __version__, coordinator


async def run_server_async() -> None:
    print("Starting MCP Stdio Server:", coordinator.app.name, file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await coordinator.app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=coordinator.app.name,
                server_version=__version__,
                capabilities=coordinator.app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_server() -> None:
    asyncio.run(run_server_async())


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nMCP Server (stdio) stopped by user.", file=sys.stderr)
    except Exception:  # noqa: BLE001 - CLI boundary logs unexpected startup failures
        print("MCP Server (stdio) encountered an error:", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("MCP Server (stdio) process exiting.", file=sys.stderr)
