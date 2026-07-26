from hotel_brain_mcp_server import mcp
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        uvicorn_config={"loop": "asyncio"},
    )
