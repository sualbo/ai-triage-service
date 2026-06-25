#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
CLIENT_ID="rate_limit_demo"

for i in {1..12}; do
  echo "Request #${i}"
  curl -i -s -X POST "${BASE_URL}/triage" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"Проверка лимита запросов номер ${i}\", \"channel\": \"chat\", \"client_id\": \"${CLIENT_ID}\"}" \
    | sed -n '1,12p'
  echo "---"
done
