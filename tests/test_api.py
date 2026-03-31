"""
Test suite for the Market Data Mainlayer API.

All Mainlayer payment checks are mocked so tests run without a real API key.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.main import app
from src.config import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def wallet_header():
    return {"X-Payer-Wallet": "test_wallet_abc123"}


@pytest.fixture(autouse=True)
def patch_entitlement_allowed(monkeypatch):
    """Default: all payment checks pass. Override in individual tests as needed."""
    monkeypatch.setattr(
        "src.main.check_payment",
        AsyncMock(return_value=True),
    )


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data


# ---------------------------------------------------------------------------
# /resources (free discovery endpoint)
# ---------------------------------------------------------------------------

class TestResources:
    def test_resources_returns_200(self, client):
        resp = client.get("/resources")
        assert resp.status_code == 200

    def test_resources_no_auth_required(self, client, monkeypatch):
        """Discovery endpoint must be free — no wallet needed."""
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/resources")
        assert resp.status_code == 200

    def test_resources_has_service_info(self, client):
        data = client.get("/resources").json()
        assert "service" in data
        assert "version" in data
        assert "payment_provider" in data

    def test_resources_lists_resources(self, client):
        data = client.get("/resources").json()
        assert "resources" in data
        assert len(data["resources"]) >= 4

    def test_resources_includes_prices_endpoint(self, client):
        data = client.get("/resources").json()
        endpoints = [r["endpoint"] for r in data["resources"]]
        assert "/prices/{symbol}" in endpoints

    def test_resources_includes_history_endpoint(self, client):
        data = client.get("/resources").json()
        endpoints = [r["endpoint"] for r in data["resources"]]
        assert "/history/{symbol}" in endpoints

    def test_resources_includes_quotes_endpoint(self, client):
        data = client.get("/resources").json()
        endpoints = [r["endpoint"] for r in data["resources"]]
        assert "/quotes/{symbol}" in endpoints

    def test_resources_has_available_symbols(self, client):
        data = client.get("/resources").json()
        assert "available_symbols" in data
        assert "BTC" in data["available_symbols"]
        assert "AAPL" in data["available_symbols"]

    def test_resources_price_usd_field(self, client):
        data = client.get("/resources").json()
        for resource in data["resources"]:
            assert "price_usd" in resource
            assert resource["price_usd"] > 0


# ---------------------------------------------------------------------------
# /prices/{symbol}
# ---------------------------------------------------------------------------

class TestSinglePrice:
    def test_price_valid_symbol(self, client, wallet_header):
        resp = client.get("/prices/BTC", headers=wallet_header)
        assert resp.status_code == 200

    def test_price_response_fields(self, client, wallet_header):
        data = client.get("/prices/BTC", headers=wallet_header).json()
        for field in ("symbol", "price", "change_24h", "change_24h_pct",
                      "volume_24h", "high_24h", "low_24h", "timestamp"):
            assert field in data, f"Missing field: {field}"

    def test_price_symbol_is_uppercased(self, client, wallet_header):
        data = client.get("/prices/btc", headers=wallet_header).json()
        assert data["symbol"] == "BTC"

    def test_price_positive_value(self, client, wallet_header):
        data = client.get("/prices/ETH", headers=wallet_header).json()
        assert data["price"] > 0

    def test_price_stock_symbol(self, client, wallet_header):
        resp = client.get("/prices/AAPL", headers=wallet_header)
        assert resp.status_code == 200

    def test_price_unknown_symbol_returns_404(self, client, wallet_header):
        resp = client.get("/prices/NOTREAL", headers=wallet_header)
        assert resp.status_code == 404

    def test_price_404_error_field(self, client, wallet_header):
        data = client.get("/prices/NOTREAL", headers=wallet_header).json()
        assert data["error"] == "not_found"

    def test_price_no_wallet_returns_402(self, client, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/prices/BTC")
        assert resp.status_code == 402

    def test_price_payment_denied_returns_402(self, client, wallet_header, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/prices/BTC", headers=wallet_header)
        assert resp.status_code == 402

    def test_price_402_has_resource_id(self, client, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        data = client.get("/prices/BTC", headers={"X-Payer-Wallet": "w"}).json()
        assert "resource_id" in data

    def test_price_high_above_price(self, client, wallet_header):
        data = client.get("/prices/BTC", headers=wallet_header).json()
        assert data["high_24h"] >= data["price"]

    def test_price_low_below_price(self, client, wallet_header):
        data = client.get("/prices/BTC", headers=wallet_header).json()
        assert data["low_24h"] <= data["price"]


# ---------------------------------------------------------------------------
# /prices (batch)
# ---------------------------------------------------------------------------

class TestBatchPrices:
    def test_batch_default_symbols(self, client, wallet_header):
        resp = client.get("/prices", headers=wallet_header)
        assert resp.status_code == 200

    def test_batch_multiple_symbols(self, client, wallet_header):
        resp = client.get("/prices?symbols=BTC,ETH,SOL", headers=wallet_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3

    def test_batch_filters_unknown_symbols(self, client, wallet_header):
        resp = client.get("/prices?symbols=BTC,NOTREAL,ETH", headers=wallet_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    def test_batch_wallet_query_param(self, client, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=True))
        resp = client.get("/prices?symbols=BTC&wallet=test_wallet")
        assert resp.status_code == 200

    def test_batch_no_wallet_returns_402(self, client, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/prices?symbols=BTC")
        assert resp.status_code == 402

    def test_batch_has_timestamp(self, client, wallet_header):
        data = client.get("/prices?symbols=BTC,ETH", headers=wallet_header).json()
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# /history/{symbol}
# ---------------------------------------------------------------------------

class TestHistory:
    def test_history_basic(self, client, wallet_header):
        resp = client.get(
            "/history/BTC?from=2024-01-01&to=2024-01-31",
            headers=wallet_header,
        )
        assert resp.status_code == 200

    def test_history_response_fields(self, client, wallet_header):
        data = client.get(
            "/history/ETH?from=2024-01-01&to=2024-01-07",
            headers=wallet_header,
        ).json()
        for field in ("symbol", "interval", "from_date", "to_date", "bars", "count"):
            assert field in data

    def test_history_bar_fields(self, client, wallet_header):
        data = client.get(
            "/history/BTC?from=2024-01-01&to=2024-01-07",
            headers=wallet_header,
        ).json()
        bar = data["bars"][0]
        for field in ("timestamp", "open", "high", "low", "close", "volume"):
            assert field in bar

    def test_history_interval_1h(self, client, wallet_header):
        resp = client.get(
            "/history/BTC?from=2024-01-01&to=2024-01-02&interval=1h",
            headers=wallet_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["interval"] == "1h"

    def test_history_invalid_interval_returns_400(self, client, wallet_header):
        resp = client.get(
            "/history/BTC?from=2024-01-01&to=2024-01-07&interval=5m",
            headers=wallet_header,
        )
        assert resp.status_code == 400

    def test_history_unknown_symbol_returns_404(self, client, wallet_header):
        resp = client.get(
            "/history/NOTREAL?from=2024-01-01&to=2024-01-07",
            headers=wallet_header,
        )
        assert resp.status_code == 404

    def test_history_no_wallet_returns_402(self, client, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/history/BTC?from=2024-01-01&to=2024-01-07")
        assert resp.status_code == 402

    def test_history_bar_ohlc_validity(self, client, wallet_header):
        data = client.get(
            "/history/BTC?from=2024-01-01&to=2024-01-31",
            headers=wallet_header,
        ).json()
        for bar in data["bars"]:
            assert bar["high"] >= bar["open"]
            assert bar["high"] >= bar["close"]
            assert bar["low"] <= bar["open"]
            assert bar["low"] <= bar["close"]
            assert bar["volume"] > 0

    def test_history_count_matches_bars_length(self, client, wallet_header):
        data = client.get(
            "/history/BTC?from=2024-01-01&to=2024-01-10",
            headers=wallet_header,
        ).json()
        assert data["count"] == len(data["bars"])


# ---------------------------------------------------------------------------
# /quotes/{symbol}
# ---------------------------------------------------------------------------

class TestQuotes:
    def test_quote_valid_symbol(self, client, wallet_header):
        resp = client.get("/quotes/BTC", headers=wallet_header)
        assert resp.status_code == 200

    def test_quote_response_fields(self, client, wallet_header):
        data = client.get("/quotes/BTC", headers=wallet_header).json()
        for field in (
            "symbol", "price", "bid", "ask", "spread", "spread_bps",
            "change_24h", "volume_24h", "vwap", "open_interest",
            "high_24h", "low_24h", "timestamp",
        ):
            assert field in data, f"Missing field: {field}"

    def test_quote_bid_below_ask(self, client, wallet_header):
        data = client.get("/quotes/ETH", headers=wallet_header).json()
        assert data["bid"] < data["ask"]

    def test_quote_spread_is_positive(self, client, wallet_header):
        data = client.get("/quotes/BTC", headers=wallet_header).json()
        assert data["spread"] > 0

    def test_quote_spread_bps_positive(self, client, wallet_header):
        data = client.get("/quotes/BTC", headers=wallet_header).json()
        assert data["spread_bps"] > 0

    def test_quote_vwap_is_positive(self, client, wallet_header):
        data = client.get("/quotes/AAPL", headers=wallet_header).json()
        assert data["vwap"] > 0

    def test_quote_stock_symbol(self, client, wallet_header):
        resp = client.get("/quotes/GOOGL", headers=wallet_header)
        assert resp.status_code == 200

    def test_quote_lowercase_symbol(self, client, wallet_header):
        data = client.get("/quotes/eth", headers=wallet_header).json()
        assert data["symbol"] == "ETH"

    def test_quote_unknown_symbol_returns_404(self, client, wallet_header):
        resp = client.get("/quotes/NOTREAL", headers=wallet_header)
        assert resp.status_code == 404

    def test_quote_no_wallet_returns_402(self, client, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/quotes/BTC")
        assert resp.status_code == 402

    def test_quote_payment_denied_returns_402(self, client, wallet_header, monkeypatch):
        monkeypatch.setattr("src.main.check_payment", AsyncMock(return_value=False))
        resp = client.get("/quotes/BTC", headers=wallet_header)
        assert resp.status_code == 402

    def test_quote_price_between_bid_and_ask(self, client, wallet_header):
        data = client.get("/quotes/BTC", headers=wallet_header).json()
        assert data["bid"] <= data["price"] <= data["ask"]


# ---------------------------------------------------------------------------
# Market data module unit tests
# ---------------------------------------------------------------------------

class TestMarketDataModule:
    def test_get_price_returns_dict(self):
        from src import market_data
        result = market_data.get_price("BTC")
        assert isinstance(result, dict)

    def test_get_price_unknown_returns_none(self):
        from src import market_data
        assert market_data.get_price("NOTREAL") is None

    def test_get_prices_filters_unknowns(self):
        from src import market_data
        results = market_data.get_prices(["BTC", "NOTREAL", "ETH"])
        assert len(results) == 2

    def test_get_quote_has_bid_ask(self):
        from src import market_data
        q = market_data.get_quote("ETH")
        assert q is not None
        assert "bid" in q and "ask" in q

    def test_get_historical_returns_bars(self):
        from src import market_data
        result = market_data.get_historical("BTC", "2024-01-01", "2024-01-07", "1d")
        assert result is not None
        assert len(result["bars"]) > 0

    def test_get_market_summary_has_dominance(self):
        from src import market_data
        summary = market_data.get_market_summary()
        assert "btc_dominance" in summary
        assert 0 < summary["btc_dominance"] < 100
