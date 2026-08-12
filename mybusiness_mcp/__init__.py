"""Google Business Profile MCP server."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("google-my-business-mcp")
except PackageNotFoundError:  # Source tree without an installed distribution.
    __version__ = "0+unknown"

USER_AGENT = f"google-my-business-mcp/{__version__}"
