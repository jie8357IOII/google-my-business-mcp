# Google My Business MCP Server

An MCP server for the **complete Google Business Profile / Google My Business REST API surface**.

It uses the same broad structural pattern as Google's official [`googleanalytics/google-analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp): a low-level MCP stdio server, a central coordinator, separate auth/client modules, Application Default Credentials (ADC), model-oriented tool descriptions, tests, and Python packaging.

The Business Profile API is much larger and is federated across several Google API services. Instead of manually duplicating every REST method and schema, this server treats Google's official **Discovery Documents as the source of truth** and dynamically generates one MCP tool for every discovered REST method.

> Community project. Not an official Google project.

## What this covers

The default service registry includes:

- **Google My Business API v4.9** — the source reference requested for Reviews, Local Posts, Media, Food Menus, followers, insurance networks, and remaining v4 capabilities.
- **Google My Business API v1** — media surface exposed from `mybusiness.googleapis.com`.
- **My Business Account Management API**.
- **My Business Business Information API**.
- **My Business Lodging API**.
- **My Business Place Actions API**.
- **My Business Notifications API**.
- **My Business Verifications API**.
- **Business Profile Performance API**.
- **My Business Q&A API** — retained as deprecated/discontinued catalog coverage; Google discontinued it on 2025-11-03.
- **My Business Business Calls API** — retained as deprecated catalog coverage; Google deprecated it on 2023-05-30.

The original Google My Business reference page publishes Discovery Documents for both v4 and v1. This MCP consumes those documents directly, so additions such as new review fields, recurring-post fields, or future schema changes do not require manually rewriting every tool.

## Architecture

```text
MCP client
  │ stdio
  ▼
mybusiness_mcp/server.py
  ▼
mybusiness_mcp/coordinator.py
  ├── static meta tools
  └── generated REST tools
       ▼
mybusiness_mcp/discovery.py ── Google Discovery Documents
       ▼
mybusiness_mcp/client.py
       ▼
mybusiness_mcp/auth.py ── Application Default Credentials
       ▼
Google Business Profile APIs
```

### Why the generated tools use compact schemas

A literal expansion of every Google request/response object into every MCP tool would make `tools/list` unnecessarily large and repeatedly consume model context.

This server therefore exposes:

1. **Every REST method as a generated `gmb_*` MCP tool.**
2. Required path and query parameters directly in each tool schema.
3. A shallow request-body shape containing the useful top-level fields.
4. `gmb_describe_method` to fetch the complete request/response schema only when needed.
5. `gmb_describe_schema` to inspect any named Discovery schema.
6. `gmb_search_methods` to find the right endpoint without guessing names.

This keeps the full API reachable while making Agent usage substantially more context-efficient.

## Meta tools

| Tool | Purpose |
|---|---|
| `gmb_list_services` | Show API services, load/deprecation states, and discovered method counts |
| `gmb_search_methods` | Search the complete discovered REST method catalog |
| `gmb_describe_method` | Return full method metadata plus request/response schemas |
| `gmb_describe_schema` | Return a complete named Google Discovery schema |
| `gmb_refresh_discovery` | Refresh Discovery Documents and rebuild generated tools |

All remaining tools are generated from Google's current Discovery Documents. Typical names follow patterns such as:

```text
gmb_v4_accounts_locations_reviews_list
gmb_v4_accounts_locations_localposts_create
gmb_info_locations_get
gmb_info_locations_patch
gmb_accounts_accounts_list
gmb_performance_locations_getdailymetricstimeseries
```

The exact catalog may change as Google changes its Discovery Documents.

## Requirements

- Python 3.10+
- A Google Cloud project approved for Google Business Profile API access
- Relevant Business Profile APIs enabled in that project
- OAuth 2.0 user credentials for a Google account that has access to the Business Profiles you want to manage
- OAuth scope:

```text
https://www.googleapis.com/auth/business.manage
```

Google Business Profile APIs are restricted APIs. Enabling an API does not grant access to arbitrary Business Profiles; the authenticated Google user must have access to the target account/location.

## Install

With `pipx` directly from GitHub:

```bash
pipx install git+https://github.com/jie8357IOII/google-my-business-mcp.git
```

For development:

```bash
git clone https://github.com/jie8357IOII/google-my-business-mcp.git
cd google-my-business-mcp
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Configure Google credentials

The server uses **Application Default Credentials**, following the operational pattern used by Google's Analytics MCP server.

A typical user-credential flow is:

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/business.manage,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=YOUR_OAUTH_CLIENT_JSON
```

Do not commit OAuth client secrets, refresh tokens, or the generated ADC file.

## MCP configuration

### Claude Code

```bash
claude mcp add google-my-business-mcp \
  --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/application_default_credentials.json" \
  -e "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID" \
  -- pipx run --spec git+https://github.com/jie8357IOII/google-my-business-mcp.git google-my-business-mcp
```

### Generic MCP JSON configuration

```json
{
  "mcpServers": {
    "google-my-business-mcp": {
      "command": "pipx",
      "args": [
        "run",
        "--spec",
        "git+https://github.com/jie8357IOII/google-my-business-mcp.git",
        "google-my-business-mcp"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/absolute/path/to/application_default_credentials.json",
        "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

## Recommended Agent workflow

For read operations, first search the method catalog instead of hard-coding endpoint assumptions:

```text
Find my Business Profile accounts and locations, then show reviews that have not received a reply.
```

The intended sequence is:

```text
gmb_search_methods("accounts")
→ account list tool
→ gmb_search_methods("locations")
→ location list/get tool
→ gmb_search_methods("reviews")
→ review list tool
```

For writes, inspect the current Google schema before execution:

```text
Update the regular business hours for locations/123. First inspect the current request schema and updateMask requirements.
```

Intended sequence:

```text
gmb_search_methods("update location")
→ gmb_describe_method(...)
→ generated update tool
```

## Discovery caching

Discovery Documents are cached for 24 hours by default so MCP startup does not repeatedly download the same API definitions.

| Environment variable | Default | Meaning |
|---|---:|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC default | Credential file path |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_PROJECT_ID` | unset | Google Cloud/quota project |
| `GMB_MCP_CACHE_DIR` | `~/.cache/google-my-business-mcp/discovery` | Discovery cache location |
| `GMB_MCP_DISCOVERY_CACHE_TTL` | `86400` | Discovery cache lifetime in seconds |
| `GMB_MCP_INCLUDE_DEPRECATED` | `1` | Set `0` to omit deprecated service tools |
| `GMB_MCP_SERVICES` | all | Comma-separated service keys to expose |

For a smaller production tool context, you can expose only the services you use most:

```bash
GMB_MCP_SERVICES=account_management,business_information,mybusiness_v4,performance
```

## Request execution

The generic client handles:

- OAuth bearer tokens from ADC
- automatic token refresh and one 401 retry for normal JSON requests
- `X-GOOG-API-FORMAT-VERSION: 2`
- optional `X-Goog-User-Project` from the configured project ID
- Google Discovery path templates including `{+name}`, `{name=accounts/*}`, and `{resourceName=**}`
- repeated and boolean query parameters
- JSON request bodies
- Discovery-declared simple media uploads
- Google-style `multipart/related` media uploads
- structured Google API error payloads

Authentication query parameters such as `access_token`, `oauth_token`, and API keys are deliberately hidden from MCP tool schemas because authentication is supplied internally.

## Write behavior

The MCP server does not impose a second confirmation mechanism. The MCP client/Agent should control confirmation policy for destructive or externally visible writes.

Where a Google API method exposes `validateOnly`, that parameter is surfaced in the generated tool schema and should be preferred before high-impact updates when appropriate.

## Development

```bash
python -m pip install -e '.[dev]'
python -m compileall mybusiness_mcp tests
pytest -q
ruff check mybusiness_mcp tests
```

The tests cover:

- nested Discovery resource traversal
- stable MCP-compatible tool naming
- compact body schemas
- `{name=locations/*}` expansion
- `{+name}` reserved expansion
- `{resourceName=**}` expansion
- ordinary path escaping
- repeated/boolean query parameters
- Google `multipart/related` body construction

## Source of truth

Google documentation used by this project:

- Google My Business REST reference: `https://developers.google.com/my-business/reference/rest`
- Federated Business Profile API overview: `https://developers.google.com/my-business/ref_overview`
- Google Business Profile change log: `https://developers.google.com/my-business/content/change-log`
- Google Business Profile deprecation schedule: `https://developers.google.com/my-business/content/sunset-dates`
- Google Analytics MCP architectural reference: `https://github.com/googleanalytics/google-analytics-mcp`

The runtime API catalog itself comes from the official Google Discovery Documents listed in `mybusiness_mcp/services.py`.

## License

Apache-2.0.
