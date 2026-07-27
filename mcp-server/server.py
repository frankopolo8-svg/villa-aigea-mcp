"""
Villa Aigea Hotel Brain — FastMCP Remote Server
Streamable HTTP transport | Endpoint: /mcp/
"""
 import os
 import asyncio
 import httpx
 from datetime import datetime, date
from typing import Optional


import os
import asyncio
import httpx
from datetime import datetime, date
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from fastmcp import FastMCP

from hotel_data import (
    HOTEL_INFO,
    ROOM_TYPES,
    EXISTING_RESERVATIONS,
    UPSELL_CATALOG,
    ROOM_READINESS,
)

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from fastmcp import FastMCP

from hotel_data import (
    HOTEL_INFO,
    ROOM_TYPES,
    EXISTING_RESERVATIONS,
    UPSELL_CATALOG,
    ROOM_READINESS,
)

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from fastmcp import FastMCP

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
def search_available_rooms(
    check_in: str,
    check_out: str,
    adults: int,
    children: int,
) -> dict:
    """
    Search for rooms available for a given date range and occupancy.

    Args:
        check_in:  Arrival date in YYYY-MM-DD format.
        check_out: Departure date in YYYY-MM-DD format.
        adults:    Number of adults (>=1).
        children:  Number of children (>=0).

    Returns:
        Available room types with room_id, capacity, price per night,
        total price, and amenities.
    """
    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD.", "available_rooms": []}

    if co <= ci:
        return {"error": "check_out must be after check_in.", "available_rooms": []}

    nights = _nights_between(check_in, check_out)
    total_guests = adults + children

    blocked_room_ids: set[str] = set()
    for res in EXISTING_RESERVATIONS:
        if _dates_overlap(check_in, check_out, res["check_in"], res["check_out"]):
            blocked_room_ids.add(res["room_id"])

    available = []
    for room in ROOM_TYPES:
        if room["room_id"] in blocked_room_ids:
            continue
        if room["availability_status"] == "maintenance":
            continue
        if adults > room["max_adults"]:
            continue
        if children > room["max_children"]:
            continue
        if total_guests > room["max_occupancy"]:
            continue

        total_price = room["price_per_night"] * nights
        available.append({
            "room_id": room["room_id"],
            "room_type": room["type"],
            "category": room["category"],
            "floor": room["floor"],
            "size_sqm": room["size_sqm"],
            "bed_configuration": room["bed_configuration"],
            "view": room["view"],
            "max_adults": room["max_adults"],
            "max_children": room["max_children"],
            "max_occupancy": room["max_occupancy"],
            "price_per_night": room["price_per_night"],
            "currency": room["currency"],
            "nights": nights,
            "total_price": total_price,
            "amenities": room["amenities"],
            "description": room["description"],
        })

    return {
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "adults": adults,
        "children": children,
        "total_guests": total_guests,
        "available_rooms_count": len(available),
        "available_rooms": available,
    }
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
    """
    Calculate a detailed price quote for a specific room and date range.

    Args:
        room_id:   The room identifier (e.g. 'STE-SV-06').
        check_in:  Arrival date in YYYY-MM-DD format.
        check_out: Departure date in YYYY-MM-DD format.
    """
    room = _room_by_id(room_id)
    if not room:
        return {"error": f"Room '{room_id}' not found.", "valid_ids": [r["room_id"] for r in ROOM_TYPES]}

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    if co <= ci:
        return {"error": "check_out must be after check_in."}

    nights = _nights_between(check_in, check_out)
    subtotal = room["price_per_night"] * nights
    city_tax_per_night = 5.0
    city_tax_total = city_tax_per_night * nights

    is_conflicted = any(
        res["room_id"] == room_id
        and _dates_overlap(check_in, check_out, res["check_in"], res["check_out"])
        for res in EXISTING_RESERVATIONS
    )

    return {
        "room_id": room_id,
        "room_type": room["type"],
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "rate_per_night": room["price_per_night"],
        "currency": room["currency"],
        "room_subtotal": subtotal,
        "taxes_and_fees": {
            "greek_city_tax": {
                "amount_per_night": city_tax_per_night,
                "total": city_tax_total,
                "note": "Mandatory Greek government accommodation tax",
            }
        },
        "total_room_cost": subtotal + city_tax_total,
        "optional_additions": {
            "breakfast": {
                "price_per_person_per_night": 28.0,
                "note": "Available at Thalassa restaurant; add when booking",
            }
        },
        "payment_policy": "30% deposit at booking; balance due 14 days before arrival",
        "cancellation_policy": (
            "Free cancellation up to 14 days before check-in; "
            "50% charge 7–13 days before; non-refundable within 7 days"
        ),
        "availability_conflict": is_conflicted,
    }


@mcp.tool()
def get_daily_briefing() -> dict:
    """
    Generate a daily operational briefing for hotel staff.
    Includes today's arrivals, departures, in-house guests,
    room readiness summary, and key VIP notes.
    Relative to demo date 2025-07-26.
    """
    today_str = "2025-07-26"
    tomorrow_str = "2025-07-27"

    arrivals_today = [r for r in EXISTING_RESERVATIONS if r["check_in"] == today_str]
    departures_today = [r for r in EXISTING_RESERVATIONS if r["check_out"] == today_str]
    arrivals_tomorrow = [r for r in EXISTING_RESERVATIONS if r["check_in"] == tomorrow_str]
    in_house = [
        r for r in EXISTING_RESERVATIONS
        if r["check_in"] <= today_str < r["check_out"]
    ]

    rooms_ready = sum(1 for r in ROOM_READINESS if r["ready_for_checkin"])
    vip_in_house = [r for r in in_house if r.get("vip_level")]

    return {
        "briefing_date": today_str,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "arrivals_today": len(arrivals_today),
            "departures_today": len(departures_today),
            "in_house_guests": len(in_house),
            "arrivals_tomorrow": len(arrivals_tomorrow),
            "rooms_ready_for_checkin": rooms_ready,
            "rooms_not_ready": len(ROOM_READINESS) - rooms_ready,
            "vip_guests_in_house": len(vip_in_house),
        },
        "arrivals_today": arrivals_today,
        "departures_today": departures_today,
        "in_house_guests": in_house,
        "arrivals_tomorrow": arrivals_tomorrow,
        "room_readiness_snapshot": ROOM_READINESS,
        "key_notes": [
            "Rossi honeymoon couple arrive tomorrow (27 Jul) — Aigea Suite; confirm champagne and rose petal arrangement.",
            "Al-Rashid (SUP-SV-03) checked in today — DND light on; no alcohol in minibar confirmed.",
            "SUP-SV-04 remains offline due to bathroom retiling; expected back 28 Jul.",
            "Yamamoto Platinum arrival 29 Jul — gluten-free menu pre-ordered with Thalassa.",
        ],
    }


@mcp.tool()
def check_room_readiness() -> dict:
    """
    Return the current housekeeping and maintenance status of every room.
    Useful for front desk to identify which rooms are ready for early
    check-in or need follow-up.
    """
    ready = [r for r in ROOM_READINESS if r["ready_for_checkin"]]
    not_ready = [r for r in ROOM_READINESS if not r["ready_for_checkin"]]
    maintenance = [r for r in ROOM_READINESS if r["housekeeping_status"] == "maintenance"]

    return {
        "as_of": "2025-07-26T11:30:00Z",
        "total_rooms": len(ROOM_READINESS),
        "ready_count": len(ready),
        "not_ready_count": len(not_ready),
        "in_maintenance_count": len(maintenance),
        "rooms_ready": ready,
        "rooms_not_ready": not_ready,
        "maintenance_rooms": maintenance,
    }


@mcp.tool()
def find_upsell_opportunities() -> dict:
    """
    Identify upsell opportunities based on current in-house reservations
    and upcoming arrivals. Returns personalised upsell suggestions matched
    to guest profiles and special occasions.
    """
    today_str = "2025-07-26"
    suggestions = []

    for res in EXISTING_RESERVATIONS:
        if not (res["check_in"] <= today_str < res["check_out"]):
            try:
                ci = datetime.strptime(res["check_in"], "%Y-%m-%d")
                today = datetime.strptime(today_str, "%Y-%m-%d")
                if (ci - today).days > 3 or ci < today:
                    continue
            except ValueError:
                continue

        room = _room_by_id(res["room_id"])
        if not room:
            continue

        guest_suggestions = []
        if "honeymoon" in (res.get("special_requests") or "").lower():
            guest_suggestions.extend([
                UPSELL_CATALOG["spa"][1],
                UPSELL_CATALOG["dining"][0],
                UPSELL_CATALOG["room_enhancements"][0],
                UPSELL_CATALOG["experiences"][0],
            ])
        if room["category"] == "Villa":
            guest_suggestions.append(UPSELL_CATALOG["room_enhancements"][2])
        if not guest_suggestions:
            guest_suggestions.extend([
                UPSELL_CATALOG["spa"][0],
                UPSELL_CATALOG["dining"][1],
                UPSELL_CATALOG["experiences"][1],
                UPSELL_CATALOG["experiences"][2],
            ])

        suggestions.append({
            "reservation_id": res["reservation_id"],
            "guest_name": res["guest_name"],
            "room_id": res["room_id"],
            "room_type": room["type"],
            "vip_level": res.get("vip_level"),
            "check_in": res["check_in"],
            "check_out": res["check_out"],
            "special_requests": res.get("special_requests"),
            "upsell_suggestions": guest_suggestions,
        })

    return {
        "analysis_date": today_str,
        "total_opportunities": len(suggestions),
        "opportunities": suggestions,
        "upsell_catalog": UPSELL_CATALOG,
    }


@mcp.tool()
def get_vip_arrivals() -> dict:
    """
    Return a list of all VIP guests with upcoming arrivals or currently
    in-house, including their VIP tier, special requests, room assignment,
    and suggested pre-arrival preparations.
    """
    today_str = "2025-07-26"
    vip_reservations = [r for r in EXISTING_RESERVATIONS if r.get("vip_level")]
    vip_data = []

    for res in vip_reservations:
        room = _room_by_id(res["room_id"])
        if res["check_in"] <= today_str < res["check_out"]:
            status = "in_house"
        elif res["check_in"] > today_str:
            status = "upcoming"
        else:
            status = "departed"

        preps = []
        if res["vip_level"] == "Platinum":
            preps = [
                "Assign most senior available butler/host",
                "Personal welcome letter from General Manager",
                "Complimentary room upgrade if available",
                "Fruit basket, sparkling wine, and local delicacies on arrival",
                "Pre-stock minibar with stated preferences",
                "Coordinate all special dietary or accessibility needs 48 h in advance",
                "Offer complimentary spa treatment on day of arrival",
            ]
        elif res["vip_level"] == "Gold":
            preps = [
                "Welcome note from Front Office Manager",
                "Champagne and chocolates on arrival",
                "Priority late check-out (up to 14:00) if requested",
                "Ensure all special requests confirmed with relevant departments",
            ]
        elif res["vip_level"] == "Silver":
            preps = [
                "Welcome fruit basket on arrival",
                "Verify all special requests with relevant teams",
                "Flag to duty manager on arrival",
            ]

        vip_data.append({
            "reservation_id": res["reservation_id"],
            "guest_name": res["guest_name"],
            "vip_level": res["vip_level"],
            "room_id": res["room_id"],
            "room_type": room["type"] if room else "Unknown",
            "check_in": res["check_in"],
            "check_out": res["check_out"],
            "adults": res["adults"],
            "children": res["children"],
            "special_requests": res.get("special_requests"),
            "status": status,
            "recommended_preparations": preps,
        })

    order = {"in_house": 0, "upcoming": 1, "departed": 2}
    vip_data.sort(key=lambda x: (order.get(x["status"], 3), x["check_in"]))

    return {
        "briefing_date": today_str,
        "total_vip_guests": len(vip_data),
        "in_house": sum(1 for v in vip_data if v["status"] == "in_house"),
        "upcoming": sum(1 for v in vip_data if v["status"] == "upcoming"),
        "vip_guests": vip_data,
    }


# ---------------------------------------------------------------------------
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
