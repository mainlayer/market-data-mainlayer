"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    mainlayer_api_key: str = os.getenv("MAINLAYER_API_KEY", "")
    mainlayer_base_url: str = os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.fr")

    # Resource IDs registered on Mainlayer (populated after running scripts/setup.py)
    resource_id_prices: str = os.getenv("RESOURCE_ID_PRICES", "")
    resource_id_historical: str = os.getenv("RESOURCE_ID_HISTORICAL", "")
    resource_id_summary: str = os.getenv("RESOURCE_ID_SUMMARY", "")
    resource_id_quotes: str = os.getenv("RESOURCE_ID_QUOTES", "")

    # Pricing (USD) — per query, no subscription required
    price_single_quote: float = 0.002   # /prices/{symbol}
    price_multi_quote: float = 0.002    # /prices (batch)
    price_historical: float = 0.005     # /history/{symbol}
    price_full_quote: float = 0.002     # /quotes/{symbol}
    price_market_summary: float = 0.002 # /market-summary

    # Cache TTL for entitlement checks (seconds)
    entitlement_cache_ttl: int = 60

    # App
    app_name: str = "Market Data Mainlayer"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
