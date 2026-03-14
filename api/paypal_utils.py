"""PayPal Checkout Orders v2 API integration for Idea Reality paid reports.

Uses httpx (already a project dependency) — no PayPal SDK needed.

Env vars required:
  PAYPAL_CLIENT_ID     — Client ID from PayPal Developer dashboard
  PAYPAL_CLIENT_SECRET — Client Secret from PayPal Developer dashboard
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

PAYPAL_API = "https://api-m.paypal.com"

# Module-level token cache: {"token": str, "expires_at": float}
_token_cache: dict[str, object] = {}


def _get_client_id() -> str | None:
    """Return PAYPAL_CLIENT_ID or None if not configured."""
    return (os.environ.get("PAYPAL_CLIENT_ID") or "").strip() or None


def _get_client_secret() -> str | None:
    """Return PAYPAL_CLIENT_SECRET or None if not configured."""
    return (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip() or None


async def get_access_token() -> str:
    """Obtain a PayPal OAuth2 access token, cached until expiry.

    POST https://api-m.paypal.com/v1/oauth2/token with Basic auth.

    Returns the access token string.
    Raises ValueError if PayPal credentials are not configured.
    Raises httpx.HTTPStatusError on API failures.
    """
    # Return cached token if still valid (with 60s buffer)
    cached_token = _token_cache.get("token")
    expires_at = _token_cache.get("expires_at")
    if cached_token and isinstance(expires_at, (int, float)) and time.time() < expires_at - 60:
        return str(cached_token)

    client_id = _get_client_id()
    client_secret = _get_client_secret()
    if not client_id or not client_secret:
        raise ValueError("PayPal is not configured (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{PAYPAL_API}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    logger.info("[PAYPAL] Access token obtained, expires_in=%s", data.get("expires_in"))
    return data["access_token"]


async def create_order(
    idea_text: str,
    idea_hash: str,
    depth: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a PayPal checkout order.

    POST https://api-m.paypal.com/v2/checkout/orders

    Returns {"order_id": str, "approve_url": str}.
    Raises httpx.HTTPStatusError on API failures.
    """
    token = await get_access_token()

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": idea_hash,
                "custom_id": idea_hash,
                "description": "Idea Reality Full Report",
                "amount": {
                    "currency_code": "USD",
                    "value": "9.99",
                },
            }
        ],
        "application_context": {
            "brand_name": "Mnemox Idea Reality",
            "return_url": success_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{PAYPAL_API}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    order_id = data["id"]
    approve_url = next(
        (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"),
        None,
    )
    logger.info("[PAYPAL] Order created: %s, approve_url: %s", order_id, approve_url)
    return {"order_id": order_id, "approve_url": approve_url}


async def capture_order(order_id: str) -> dict:
    """Capture payment for an approved PayPal order.

    POST https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture

    Returns {"status": str, "custom_id": str, "payer_email": str}.
    Raises httpx.HTTPStatusError on API failures.
    """
    token = await get_access_token()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{PAYPAL_API}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    status = data.get("status", "UNKNOWN")
    custom_id = None
    payer_email = None

    try:
        custom_id = data["purchase_units"][0]["payments"]["captures"][0]["custom_id"]
    except (KeyError, IndexError):
        logger.warning("[PAYPAL] Could not extract custom_id from capture response")

    try:
        payer_email = data["payer"]["email_address"]
    except (KeyError,):
        logger.warning("[PAYPAL] Could not extract payer_email from capture response")

    logger.info("[PAYPAL] Order %s captured: status=%s, custom_id=%s", order_id, status, custom_id)
    return {"status": status, "custom_id": custom_id, "payer_email": payer_email}


async def get_order(order_id: str) -> dict:
    """Retrieve a PayPal order by ID.

    GET https://api-m.paypal.com/v2/checkout/orders/{order_id}

    Returns the full order response dict.
    Raises httpx.HTTPStatusError on API failures.
    """
    token = await get_access_token()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{PAYPAL_API}/v2/checkout/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        resp.raise_for_status()

    return resp.json()
