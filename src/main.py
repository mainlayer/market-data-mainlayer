"""
Market Data Mainlayer — FastAPI application

AI agents pay per query to access real-time and historical market data.
Each query costs $0.002. Payment gating is handled by Mainlayer
(https://api.mainlayer.fr) — the payment infrastructure for autonomous agents.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse

from .config import settings
from .mainlayer import check_payment, payment_required_response, missing_wallet_response
from .models import (
    PriceResponse,
    MultiPriceResponse,
    QuoteResponse,
    HistoricalResponse,
    MarketSummaryResponse,
    ResourcesResponse,
    ResourceItem,
    ErrorResponse,
)
from . import market_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Market Data Mainlayer",
    description=(
        "Real-time market data API for AI agents. "
        "Each query is billed at $0.002 via Mainlayer — "
        "the payment infrastructure for autonomous agents. "
        "No subscription needed: agents pay only for what they query."
    ),
    version=settings.app_version,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wallet_from_request(request: Request, query_wallet: str | None = None) -> str | None:
    """Prefer the X-Payer-Wallet header; fall back to the wallet query parameter."""
    return request.headers.get("X-Payer-Wallet") or query_wallet


async def _gate(resource_id: str, price: float, wallet: str | None) -> JSONResponse | None:
    """
    Return a 402 JSONResponse if payment is missing or invalid, else None.
    Call this before returning data; if the result is not None, return it directly.
    """
    if not wallet:
        return missing_wallet_response(resource_id, price)

    has_access = await check_payment(
        resource_id=resource_id,
        payer_wallet=wallet,
        api_key=settings.mainlayer_api_key,
    )
    if not has_access:
        return payment_required_response(resource_id, price)

    return None


# ---------------------------------------------------------------------------
# Free / discovery endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health() -> dict:
    """Health check — always returns 200."""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get(
    "/resources",
    response_model=ResourcesResponse,
    tags=["discovery"],
    summary="List all available data resources with prices",
)
async def list_resources() -> ResourcesResponse:
    """
    Free endpoint — lists every billable resource, its price per query,
    and how to call it.

    AI agents should call this first to discover what data is available
    and what each query costs before committing a payment.
    """
    return ResourcesResponse(
        service=settings.app_name,
        version=settings.app_version,
        payment_provider="Mainlayer",
        payment_docs="https://api.mainlayer.fr/docs",
        available_symbols=sorted(market_data.ALL_SYMBOLS),
        resources=[
            ResourceItem(
                resource_id=settings.resource_id_prices,
                name="Current Price",
                description=(
                    "Current price, 24h change, volume, and market cap for a single symbol. "
                    "Ideal for quick price checks by trading agents."
                ),
                endpoint="/prices/{symbol}",
                method="GET",
                price_usd=settings.price_single_quote,
                parameters=["symbol (path)", "X-Payer-Wallet (header)"],
                example="GET /prices/BTC  -H 'X-Payer-Wallet: <wallet>'",
            ),
            ResourceItem(
                resource_id=settings.resource_id_prices,
                name="Batch Prices",
                description=(
                    "Current prices for up to 20 symbols in a single call. "
                    "One flat fee regardless of how many symbols you request."
                ),
                endpoint="/prices",
                method="GET",
                price_usd=settings.price_multi_quote,
                parameters=["symbols (query, comma-separated)", "wallet (query)"],
                example="GET /prices?symbols=BTC,ETH,SOL&wallet=<wallet>",
            ),
            ResourceItem(
                resource_id=settings.resource_id_historical,
                name="Price History",
                description=(
                    "OHLCV bars for a symbol over a date range. "
                    "Supports 1h, 4h, 1d, and 1w intervals. "
                    "Suitable for backtesting and ML feature engineering."
                ),
                endpoint="/history/{symbol}",
                method="GET",
                price_usd=settings.price_historical,
                parameters=[
                    "symbol (path)",
                    "from (query, YYYY-MM-DD)",
                    "to (query, YYYY-MM-DD)",
                    "interval (query: 1h|4h|1d|1w, default 1d)",
                    "wallet (query)",
                ],
                example=(
                    "GET /history/ETH?from=2024-01-01&to=2024-03-31"
                    "&interval=1d&wallet=<wallet>"
                ),
            ),
            ResourceItem(
                resource_id=settings.resource_id_quotes,
                name="Full Quote",
                description=(
                    "Full Level-1 quote with bid price, ask price, spread, "
                    "VWAP, open interest, and all standard 24h stats. "
                    "Richer than /prices — use when spread or VWAP matters."
                ),
                endpoint="/quotes/{symbol}",
                method="GET",
                price_usd=settings.price_full_quote,
                parameters=["symbol (path)", "X-Payer-Wallet (header)"],
                example="GET /quotes/AAPL  -H 'X-Payer-Wallet: <wallet>'",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Paid endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/prices/{symbol}",
    response_model=PriceResponse,
    tags=["market data"],
    responses={402: {"model": dict}, 404: {"model": ErrorResponse}},
    summary="Current price for a single symbol — $0.002 per call",
)
async def get_price(symbol: str, request: Request) -> PriceResponse | JSONResponse:
    """
    Returns the current price and 24h stats for the requested symbol.

    **Payment:** Include your wallet address in the `X-Payer-Wallet` header.
    Each successful call costs **$0.002** billed via Mainlayer.
    """
    wallet = _wallet_from_request(request)
    gate = await _gate(settings.resource_id_prices, settings.price_single_quote, wallet)
    if gate:
        return gate

    price_data = market_data.get_price(symbol.upper())
    if price_data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="not_found",
                message=(
                    f"Symbol '{symbol.upper()}' is not available. "
                    "Call /resources for the full list."
                ),
            ).model_dump(),
        )

    return PriceResponse(**price_data)


@app.get(
    "/prices",
    response_model=MultiPriceResponse,
    tags=["market data"],
    responses={402: {"model": dict}},
    summary="Current prices for multiple symbols — $0.002 per call",
)
async def get_prices(
    request: Request,
    symbols: Annotated[
        str,
        Query(description="Comma-separated list of symbols, e.g. BTC,ETH,SOL"),
    ] = "BTC,ETH",
    wallet: Annotated[str | None, Query(description="Your payer wallet address")] = None,
) -> MultiPriceResponse | JSONResponse:
    """
    Returns prices for up to 20 symbols in a single call.

    **Payment:** Pass your wallet via the `wallet` query parameter or
    `X-Payer-Wallet` header. Costs **$0.002** per call regardless of
    how many symbols are requested.
    """
    effective_wallet = _wallet_from_request(request, wallet)
    gate = await _gate(settings.resource_id_prices, settings.price_multi_quote, effective_wallet)
    if gate:
        return gate

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:20]
    prices = market_data.get_prices(symbol_list)

    return MultiPriceResponse(
        prices=[PriceResponse(**p) for p in prices],
        count=len(prices),
        timestamp=datetime.now(timezone.utc),
    )


@app.get(
    "/history/{symbol}",
    response_model=HistoricalResponse,
    tags=["market data"],
    responses={402: {"model": dict}, 400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Historical OHLCV data — $0.005 per call",
)
async def get_history(
    symbol: str,
    request: Request,
    from_date: Annotated[
        str, Query(alias="from", description="Start date (YYYY-MM-DD)")
    ] = "2024-01-01",
    to_date: Annotated[
        str, Query(alias="to", description="End date (YYYY-MM-DD)")
    ] = "2024-12-31",
    interval: Annotated[
        str, Query(description="Bar interval: 1h, 4h, 1d, 1w")
    ] = "1d",
    wallet: Annotated[str | None, Query(description="Your payer wallet address")] = None,
) -> HistoricalResponse | JSONResponse:
    """
    Returns OHLCV bars for a symbol between two dates.

    **Payment:** **$0.005** per call billed via Mainlayer. This endpoint costs
    more than spot-price endpoints because it returns large datasets suitable
    for backtesting and analysis.
    """
    effective_wallet = _wallet_from_request(request, wallet)
    gate = await _gate(settings.resource_id_historical, settings.price_historical, effective_wallet)
    if gate:
        return gate

    if interval not in {"1h", "4h", "1d", "1w"}:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="invalid_interval",
                message="interval must be one of: 1h, 4h, 1d, 1w",
            ).model_dump(),
        )

    result = market_data.get_historical(symbol.upper(), from_date, to_date, interval)
    if result is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="not_found",
                message=f"Symbol '{symbol.upper()}' not found or date range is invalid.",
            ).model_dump(),
        )

    return HistoricalResponse(**result)


@app.get(
    "/quotes/{symbol}",
    response_model=QuoteResponse,
    tags=["market data"],
    responses={402: {"model": dict}, 404: {"model": ErrorResponse}},
    summary="Full quote with bid/ask/volume — $0.002 per call",
)
async def get_quote(symbol: str, request: Request) -> QuoteResponse | JSONResponse:
    """
    Returns a full Level-1 quote for the requested symbol, including:
    - **bid** and **ask** prices
    - **spread** (absolute and in basis points)
    - **VWAP** (volume-weighted average price)
    - **open interest**
    - All standard 24h stats (change, high, low, volume, market cap)

    **Payment:** Include your wallet address in the `X-Payer-Wallet` header.
    Each successful call costs **$0.002** billed via Mainlayer.
    """
    wallet = _wallet_from_request(request)
    gate = await _gate(settings.resource_id_quotes, settings.price_full_quote, wallet)
    if gate:
        return gate

    quote_data = market_data.get_quote(symbol.upper())
    if quote_data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="not_found",
                message=(
                    f"Symbol '{symbol.upper()}' is not available. "
                    "Call /resources for the full list."
                ),
            ).model_dump(),
        )

    return QuoteResponse(**quote_data)
