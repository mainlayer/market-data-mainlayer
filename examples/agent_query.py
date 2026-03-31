"""
Autonomous agent example — pay and query market data with Mainlayer.

This script simulates an AI trading agent that:
1. Discovers available data by calling /catalog (free)
2. Pays for access via Mainlayer POST /pay
3. Fetches the data it needs
4. Makes a simple trading decision

Run:
    MAINLAYER_API_KEY=ml_... AGENT_WALLET=<wallet> python examples/agent_query.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

import httpx

# --- Configuration -----------------------------------------------------------

API_BASE = os.getenv("MARKET_API_BASE", "http://localhost:8000")
MAINLAYER_BASE = os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.fr")
MAINLAYER_API_KEY = os.getenv("MAINLAYER_API_KEY", "")
AGENT_WALLET = os.getenv("AGENT_WALLET", "")

SYMBOLS_TO_WATCH = ["BTC", "ETH", "SOL"]


# --- Mainlayer payment helper ------------------------------------------------

async def pay_for_resource(client: httpx.AsyncClient, resource_id: str) -> bool:
    """
    Instruct Mainlayer to execute a payment from the agent's wallet
    to the data provider for the given resource.
    """
    if not MAINLAYER_API_KEY or not AGENT_WALLET:
        print("  WARN: MAINLAYER_API_KEY or AGENT_WALLET not set — skipping payment")
        return False

    resp = await client.post(
        f"{MAINLAYER_BASE}/pay",
        headers={"Authorization": f"Bearer {MAINLAYER_API_KEY}"},
        json={"resource_id": resource_id, "payer_wallet": AGENT_WALLET},
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Paid. tx={data.get('transaction_id', 'n/a')} amount={data.get('amount_usdc', '?')} USDC")
        return True
    else:
        print(f"  Payment failed ({resp.status_code}): {resp.text}")
        return False


# --- Market data helpers -----------------------------------------------------

async def fetch_catalog(client: httpx.AsyncClient) -> dict:
    resp = await client.get(f"{API_BASE}/catalog")
    resp.raise_for_status()
    return resp.json()


async def fetch_prices(client: httpx.AsyncClient, symbols: list[str], resource_id: str) -> dict | None:
    """Attempt to fetch prices; pay if 402, then retry once."""
    params = {"symbols": ",".join(symbols), "wallet": AGENT_WALLET}
    resp = await client.get(f"{API_BASE}/prices", params=params)

    if resp.status_code == 402:
        print("  [402] Payment required — paying via Mainlayer...")
        paid = await pay_for_resource(client, resource_id)
        if not paid:
            return None
        # Retry after payment
        resp = await client.get(f"{API_BASE}/prices", params=params)

    if resp.status_code == 200:
        return resp.json()

    print(f"  ERROR fetching prices: {resp.status_code} {resp.text}")
    return None


async def fetch_historical(
    client: httpx.AsyncClient,
    symbol: str,
    resource_id: str,
    from_date: str = "2024-01-01",
    to_date: str = "2024-06-30",
    interval: str = "1d",
) -> dict | None:
    """Attempt to fetch historical data; pay if 402, then retry once."""
    params = {
        "from": from_date,
        "to": to_date,
        "interval": interval,
        "wallet": AGENT_WALLET,
    }
    resp = await client.get(f"{API_BASE}/historical/{symbol}", params=params)

    if resp.status_code == 402:
        print("  [402] Payment required for historical data — paying via Mainlayer...")
        paid = await pay_for_resource(client, resource_id)
        if not paid:
            return None
        resp = await client.get(f"{API_BASE}/historical/{symbol}", params=params)

    if resp.status_code == 200:
        return resp.json()

    print(f"  ERROR fetching historical data: {resp.status_code} {resp.text}")
    return None


# --- Naive trading logic -----------------------------------------------------

def simple_momentum_signal(bars: list[dict]) -> str:
    """
    A trivially simple momentum signal:
    - If the last 7 closes are above the 30-bar SMA → BUY
    - If the last 7 closes are below the 30-bar SMA → SELL
    - Otherwise → HOLD
    """
    if len(bars) < 30:
        return "HOLD (insufficient data)"

    closes = [b["close"] for b in bars]
    sma30 = sum(closes[-30:]) / 30
    recent = closes[-7:]

    if all(c > sma30 for c in recent):
        return "BUY (price above 30-bar SMA for 7 consecutive bars)"
    elif all(c < sma30 for c in recent):
        return "SELL (price below 30-bar SMA for 7 consecutive bars)"
    return "HOLD"


# --- Main agent loop ---------------------------------------------------------

async def run_agent() -> None:
    print("=" * 60)
    print("  Market Data Agent — powered by Mainlayer")
    print(f"  Wallet: {AGENT_WALLET or '(not set)'}")
    print(f"  API: {API_BASE}")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Discover what's available (free)
        print("Step 1: Fetching data catalog (free)...")
        try:
            catalog = await fetch_catalog(client)
        except Exception as exc:
            print(f"  Could not reach API at {API_BASE}: {exc}")
            sys.exit(1)

        endpoints = {ep["endpoint"]: ep for ep in catalog.get("endpoints", [])}
        prices_resource_id = ""
        historical_resource_id = ""

        # Extract resource IDs from catalog (if the server embeds them)
        for ep in catalog.get("endpoints", []):
            if "/prices" in ep["endpoint"] and "{" not in ep["endpoint"]:
                prices_resource_id = ep.get("resource_id", "")
            if "/historical" in ep["endpoint"]:
                historical_resource_id = ep.get("resource_id", "")

        # Fall back to env vars
        prices_resource_id = prices_resource_id or os.getenv("RESOURCE_ID_PRICES", "")
        historical_resource_id = historical_resource_id or os.getenv("RESOURCE_ID_HISTORICAL", "")

        print(f"  Available symbols: {len(catalog.get('available_symbols', []))}")
        print(f"  Endpoints: {len(catalog.get('endpoints', []))}")
        print()

        # Step 2: Fetch current prices
        print(f"Step 2: Fetching current prices for {SYMBOLS_TO_WATCH}...")
        prices_data = await fetch_prices(client, SYMBOLS_TO_WATCH, prices_resource_id)

        if prices_data:
            print(f"  Retrieved {prices_data['count']} prices:")
            for quote in prices_data.get("prices", []):
                sign = "+" if quote["change_24h"] >= 0 else ""
                print(
                    f"    {quote['symbol']:6s}  ${quote['price']:>12,.2f}  "
                    f"24h: {sign}{quote['change_24h']:.2f}%"
                )
        print()

        # Step 3: Fetch historical data for BTC and generate a signal
        print("Step 3: Fetching 6-month historical OHLCV for BTC (daily bars)...")
        hist = await fetch_historical(
            client,
            "BTC",
            historical_resource_id,
            from_date="2024-01-01",
            to_date="2024-06-30",
            interval="1d",
        )

        if hist:
            bars = hist.get("bars", [])
            print(f"  Received {len(bars)} daily bars ({hist['from_date']} → {hist['to_date']})")
            if bars:
                latest = bars[-1]
                print(
                    f"  Latest bar — O:{latest['open']}  H:{latest['high']}  "
                    f"L:{latest['low']}  C:{latest['close']}  V:{latest['volume']:,.0f}"
                )

            signal = simple_momentum_signal(bars)
            print(f"\n  Trading signal for BTC: {signal}")
        print()

        print("Agent run complete.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_agent())
