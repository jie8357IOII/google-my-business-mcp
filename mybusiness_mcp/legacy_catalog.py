"""Versioned REST catalog for supported Google My Business v4 methods.

Google no longer publishes a working Discovery URL for the legacy v4 surface,
although these endpoints remain the documented interface for posts, media, and
reviews.  Keep this intentionally narrow and covered by contract tests.
"""

from __future__ import annotations

from typing import Any


def _parameter(
    *, location: str, required: bool = False, **extra: Any
) -> dict[str, Any]:
    return {"type": "string", "location": location, "required": required, **extra}


def _method(
    method_id: str,
    http_method: str,
    path: str,
    *,
    parameters: dict[str, Any],
    request: str | None = None,
    description: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": method_id,
        "httpMethod": http_method,
        "path": path,
        "parameters": parameters,
        "description": description,
    }
    if request:
        result["request"] = {"$ref": request}
    return result


NAME = _parameter(location="path", required=True)
PARENT = _parameter(location="path", required=True)
PAGE = {
    "pageSize": _parameter(location="query", format="int32"),
    "pageToken": _parameter(location="query"),
}


BUNDLED_V4_CATALOG: dict[str, Any] = {
    "kind": "discovery#restDescription",
    "protocol": "rest",
    "name": "mybusiness",
    "version": "v4",
    "rootUrl": "https://mybusiness.googleapis.com/",
    "servicePath": "",
    "schemas": {
        "LocalPost": {"type": "object", "additionalProperties": True},
        "MediaItem": {"type": "object", "additionalProperties": True},
        "ReviewReply": {"type": "object", "additionalProperties": True},
    },
    "resources": {
        "accounts": {
            "resources": {
                "locations": {
                    "resources": {
                        "localPosts": {
                            "methods": {
                                "create": _method(
                                    "mybusiness.accounts.locations.localPosts.create",
                                    "POST",
                                    "v4/{parent=accounts/*/locations/*}/localPosts",
                                    parameters={"parent": PARENT},
                                    request="LocalPost",
                                    description="Creates a local post for a location.",
                                ),
                                "get": _method(
                                    "mybusiness.accounts.locations.localPosts.get",
                                    "GET",
                                    "v4/{name=accounts/*/locations/*/localPosts/*}",
                                    parameters={"name": NAME},
                                    description="Gets a local post.",
                                ),
                                "list": _method(
                                    "mybusiness.accounts.locations.localPosts.list",
                                    "GET",
                                    "v4/{parent=accounts/*/locations/*}/localPosts",
                                    parameters={"parent": PARENT, **PAGE},
                                    description="Lists local posts for a location.",
                                ),
                                "patch": _method(
                                    "mybusiness.accounts.locations.localPosts.patch",
                                    "PATCH",
                                    "v4/{name=accounts/*/locations/*/localPosts/*}",
                                    parameters={
                                        "name": NAME,
                                        "updateMask": _parameter(
                                            location="query", required=True
                                        ),
                                    },
                                    request="LocalPost",
                                    description="Updates a local post using an update mask.",
                                ),
                                "delete": _method(
                                    "mybusiness.accounts.locations.localPosts.delete",
                                    "DELETE",
                                    "v4/{name=accounts/*/locations/*/localPosts/*}",
                                    parameters={"name": NAME},
                                    description="Deletes a local post.",
                                ),
                            }
                        },
                        "media": {
                            "methods": {
                                "create": _method(
                                    "mybusiness.accounts.locations.media.create",
                                    "POST",
                                    "v4/{parent=accounts/*/locations/*}/media",
                                    parameters={"parent": PARENT},
                                    request="MediaItem",
                                    description="Creates a media item from a source URL.",
                                ),
                                "get": _method(
                                    "mybusiness.accounts.locations.media.get",
                                    "GET",
                                    "v4/{name=accounts/*/locations/*/media/*}",
                                    parameters={"name": NAME},
                                    description="Gets a media item.",
                                ),
                                "list": _method(
                                    "mybusiness.accounts.locations.media.list",
                                    "GET",
                                    "v4/{parent=accounts/*/locations/*}/media",
                                    parameters={"parent": PARENT, **PAGE},
                                    description="Lists media for a location.",
                                ),
                                "patch": _method(
                                    "mybusiness.accounts.locations.media.patch",
                                    "PATCH",
                                    "v4/{name=accounts/*/locations/*/media/*}",
                                    parameters={
                                        "name": NAME,
                                        "updateMask": _parameter(location="query"),
                                    },
                                    request="MediaItem",
                                    description="Updates media item metadata using an update mask.",
                                ),
                                "delete": _method(
                                    "mybusiness.accounts.locations.media.delete",
                                    "DELETE",
                                    "v4/{name=accounts/*/locations/*/media/*}",
                                    parameters={"name": NAME},
                                    description="Deletes a media item.",
                                ),
                            }
                        },
                        "reviews": {
                            "methods": {
                                "get": _method(
                                    "mybusiness.accounts.locations.reviews.get",
                                    "GET",
                                    "v4/{name=accounts/*/locations/*/reviews/*}",
                                    parameters={"name": NAME},
                                    description="Gets a review.",
                                ),
                                "list": _method(
                                    "mybusiness.accounts.locations.reviews.list",
                                    "GET",
                                    "v4/{parent=accounts/*/locations/*}/reviews",
                                    parameters={"parent": PARENT, **PAGE},
                                    description="Lists reviews for a location.",
                                ),
                                "updateReply": _method(
                                    "mybusiness.accounts.locations.reviews.updateReply",
                                    "PUT",
                                    "v4/{name=accounts/*/locations/*/reviews/*}/reply",
                                    parameters={"name": NAME},
                                    request="ReviewReply",
                                    description="Creates or updates the reply to a review.",
                                ),
                                "deleteReply": _method(
                                    "mybusiness.accounts.locations.reviews.deleteReply",
                                    "DELETE",
                                    "v4/{name=accounts/*/locations/*/reviews/*}/reply",
                                    parameters={"name": NAME},
                                    description="Deletes the reply to a review.",
                                ),
                            }
                        },
                    }
                }
            }
        }
    },
}


BUNDLED_CATALOGS = {"mybusiness_v4": BUNDLED_V4_CATALOG}
