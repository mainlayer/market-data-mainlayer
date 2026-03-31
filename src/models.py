"""Pydantic models for request/response types."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PriceResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_24h_pct: float
    volume_24h: float
    market_cap: Optional[float]
    high_24h: float
    low_24h: float
    timestamp: datetime


class MultiPriceResponse(BaseModel):
    prices: list[PriceResponse]
    count: int
    timestamp: datetime


class QuoteResponse(BaseModel):
    """Full Level-1 quote with bid/ask spread, VWAP, and open interest."""
    symbol: str
    price: float
    bid: float
    ask: float
    spread: float
    spread_bps: float
    change_24h: float
    change_24h_pct: float
    volume_24h: float
    open_interest: float
    vwap: float
    market_cap: Optional[float]
    high_24h: float
    low_24h: float
    timestamp: datetime


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoricalResponse(BaseModel):
    symbol: str
    interval: str
    from_date: str
    to_date: str
    bars: list[OHLCVBar]
    count: int


class MarketSummaryResponse(BaseModel):
    total_market_cap: float
    total_volume_24h: float
    btc_dominance: float
    eth_dominance: float
    market_cap_change_24h: float
    active_symbols: int
    top_gainers: list[dict]
    top_losers: list[dict]
    timestamp: datetime


class ResourceItem(BaseModel):
    """A single billable data resource available on this API."""
    resource_id: str
    name: str
    description: str
    endpoint: str
    method: str
    price_usd: float
    parameters: list[str]
    example: str


class ResourcesResponse(BaseModel):
    """Free discovery endpoint — lists all available resources and their prices."""
    service: str
    version: str
    payment_provider: str
    payment_docs: str
    available_symbols: list[str]
    resources: list[ResourceItem]


class CatalogItem(BaseModel):
    endpoint: str
    description: str
    price_usdc: float
    method: str
    parameters: list[str]
    example: str


class CatalogResponse(BaseModel):
    service: str
    version: str
    payment_provider: str
    available_symbols: list[str]
    endpoints: list[CatalogItem]


class PaymentRequiredResponse(BaseModel):
    error: str = "payment_required"
    message: str
    resource_id: str
    price_usd: float
    how_to_pay: str = "POST https://api.mainlayer.fr/pay with {resource_id, payer_wallet}"


class ErrorResponse(BaseModel):
    error: str
    message: str
