from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status

from app.config import settings
from app.database import init_db
from app.llm_client import fallback_result, triage_with_llm
from app.logger import logger
from app.rate_limiter import rate_limiter
from app.repository import save_ticket
from app.schemas import TicketRecord, TriageRequest, TriageResponse


def sanitize_error(exc: Exception) -> str:
    """Return safe error text for SQLite audit log without leaking provider details."""
    error_type = type(exc).__name__
    message = str(exc)

    sensitive_markers = (
        "api key",
        "openai_api_key",
        "invalid_api_key",
        "authentication",
        "authorization",
        "bearer",
        "token",
        "secret",
    )

    if any(marker in message.lower() for marker in sensitive_markers):
        return f"{error_type}: LLM provider authentication/configuration error"

    if len(message) > 300:
        message = message[:300] + "..."

    return f"{error_type}: {message}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("%s started in %s mode", settings.app_name, settings.environment)
    yield
    logger.info("%s stopped", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="MVP service for AI-based customer request triage with SQLite audit log.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@app.post("/triage", response_model=TriageResponse)
def triage(payload: TriageRequest, response: Response) -> TriageResponse:
    logger.info(
        "Incoming triage request: client_id=%s channel=%s text_len=%s",
        payload.client_id,
        payload.channel,
        len(payload.text),
    )

    decision = rate_limiter.check(payload.client_id)
    response.headers["X-RateLimit-Limit"] = str(settings.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)

    if not decision.allowed:
        response.headers["Retry-After"] = str(decision.retry_after_seconds)
        logger.warning("Rate limit exceeded: client_id=%s", payload.client_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests for this client_id. Try again later.",
                "retry_after_seconds": decision.retry_after_seconds,
            },
        )

    error_text: str | None = None
    try:
        result = triage_with_llm(payload)
    except Exception as exc:  # noqa: BLE001 - fallback must catch all LLM/service failures
        error_text = sanitize_error(exc)
        logger.exception("LLM processing failed. Fallback escalation is used.")
        result = fallback_result()

    ticket_id = save_ticket(
        TicketRecord(
            client_id=payload.client_id,
            channel=payload.channel,
            text=payload.text,
            category=result.category,
            confidence=result.confidence,
            escalate=result.escalate,
            draft_reply=result.draft_reply,
            error=error_text,
        )
    )
    response.headers["X-Ticket-ID"] = str(ticket_id)

    return TriageResponse(**result.model_dump())
