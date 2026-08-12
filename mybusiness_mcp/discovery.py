"""Discovery document loading and MCP tool generation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .legacy_catalog import BUNDLED_CATALOGS
from .services import SERVICE_BY_KEY, SERVICES, ServiceDefinition

SENSITIVE_GLOBAL_PARAMETERS = {
    "access_token",
    "oauth_token",
    "key",
    "upload_protocol",
    "uploadType",
    "alt",
    "callback",
}

_TEMPLATE_RE = re.compile(r"\{(\+)?([^}=]+)(?:=([^}]+))?\}")
_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9_]+")


@dataclass(slots=True)
class MethodDescriptor:
    tool_name: str
    service: ServiceDefinition
    resource_path: tuple[str, ...]
    method_name: str
    method: dict[str, Any]
    document: dict[str, Any]

    @property
    def method_id(self) -> str:
        return str(
            self.method.get("id") or ".".join((*self.resource_path, self.method_name))
        )

    @property
    def display_name(self) -> str:
        return ".".join((*self.resource_path, self.method_name))

    @property
    def http_method(self) -> str:
        return str(self.method.get("httpMethod", "GET")).upper()

    @property
    def path(self) -> str:
        return str(self.method.get("path", ""))

    @property
    def base_url(self) -> str:
        root = self.document.get("rootUrl")
        service_path = self.document.get("servicePath", "")
        if root:
            return str(root).rstrip("/") + "/" + str(service_path).lstrip("/")
        return str(self.document.get("baseUrl", "")).rstrip("/") + "/"


class DiscoveryError(RuntimeError):
    pass


class DiscoveryCatalog:
    """Loads Google Discovery docs and exposes every REST method as a descriptor."""

    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.cache_dir = cache_dir or Path(
            os.environ.get(
                "GMB_MCP_CACHE_DIR",
                Path.home() / ".cache" / "google-my-business-mcp" / "discovery",
            )
        )
        self.cache_ttl_seconds = cache_ttl_seconds or int(
            os.environ.get("GMB_MCP_DISCOVERY_CACHE_TTL", "86400")
        )
        self.timeout_seconds = timeout_seconds
        self._documents: dict[str, dict[str, Any]] = {}
        self._errors: dict[str, str] = {}
        self._methods: dict[str, MethodDescriptor] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    @property
    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    @property
    def methods(self) -> dict[str, MethodDescriptor]:
        return dict(self._methods)

    @property
    def documents(self) -> dict[str, dict[str, Any]]:
        return dict(self._documents)

    async def ensure_loaded(self, *, force: bool = False) -> None:
        if self._loaded and not force:
            return
        async with self._lock:
            if self._loaded and not force:
                return
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            services = _enabled_services()
            results = await asyncio.gather(
                *(self._load_service(service, force=force) for service in services),
                return_exceptions=True,
            )
            self._documents.clear()
            self._errors.clear()
            for service, result in zip(services, results):
                if isinstance(result, BaseException):
                    bundled = BUNDLED_CATALOGS.get(service.key)
                    if bundled is None:
                        self._errors[service.key] = str(result)
                    else:
                        self._documents[service.key] = bundled
                        self._errors[service.key] = (
                            f"live discovery failed; using bundled catalog: {result}"
                        )
                else:
                    self._documents[service.key] = result
            self._rebuild_methods()
            self._loaded = True

    async def refresh(self) -> None:
        await self.ensure_loaded(force=True)

    def get_method(self, tool_name: str) -> MethodDescriptor:
        try:
            return self._methods[tool_name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown Google Business Profile MCP tool: {tool_name}"
            ) from exc

    def find_methods(self, query: str, limit: int = 25) -> list[MethodDescriptor]:
        q = query.strip().lower()
        ranked: list[tuple[int, MethodDescriptor]] = []
        for descriptor in self._methods.values():
            haystacks = [
                descriptor.tool_name.lower(),
                descriptor.display_name.lower(),
                descriptor.method_id.lower(),
                str(descriptor.method.get("description", "")).lower(),
                descriptor.service.title.lower(),
            ]
            if not q:
                score = 1
            elif q in haystacks[0]:
                score = 5
            elif q in haystacks[1] or q in haystacks[2]:
                score = 4
            elif any(q in item for item in haystacks[3:]):
                score = 2
            else:
                continue
            ranked.append((score, descriptor))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].tool_name))
        return [item for _, item in ranked[: max(1, min(limit, 100))]]

    def describe_schema(self, service_key: str, schema_name: str) -> dict[str, Any]:
        document = self._documents.get(service_key)
        if not document:
            raise KeyError(f"Discovery document not loaded: {service_key}")
        schemas = document.get("schemas", {})
        if schema_name not in schemas:
            raise KeyError(f"Schema {schema_name!r} not found in {service_key}")
        return schemas[schema_name]

    async def _load_service(
        self, service: ServiceDefinition, *, force: bool
    ) -> dict[str, Any]:
        cache_path = self.cache_dir / f"{service.key}.json"
        if not force and cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age <= self.cache_ttl_seconds:
                try:
                    return json.loads(cache_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass

        headers = {"User-Agent": "google-my-business-mcp/0.2.0"}
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, headers=headers
        ) as client:
            response = await client.get(service.discovery_url)
            response.raise_for_status()
            document = response.json()
        if not isinstance(document, dict) or document.get("protocol") != "rest":
            raise DiscoveryError(f"Invalid REST discovery document for {service.key}")
        tmp_path = cache_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(cache_path)
        return document

    def _rebuild_methods(self) -> None:
        self._methods.clear()
        for service_key, document in self._documents.items():
            service = SERVICE_BY_KEY[service_key]
            for resource_path, method_name, method in walk_methods(document):
                tool_name = build_tool_name(service, resource_path, method_name, method)
                original = tool_name
                if tool_name in self._methods:
                    suffix = hashlib.sha1(
                        str(method.get("id", original)).encode("utf-8")
                    ).hexdigest()[:6]
                    tool_name = f"{original[:56]}_{suffix}"
                self._methods[tool_name] = MethodDescriptor(
                    tool_name=tool_name,
                    service=service,
                    resource_path=resource_path,
                    method_name=method_name,
                    method=method,
                    document=document,
                )


def _enabled_services() -> tuple[ServiceDefinition, ...]:
    """Return services selected by environment variables.

    Deprecated services stay in the default catalog because this project aims
    to represent the complete Business Profile REST surface. Set
    GMB_MCP_INCLUDE_DEPRECATED=0 to omit them.
    """
    include_deprecated = os.environ.get("GMB_MCP_INCLUDE_DEPRECATED", "1") not in {
        "0",
        "false",
        "False",
    }
    requested = {
        item.strip()
        for item in os.environ.get("GMB_MCP_SERVICES", "").split(",")
        if item.strip()
    }
    result = []
    for service in SERVICES:
        if requested and service.key not in requested:
            continue
        if service.deprecated and not include_deprecated:
            continue
        result.append(service)
    return tuple(result)


def walk_methods(
    document: dict[str, Any],
) -> Iterable[tuple[tuple[str, ...], str, dict[str, Any]]]:
    """Yield all REST methods recursively from a Google Discovery document."""

    def visit(resources: dict[str, Any], prefix: tuple[str, ...]):
        for resource_name, resource in resources.items():
            path = (*prefix, resource_name)
            for method_name, method in resource.get("methods", {}).items():
                yield path, method_name, method
            yield from visit(resource.get("resources", {}), path)

    for method_name, method in document.get("methods", {}).items():
        yield (), method_name, method
    yield from visit(document.get("resources", {}), ())


def build_tool_name(
    service: ServiceDefinition,
    resource_path: tuple[str, ...],
    method_name: str,
    method: dict[str, Any],
) -> str:
    """Create a stable MCP-compatible tool name no longer than 64 chars."""
    parts = ["gmb", service.short_name, *resource_path, method_name]
    raw = "_".join(parts)
    normalized = _NON_ALNUM_RE.sub("_", raw).strip("_").lower()
    if len(normalized) <= 64:
        return normalized
    digest = hashlib.sha1(
        str(method.get("id", normalized)).encode("utf-8")
    ).hexdigest()[:8]
    return f"{normalized[:55].rstrip('_')}_{digest}"


def method_input_schema(descriptor: MethodDescriptor) -> dict[str, Any]:
    """Create a compact MCP input schema for a REST method.

    Request bodies are intentionally shallow. Agents can call
    gmb_describe_method/gmb_describe_schema for full Discovery schemas without
    inflating tools/list by repeating large object graphs on every method.
    """
    method = descriptor.method
    document = descriptor.document
    properties: dict[str, Any] = {}
    required: list[str] = []

    parameters: dict[str, Any] = {}
    parameters.update(document.get("parameters", {}))
    parameters.update(method.get("parameters", {}))

    for name, parameter in parameters.items():
        if name in SENSITIVE_GLOBAL_PARAMETERS:
            continue
        schema = discovery_parameter_to_json_schema(parameter)
        schema["x-google-location"] = parameter.get("location", "query")
        properties[name] = schema
        if parameter.get("required"):
            required.append(name)

    if "request" in method:
        request = method["request"]
        body_schema: dict[str, Any] = {
            "type": "object",
            "description": "JSON request body. Use gmb_describe_method for the complete Google Discovery schema before complex writes.",
            "additionalProperties": True,
        }
        ref = request.get("$ref")
        if ref:
            body_schema["x-google-schema-ref"] = ref
            source = document.get("schemas", {}).get(ref, {})
            top_props = source.get("properties", {})
            if top_props:
                body_schema["properties"] = {
                    key: shallow_schema(value) for key, value in top_props.items()
                }
        properties["body"] = body_schema

    if method.get("supportsMediaUpload") or method.get("mediaUpload"):
        properties["media_path"] = {
            "type": "string",
            "description": "Local file path for a media upload. Only use for methods whose Discovery document declares media upload support.",
        }
        properties["media_content_type"] = {
            "type": "string",
            "description": "Optional MIME type for media_path; guessed from the filename when omitted.",
        }

    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = sorted(set(required))
    return result


def discovery_parameter_to_json_schema(parameter: dict[str, Any]) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    ptype = parameter.get("type", "string")
    if parameter.get("repeated"):
        schema["type"] = "array"
        schema["items"] = {"type": ptype}
    else:
        schema["type"] = ptype
    if parameter.get("description"):
        schema["description"] = str(parameter["description"])[:800]
    for key in ("enum", "format", "pattern"):
        if key in parameter:
            schema[key] = parameter[key]
    for key in ("minimum", "maximum"):
        if key in parameter:
            value = parameter[key]
            try:
                schema[key] = float(value) if "." in str(value) else int(value)
            except (TypeError, ValueError):
                pass
    if "default" in parameter:
        default = parameter["default"]
        try:
            if ptype == "boolean" and isinstance(default, str):
                default = default.lower() == "true"
            elif ptype == "integer" and isinstance(default, str):
                default = int(default)
            elif ptype == "number" and isinstance(default, str):
                default = float(default)
            schema["default"] = default
        except (TypeError, ValueError):
            pass
    return schema


def shallow_schema(source: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in source:
        return {
            "type": "object",
            "description": str(
                source.get("description", f"Google schema: {source['$ref']}")
            )[:800],
            "additionalProperties": True,
            "x-google-schema-ref": source["$ref"],
        }
    if source.get("type") == "array":
        item = source.get("items", {})
        if "$ref" in item:
            items = {
                "type": "object",
                "additionalProperties": True,
                "x-google-schema-ref": item["$ref"],
            }
        else:
            items = {
                key: item[key] for key in ("type", "format", "enum") if key in item
            }
        result = {"type": "array", "items": items or {}}
    else:
        result = {
            key: source[key] for key in ("type", "format", "enum") if key in source
        }
        if not result:
            result["type"] = "object"
            result["additionalProperties"] = True
    if source.get("description"):
        result["description"] = str(source["description"])[:800]
    return result


def descriptor_summary(descriptor: MethodDescriptor) -> dict[str, Any]:
    method = descriptor.method
    return {
        "tool_name": descriptor.tool_name,
        "service": descriptor.service.key,
        "service_title": descriptor.service.title,
        "deprecated_service": descriptor.service.deprecated,
        "method_id": descriptor.method_id,
        "resource": descriptor.display_name,
        "http_method": descriptor.http_method,
        "path": descriptor.path,
        "description": method.get("description", ""),
    }
