import asyncio
from types import SimpleNamespace

from mybusiness_mcp import coordinator
from mybusiness_mcp.discovery import MethodDescriptor
from mybusiness_mcp.services import SERVICE_BY_KEY


def descriptor(method="PATCH"):
    return MethodDescriptor(
        tool_name="write_tool",
        service=SERVICE_BY_KEY["business_information"],
        resource_path=("locations",),
        method_name="patch",
        method={
            "path": "v1/{location.name=locations/*}",
            "httpMethod": method,
        },
        document={"baseUrl": "https://example.test/"},
    )


class FakeCatalog:
    async def ensure_loaded(self):
        return None

    def get_method(self, name):
        return descriptor("GET" if name == "read_tool" else "PATCH")


class FakeClient:
    def __init__(self):
        self.calls = []

    async def execute(self, method, arguments):
        self.calls.append((method, arguments))
        return {"ok": True}


class FakeSession:
    def __init__(self, action="accept", error=None):
        self.action = action
        self.error = error
        self.messages = []

    async def elicit_form(self, message, requestedSchema):
        self.messages.append((message, requestedSchema))
        if self.error:
            raise self.error
        return SimpleNamespace(action=self.action, content={})


def test_tool_annotations_are_conservative():
    assert coordinator.tool_annotations("GET").readOnlyHint is True
    assert coordinator.tool_annotations("POST").readOnlyHint is False
    assert coordinator.tool_annotations("DELETE").destructiveHint is True
    assert coordinator.tool_annotations("UNKNOWN").readOnlyHint is False


def test_confirmation_preview_redacts_secrets_and_signed_urls():
    preview = coordinator.operation_preview(
        descriptor(),
        {
            "location.name": "locations/123",
            "updateMask": "websiteUri",
            "body": {
                "access_token": "secret",
                "sourceUrl": "https://assets.test/file.jpg?X-Amz-Signature=abc",
            },
        },
    )
    assert "secret" not in preview
    assert "X-Amz-Signature=abc" not in preview
    assert "websiteUri" in preview
    assert "locations/123" in preview


def test_declined_confirmation_performs_zero_http_calls(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(coordinator, "catalog", FakeCatalog())
    monkeypatch.setattr(coordinator, "client", fake_client)
    monkeypatch.setenv("GMB_MCP_REQUIRE_WRITE_CONFIRMATION", "1")

    result = asyncio.run(
        coordinator.execute_tool(
            "write_tool", {"body": {"title": "New"}}, session=FakeSession("decline")
        )
    )

    assert result["code"] == "WRITE_CONFIRMATION_DECLINED"
    assert result["mutation_performed"] is False
    assert fake_client.calls == []


def test_confirmation_timeout_fails_closed_with_zero_http_calls(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(coordinator, "catalog", FakeCatalog())
    monkeypatch.setattr(coordinator, "client", fake_client)
    monkeypatch.setenv("GMB_MCP_REQUIRE_WRITE_CONFIRMATION", "1")

    result = asyncio.run(
        coordinator.execute_tool(
            "write_tool",
            {"body": {"title": "New"}},
            session=FakeSession(error=TimeoutError("timed out")),
        )
    )

    assert result["code"] == "WRITE_CONFIRMATION_UNAVAILABLE"
    assert fake_client.calls == []


def test_accepted_confirmation_executes_once(monkeypatch):
    fake_client = FakeClient()
    session = FakeSession("accept")
    monkeypatch.setattr(coordinator, "catalog", FakeCatalog())
    monkeypatch.setattr(coordinator, "client", fake_client)
    monkeypatch.setenv("GMB_MCP_REQUIRE_WRITE_CONFIRMATION", "1")

    result = asyncio.run(
        coordinator.execute_tool(
            "write_tool", {"body": {"title": "New"}}, session=session
        )
    )

    assert result == {"ok": True}
    assert len(fake_client.calls) == 1
    assert "Confirm this Google Business Profile write" in session.messages[0][0]


def test_read_skips_elicitation(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(coordinator, "catalog", FakeCatalog())
    monkeypatch.setattr(coordinator, "client", fake_client)
    monkeypatch.setenv("GMB_MCP_REQUIRE_WRITE_CONFIRMATION", "1")

    result = asyncio.run(
        coordinator.execute_tool(
            "read_tool", {}, session=FakeSession(error=AssertionError())
        )
    )

    assert result == {"ok": True}
    assert len(fake_client.calls) == 1
