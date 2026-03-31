"""
Register market data resources on Mainlayer.

Run once before starting the API server:
    python scripts/setup.py

The script prints the resource IDs to add to your .env file.
"""

import asyncio
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

MAINLAYER_API_KEY = os.getenv("MAINLAYER_API_KEY", "")
MAINLAYER_BASE_URL = os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.fr")

RESOURCES = [
    {
        "env_key": "RESOURCE_ID_PRICES",
        "name": "Market Data — Current Prices",
        "description": (
            "Real-time spot prices, 24h stats, and volume for 30 major crypto and equity symbols. "
            "Suitable for trading agents that need live quotes."
        ),
        "price_usdc": 0.001,
        "endpoint_hint": "/prices",
    },
    {
        "env_key": "RESOURCE_ID_HISTORICAL",
        "name": "Market Data — Historical OHLCV",
        "description": (
            "OHLCV bars from 1h to 1w interval for any supported symbol. "
            "Suitable for backtesting, trend analysis, and ML feature engineering."
        ),
        "price_usdc": 0.005,
        "endpoint_hint": "/historical",
    },
    {
        "env_key": "RESOURCE_ID_SUMMARY",
        "name": "Market Data — Market Summary",
        "description": (
            "Aggregate market statistics: total market cap, 24h volume, "
            "BTC/ETH dominance, and top movers."
        ),
        "price_usdc": 0.001,
        "endpoint_hint": "/market-summary",
    },
]


async def register_resource(client: httpx.AsyncClient, resource: dict) -> str | None:
    headers = {
        "Authorization": f"Bearer {MAINLAYER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "name": resource["name"],
        "description": resource["description"],
        "price_usdc": resource["price_usdc"],
    }
    try:
        resp = await client.post(f"{MAINLAYER_BASE_URL}/resources", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        resource_id = data.get("id") or data.get("resource_id")
        return resource_id
    except httpx.HTTPStatusError as exc:
        print(f"  ERROR {exc.response.status_code}: {exc.response.text}")
        return None
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return None


async def main() -> None:
    if not MAINLAYER_API_KEY:
        print("ERROR: MAINLAYER_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    print(f"Registering resources on Mainlayer ({MAINLAYER_BASE_URL})...\n")

    env_lines: list[str] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for resource in RESOURCES:
            print(f"Registering: {resource['name']}")
            resource_id = await register_resource(client, resource)
            if resource_id:
                print(f"  OK  id={resource_id}")
                env_lines.append(f"{resource['env_key']}={resource_id}")
            else:
                print(f"  FAILED — check your API key and try again.")
            print()

    if env_lines:
        print("=" * 60)
        print("Add these lines to your .env file:")
        print("=" * 60)
        for line in env_lines:
            print(line)
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
