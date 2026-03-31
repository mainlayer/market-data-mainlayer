# Market Data Mainlayer

Real-time market data API with micropayment access — built on [Mainlayer](https://api.mainlayer.xyz), the payment infrastructure for AI agents.

AI agents pay **per query**, with no subscription and no monthly commitment. One API call = one payment = one result.

---

## What It Does

Provides real-time and historical price data for 30 major crypto and equity symbols — BTC, ETH, AAPL, NVDA, and more. Every endpoint is pay-per-call: your agent pays only for what it actually queries.

**Perfect for:**
- Trading agents that need live quotes without a subscription
- Backtesting pipelines that pull historical OHLCV on demand
- Portfolio agents that monitor prices at their own frequency
- Any AI workflow that needs market data without a billing contract

---

## Pricing

| Endpoint | What You Get | Price per Call |
|---|---|---|
| `GET /prices/{symbol}` | Current price + 24h stats | **$0.002** |
| `GET /prices` | Batch prices for up to 20 symbols | **$0.002** |
| `GET /quotes/{symbol}` | Full quote: bid, ask, spread, VWAP, open interest | **$0.002** |
| `GET /history/{symbol}` | OHLCV bars (1h / 4h / 1d / 1w) | **$0.005** |
| `GET /resources` | List all resources + prices | **Free** |
| `GET /health` | Health check | **Free** |

---

## Quick Start

### 1. Get a Mainlayer API key

Sign up at [api.mainlayer.xyz](https://api.mainlayer.xyz) to get your API key and a wallet address.

### 2. Clone and configure

```bash
git clone <repo-url>
cd market-data-mainlayer
cp .env.example .env
# Edit .env — add your MAINLAYER_API_KEY
```

### 3. Register resources on Mainlayer

```bash
pip install -r requirements.txt
python scripts/setup.py
# Copy the printed RESOURCE_ID_* values into .env
```

### 4. Start the API

```bash
uvicorn src.main:app --reload
# or
docker compose up
```

### 5. Discover what's available (free)

```bash
curl http://localhost:8000/resources
```

---

## How to Pay and Query

Agents follow a simple two-step flow for each query:

**Step 1 — Pay via Mainlayer:**

```bash
curl -X POST https://api.mainlayer.xyz/pay \
  -H "Authorization: Bearer $MAINLAYER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "<RESOURCE_ID_PRICES>", "payer_wallet": "<YOUR_WALLET>"}'
```

**Step 2 — Query the data:**

```bash
curl https://localhost:8000/prices/BTC \
  -H "X-Payer-Wallet: <YOUR_WALLET>"
```

The API checks with Mainlayer that your wallet has a valid entitlement, then returns the data.

---

## API Reference

### `GET /resources` — Free

Lists all available resources, their prices, and example calls. Call this first.

```json
{
  "service": "Market Data Mainlayer",
  "payment_provider": "Mainlayer",
  "available_symbols": ["AAPL", "AMD", "AMZN", "..."],
  "resources": [
    {
      "name": "Current Price",
      "endpoint": "/prices/{symbol}",
      "price_usd": 0.002,
      "example": "GET /prices/BTC  -H 'X-Payer-Wallet: <wallet>'"
    }
  ]
}
```

### `GET /prices/{symbol}` — $0.002

Current price and 24h stats for a single symbol.

```bash
curl http://localhost:8000/prices/BTC \
  -H "X-Payer-Wallet: your_wallet_here"
```

```json
{
  "symbol": "BTC",
  "price": 68420.50,
  "change_24h": 2.31,
  "change_24h_pct": 2.31,
  "volume_24h": 28000000000,
  "market_cap": 1346000000000,
  "high_24h": 69105.30,
  "low_24h": 67218.10,
  "timestamp": "2024-03-15T10:30:00Z"
}
```

### `GET /prices` — $0.002

Batch prices for up to 20 symbols in one call. One flat fee.

```bash
curl "http://localhost:8000/prices?symbols=BTC,ETH,SOL,AAPL&wallet=your_wallet"
```

### `GET /quotes/{symbol}` — $0.002

Full Level-1 quote with bid/ask spread, VWAP, and open interest.

```bash
curl http://localhost:8000/quotes/ETH \
  -H "X-Payer-Wallet: your_wallet_here"
```

```json
{
  "symbol": "ETH",
  "price": 3741.20,
  "bid": 3740.73,
  "ask": 3741.67,
  "spread": 0.94,
  "spread_bps": 2.5,
  "vwap": 3738.12,
  "open_interest": 7230000000,
  "volume_24h": 14500000000,
  "timestamp": "2024-03-15T10:30:00Z"
}
```

### `GET /history/{symbol}` — $0.005

Historical OHLCV bars. Supports `1h`, `4h`, `1d`, `1w` intervals.

```bash
curl "http://localhost:8000/history/ETH?from=2024-01-01&to=2024-03-31&interval=1d&wallet=your_wallet"
```

```json
{
  "symbol": "ETH",
  "interval": "1d",
  "from_date": "2024-01-01",
  "to_date": "2024-03-31",
  "count": 91,
  "bars": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "open": 2281.50,
      "high": 2320.80,
      "low": 2255.10,
      "close": 2310.40,
      "volume": 12300000000
    }
  ]
}
```

---

## Payment Responses

If a wallet is missing or the entitlement check fails, the API returns `HTTP 402`:

```json
{
  "error": "payment_required",
  "message": "Payment of $0.0020 required to access this endpoint.",
  "resource_id": "res_abc123",
  "price_usd": 0.002,
  "how_to_pay": "POST https://api.mainlayer.xyz/pay with {resource_id, payer_wallet}"
}
```

---

## Supported Symbols

**Crypto:** BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOGE, DOT, LINK, MATIC, UNI, LTC, ATOM, FIL, APT, ARB, OP, INJ, SUI

**Equities:** AAPL, MSFT, NVDA, GOOGL, AMZN, TSLA, META, AMD, NFLX, COIN

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MAINLAYER_API_KEY` | Yes | Your Mainlayer API key |
| `MAINLAYER_BASE_URL` | No | Defaults to `https://api.mainlayer.xyz` |
| `RESOURCE_ID_PRICES` | Yes | Resource ID for price endpoints |
| `RESOURCE_ID_HISTORICAL` | Yes | Resource ID for history endpoint |
| `RESOURCE_ID_QUOTES` | Yes | Resource ID for quotes endpoint |
| `DEBUG` | No | Set to `true` for verbose logging |

---

## Architecture

```
src/
  main.py          # FastAPI app — routes and payment gating
  mainlayer.py     # Mainlayer client + entitlement cache
  market_data.py   # Mock data generator (replace with real vendor)
  models.py        # Pydantic request/response models
  config.py        # Settings loaded from environment

scripts/
  setup.py         # Register resources on Mainlayer (run once)

examples/
  agent_query.py   # Full agent example: discover → pay → query
  curl_examples.sh # curl recipes for every endpoint

tests/
  test_api.py      # 60+ tests covering all endpoints
```

---

## Powered by Mainlayer

[Mainlayer](https://api.mainlayer.xyz) is payment infrastructure for AI agents — the same way Stripe powers payments for web apps, Mainlayer powers payments for autonomous agents. Agents pay for exactly what they use, with no subscriptions, no contracts, and no human in the loop.
