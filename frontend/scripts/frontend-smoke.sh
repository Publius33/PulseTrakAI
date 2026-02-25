#!/usr/bin/env bash
# Simple frontend smoke test: fetch the dev server root and check for app title
URL=${1:-http://localhost:5173/}
set -e
resp=$(curl -fsS "$URL" | head -n 200)
if echo "$resp" | grep -q "PulseTrakAI"; then
  echo "SMOKE OK: frontend responded and contains PulseTrakAI"
  exit 0
else
  echo "SMOKE FAIL: frontend did not contain PulseTrakAI"
  exit 2
fi
