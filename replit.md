# Villa Aigea Hotel Brain MCP Server

A Python remote MCP server for Villa Aigea, a boutique luxury hotel on the Greek island of Evia. Exposes hotel data via 8 read-only MCP tools over Streamable HTTP transport.

## Run & Operate

- `cd mcp-server && python3 server.py` — start the MCP server (port 8000 by default, or `$PORT`)
- Managed workflow: `artifacts/api-server: Villa Aigea MCP Server`

## Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/` | GET | Health string: "Villa Aigea Hotel Brain MCP Server is running" |
| `/health` | GET | JSON health check `{"status": "ok", ...}` |
| `/mcp/` | POST | MCP Streamable HTTP transport (session-based) |

## MCP Tools

- `get_hotel_information` — hotel description, facilities, awards, policies
- `search_available_rooms(check_in, check_out, adults, children)` — availability search with pricing
- `get_room_details(room_id)` — full room spec + live readiness status
- `get_price_quote(room_id, check_in, check_out)` — nightly rate, taxes, cancellation policy
- `get_daily_briefing` — arrivals, departures, in-house guests, VIP notes
- `check_room_readiness` — full housekeeping board for all 8 rooms
- `find_upsell_opportunities` — guest-matched spa/dining/experience suggestions
- `get_vip_arrivals` — VIP tiers (Platinum/Gold/Silver) with prep checklists

## Stack

- Python 3.13, FastMCP 3.4.4, uvicorn, Starlette
- Transport: Streamable HTTP (`/mcp/`)
- No database — demo data in `mcp-server/hotel_data.py`
- No authentication required (demo mode)

## Where things live

- `mcp-server/server.py` — FastMCP server, tools, custom HTTP routes
- `mcp-server/hotel_data.py` — all demo hotel data (rooms, reservations, upsells, readiness)
- `artifacts/api-server/.replit-artifact/artifact.toml` — deployment configuration

## Deployment

- Target: `autoscale`
- Run command: `sh -c "cd ../../mcp-server && python3 server.py"`
- Health check: `GET /health`
- PORT env var injected automatically by Replit

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- The artifact service CWD is `artifacts/api-server/`, so paths to `mcp-server/` use `../../mcp-server/`.
- The MCP endpoint requires a session handshake (initialize) before `tools/list` or tool calls — a bare POST without `Mcp-Session-Id` correctly returns "Missing session ID".
- Demo data is fixed; all tools reflect a snapshot date of 2025-07-26.
