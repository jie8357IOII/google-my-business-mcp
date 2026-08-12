"""Register Google Business Profile REST methods as MCP tools."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from mcp import types as mcp_types
from mcp.server.lowlevel import Server

from .client import BusinessProfileClient, GoogleApiError
from .discovery import DiscoveryCatalog, method_input_schema

app = Server(name="Google Business Profile MCP Server")
catalog = DiscoveryCatalog()
client = BusinessProfileClient()

_READ_METHODS = {"GET", "HEAD", "OPTIONS"}
_SENSITIVE_KEY = re.compile(
    r"(?:access|refresh|oauth)[_-]?token|authorization|client[_-]?secret|"
    r"password|credential|api[_-]?key",
    re.IGNORECASE,
)
_SIGNED_URL_KEYS = {
    "x-amz-algorithm",
    "x-amz-credential",
    "x-amz-date",
    "x-amz-expires",
    "x-amz-signature",
    "x-amz-signedheaders",
    "x-goog-algorithm",
    "x-goog-credential",
    "x-goog-date",
    "x-goog-expires",
    "x-goog-signature",
    "x-goog-signedheaders",
    "sig",
    "signature",
    "token",
}
_SIGNED_URL_PREFIXES = ("x-amz-", "x-goog-")
_DEFAULT_CONFIRMATION_TIMEOUT_SECONDS = 120.0
_MAX_CONFIRMATION_TIMEOUT_SECONDS = 600.0


def tool_annotations(http_method: str) -> mcp_types.ToolAnnotations:
    """Return conservative MCP safety hints for an HTTP method."""
    method = http_method.upper()
    read_only = method in _READ_METHODS
    return mcp_types.ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=method == "DELETE",
        idempotentHint=method in {"GET", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"},
        openWorldHint=True,
    )


def _sanitize(value: Any, key: str = "") -> Any:
    if _SENSITIVE_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {
            item_key: _sanitize(item, str(item_key)) for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item, key) for item in value]
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        parts = urlsplit(value)
        query_keys = {
            pair.split("=", 1)[0].lower() for pair in parts.query.split("&") if pair
        }
        has_signed_key = bool(query_keys & _SIGNED_URL_KEYS) or any(
            key.startswith(_SIGNED_URL_PREFIXES) for key in query_keys
        )
        if has_signed_key:
            return urlunsplit(
                (parts.scheme, parts.netloc, parts.path, "<redacted>", "")
            )
    return value


def operation_preview(descriptor: Any, arguments: dict[str, Any]) -> str:
    preview = {
        "resource": descriptor.path,
        "method": descriptor.http_method,
        "update_mask": arguments.get("updateMask"),
        "target": {
            key: value
            for key, value in arguments.items()
            if key != "body" and (key == "name" or key == "parent" or ".name" in key)
        },
        "body": arguments.get("body"),
        "arguments": arguments,
    }
    rendered = json.dumps(_sanitize(preview), indent=2, ensure_ascii=False, default=str)
    if len(rendered) > 12000:
        raise ValueError("Write preview exceeds 12000 characters; narrow the operation")
    return rendered


def write_confirmation_required() -> bool:
    return os.environ.get("GMB_MCP_REQUIRE_WRITE_CONFIRMATION", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def write_confirmation_timeout_seconds() -> float:
    """Return a bounded timeout for MCP write elicitation."""
    raw = os.environ.get(
        "GMB_MCP_WRITE_CONFIRMATION_TIMEOUT_SECONDS",
        str(_DEFAULT_CONFIRMATION_TIMEOUT_SECONDS),
    )
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise ValueError(
            "GMB_MCP_WRITE_CONFIRMATION_TIMEOUT_SECONDS must be a number"
        ) from exc
    if not 0 < timeout <= _MAX_CONFIRMATION_TIMEOUT_SECONDS:
        raise ValueError(
            "GMB_MCP_WRITE_CONFIRMATION_TIMEOUT_SECONDS must be greater than 0 "
            f"and at most {_MAX_CONFIRMATION_TIMEOUT_SECONDS:g}"
        )
    return timeout


def _acknowledged(result: Any) -> bool:
    content = getattr(result, "content", None)
    if hasattr(content, "model_dump"):
        content = content.model_dump()
    return (
        getattr(result, "action", None) == "accept"
        and isinstance(content, dict)
        and content.get("acknowledge") is True
    )


async def require_write_confirmation(
    descriptor: Any, arguments: dict[str, Any], session: Any
) -> bool:
    """Elicit an exact, fail-closed confirmation before a write request."""
    if descriptor.http_method in _READ_METHODS:
        return True
    if not write_confirmation_required():
        return True
    preview = operation_preview(descriptor, arguments)
    result = await asyncio.wait_for(
        session.elicit_form(
            message="Confirm this Google Business Profile write:\n\n" + preview,
            requestedSchema={
                "type": "object",
                "properties": {
                    "acknowledge": {
                        "type": "boolean",
                        "title": "I approve exactly this operation",
                    }
                },
                "required": ["acknowledge"],
            },
        ),
        timeout=write_confirmation_timeout_seconds(),
    )
    return _acknowledged(result)


async def execute_tool(
    name: str, arguments: dict[str, Any], *, session: Any | None
) -> dict[str, Any]:
    """Execute one tool, keeping the confirmation gate testable and fail-closed."""
    await catalog.ensure_loaded()
    descriptor = catalog.get_method(name)
    if descriptor.http_method not in _READ_METHODS and write_confirmation_required():
        if session is None:
            return {
                "error": "Write confirmation unavailable",
                "code": "WRITE_CONFIRMATION_UNAVAILABLE",
                "mutation_performed": False,
            }
        try:
            approved = await require_write_confirmation(descriptor, arguments, session)
        except Exception as exc:  # noqa: BLE001 - all elicitation failures fail closed
            return {
                "error": f"Write confirmation unavailable: {exc}",
                "code": "WRITE_CONFIRMATION_UNAVAILABLE",
                "mutation_performed": False,
            }
        if not approved:
            return {
                "error": "Write confirmation declined or cancelled",
                "code": "WRITE_CONFIRMATION_DECLINED",
                "mutation_performed": False,
            }
    return await client.execute(descriptor, arguments)


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
                annotations=tool_annotations(descriptor.http_method),
            )
        )

    return tools


@app.call_tool()
async def call_mcp_tool(
    name: str, arguments: dict[str, Any]
) -> list[mcp_types.Content]:
    """Call the Google REST method represented by an MCP tool."""
    try:
        try:
            session = app.request_context.session
        except LookupError:
            session = None
        result = await execute_tool(name, arguments, session=session)
    except GoogleApiError as exc:
        result = {
            "error": str(exc),
            "status_code": exc.status_code,
            "google_error": exc.payload,
        }
    except Exception as exc:  # noqa: BLE001 - MCP boundary returns a structured error
        print(f"MCP Server: Error executing {name!r}: {exc}", file=sys.stderr)
        result = {"error": f"Failed to execute tool {name!r}: {exc}"}

    return [
        mcp_types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False, default=str),
        )
    ]
