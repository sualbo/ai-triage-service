#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "1) Health check"
curl -s "${BASE_URL}/health" | python -m json.tool

echo "\n2) Billing request"
curl -s -X POST "${BASE_URL}/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Здравствуйте, я оплатил заказ, но доступ к курсу не открылся.",
    "channel": "email",
    "client_id": "client_001"
  }' | python -m json.tool

echo "\n3) Complaint request"
curl -s -X POST "${BASE_URL}/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Я очень недоволен поддержкой. Деньги списали, ответа нет уже три дня.",
    "channel": "chat",
    "client_id": "client_002"
  }' | python -m json.tool

echo "\n4) SQLite last records"
python scripts/query_tickets.py
