#!/usr/bin/env bash
# Integration smoke script: exercises admin login, plans, create customer, create subscription, cancel subscription, track event, fetch alerts.
# Requires backend running at http://localhost:8000 and ADMIN_PASSWORD and ADMIN_JWT_SECRET set in the environment used by the backend.
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-adminpass}
ADMIN_JWT_SECRET=${ADMIN_JWT_SECRET:-devsecret}

echo "1) Admin login"
TOKEN=$(curl -sS -X POST "$BASE/api/admin/login" -H 'Content-Type: application/json' -d "{\"password\": \"$ADMIN_PASSWORD\"}" | jq -r .access_token)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then echo "Failed to get token"; exit 2; fi
echo " token ok"

AUTH="Authorization: Bearer $TOKEN"

echo "2) List plans"
curl -sS -H "$AUTH" "$BASE/api/plans" | jq .

echo "3) Create customer"
CUST=$(curl -sS -X POST "$BASE/api/customers" -H 'Content-Type: application/json' -H "$AUTH" -d '{"email":"smoke@example.com"}' | jq -r .id)
if [ -z "$CUST" ] || [ "$CUST" = "null" ]; then echo "Failed create customer"; exit 2; fi
echo " customer: $CUST"

echo "4) Create subscription (50 cents)"
SUB=$(curl -sS -X POST "$BASE/api/subscriptions" -H 'Content-Type: application/json' -H "$AUTH" -d "{\"customer_stripe_id\": \"$CUST\", \"price_cents\": 500, \"currency\": \"usd\"}" | jq -r .id)
if [ -z "$SUB" ] || [ "$SUB" = "null" ]; then echo "Failed create subscription"; exit 2; fi
echo " subscription: $SUB"

echo "5) Cancel subscription"
curl -sS -X POST "$BASE/api/subscriptions/$SUB/cancel" -H "$AUTH" | jq .

echo "6) Track analytics event"
curl -sS -X POST "$BASE/api/analytics/track" -H 'Content-Type: application/json' -d '{"event":"page_view"}' | jq .

echo "7) Fetch alerts (may be empty)"
curl -sS -H "$AUTH" "$BASE/api/alerts" | jq .

echo "Integration smoke completed"
