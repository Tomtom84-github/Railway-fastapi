"""Streamable HTTP MCP server providing current time information."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastmcp import FastMCP
from fastmcp.adapters.streamable_http import StreamableHTTPServer
from zoneinfo import ZoneInfo

mcp = FastMCP(
    name="time-mcp-server",
    version="1.0.0",
    description="Simple MCP server that returns the current time.",
)


@mcp.tool(name="current_time", description="Get the current time optionally in a specific timezone.")
async def current_time(timezone_name: Optional[str] = None) -> dict[str, str]:
    """Return the current time as an ISO formatted string.

    Args:
        timezone_name: Optional IANA timezone identifier (e.g. "Europe/Berlin").

    Returns:
        A dictionary containing the resolved timezone and current time.
    """

    tz = timezone.utc
    tz_label = "UTC"

    if timezone_name:
        try:
            tz = ZoneInfo(timezone_name)
            tz_label = timezone_name
        except Exception as exc:  # pragma: no cover - defensive path
            raise ValueError(f"Unknown timezone: {timezone_name}") from exc

    now = datetime.now(tz)
    return {"timezone": tz_label, "iso_time": now.isoformat()}


app = StreamableHTTPServer(mcp).app
