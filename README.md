# Google My Business MCP Server

> Inspired by the [Google Ads MCP Server](https://github.com/googleads/google-ads-mcp).

This repository contains the source code for an
[MCP](https://modelcontextprotocol.io) server that interacts with the
[Google Business Profile APIs](https://developers.google.com/my-business/).

It intentionally contains no Agent workflow, SEO automation, business logic,
asset hosting, or high-level orchestration. Its job is to expose Google
Business Profile REST methods as MCP tools and return Google API responses.

> This is a community project and is not an official Google product.

## Tools

The server turns Google REST methods into MCP tools for LLMs and AI agents.
Tool names follow this pattern:

```text
gmb_<service>_<resource>_<method>
```

Depending on the available Google APIs and Discovery Documents, tools can
cover:

- accounts and locations;
- business information;
- local posts;
- location media;
- reviews and review replies;
- performance;
- lodging, place actions, notifications, and verifications.

Path and query parameters are normal tool arguments. Methods with a request
payload accept a `body` object. Methods whose Google Discovery definition
declares media upload support also accept `media_path` and an optional
`media_content_type`.

The server prefers Google's live Discovery Documents. Because Google no longer
publishes a working Discovery URL for the legacy v4 surface, the package
contains a narrow, version-controlled, contract-tested fallback catalog for
Local Posts, media, and reviews. The fallback is used only when live discovery
for that service fails.

### MCP resources and discovery helpers

The current release exposes Google REST methods as MCP tools only. It does not
yet register MCP Resources for Discovery Documents, schemas, or release notes.

> **TODO:** Expose bounded discovery helpers such as `gmb_find_methods`,
> `gmb_describe_method`, and `gmb_describe_schema`, or equivalent MCP Resources.
> Until then, complex request bodies must be checked against the linked Google
> API reference before execution.

### Configuring and namespacing tools

The current release can limit discovery to selected Google service families
with `GMB_MCP_SERVICES`, and deprecated services can be excluded with
`GMB_MCP_INCLUDE_DEPRECATED=0`.

> **TODO:** Add a fail-closed per-tool allowlist and optional namespace prefixes
> without requiring a new configuration framework. Individual MCP clients may
> apply their own tool allowlist in the meantime.

## Safety notes

1. The MCP server exposes Business Profile data to the Agent or LLM connected
   to it. Only connect it to clients you trust.
2. Tool annotations are conservative: GET, HEAD, and OPTIONS are read-only;
   DELETE is destructive; unknown methods are treated as writes.
3. Set `GMB_MCP_REQUIRE_WRITE_CONFIRMATION=1` to require MCP elicitation before
   every write. The preview includes the exact resource, target, update mask,
   body, and other non-secret arguments.
4. Write confirmation fails closed when it is declined, cancelled, unavailable,
   not explicitly acknowledged, or times out. No Google API request is sent in
   those cases.
5. Secret fields and signed URL query strings are redacted from confirmation
   previews. Do not place credentials in request bodies or source URLs.
6. Local Post media uses Google's `sourceUrl` field. This project does not host
   or publish local files for Google to fetch.

The confirmation timeout defaults to 120 seconds. It can be changed to a value
greater than 0 and no more than 600 seconds with
`GMB_MCP_WRITE_CONFIRMATION_TIMEOUT_SECONDS`.

## Setup instructions

Setup has six steps:

1. Configure Python.
2. Create or select a Google Cloud project.
3. Request Google Business Profile API access for that project.
4. Enable the Google Business Profile APIs you need.
5. Configure Application Default Credentials.
6. Configure your MCP client.

### Configure Python

Python 3.10 or newer is required. Install
[pipx](https://pipx.pypa.io/stable/), then install the server:

```bash
pipx install git+https://github.com/jie8357IOII/google-my-business-mcp.git
```

### Enable APIs

Google Business Profile API access is granted to a Google Cloud project. Follow
Google's [prerequisites](https://developers.google.com/my-business/content/prereqs)
and submit the access request before expecting the legacy Google My Business API
to appear in the API Library.

Enable the relevant
[Google Business Profile APIs](https://developers.google.com/my-business/content/basic-setup)
in your Google Cloud project. The exact set depends on the tools you intend to
use, such as Business Information, Account Management, Performance, or the
legacy Google My Business v4 surface.

Google does not provide a separate GBP sandbox. Use a real account you are
authorized to manage, begin with read-only acceptance checks, and only use a
method's `validateOnly` parameter when that method officially supports it.

### Configure credentials

The server uses
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)
with this OAuth scope:

```text
https://www.googleapis.com/auth/business.manage
```

The Google account used for authentication must have access to the relevant
Business Profile accounts or locations. For a local interactive setup, use an
OAuth desktop client you control:

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/business.manage,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=YOUR_OAUTH_CLIENT_JSON
```

Do not commit the OAuth client JSON, ADC file, refresh token, or access token.

The server currently reads credentials through ADC; it does not host an OAuth
callback or consent flow itself.

> **TODO:** Evaluate an optional built-in OAuth proxy only if remote MCP hosting
> becomes a supported use case. Local stdio installations should continue to
> prefer ADC so the server does not store OAuth client secrets.

### Configure your MCP client

Point `GOOGLE_APPLICATION_CREDENTIALS` to the ADC file created during the
previous step:

```json
{
  "mcpServers": {
    "google-my-business": {
      "command": "pipx",
      "args": [
        "run",
        "--spec",
        "git+https://github.com/jie8357IOII/google-my-business-mcp.git",
        "google-my-business-mcp"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_APPLICATION_DEFAULT_CREDENTIALS_JSON",
        "GMB_MCP_REQUIRE_WRITE_CONFIRMATION": "1"
      }
    }
  }
}
```

The server uses the MCP stdio transport.

If the package was installed once with `pipx install`, the MCP client can call
the installed executable directly instead:

```json
{
  "mcpServers": {
    "google-my-business": {
      "command": "google-my-business-mcp",
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_APPLICATION_DEFAULT_CREDENTIALS_JSON",
        "GMB_MCP_REQUIRE_WRITE_CONFIRMATION": "1"
      }
    }
  }
}
```

> **TODO:** Add verified client-specific examples for Hermes, Claude Desktop,
> Cursor, VS Code, and other MCP hosts. The JSON shape and executable resolution
> can differ between clients and operating systems.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC default lookup | Path to an ADC-compatible credential file. |
| `GOOGLE_CLOUD_PROJECT` | unset | Preferred quota and Google Cloud project ID. |
| `GOOGLE_PROJECT_ID` | unset | Fallback project ID when `GOOGLE_CLOUD_PROJECT` is unset. |
| `GMB_MCP_REQUIRE_WRITE_CONFIRMATION` | `0` | Set to `1` to require exact MCP elicitation before writes. |
| `GMB_MCP_WRITE_CONFIRMATION_TIMEOUT_SECONDS` | `120` | Write confirmation timeout; must be greater than 0 and no more than 600. |
| `GMB_MCP_CACHE_DIR` | user cache directory | Directory for Google Discovery Document cache files. |
| `GMB_MCP_DISCOVERY_CACHE_TTL` | `86400` | Discovery cache lifetime in seconds. |
| `GMB_MCP_SERVICES` | all registered services | Comma-separated service keys to load. |
| `GMB_MCP_INCLUDE_DEPRECATED` | `1` | Set to `0` to exclude services marked deprecated. |

Current service keys are `mybusiness_v4`, `mybusiness_v1`,
`account_management`, `business_information`, `lodging`, `place_actions`,
`notifications`, `verifications`, `performance`, `qanda`, and
`business_calls`.

## Try it out

Start your MCP client and verify the server appears in its list of connected
servers. Example read-only prompts:

- What Business Profile accounts can I access?
- List every location I can manage, following all pagination tokens.
- Read the latest Local Posts for a selected location.
- Show recent reviews for a selected location.

Before asking an Agent to write, enable confirmation and verify the target,
body, update mask, media URL, and deletion target shown in the elicitation.

## Current limitations and TODO roadmap

The following capabilities are intentionally visible as TODOs rather than being
described as available:

- **TODO — MCP Resources:** publish bounded Discovery Document, schema, and
  release-note resources.
- **TODO — discovery helper tools:** register method search and schema inspection
  helpers without inflating every tool schema.
- **TODO — per-tool configuration:** add a built-in fail-closed allowlist and
  optional namespace prefixes.
- **TODO — client guides:** add tested configuration examples for major MCP
  clients, including Hermes.
- **TODO — remote authentication:** evaluate an OAuth proxy with secure token
  storage if remote hosting becomes a supported scope.
- **TODO — remote transport:** evaluate MCP Streamable HTTP. The current server
  supports stdio only.
- **TODO — deployment artifacts:** add Docker and Google Cloud Run instructions
  only after remote authentication and transport have production tests.
- **TODO — startup diagnostics:** provide a safe readiness report covering ADC,
  enabled services, Discovery fallback, and tool counts without exposing
  credentials or customer data.

Developer tokens and login customer IDs are Google Ads concepts and are not GBP
TODOs. Telemetry is not collected. Agent workflows, asset hosting, SEO logic,
and business-specific orchestration remain outside this repository by design.

## Development

```bash
git clone https://github.com/jie8357IOII/google-my-business-mcp.git
cd google-my-business-mcp
python -m pip install -e '.[dev]'
pytest
python -m compileall mybusiness_mcp
ruff check mybusiness_mcp tests
```

Project layout:

```text
mybusiness_mcp/
├── server.py          # stdio entry point
├── coordinator.py     # MCP tool registration and write confirmation
├── auth.py            # Google ADC authentication
├── client.py          # authenticated REST requests and media uploads
├── discovery.py       # Discovery Document to MCP tool definitions
├── legacy_catalog.py  # tested fallback for the legacy v4 surface
└── services.py        # Google API service registry
```

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0
