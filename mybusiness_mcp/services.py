"""Google Business Profile service registry.

The Business Profile API is federated across several Google API endpoints.
The legacy Google My Business endpoint remains important for posts, reviews,
media, food menus, and other v4.9 functionality.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceDefinition:
    key: str
    short_name: str
    title: str
    discovery_url: str
    docs_url: str
    deprecated: bool = False
    deprecation_note: str | None = None


SERVICES: tuple[ServiceDefinition, ...] = (
    ServiceDefinition(
        key="mybusiness_v4",
        short_name="v4",
        title="Google My Business API v4.9",
        discovery_url="https://mybusiness.googleapis.com/$discovery/rest?version=v4",
        docs_url="https://developers.google.com/my-business/reference/rest",
    ),
    ServiceDefinition(
        key="mybusiness_v1",
        short_name="v1",
        title="Google My Business API v1 (media)",
        discovery_url="https://mybusiness.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/rest",
    ),
    ServiceDefinition(
        key="account_management",
        short_name="accounts",
        title="My Business Account Management API",
        discovery_url="https://mybusinessaccountmanagement.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/accountmanagement/rest",
    ),
    ServiceDefinition(
        key="business_information",
        short_name="info",
        title="My Business Business Information API",
        discovery_url="https://mybusinessbusinessinformation.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/businessinformation/rest",
    ),
    ServiceDefinition(
        key="lodging",
        short_name="lodging",
        title="My Business Lodging API",
        discovery_url="https://mybusinesslodging.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/lodging/rest",
    ),
    ServiceDefinition(
        key="place_actions",
        short_name="actions",
        title="My Business Place Actions API",
        discovery_url="https://mybusinessplaceactions.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/placeactions/rest",
    ),
    ServiceDefinition(
        key="notifications",
        short_name="notifications",
        title="My Business Notifications API",
        discovery_url="https://mybusinessnotifications.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/notifications/rest",
    ),
    ServiceDefinition(
        key="verifications",
        short_name="verify",
        title="My Business Verifications API",
        discovery_url="https://mybusinessverifications.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/verifications/rest",
    ),
    ServiceDefinition(
        key="performance",
        short_name="performance",
        title="Business Profile Performance API",
        discovery_url="https://businessprofileperformance.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/performance/rest",
    ),
    ServiceDefinition(
        key="qanda",
        short_name="qanda",
        title="My Business Q&A API",
        discovery_url="https://mybusinessqanda.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/qanda/rest",
        deprecated=True,
        deprecation_note=(
            "The My Business Q&A API was discontinued on 2025-11-03; "
            "retained for reference/catalog completeness."
        ),
    ),
    ServiceDefinition(
        key="business_calls",
        short_name="calls",
        title="My Business Business Calls API",
        discovery_url="https://mybusinessbusinesscalls.googleapis.com/$discovery/rest?version=v1",
        docs_url="https://developers.google.com/my-business/reference/businesscalls/rest",
        deprecated=True,
        deprecation_note=(
            "The My Business Business Calls API was deprecated on 2023-05-30; "
            "retained for reference/catalog completeness."
        ),
    ),
)

SERVICE_BY_KEY = {service.key: service for service in SERVICES}
