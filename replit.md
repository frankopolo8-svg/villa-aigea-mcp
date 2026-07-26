# Hotel Brain MCP Server

A Python remote MCP server that exposes the HotelBrain decision engine as MCP tools over Streamable HTTP transport. Used to connect hotel operations data to AI agents (e.g. OpenAI Agent Builder).

## Run & Operate

- `cd mcp-server && python3 main.py` — start the MCP server (port from `$PORT`, default 8000)
- Managed workflow: `artifacts/api-server: Villa Aigea MCP Server`
- Demo data: `mcp-server/demo_data.json` — edit live, changes are picked up on every tool call

## Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/` | GET | Identity string: "Hotel Brain MCP Server is running" |
| `/health` | GET | JSON health check `{"status": "ok", ...}` |
| `/mcp` | POST | MCP Streamable HTTP transport (session-based) |

Note: `/mcp/` (trailing slash) redirects to `/mcp`.

## MCP Tools

All tools load `demo_data.json` fresh on every call so the file can be edited without restarting.

| Tool | Description |
|------|-------------|
| `get_daily_briefing(limit)` | Operational briefing with top-priority cases |
| `get_top_priorities(limit)` | All detected cases ranked by priority score |
| `check_room_readiness` | Rooms at risk of not being ready before guest arrival |
| `find_guest_recovery_cases` | Guests at risk of dissatisfaction (sentiment, delay, complaints) |
| `find_upsell_opportunities` | Personalised offers with purchase probability and expected value |
| `get_vip_arrivals` | VIP arrivals requiring preparation within 24 hours |
| `get_maintenance_issues` | Active maintenance issues ranked by severity and occupancy |
| `ask_hotel_brain(question)` | Natural-language query router (Greek and English) |

## Stack

- Python 3.13, FastMCP 3.4.4, uvicorn, Starlette
- Transport: Streamable HTTP (`/mcp`)
- No database — state loaded from `mcp-server/demo_data.json` on each request
- No authentication (demo mode)

## Where things live

- `mcp-server/main.py` — entry point
- `mcp-server/hotel_brain_mcp_server.py` — FastMCP server, tools, custom HTTP routes
- `mcp-server/hotel_ai_brain.py` — deterministic decision engine (`HotelBrain` class)
- `mcp-server/demo_data.json` — hotel state (guests, rooms, offers, policies)
- `artifacts/api-server/.replit-artifact/artifact.toml` — deployment configuration

## Architecture

The `HotelBrain` engine runs five scoring pipelines against the JSON state:
1. **Room readiness** — flags rooms not ready within the arrival window
2. **Guest recovery** — detects dissatisfaction from sentiment, response delay, complaint count
3. **Upsell** — matches offers to guest preferences/history with probability scoring
4. **VIP arrivals** — surfaces VIP guests arriving within 24 hours
5. **Maintenance** — ranks active issues by severity and whether the room is occupied

Each pipeline produces `Decision` objects scored on `urgency`, `impact`, `confidence` → `priority` (explainable weighted formula). All decisions are sorted by priority before being returned to tools.

## Deployment

- Target: `autoscale`
- Run command: `sh -c "cd ../../mcp-server && python3 main.py"`
- Health check: `GET /health`
- `PORT` env var injected automatically by Replit

## Gotchas

- The artifact service CWD is `artifacts/api-server/`, so `mcp-server/` is reached via `../../mcp-server/`.
- MCP clients must POST to `/mcp` (no trailing slash). `/mcp/` returns a 307 redirect.
- `demo_data.json` uses a hardcoded `"now"` timestamp — update it to get time-accurate urgency scores.
