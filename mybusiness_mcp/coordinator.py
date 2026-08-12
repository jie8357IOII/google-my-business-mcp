"""Register Google Business Profile REST methods as MCP tools."""

from __future__ import annotations

import json
import sys
from typing import Any

from mcp import types as mcp_types
from mcp.server.lowlevel import Server

from .client import BusinessProfileClient, GoogleApiError
from .discovery import DiscoveryCatalog, method_input_schema


app = Server(name="Google Business Profile MCP Server")
catalog = DiscoveryCatalog()
client = BusinessProfileClient()


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    """Expose each discovered Google REST method as one MCP tool."""
    await catalog.ensure_loaded()
    tools: list[mcp_types.Tool] = []

    for descriptor in sorted(catalog.methods.values(), key=lambda item: item.tool_name):
        description = (
            f"{descriptor.http_method} {descriptor.path}. "
            f"{descriptor.method.get('description', '')}"
        ).strip()
        if descriptor.service.deprecated:
            description = f"[DEPRECATED] {description}"

        schema = method_input_schema(descriptor)
        body_schema = schema.get("properties", {}).get("body")
        if isinstance(body_schema, dict):
            body_schema["description"] = "JSON request body for this Google API method."

        tools.append(
            mcp_types.Tool(
                name=descriptor.tool_name,
                description=description[:1200],
                inputSchema=schema,
            )
        )

    return tools


@app.call_tool()
async def call_mcp_tool(
    name: str, arguments: dict[str, Any]
) -> list[mcp_types.Content]:
    """Call the Google REST method represented by an MCP tool."""
    try:
        await catalog.ensure_loaded()
        descriptor = catalog.get_method(name)
        result = await client.execute(descriptor, arguments)
    except GoogleApiError as exc:
        result = {
            "error": str(exc),
            "status_code": exc.status_code,
            "google_error": exc.payload,
        }
    except Exception as exc:
        print(f"MCP Server: Error executing {name!r}: {exc}", file=sys.stderr)
        result = {"error": f"Failed to execute tool {name!r}: {exc}"}

    return [
        mcp_types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False, default=str),
        )
    ]
