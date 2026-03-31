"""
Realistic mock market data.

Prices are plausible snapshots; in production replace the fetcher functions
with calls to a real data vendor (e.g. CoinGecko, Polygon.io, Alpha Vantage).
"""

import math
import random
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Static snapshot (base prices)
# ---------------------------------------------------------------------------

CRYPTO_BASE: dict[str, dict] = {
    "BTC":  {"price": 68_420.50, "market_cap": 1_346_000_000_000, "change_24h":  2.31},
    "ETH":  {"price":  3_741.20, "market_cap":   449_000_000_000, "change_24h":  1.87},
    "SOL":  {"price":    178.55, "market_cap":    82_000_000_000, "change_24h":  4.12},
    "BNB":  {"price":    592.30, "market_cap":    86_000_000_000, "change_24h": -0.54},
    "XRP":  {"price":      0.5834, "market_cap":  32_000_000_000, "change_24h":  0.92},
    "ADA":  {"price":      0.4612, "market_cap":  16_000_000_000, "change_24h": -1.23},
    "AVAX": {"price":     38.72, "market_cap":    16_000_000_000, "change_24h":  3.45},
    "DOGE": {"price":      0.1642, "market_cap":  23_000_000_000, "change_24h":  6.78},
    "DOT":  {"price":      8.91,  "market_cap":  11_500_000_000, "change_24h": -2.10},
    "LINK": {"price":     18.44,  "market_cap":  10_800_000_000, "change_24h":  1.55},
    "MATIC":{"price":      0.8821, "market_cap":  8_700_000_000, "change_24h":  2.33},
    "UNI":  {"price":     12.37,  "market_cap":   9_300_000_000, "change_24h": -0.88},
    "LTC":  {"price":     92.15,  "market_cap":   6_800_000_000, "change_24h":  0.41},
    "ATOM": {"price":     10.28,  "market_cap":   4_000_000_000, "change_24h":  2.97},
    "FIL":  {"price":      6.14,  "market_cap":   2_900_000_000, "change_24h": -3.21},
    "APT":  {"price":     11.63,  "market_cap":   5_200_000_000, "change_24h":  5.44},
    "ARB":  {"price":      1.87,  "market_cap":   4_700_000_000, "change_24h":  1.02},
    "OP":   {"price":      3.12,  "market_cap":   3_200_000_000, "change_24h":  0.74},
    "INJ":  {"price":     34.50,  "market_cap":   3_300_000_000, "change_24h":  7.11},
    "SUI":  {"price":      1.68,  "market_cap":   1_900_000_000, "change_24h":  3.89},
}

STOCK_BASE: dict[str, dict] = {
    "AAPL": {"price": 189.84, "market_cap": 2_940_000_000_000, "change_24h":  0.73},
    "MSFT": {"price": 421.55, "market_cap": 3_130_000_000_000, "change_24h":  0.45},
    "NVDA": {"price": 875.39, "market_cap": 2_160_000_000_000, "change_24h":  2.11},
    "GOOGL":{"price": 174.12, "market_cap": 2_170_000_000_000, "change_24h":  0.31},
    "AMZN": {"price": 190.40, "market_cap": 2_000_000_000_000, "change_24h":  1.02},
    "TSLA": {"price": 172.63, "market_cap":  549_000_000_000, "change_24h": -1.87},
    "META": {"price": 505.22, "market_cap": 1_280_000_000_000, "change_24h":  0.89},
    "AMD":  {"price": 175.30, "market_cap":  284_000_000_000, "change_24h":  3.34},
    "NFLX": {"price": 634.47, "market_cap":  278_000_000_000, "change_24h":  0.58},
    "COIN": {"price": 241.80, "market_cap":   60_000_000_000, "change_24h":  4.22},
}

ALL_SYMBOLS: set[str] = set(CRYPTO_BASE) | set(STOCK_BASE)
_BASE: dict[str, dict] = {**CRYPTO_BASE, **STOCK_BASE}

# Typical daily volumes (USD)
_VOLUME: dict[str, float] = {
    "BTC":  28_000_000_000,
    "ETH":  14_500_000_000,
    "SOL":   3_200_000_000,
    "BNB":   1_900_000_000,
    "XRP":   1_400_000_000,
    "ADA":     620_000_000,
    "AVAX":    850_000_000,
    "DOGE":    990_000_000,
    "DOT":     380_000_000,
    "LINK":    520_000_000,
    "MATIC":   440_000_000,
    "UNI":     310_000_000,
    "LTC":     480_000_000,
    "ATOM":    270_000_000,
    "FIL":     160_000_000,
    "APT":     390_000_000,
    "ARB":     420_000_000,
    "OP":      280_000_000,
    "INJ":     340_000_000,
    "SUI":     190_000_000,
    "AAPL":  62_000_000_000,
    "MSFT":  28_000_000_000,
    "NVDA":  45_000_000_000,
    "GOOGL": 22_000_000_000,
    "AMZN":  35_000_000_000,
    "TSLA":  38_000_000_000,
    "META":  22_000_000_000,
    "AMD":   12_000_000_000,
    "NFLX":   4_200_000_000,
    "COIN":   3_800_000_000,
}


def _jitter(value: float, pct: float = 0.002) -> float:
    """Add a tiny random jitter to simulate live price feed variance."""
    return value * (1 + random.uniform(-pct, pct))


def get_price(symbol: str) -> dict | None:
    symbol = symbol.upper()
    base = _BASE.get(symbol)
    if base is None:
        return None

    price = _jitter(base["price"])
    change_24h = base["change_24h"] + random.uniform(-0.3, 0.3)
    volume = _jitter(_VOLUME.get(symbol, 1_000_000), 0.05)
    high = price * (1 + abs(change_24h) / 100 + 0.005)
    low  = price * (1 - abs(change_24h) / 100 - 0.003)

    return {
        "symbol": symbol,
        "price": round(price, 6 if price < 1 else 2),
        "change_24h": round(change_24h, 4),
        "change_24h_pct": round(change_24h, 2),
        "volume_24h": round(volume, 0),
        "market_cap": base.get("market_cap"),
        "high_24h": round(high, 6 if price < 1 else 2),
        "low_24h": round(low, 6 if price < 1 else 2),
        "timestamp": datetime.now(timezone.utc),
    }


def get_prices(symbols: list[str]) -> list[dict]:
    results = []
    for sym in symbols:
        data = get_price(sym)
        if data:
            results.append(data)
    return results


def get_historical(
    symbol: str,
    from_date: str,
    to_date: str,
    interval: str = "1d",
) -> dict | None:
    """
    Generate synthetic OHLCV bars using a seeded random walk so that
    results are deterministic for a given symbol+date range.
    """
    symbol = symbol.upper()
    base = _BASE.get(symbol)
    if base is None:
        return None

    INTERVAL_DELTA = {
        "1h":  timedelta(hours=1),
        "4h":  timedelta(hours=4),
        "1d":  timedelta(days=1),
        "1w":  timedelta(weeks=1),
    }
    delta = INTERVAL_DELTA.get(interval, timedelta(days=1))

    try:
        start = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        end   = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    if end < start:
        return None

    # Seed random walk from symbol so results are consistent
    rng = random.Random(symbol)
    price = base["price"] * 0.85  # Start a bit below current for a rising look
    volatility = 0.015 if symbol in CRYPTO_BASE else 0.008

    bars = []
    current = start
    while current <= end:
        open_price = price
        returns = [rng.gauss(0.0003, volatility) for _ in range(4)]
        high_price  = open_price * (1 + max(0, max(returns)) + abs(rng.gauss(0, volatility / 2)))
        low_price   = open_price * (1 - max(0, -min(returns)) - abs(rng.gauss(0, volatility / 2)))
        close_price = open_price * (1 + rng.gauss(0.0003, volatility))
        close_price = max(close_price, low_price * 1.001)
        close_price = min(close_price, high_price * 0.999)

        volume = _VOLUME.get(symbol, 1_000_000) * rng.uniform(0.6, 1.4)
        # Scale volume to interval
        if interval == "1h":
            volume /= 24
        elif interval == "4h":
            volume /= 6
        elif interval == "1w":
            volume *= 7

        precision = 6 if open_price < 1 else 2
        bars.append({
            "timestamp": current,
            "open":   round(open_price, precision),
            "high":   round(high_price, precision),
            "low":    round(low_price, precision),
            "close":  round(close_price, precision),
            "volume": round(volume, 0),
        })

        price = close_price
        current += delta

    return {
        "symbol": symbol,
        "interval": interval,
        "from_date": from_date,
        "to_date": to_date,
        "bars": bars,
        "count": len(bars),
    }


def get_market_summary() -> dict:
    total_market_cap = sum(
        b.get("market_cap", 0) for b in _BASE.values() if b.get("market_cap")
    )
    total_volume = sum(_VOLUME.values())
    btc_cap = CRYPTO_BASE["BTC"]["market_cap"]
    eth_cap = CRYPTO_BASE["ETH"]["market_cap"]

    changes = [
        {"symbol": sym, "change": data["change_24h"]}
        for sym, data in _BASE.items()
    ]
    changes.sort(key=lambda x: x["change"], reverse=True)

    return {
        "total_market_cap": total_market_cap,
        "total_volume_24h": total_volume,
        "btc_dominance": round(btc_cap / total_market_cap * 100, 2),
        "eth_dominance": round(eth_cap / total_market_cap * 100, 2),
        "market_cap_change_24h": round(
            sum(d["change_24h"] for d in _BASE.values()) / len(_BASE), 2
        ),
        "active_symbols": len(_BASE),
        "top_gainers": changes[:5],
        "top_losers": changes[-5:][::-1],
        "timestamp": datetime.now(timezone.utc),
    }
