"""Generic authenticated executor for Google Discovery REST methods."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from . import USER_AGENT
from .auth import get_access_token
from .discovery import MethodDescriptor

_TEMPLATE_RE = re.compile(r"\{(\+)?([^}=]+)(?:=([^}]+))?\}")


class GoogleApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, payload: Any = None) -> None:
        super().__init__(f"Google API error {status_code}: {message}")
        self.status_code = status_code
        self.payload = payload


class BusinessProfileClient:
    def __init__(self, *, timeout_seconds: float = 60.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def execute(
        self, descriptor: MethodDescriptor, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        args = dict(arguments or {})
        original_args = dict(args)
        path = expand_google_path_template(descriptor.path, args)
        url = descriptor.base_url.rstrip("/") + "/" + path.lstrip("/")
        params = build_query_parameters(descriptor, args)
        body = args.pop("body", None)
        media_path = args.pop("media_path", None)
        media_content_type = args.pop("media_content_type", None)

        if media_path:
            return await self._execute_media_upload(
                descriptor,
                url=url,
                params=params,
                body=body,
                media_path=Path(media_path),
                media_content_type=media_content_type,
                original_args=original_args,
            )
        return await self._request_json(
            descriptor.http_method,
            url,
            params=params,
            json_body=body,
        )

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: list[tuple[str, str]],
        json_body: Any,
    ) -> dict[str, Any]:
        token = await get_access_token()
        response = await self._send(
            method,
            url,
            params=params,
            json_body=json_body,
            token=token,
        )
        if response.status_code == 401:
            token = await get_access_token(force_refresh=True)
            response = await self._send(
                method,
                url,
                params=params,
                json_body=json_body,
                token=token,
            )
        return parse_response(response)

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: list[tuple[str, str]],
        json_body: Any,
        token: str,
    ) -> httpx.Response:
        headers = _google_headers(token)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as http:
            return await http.request(
                method,
                url,
                params=params,
                json=json_body if json_body is not None else None,
                headers=headers,
            )

    async def _execute_media_upload(
        self,
        descriptor: MethodDescriptor,
        *,
        url: str,
        params: list[tuple[str, str]],
        body: Any,
        media_path: Path,
        media_content_type: str | None,
        original_args: dict[str, Any],
    ) -> dict[str, Any]:
        if not media_path.is_file():
            raise FileNotFoundError(media_path)
        media_info = descriptor.method.get("mediaUpload") or {}
        protocols = media_info.get("protocols", {})
        multipart = protocols.get("multipart")
        simple = protocols.get("simple")
        protocol = multipart or simple
        if not protocol:
            raise ValueError(f"{descriptor.tool_name} does not declare an upload protocol")

        upload_path = protocol.get("path")
        if upload_path:
            upload_url = descriptor.base_url.rstrip("/") + "/" + expand_google_path_template(
                str(upload_path), dict(original_args)
            ).lstrip("/")
        else:
            upload_url = url

        mime = media_content_type or mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
        token = await get_access_token()
        headers = _google_headers(token)
        content = media_path.read_bytes()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as http:
            if multipart:
                boundary = "gmb_mcp_" + secrets.token_hex(12)
                metadata = json.dumps(body or {}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                payload = build_multipart_related(boundary, metadata, content, mime)
                headers["Content-Type"] = f"multipart/related; boundary={boundary}"
                response = await http.request(
                    descriptor.http_method,
                    upload_url,
                    params=[*params, ("uploadType", "multipart")],
                    content=payload,
                    headers=headers,
                )
            else:
                headers["Content-Type"] = mime
                response = await http.request(
                    descriptor.http_method,
                    upload_url,
                    params=[*params, ("uploadType", "media")],
                    content=content,
                    headers=headers,
                )
        return parse_response(response)


def expand_google_path_template(path: str, arguments: dict[str, Any]) -> str:
    """Expand Google Discovery URI templates including {+name} and {name=**}."""

    def replace(match: re.Match[str]) -> str:
        reserved = bool(match.group(1))
        variable = match.group(2)
        pattern = match.group(3) or ""
        if variable not in arguments:
            raise ValueError(f"Missing required path parameter: {variable}")
        value = str(arguments.pop(variable))
        preserve_slashes = reserved or "/" in pattern or "**" in pattern
        safe = "/:@!$&'()*+,;=" if preserve_slashes else ""
        return quote(value, safe=safe)

    return _TEMPLATE_RE.sub(replace, path)


def build_query_parameters(
    descriptor: MethodDescriptor, arguments: dict[str, Any]
) -> list[tuple[str, str]]:
    parameters: dict[str, Any] = {}
    parameters.update(descriptor.document.get("parameters", {}))
    parameters.update(descriptor.method.get("parameters", {}))
    result: list[tuple[str, str]] = []
    for name, spec in parameters.items():
        if spec.get("location") != "query" or name not in arguments:
            continue
        value = arguments.pop(name)
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, bool):
                encoded = "true" if item else "false"
            elif isinstance(item, (dict, list)):
                encoded = json.dumps(item, separators=(",", ":"))
            else:
                encoded = str(item)
            result.append((name, encoded))
    return result


def parse_response(response: httpx.Response) -> dict[str, Any]:
    if response.content:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"text": response.text}
    else:
        payload = {}
    if response.is_error:
        message = "request failed"
        if isinstance(payload, dict):
            error = payload.get("error", payload)
            if isinstance(error, dict):
                message = str(error.get("message") or error)
            else:
                message = str(error)
        raise GoogleApiError(response.status_code, message, payload)
    if isinstance(payload, dict):
        return payload
    return {"data": payload}


def _google_headers(token: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "X-GOOG-API-FORMAT-VERSION": "2",
        "User-Agent": USER_AGENT,
    }
    quota_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_PROJECT_ID")
    if quota_project:
        headers["X-Goog-User-Project"] = quota_project
    return headers


def build_multipart_related(
    boundary: str, metadata: bytes, media: bytes, media_content_type: str
) -> bytes:
    """Build Google's multipart/related upload body (not multipart/form-data)."""
    marker = boundary.encode("ascii")
    return b"".join(
        [
            b"--" + marker + b"\r\n",
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
            metadata,
            b"\r\n--" + marker + b"\r\n",
            f"Content-Type: {media_content_type}\r\n\r\n".encode("ascii"),
            media,
            b"\r\n--" + marker + b"--\r\n",
        ]
    )
