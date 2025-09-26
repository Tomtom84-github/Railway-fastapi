# main.py
"""FastMCP time server with timezone and city fallback support."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastmcp import FastMCP

__all__ = ["app", "mcp"]

mcp = FastMCP("time-mcp-server")

# --- Simple city → IANA timezone mapping (extend as needed) ---
# Keys are normalized with .casefold(); you can add more cities or synonyms.
CITY_TO_TZ: Dict[str, str] = {
    # Deutschland / DACH
    "berlin": "Europe/Berlin",
    "münchen": "Europe/Berlin",
    "munich": "Europe/Berlin",
    "hamburg": "Europe/Berlin",
    "köln": "Europe/Berlin",
    "cologne": "Europe/Berlin",
    "frankfurt": "Europe/Berlin",
    "stuttgart": "Europe/Berlin",
    "leipzig": "Europe/Berlin",
    "dresden": "Europe/Berlin",
    "zürich": "Europe/Zurich",
    "zurich": "Europe/Zurich",
    "wien": "Europe/Vienna",
    "vienna": "Europe/Vienna",

    # Europa
    "madrid": "Europe/Madrid",
    "barcelona": "Europe/Madrid",
    "paris": "Europe/Paris",
    "london": "Europe/London",
    "dublin": "Europe/Dublin",
    "lisbon": "Europe/Lisbon",
    "roma": "Europe/Rome",
    "rome": "Europe/Rome",
    "milano": "Europe/Rome",
    "milan": "Europe/Rome",
    "prague": "Europe/Prague",
    "praha": "Europe/Prague",
    "budapest": "Europe/Budapest",
    "warsaw": "Europe/Warsaw",
    "moscow": "Europe/Moscow",
    "moskau": "Europe/Moscow",
    "st. petersburg": "Europe/Moscow",
    "istanbul": "Europe/Istanbul",
    "athens": "Europe/Athens",
    "oslo": "Europe/Oslo",
    "stockholm": "Europe/Stockholm",
    "helsinki": "Europe/Helsinki",

    # Nordamerika
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "toronto": "America/Toronto",
    "mexico city": "America/Mexico_City",

    # Südamerika
    "são paulo": "America/Sao_Paulo",
    "sao paulo": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "santiago": "America/Santiago",
    "bogotá": "America/Bogota",
    "bogota": "America/Bogota",
    "lima": "America/Lima",

    # Asien
    "tokyo": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "kolkata": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",

    # Ozeanien / Afrika
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "nairobi": "Africa/Nairobi",
}


def _normalize_key(s: str) -> str:
    """Normalize city/tz input for dictionary lookups."""
    return s.strip().replace("_", " ").replace("-", " ").casefold()


def _resolve_timezone(
    timezone_name: Optional[str] = None,
    city: Optional[str] = None,
) -> ZoneInfo:
    """
    Resolve a ZoneInfo from either an explicit IANA timezone or a city name.
    Fallbacks to UTC on failure.
    """
    # Priority 1: explicit timezone_name
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            pass  # fall through to city or UTC

    # Priority 2: city mapping
    if city:
        key = _normalize_key(city)
        # direct mapping
        if key in CITY_TO_TZ:
            try:
                return ZoneInfo(CITY_TO_TZ[key])
            except ZoneInfoNotFoundError:
                pass
        # soft: try removing dots (e.g., "st. petersburg")
        soft_key = key.replace(".", "")
        if soft_key in CITY_TO_TZ:
            try:
                return ZoneInfo(CITY_TO_TZ[soft_key])
            except ZoneInfoNotFoundError:
                pass

    # Fallback: UTC
    return ZoneInfo("UTC")


@mcp.tool(
    description=(
        "Gibt die aktuelle Zeit zurück. "
        "Ohne Parameter in UTC. "
        "Optional per IANA-Zeitzone (z. B. 'Europe/Madrid') "
        "oder per Städtenamen (z. B. 'Madrid')."
    )
)
def current_time(
    timezone_name: str | None = None,
    city: str | None = None,
    as_utc: bool = False,
) -> str:
    """
    Return the current time as an ISO-8601 string.

    Args:
        timezone_name: Optional IANA timezone (e.g., 'Europe/Moscow').
        city: Optional city name (e.g., 'Moscow'). Common mappings included.
        as_utc: If True, forces UTC regardless of other params.

    Examples:
        current_time() -> '2025-09-26T11:20:47+00:00'
        current_time(timezone_name='Europe/Madrid')
        current_time(city='Madrid')
        current_time(city='Moskau')  # German synonym
    """
    if as_utc:
        return datetime.now(timezone.utc).isoformat()

    tz = _resolve_timezone(timezone_name=timezone_name, city=city)
    return datetime.now(tz).isoformat()


# The ASGI app Render/Railway/etc. can serve via Uvicorn/Hypercorn.
app = mcp.http_app()


def create_app() -> object:
    """Return the ASGI app for ASGI servers such as Uvicorn."""
    return app


if __name__ == "__main__":
    # Run the HTTP transport directly for local testing.
    mcp.run(transport="http", host="0.0.0.0", port=8000)
