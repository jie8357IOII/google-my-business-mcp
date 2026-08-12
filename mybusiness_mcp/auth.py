"""Application Default Credentials for Google Business Profile APIs."""

from __future__ import annotations

import asyncio
import contextlib
import os
import subprocess
import threading
from unittest.mock import patch

import google.auth
from google.auth.transport.requests import Request


BUSINESS_MANAGE_SCOPE = "https://www.googleapis.com/auth/business.manage"
_client_lock = threading.Lock()
_credentials = None


@contextlib.contextmanager
def prevent_stdio_inheritance():
    """Avoid gcloud inheriting MCP stdio handles on Windows.

    This mirrors the defensive credential-loading pattern used by Google's
    official Analytics MCP server.
    """
    original_popen = subprocess.Popen

    def safe_popen(*args, **kwargs):
        if kwargs.get("stdin") is None:
            kwargs["stdin"] = subprocess.DEVNULL
        return original_popen(*args, **kwargs)

    with patch("subprocess.Popen", new=safe_popen):
        yield


def _get_credentials_sync():
    global _credentials
    with _client_lock:
        if _credentials is None:
            with prevent_stdio_inheritance():
                credentials, _ = google.auth.default(scopes=[BUSINESS_MANAGE_SCOPE])
            quota_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
                "GOOGLE_PROJECT_ID"
            )
            if quota_project and hasattr(credentials, "with_quota_project"):
                credentials = credentials.with_quota_project(quota_project)
            _credentials = credentials
        if not _credentials.valid or not _credentials.token:
            _credentials.refresh(Request())
        return _credentials


async def get_access_token(*, force_refresh: bool = False) -> str:
    global _credentials

    def work() -> str:
        global _credentials
        credentials = _get_credentials_sync()
        if force_refresh:
            with _client_lock:
                credentials.refresh(Request())
        if not credentials.token:
            raise RuntimeError(
                "Google Application Default Credentials did not yield an access token"
            )
        return str(credentials.token)

    return await asyncio.to_thread(work)
