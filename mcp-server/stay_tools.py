import httpx


async def _stay(action: str, payload: dict) -> dict:
    from fastmcp.server.dependencies import get_http_headers

    # Forward only the caller's dedicated booking credential to the fixed host.
    key = get_http_headers().get("x-concierge-key")
    if not key:
        return {"error": "booking_access_unavailable"}
    url = f"https://villa-aigea-booking-gem.lovable.app/api/public/stays/{action}"
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(url, json=payload, headers={"X-Concierge-Key": key})
        if not response.is_success:
            return {"error": "booking_host_error", "status_code": response.status_code}
        result = response.json()
        if not isinstance(result, dict) or not result:
            return {"error": "unverified_booking_result"}
        if action == "confirm" and result.get("confirmed") is not True:
            return {"error": "reservation_not_confirmed"}
        return result
    except (ValueError, httpx.RequestError):
        return {"error": "unverified_booking_result", "instruction": "Check stored status before retrying."}


async def confirm_stay(room_type: str, check_in: str, check_out: str, adults: int,
                       children: int, guest_name: str, guest_email: str, guest_phone: str,
                       guest_approved: bool, idempotency_key: str, extras: list[str],
                       request_reference: str | None = None) -> dict:
    """Confirm an available stay after explicit guest approval. Reuse the same key on retry."""
    if not guest_approved or not idempotency_key.strip():
        return {"error": "approval_and_operation_key_required"}
    payload = dict(room_type=room_type, check_in=check_in, check_out=check_out, adults=adults,
                   children=children, guest_name=guest_name, guest_email=guest_email,
                   guest_phone=guest_phone, guest_approved=True, idempotency_key=idempotency_key,
                   extras=extras)
    if request_reference:
        payload["request_reference"] = request_reference
    return await _stay("confirm", payload)


async def lookup_stay(reference: str, guest_email: str) -> dict:
    """Verify a stored reservation using the guest's reference and matching email."""
    return await _stay("lookup", dict(reference=reference, guest_email=guest_email))


async def change_stay_dates(reference: str, guest_email: str, check_in: str,
                            check_out: str, guest_approved: bool) -> dict:
    """Change a verified stay after explicit approval. Verify the resulting dates by lookup."""
    if not guest_approved:
        return {"error": "guest_approval_required"}
    return await _stay("change-dates", dict(reference=reference, guest_email=guest_email,
                                            check_in=check_in, check_out=check_out))


async def cancel_stay(reference: str, guest_email: str, guest_approved: bool) -> dict:
    """Cancel a verified stay after explicit approval. Verify the final status by lookup."""
    if not guest_approved:
        return {"error": "guest_approval_required"}
    return await _stay("cancel", dict(reference=reference, guest_email=guest_email, guest_approved=True))


def register_stay_tools(mcp):
    for tool in (confirm_stay, lookup_stay, change_stay_dates, cancel_stay):
        mcp.tool()(tool)
