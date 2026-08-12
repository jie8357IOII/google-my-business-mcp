# Google My Business MCP Server

A simple MCP server for Google Business Profile / Google My Business REST APIs.

The project follows the basic structure of Google's official `googleanalytics/google-analytics-mcp`: MCP stdio server, central tool registration, Google authentication, API client, tests, and Python packaging.

It intentionally contains **no Agent workflow, SEO automation, business logic, or high-level orchestration**. Its job is only to expose Google Business Profile REST methods as MCP tools and return Google's API responses.

> Community project. Not an official Google project.

## How it works

```text
MCP client
  -> MCP tool
  -> Google Business Profile REST method
  -> Google API JSON response
```

Google Discovery Documents are used internally so REST methods and parameters do not need to be duplicated manually in the codebase.

The default service set includes the Google My Business v4/v1 APIs and the current Business Profile APIs for accounts, business information, lodging, place actions, notifications, verifications, and performance. Deprecated Google services may still appear when their Discovery Documents remain available.

## Install

Python 3.10+ is required.

```bash
pipx install git+https://github.com/jie8357IOII/google-my-business-mcp.git
```

For development:

```bash
git clone https://github.com/jie8357IOII/google-my-business-mcp.git
cd google-my-business-mcp
python -m pip install -e '.[dev]'
pytest
```

## Authentication

The server uses Google Application Default Credentials (ADC) with the Business Profile scope:

```text
https://www.googleapis.com/auth/business.manage
```

Example:

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/business.manage,https://www.googleapis.com/auth/cloud-platform \
  --client-id-file=YOUR_OAUTH_CLIENT_JSON
```

The Google account used for authentication must have access to the relevant Business Profile account or locations.

## MCP configuration

Example configuration for an MCP client:

```json
{
  "mcpServers": {
    "google-my-business": {
      "command": "google-my-business-mcp",
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/application_default_credentials.json"
      }
    }
  }
}
```

You can also run it directly:

```bash
google-my-business-mcp
```

The transport is stdio.

## Tools

Each Google REST method is exposed directly as an MCP tool. Tool names use the following style:

```text
gmb_<service>_<resource>_<method>
```

Examples can include tools for locations, reviews, local posts, media, verification, business information, and performance depending on the Discovery Documents currently published by Google.

Path and query parameters are exposed as normal MCP arguments. Methods with a request payload accept a `body` object. Media-capable methods can additionally accept a local `media_path` and optional `media_content_type`.

No additional workflow layer is added on top of the Google API.

## Project structure

```text
mybusiness_mcp/
├── server.py       # stdio entry point
├── coordinator.py  # MCP tool registration and dispatch
├── auth.py         # Google ADC credentials
├── client.py       # authenticated REST requests
├── discovery.py    # Discovery Document -> MCP tool definitions
└── services.py     # Google API service registry
```

## License

Apache-2.0
