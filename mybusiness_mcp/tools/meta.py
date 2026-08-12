"""Low-context helper tools for discovering the large Business Profile API."""

from __future__ import annotations

from typing import Any

from ..discovery import DiscoveryCatalog, descriptor_summary
from ..services import SERVICES


async def list_services(catalog: DiscoveryCatalog) -> list[dict[str, Any]]:
    await catalog.ensure_loaded()
    return [
        {
            "key": service.key,
            "title": service.title,
            "discovery_url": service.discovery_url,
            "docs_url": service.docs_url,
            "deprecated": service.deprecated,
            "deprecation_note": service.deprecation_note,
            "loaded": service.key in catalog.documents,
            "load_error": catalog.errors.get(service.key),
            "method_count": sum(
                1
                for item in catalog.methods.values()
                if item.service.key == service.key
            ),
        }
        for service in SERVICES
    ]


async def search_methods(
    catalog: DiscoveryCatalog, query: str, limit: int = 25
) -> list[dict[str, Any]]:
    await catalog.ensure_loaded()
    return [descriptor_summary(item) for item in catalog.find_methods(query, limit)]


async def describe_method(
    catalog: DiscoveryCatalog, tool_name: str
) -> dict[str, Any]:
    await catalog.ensure_loaded()
    descriptor = catalog.get_method(tool_name)
    method = descriptor.method
    request_ref = (method.get("request") or {}).get("$ref")
    response_ref = (method.get("response") or {}).get("$ref")
    result = descriptor_summary(descriptor)
    result.update(
        {
            "parameters": method.get("parameters", {}),
            "request": method.get("request"),
            "response": method.get("response"),
            "request_schema": descriptor.document.get("schemas", {}).get(request_ref)
            if request_ref
            else None,
            "response_schema": descriptor.document.get("schemas", {}).get(response_ref)
            if response_ref
            else None,
            "supports_media_upload": bool(
                method.get("supportsMediaUpload") or method.get("mediaUpload")
            ),
            "media_upload": method.get("mediaUpload"),
            "scopes": method.get("scopes", []),
            "deprecated_service_note": descriptor.service.deprecation_note,
        }
    )
    return result


async def describe_schema(
    catalog: DiscoveryCatalog, service_key: str, schema_name: str
) -> dict[str, Any]:
    await catalog.ensure_loaded()
    return catalog.describe_schema(service_key, schema_name)
