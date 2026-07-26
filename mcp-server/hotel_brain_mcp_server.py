"""
Hotel Brain Remote MCP Server
Demo-only server exposing the HotelBrain decision engine as MCP tools.

Transport: Streamable HTTP
Expected public endpoint after deployment: https://YOUR-DOMAIN/mcp
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from hotel_ai_brain import DecisionType, HotelBrain, load_state


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.environ.get("HOTEL_DATA_FILE", BASE_DIR / "demo_data.json"))

mcp = FastMCP(
    name="Hotel Brain",
    instructions=(
        "Hotel operations decision engine. Use these tools as the source of truth "
        "for room readiness, guest recovery, VIP arrivals, maintenance, upselling, "
        "and the daily management briefing. Never invent hotel records."
    ),
)


# ---------------------------------------------------------------------------
# Custom HTTP routes (health check + root identity)
# ---------------------------------------------------------------------------


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> PlainTextResponse:
    return PlainTextResponse("Hotel Brain MCP Server is running")


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "Hotel Brain MCP Server",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transport": "http",
            "mcp_endpoint": "/mcp",
            "data_file": str(DATA_FILE),
        }
    )


# ---------------------------------------------------------------------------
# Brain helpers
# ---------------------------------------------------------------------------


def get_brain() -> HotelBrain:
    """Load fresh state for every call so demo_data.json can be edited live."""
    return HotelBrain(load_state(DATA_FILE))


def decisions_by_type(decision_type: DecisionType) -> list[dict[str, Any]]:
    return [
        decision.to_dict()
        for decision in get_brain().analyze()
        if decision.decision_type == decision_type
    ]


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_daily_briefing(limit: int = 5) -> dict[str, Any]:
    """
    Return the hotel's current operational briefing and highest-priority cases.

    Args:
        limit: Maximum number of top priorities to return, from 1 to 20.
    """
    safe_limit = max(1, min(limit, 20))
    return get_brain().briefing(limit=safe_limit)


@mcp.tool()
def get_top_priorities(limit: int = 10) -> dict[str, Any]:
    """
    Return all detected hotel cases ordered by priority score.

    Args:
        limit: Maximum number of cases to return, from 1 to 30.
    """
    safe_limit = max(1, min(limit, 30))
    decisions = get_brain().analyze()[:safe_limit]
    return {
        "count": len(decisions),
        "items": [decision.to_dict() for decision in decisions],
    }


@mcp.tool()
def check_room_readiness() -> dict[str, Any]:
    """Find rooms at risk of not being ready before the next guest arrives."""
    items = decisions_by_type(DecisionType.ROOM_READINESS)
    return {"count": len(items), "items": items}


@mcp.tool()
def find_guest_recovery_cases() -> dict[str, Any]:
    """
    Find guests at risk of dissatisfaction based on messages, response delay,
    complaint history, loyalty status, and departure timing.
    """
    items = decisions_by_type(DecisionType.GUEST_RECOVERY)
    return {"count": len(items), "items": items}


@mcp.tool()
def find_upsell_opportunities() -> dict[str, Any]:
    """
    Find personalized upsell opportunities and return estimated purchase
    probability, expected value, evidence, and a draft-action recommendation.
    """
    items = decisions_by_type(DecisionType.UPSELL)
    return {
        "count": len(items),
        "estimated_value_eur": round(
            sum(float(item.get("estimated_value_eur", 0)) for item in items), 2
        ),
        "items": items,
    }


@mcp.tool()
def get_vip_arrivals() -> dict[str, Any]:
    """Return VIP arrivals requiring preparation within the next 24 hours."""
    items = decisions_by_type(DecisionType.VIP_ARRIVAL)
    return {"count": len(items), "items": items}


@mcp.tool()
def get_maintenance_issues() -> dict[str, Any]:
    """Return active room maintenance issues ordered by operational priority."""
    items = decisions_by_type(DecisionType.MAINTENANCE)
    return {"count": len(items), "items": items}


@mcp.tool()
def ask_hotel_brain(question: str) -> dict[str, Any]:
    """
    Route a natural-language management question to the deterministic HotelBrain
    engine. Useful as a fallback when no specialized tool is an exact match.

    Args:
        question: The hotel-management question in Greek or English.
    """
    if not question or not question.strip():
        raise ValueError("question is required")
    return get_brain().answer(question.strip())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        uvicorn_config={"loop": "asyncio"},
    )
