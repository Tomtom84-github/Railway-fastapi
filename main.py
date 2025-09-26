"""FastMCP time server ready for HTTP deployments."""
from __future__ import annotations

from datetime import datetime, timezone

from fastmcp import FastMCP

__all__ = ["app", "mcp"]

mcp = FastMCP("time-mcp-server")


@mcp.tool(description="Gibt die aktuelle Zeit im ISO-8601-Format zurück.")
def current_time() -> str:
    """Return the current UTC time as an ISO formatted string."""

    return datetime.now(timezone.utc).isoformat()


# The ASGI app Railway (or any other platform) can serve via Uvicorn/Hypercorn.
app = mcp.http_app()


def create_app() -> object:
    """Return the ASGI app for ASGI servers such as Uvicorn."""

    return app


if __name__ == "__main__":
    # Run the HTTP transport directly for local testing.
    mcp.run(transport="http", host="0.0.0.0", port=8000)
