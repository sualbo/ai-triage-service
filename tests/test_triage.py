from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Configure app before importing it.
TEST_DB_PATH = Path("/tmp/ai_triage_service_test.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["LLM_FAKE_MODE"] = "true"
os.environ["DB_PATH"] = str(TEST_DB_PATH)
os.environ["LOG_FILE"] = "/tmp/ai_triage_service_test.log"
os.environ["REQUESTS_PER_MINUTE"] = "2"

from fastapi.testclient import TestClient  # noqa: E402

from app.llm_client import fallback_result  # noqa: E402
from app.main import app  # noqa: E402


def test_triage_success_and_sqlite_audit() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={
                "text": "Здравствуйте, я оплатил заказ, но доступ к курсу не открылся.",
                "channel": "email",
                "client_id": "test_client_success",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "billing"
    assert data["confidence"] in {"high", "medium", "low"}
    assert isinstance(data["escalate"], bool)
    assert "X-Ticket-ID" in response.headers
    assert TEST_DB_PATH.exists()


def test_validation_error_for_missing_text() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={"channel": "form", "client_id": "test_client_validation"},
        )

    assert response.status_code == 422


def test_rate_limit_by_client_id() -> None:
    with TestClient(app) as client:
        payload = {"text": "Проверка лимита", "channel": "chat", "client_id": "test_client_limited"}
        first = client.post("/triage", json=payload)
        second = client.post("/triage", json=payload)
        third = client.post("/triage", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_fallback_result_is_safe_escalation() -> None:
    result = fallback_result()

    assert result.category == "other"
    assert result.confidence == "low"
    assert result.escalate is True
    assert "оператор" in result.draft_reply.lower()
