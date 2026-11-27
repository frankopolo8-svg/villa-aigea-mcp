"""
Villa Aigea Hotel Brain — FastMCP Remote Server
Streamable HTTP transport | Endpoint: /mcp/
"""
import os
import asyncio
import httpx
from datetime import datetime, date
from typing import Optional
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from hotel_data import (

    HOTEL_INFO,
    ROOM_TYPES,
    EXISTING_RESERVATIONS,
    UPSELL_CATALOG,
    ROOM_READINESS,
)





# ---------------------------------------------------------------------------
# Server initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Villa Aigea Hotel Brain",
    instructions=(
        "You are the AI brain for Villa Aigea, a boutique luxury hotel on the Greek island "
        "of Evia. Use the available tools to answer guest enquiries, assist hotel staff, "
        "provide room availability and pricing, generate daily briefings, and surface upsell "
        "opportunities. Always be accurate and never invent data beyond what the tools return."
    ),
)

# ---------------------------------------------------------------------------
# Custom HTTP routes
# ---------------------------------------------------------------------------


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> PlainTextResponse:
    return PlainTextResponse("Villa Aigea Hotel Brain MCP Server is running")


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "Villa Aigea Hotel Brain MCP Server",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "transport": "streamable-http",
            "mcp_endpoint": "/mcp/",
        }
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _nights_between(check_in: str, check_out: str) -> int:
    fmt = "%Y-%m-%d"
    return (datetime.strptime(check_out, fmt) - datetime.strptime(check_in, fmt)).days


def _dates_overlap(a_in: str, a_out: str, b_in: str, b_out: str) -> bool:
    fmt = "%Y-%m-%d"
    a_start = datetime.strptime(a_in, fmt)
    a_end = datetime.strptime(a_out, fmt)
    b_start = datetime.strptime(b_in, fmt)
    b_end = datetime.strptime(b_out, fmt)
    return a_start < b_end and b_start < a_end


def _room_by_id(room_id: str) -> Optional[dict]:
    for room in ROOM_TYPES:
        if room["room_id"] == room_id:
            return room
    return None


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_hotel_information() -> dict:
    """
    Return comprehensive information about Villa Aigea hotel,
    including location, description, facilities, awards, sustainability
    credentials, and general policies.
    """
    return HOTEL_INFO


@mcp.tool()
async def search_available_rooms(
    check_in: str,
    check_out: str,
    adults: int,
    children: int,
) -> dict:
    """
    Search the fictional Villa Aigea demo inventory.

    The results come from the same availability endpoint used by
    the public demo website. No real PMS, reservation or payment
    system is accessed.
    """
    endpoint = (
        "https://villa-aigea-booking-gem.lovable.app/"
        "api/public/demo-search-availability"
    )

    payload = {
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "children": children,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            result = response.json()

        if not isinstance(result, dict):
            return {
                "error": "invalid_endpoint_response",
                "message": "The demo endpoint returned an invalid response.",
                "available_rooms": [],
            }

        return result

    except httpx.HTTPStatusError as exc:
        return {
            "error": "availability_endpoint_error",
            "status_code": exc.response.status_code,
            "message": "The demo availability endpoint returned an error.",
            "available_rooms": [],
        }

    except (httpx.RequestError, ValueError) as exc:
        return {
            "error": "availability_endpoint_unavailable",
            "message": str(exc),
            "available_rooms": [],
        }
@mcp.tool()
async def get_room_photos(room_type: str | None = None) -> dict:
    """Return official Villa Aigea room photo URLs."""

    endpoint = (
        "https://villa-aigea-booking-gem.lovable.app/"
        "api/public/demo-room-photos"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            result = response.json()

        rooms = result.get("rooms", [])

        if room_type:
            query = room_type.strip().lower()
            rooms = [
                room for room in rooms
                if query in room.get("room_type", "").lower()
            ]

        return {
            "rooms": rooms
        }

    except (httpx.HTTPError, ValueError) as exc:
        return {
            "error": "room_photos_unavailable",
            "message": str(exc),
            "rooms": []
        }
@mcp.tool()
async def get_hotel_marketing_catalog(
    category: str | None = None,
    interest: str | None = None,
    language: str | None = None,
    max_photos: int = 3,
) -> dict:
    """
    Return public Villa Aigea hotel facilities and experiences with
    their official photo URLs. Use for restaurant, dining, spa, massage,
    wellness, pool, beach, yacht, yoga and other guest experiences.
    """
    endpoint = (
        "https://villa-aigea-booking-gem.lovable.app/"
        "api/public/get-hotel-marketing-catalog"
    )

    safe_max_photos = max(1, min(max_photos, 3))
    params = {"max_photos": safe_max_photos}

    if category:
        params["category"] = category
    if interest:
        params["interest"] = interest
    if language:
        params["language"] = language

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            result = response.json()

            if not isinstance(result, dict):
                return {"error": "invalid_catalog_response", "items": []}

            items = result.get("items", [])
            if not isinstance(items, list):
                return {"error": "invalid_catalog_items", "items": []}
            output = []

            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("title", "Villa Aigea experience")
                item_category = item.get("category", "hotel")
                description = (
                    item.get("short_description")
                    or item.get("full_description")
                    or ""
                )
                primary_image_url = (
                    item.get("primary_image_url")
                    or item.get("cover_image_url")
                    or ""
                )
                public_page_url = item.get("public_page_url", "")
                call_to_action = item.get("call_to_action", "")

                entry = {
                    "title": title,
                    "category": item_category,
                    "description": description,
                    "primary_image_url": primary_image_url,
                    "public_page_url": public_page_url,
                    "call_to_action": call_to_action,
                    "photos": [],
                }

                photos = item.get("photos", [])
                if not isinstance(photos, list):
                    photos = []

                if not photos and primary_image_url:
                    photos = [{
                        "url": primary_image_url,
                        "caption": title,
                    }]

                seen_urls = set()

                for photo in photos[:safe_max_photos]:
                    if not isinstance(photo, dict):
                        continue

                    photo_url = photo.get("url") or photo.get("image_url")
                    caption = photo.get("caption") or title

                    if not photo_url or photo_url in seen_urls:
                        continue

                    seen_urls.add(photo_url)

                    entry["photos"].append({"url": photo_url, "caption": caption})

                output.append(entry)

            if not output:
                return {"items": [], "message": "No matching Villa Aigea experiences were found."}

            return {"items": output}

    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
        return {"error": "marketing_catalog_unavailable", "message": str(exc), "items": []}

@mcp.tool()
async def create_booking_request(
    room_type: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int,
    guest_name: str,
    guest_email: str,
    guest_phone: str,
) -> dict:
    """
    Create a demo booking request for hotel confirmation.

    This does not create a confirmed or paid reservation.
    """
    endpoint = (
        "https://villa-aigea-booking-gem.lovable.app/"
        "api/public/demo-create-booking-request"
    )

    payload = {
        "room_type": room_type,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "children": children,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "guest_phone": guest_phone,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            result = response.json()

        if not isinstance(result, dict):
            return {
                "status": "error",
                "message": "The booking endpoint returned an invalid response.",
            }

        return result

    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "status_code": exc.response.status_code,
            "message": "The booking request endpoint returned an error.",
        }

    except (httpx.RequestError, ValueError) as exc:
        return {
            "status": "error",
            "message": str(exc),
        }
        
@mcp.tool()
def get_room_details(room_id: str) -> dict:
    """
    Return full details for a specific room, including description,
    amenities, bed configuration, floor, size, view, and current
    availability status.

    Args:
        room_id: The room identifier (e.g. 'SUP-SV-03').
    """
    room = _room_by_id(room_id)
    if not room:
        return {
            "error": f"Room '{room_id}' not found.",
            "valid_ids": [r["room_id"] for r in ROOM_TYPES],
        }
    readiness = next((r for r in ROOM_READINESS if r["room_id"] == room_id), None)
    return {**room, "readiness": readiness}


@mcp.tool()
def get_price_quote(room_id: str, check_in: str, check_out: str) -> dict:
    """Return a verified quote when an authoritative pricing source is connected."""
    return {"status": "unavailable", "reason": "verified_pricing_source_not_connected", "room_id": room_id}


@mcp.tool()
def get_daily_briefing() -> dict:
    """Staff-only operational data requires an authenticated PMS integration."""
    return {"status": "unavailable", "reason": "authenticated_pms_required"}


@mcp.tool()
def check_room_readiness() -> dict:
    """Current housekeeping data requires an authenticated PMS integration."""
    return {"status": "unavailable", "reason": "authenticated_pms_required"}


@mcp.tool()
def find_upsell_opportunities() -> dict:
    """Use get_hotel_marketing_catalog for verified service options and let the AI personalize recommendations."""
    return {"status": "requires_catalog", "source_tool": "get_hotel_marketing_catalog"}


@mcp.tool()
def get_vip_arrivals() -> dict:
    """Private VIP records require an authenticated staff-only PMS integration."""
    return {"status": "unavailable", "reason": "authenticated_pms_required"}


@mcp.tool()
async def search_hotel_knowledge(query: str) -> dict:
    """Search the official Villa Aigea guest knowledge base."""

    vector_store_id = "vs_6a6a85b7e23c819198d871919f6c49d7"
    api_key = os.getenv("VILLA_AIGEA_KNOWLEDGE_API_KEY")

    if not api_key:
        return {
            "error": "knowledge_api_not_configured",
            "results": []
        }

    endpoint = (
        f"https://api.openai.com/v1/"
        f"vector_stores/{vector_store_id}/search"
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "query": query,
                    "max_num_results": 3
                }
            )
            response.raise_for_status()
            data = response.json()

        return {
            "results": data.get("data", [])
        }

    except (httpx.HTTPError, ValueError):
        return {
            "error": "knowledge_search_unavailable",
            "results": []
        }# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    asyncio.run(
        mcp.run_http_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=port,
            path="/mcp/",
            show_banner=True,
        )
    )
