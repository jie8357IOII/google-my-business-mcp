"""Singleton MCP server and Google Business Profile tool coordinator.

This follows the structure of Google's official Analytics MCP server: a single
low-level MCP Server coordinates tool listing and tool dispatch, while API and
authentication logic live in separate modules.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from mcp import types as mcp_types
from mcp.server.lowlevel import Server

from .client import BusinessProfileClient, GoogleApiError
from .discovery import DiscoveryCatalog, method_input_schema
from .tools.meta import describe_method, describe_schema, list_services, search_methods


app = Server(name="Google Business Profile MCP Server")
catalog = DiscoveryCatalog()
client = BusinessProfileClient()


META_TOOLS = [
    mcp_types.Tool(
        name="gmb_list_services",
        description=(
            "List all Google Business Profile API services, deprecation states, "
            "load status, and discovered method counts."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    mcp_types.Tool(
        name="gmb_search_methods",
        description=(
            "Search the complete Google Business Profile REST method catalog "
            "before choosing a specific API tool."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search phrase such as reviews, local posts, hours, "
                        "attributes, performance, verification, or media."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 25,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    mcp_types.Tool(
        name="gmb_describe_method",
        description=(
            "Return complete Google Discovery metadata, parameters, request "
            "schema, response schema, and media-upload metadata for one "
            "generated MCP API tool."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": (
                        "Generated MCP tool name returned by gmb_search_methods "
                        "or tools/list."
                    ),
                }
            },
            "required": ["tool_name"],
            "additionalProperties": False,
        },
    ),
    mcp_types.Tool(
        name="gmb_describe_schema",
        description=(
            "Return one full named schema from a Google Business Profile "
            "Discovery document."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service_key": {
                    "type": "string",
                    "description": "Service key from gmb_list_services.",
                },
                "schema_name": {
                    "type": "string",
                    "description": (
                        "Google Discovery schema name such as Location or LocalPost."
                    ),
                },
            },
            "required": ["service_key", "schema_name"],
            "additionalProperties": False,
        },
    ),
    mcp_types.Tool(
        name="gmb_refresh_discovery",
        description=(
            "Refresh all Google Business Profile Discovery documents and "
            "rebuild the generated MCP method catalog."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    await catalog.ensure_loaded()
    generated: list[mcp_types.Tool] = []
    for descriptor in sorted(catalog.methods.values(), key=lambda item: item.tool_name):
        description = descriptor.method.get("description", "")
        prefix = f"{descriptor.http_method} {descriptor.path}. "
        if descriptor.service.deprecated:
            prefix = "[DEPRECATED SERVICE] " + prefix
        generated.append(
            mcp_types.Tool(
                name=descriptor.tool_name,
                description=(prefix + str(description)).strip()[:1200],
                inputSchema=method_input_schema(descriptor),
            )
        )
    return [*META_TOOLS, *generated]


@app.call_tool()
async def call_mcp_tool(
    name: str, arguments: dict[str, Any]
) -> list[mcp_types.Content]:
    try:
        await catalog.ensure_loaded()
        if name == "gmb_list_services":
            result = await list_services(catalog)
        elif name == "gmb_search_methods":
            result = await search_methods(
                catalog,
                query=str(arguments.get("query", "")),
                limit=int(arguments.get("limit", 25)),
            )
        elif name == "gmb_describe_method":
            result = await describe_method(catalog, str(arguments["tool_name"]))
        elif name == "gmb_describe_schema":
            result = await describe_schema(
                catalog,
                str(arguments["service_key"]),
                str(arguments["schema_name"]),
            )
        elif name == "gmb_refresh_discovery":
            await catalog.refresh()
            result = {
                "loaded_services": sorted(catalog.documents),
                "errors": catalog.errors,
                "method_count": len(catalog.methods),
            }
        elif name in catalog.methods:
            descriptor = catalog.get_method(name)
            result = await client.execute(descriptor, arguments)
        else:
            result = {"error": f"Tool {name!r} is not implemented by this server."}
        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False, default=str),
            )
        ]
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
