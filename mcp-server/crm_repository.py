"""Database adapter for the proposed hotel CRM migrations.
Only call from a trusted backend after verifying guest identity and confirmation.
Never expose this adapter directly as an unauthenticated MCP mutation tool.
"""
import os
from uuid import UUID
from datetime import date

async def mutate_reservation(*, operation_key: UUID, verified_guest_id: UUID,
                             action: str, booking_code: UUID | None = None,
                             room_id: str | None = None,
                             check_in: date | None = None, check_out: date | None = None,
                             adults: int | None = None, children: int | None = None,
                             version: int | None = None):
    import asyncpg
    dsn = os.environ.get("HOTEL_CRM_DATABASE_URL")
    if not dsn:
        raise RuntimeError("Hotel CRM database is not configured")
    if action not in ("create", "change", "cancel"):
        raise ValueError("Invalid reservation action")
    if action != "create" and (booking_code is None or version is None):
        raise ValueError("Booking code and version required")
    connection = await asyncpg.connect(dsn, timeout=10, command_timeout=20)
    try:
        async with connection.transaction():
            return await connection.fetchval(
                "SELECT hotel_crm.mutate_reservation($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
                operation_key, verified_guest_id, action, booking_code, room_id,
                check_in, check_out, adults, children, version,
            )
    finally:
        await connection.close()
