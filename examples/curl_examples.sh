#!/usr/bin/env bash
# curl examples for the Market Data Mainlayer API
# Set these before running:
#   export WALLET=<your_wallet_address>
#   export API=http://localhost:8000

API="${API:-http://localhost:8000}"
WALLET="${WALLET:-agent_wallet_abc123}"

echo "=== Market Data Mainlayer — curl examples ==="
echo "API: $API"
echo "Wallet: $WALLET"
echo ""

# ---------------------------------------------------------------------------
# 1. Catalog (free — no wallet needed)
# ---------------------------------------------------------------------------
echo "--- GET /catalog (free) ---"
curl -s "$API/catalog" | python3 -m json.tool
echo ""

# ---------------------------------------------------------------------------
# 2. Single price — no wallet (expect 402)
# ---------------------------------------------------------------------------
echo "--- GET /prices/BTC (no wallet → 402) ---"
curl -s -w "\nHTTP %{http_code}\n" "$API/prices/BTC"
echo ""

# ---------------------------------------------------------------------------
# 3. Single price — with wallet header
# ---------------------------------------------------------------------------
echo "--- GET /prices/BTC (with wallet) ---"
curl -s \
  -H "X-Payer-Wallet: $WALLET" \
  "$API/prices/BTC" | python3 -m json.tool
echo ""

# ---------------------------------------------------------------------------
# 4. Pay via Mainlayer (replace with your real resource_id)
# ---------------------------------------------------------------------------
RESOURCE_ID="${RESOURCE_ID_PRICES:-your_resource_id_here}"
echo "--- POST https://api.mainlayer.xyz/pay ---"
curl -s -X POST "https://api.mainlayer.xyz/pay" \
  -H "Authorization: Bearer $MAINLAYER_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"resource_id\": \"$RESOURCE_ID\", \"payer_wallet\": \"$WALLET\"}" \
  | python3 -m json.tool
echo ""

# ---------------------------------------------------------------------------
# 5. Multiple prices
# ---------------------------------------------------------------------------
echo "--- GET /prices?symbols=BTC,ETH,SOL ---"
curl -s \
  "$API/prices?symbols=BTC,ETH,SOL&wallet=$WALLET" \
  | python3 -m json.tool
echo ""

# ---------------------------------------------------------------------------
# 6. Historical data (daily OHLCV)
# ---------------------------------------------------------------------------
echo "--- GET /historical/ETH?from=2024-01-01&to=2024-03-31&interval=1d ---"
curl -s \
  "$API/historical/ETH?from=2024-01-01&to=2024-03-31&interval=1d&wallet=$WALLET" \
  | python3 -m json.tool | head -60
echo ""

# ---------------------------------------------------------------------------
# 7. Market summary
# ---------------------------------------------------------------------------
echo "--- GET /market-summary ---"
curl -s \
  "$API/market-summary?wallet=$WALLET" \
  | python3 -m json.tool
echo ""

# ---------------------------------------------------------------------------
# 8. Entitlement check (direct Mainlayer API)
# ---------------------------------------------------------------------------
echo "--- GET https://api.mainlayer.xyz/entitlements/check ---"
curl -s \
  -H "Authorization: Bearer $MAINLAYER_API_KEY" \
  "https://api.mainlayer.xyz/entitlements/check?resource_id=$RESOURCE_ID&payer_wallet=$WALLET" \
  | python3 -m json.tool
echo ""

echo "Done."
