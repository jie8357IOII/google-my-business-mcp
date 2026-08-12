import asyncio

from mybusiness_mcp.discovery import (
    DiscoveryCatalog,
    MethodDescriptor,
    build_tool_name,
    method_input_schema,
    walk_methods,
)
from mybusiness_mcp.services import SERVICE_BY_KEY

DOC = {
    "protocol": "rest",
    "rootUrl": "https://example.googleapis.com/",
    "servicePath": "v1/",
    "parameters": {"prettyPrint": {"type": "boolean", "location": "query"}},
    "schemas": {
        "Location": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Business title"},
                "categories": {"$ref": "Categories"},
            },
        }
    },
    "resources": {
        "locations": {
            "methods": {
                "get": {
                    "id": "example.locations.get",
                    "path": "v1/{name=locations/*}",
                    "httpMethod": "GET",
                    "description": "Get a location.",
                    "parameters": {
                        "name": {
                            "type": "string",
                            "location": "path",
                            "required": True,
                        },
                        "readMask": {
                            "type": "string",
                            "location": "query",
                            "required": True,
                        },
                    },
                },
                "patch": {
                    "id": "example.locations.patch",
                    "path": "v1/{location.name=locations/*}",
                    "httpMethod": "PATCH",
                    "parameters": {
                        "location.name": {
                            "type": "string",
                            "location": "path",
                            "required": True,
                        },
                        "updateMask": {
                            "type": "string",
                            "location": "query",
                            "required": True,
                        },
                    },
                    "request": {"$ref": "Location"},
                },
            },
            "resources": {
                "reviews": {
                    "methods": {
                        "list": {
                            "id": "example.locations.reviews.list",
                            "path": "v1/{parent=locations/*}/reviews",
                            "httpMethod": "GET",
                            "parameters": {
                                "parent": {
                                    "type": "string",
                                    "location": "path",
                                    "required": True,
                                }
                            },
                        }
                    }
                }
            },
        }
    },
}


def test_walks_nested_methods():
    found = [(path, name) for path, name, _ in walk_methods(DOC)]
    assert (("locations",), "get") in found
    assert (("locations", "reviews"), "list") in found


def test_tool_name_is_stable_and_compatible():
    method = DOC["resources"]["locations"]["resources"]["reviews"]["methods"]["list"]
    tool = build_tool_name(
        SERVICE_BY_KEY["business_information"],
        ("locations", "reviews"),
        "list",
        method,
    )
    assert tool == "gmb_info_locations_reviews_list"
    assert len(tool) <= 64


def test_compact_body_schema_preserves_top_level_fields():
    method = DOC["resources"]["locations"]["methods"]["patch"]
    descriptor = MethodDescriptor(
        tool_name="gmb_info_locations_patch",
        service=SERVICE_BY_KEY["business_information"],
        resource_path=("locations",),
        method_name="patch",
        method=method,
        document=DOC,
    )
    schema = method_input_schema(descriptor)
    assert set(schema["required"]) == {"location.name", "updateMask"}
    assert schema["properties"]["body"]["properties"]["title"]["type"] == "string"
    assert (
        schema["properties"]["body"]["properties"]["categories"]["x-google-schema-ref"]
        == "Categories"
    )


def test_legacy_v4_404_falls_back_to_versioned_catalog(monkeypatch, tmp_path):
    monkeypatch.setenv("GMB_MCP_SERVICES", "mybusiness_v4")

    async def fail_live_discovery(service, *, force):
        raise RuntimeError("404 Not Found")

    catalog = DiscoveryCatalog(cache_dir=tmp_path)
    monkeypatch.setattr(catalog, "_load_service", fail_live_discovery)
    asyncio.run(catalog.ensure_loaded())

    assert "using bundled catalog" in catalog.errors["mybusiness_v4"]
    expected_legacy_tools = {
        "gmb_v4_accounts_locations_localposts_create",
        "gmb_v4_accounts_locations_localposts_get",
        "gmb_v4_accounts_locations_localposts_list",
        "gmb_v4_accounts_locations_localposts_patch",
        "gmb_v4_accounts_locations_localposts_delete",
        "gmb_v4_accounts_locations_media_create",
        "gmb_v4_accounts_locations_media_get",
        "gmb_v4_accounts_locations_media_list",
        "gmb_v4_accounts_locations_media_patch",
        "gmb_v4_accounts_locations_media_delete",
        "gmb_v4_accounts_locations_reviews_get",
        "gmb_v4_accounts_locations_reviews_list",
        "gmb_v4_accounts_locations_reviews_updatereply",
        "gmb_v4_accounts_locations_reviews_deletereply",
    }
    assert expected_legacy_tools.issubset(catalog.methods)
    local_post_patch = catalog.get_method(
        "gmb_v4_accounts_locations_localposts_patch"
    ).method
    assert local_post_patch["request"]["$ref"] == "LocalPost"
    assert local_post_patch["path"] == (
        "v4/{name=accounts/*/locations/*/localPosts/*}"
    )
    assert local_post_patch["parameters"]["updateMask"]["required"] is True
    media_patch = catalog.get_method("gmb_v4_accounts_locations_media_patch")
    assert media_patch.method["request"]["$ref"] == "MediaItem"
    assert media_patch.method["path"] == (
        "v4/{name=accounts/*/locations/*/media/*}"
    )
    assert media_patch.method["parameters"]["name"]["required"] is True
    assert media_patch.method["parameters"]["updateMask"]["required"] is False
