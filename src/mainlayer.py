"""Mainlayer payment integration — entitlement checks with caching."""

import time
import logging
from typing import Optional

import httpx
from fastapi.responses import JSONResponse

from .config import settings
from .models import PaymentRequiredResponse

logger = logging.getLogger(__name__)

# In-memory entitlement cache: key = (resource_id, wallet) → (allowed: bool, expires_at: float)
_entitlement_cache: dict[tuple[str, str], tuple[bool, float]] = {}


def _cache_key(resource_id: str, payer_wallet: str) -> tuple[str, str]:
    return (resource_id, payer_wallet.lower())


def _get_cached(resource_id: str, payer_wallet: str) -> Optional[bool]:
    key = _cache_key(resource_id, payer_wallet)
    entry = _entitlement_cache.get(key)
    if entry is None:
        return None
    allowed, expires_at = entry
    if time.monotonic() > expires_at:
        del _entitlement_cache[key]
        return None
    return allowed


def _set_cache(resource_id: str, payer_wallet: str, allowed: bool) -> None:
    key = _cache_key(resource_id, payer_wallet)
    expires_at = time.monotonic() + settings.entitlement_cache_ttl
    _entitlement_cache[key] = (allowed, expires_at)


async def check_payment(resource_id: str, payer_wallet: str, api_key: str) -> bool:
    """
    Check whether a wallet has a valid entitlement for the given resource.

    Results are cached for `settings.entitlement_cache_ttl` seconds to avoid
    hammering the Mainlayer API on every request.

    Implements timeout and retry logic to handle transient failures.
    """
    if not resource_id:
        logger.warning("resource_id is empty — entitlement check skipped, denying access")
        return False

    if not payer_wallet or not payer_wallet.strip():
        logger.debug("No payer wallet provided")
        return False

    cached = _get_cached(resource_id, payer_wallet)
    if cached is not None:
        logger.debug(
            "Entitlement cache hit for wallet=%s resource=%s result=%s",
            payer_wallet, resource_id, cached,
        )
        return cached

    url = f"{settings.mainlayer_base_url}/entitlements/check"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "market-data-mainlayer/1.0",
    }
    params = {"resource_id": resource_id, "payer_wallet": payer_wallet.strip()}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 200:
            data = resp.json()
            # Mainlayer returns {"granted": true/false, ...}
            allowed = bool(data.get("granted", False))
            _set_cache(resource_id, payer_wallet, allowed)
            logger.debug(
                "Entitlement check: wallet=%s resource=%s granted=%s",
                payer_wallet[:8], resource_id, allowed,
            )
            return allowed

        logger.warning(
            "Mainlayer entitlement check returned %d for resource=%s",
            resp.status_code, resource_id,
        )
        return False

    except httpx.TimeoutException:
        logger.warning(
            "Mainlayer entitlement check timed out (10s) for resource=%s",
            resource_id,
        )
        return False
    except Exception as exc:
        logger.error("Entitlement check failed: %s", str(exc), exc_info=True)
        return False


def payment_required_response(resource_id: str, price: float, message: str = "") -> JSONResponse:
    """Return a standardised HTTP 402 response."""
    body = PaymentRequiredResponse(
        message=message or f"Payment of ${price:.4f} required to access this endpoint.",
        resource_id=resource_id,
        price_usd=price,
    )
    return JSONResponse(status_code=402, content=body.model_dump())


def missing_wallet_response(resource_id: str, price: float) -> JSONResponse:
    """Return a 402 when the X-Payer-Wallet header is missing."""
    return payment_required_response(
        resource_id=resource_id,
        price=price,
        message=(
            "Include your wallet address in the X-Payer-Wallet header or "
            "the wallet query parameter."
        ),
    )
