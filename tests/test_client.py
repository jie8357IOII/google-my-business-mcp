from mybusiness_mcp.client import (
    build_multipart_related,
    build_query_parameters,
    expand_google_path_template,
)
from mybusiness_mcp.discovery import MethodDescriptor
from mybusiness_mcp.services import SERVICE_BY_KEY


def descriptor(path, parameters):
    return MethodDescriptor(
        tool_name="test",
        service=SERVICE_BY_KEY["business_information"],
        resource_path=("locations",),
        method_name="get",
        method={"path": path, "httpMethod": "GET", "parameters": parameters},
        document={"baseUrl": "https://example.test/", "parameters": {}},
    )


def test_google_pattern_expansion_preserves_resource_name_slashes():
    args = {"name": "locations/123"}
    assert (
        expand_google_path_template("v1/{name=locations/*}", args)
        == "v1/locations/123"
    )
    assert args == {}


def test_reserved_expansion_preserves_slashes():
    args = {"name": "accounts/1/locations/2"}
    assert (
        expand_google_path_template("v4/{+name}", args)
        == "v4/accounts/1/locations/2"
    )


def test_double_star_resource_name_preserves_slashes():
    args = {"resourceName": "accounts/1/locations/2/media/3"}
    got = expand_google_path_template("v1/{resourceName=**}:startUpload", args)
    assert got == "v1/accounts/1/locations/2/media/3:startUpload"


def test_plain_template_encodes_slash():
    args = {"id": "a/b"}
    assert expand_google_path_template("v1/items/{id}", args) == "v1/items/a%2Fb"


def test_query_mapping_handles_boolean_and_repeated():
    d = descriptor(
        "v1/{name=locations/*}",
        {
            "name": {"location": "path", "required": True},
            "validateOnly": {"location": "query", "type": "boolean"},
            "field": {"location": "query", "type": "string", "repeated": True},
        },
    )
    args = {"validateOnly": True, "field": ["title", "websiteUri"]}
    params = build_query_parameters(d, args)
    assert params == [
        ("validateOnly", "true"),
        ("field", "title"),
        ("field", "websiteUri"),
    ]


def test_multipart_related_has_google_expected_shape():
    payload = build_multipart_related("abc123", b'{"x":1}', b"JPEG", "image/jpeg")
    assert payload.startswith(b"--abc123\r\nContent-Type: application/json")
    assert b'{"x":1}' in payload
    assert b"Content-Type: image/jpeg\r\n\r\nJPEG" in payload
    assert payload.endswith(b"--abc123--\r\n")
