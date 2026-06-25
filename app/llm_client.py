from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.config import settings
from app.logger import logger
from app.schemas import TriageRequest, TriageResult


TRIAGE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {"type": "string", "enum": ["billing", "support", "complaint", "other"]},
        "draft_reply": {
            "type": "string",
            "description": "1-6 short, polite support sentences. Do not invent facts.",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "escalate": {"type": "boolean"},
    },
    "required": ["category", "draft_reply", "confidence", "escalate"],
}

SYSTEM_PROMPT = """
Ты — ассистент службы поддержки.
Твоя задача: классифицировать обращение клиента и написать черновик ответа.

Категории:
- billing — вопросы оплаты, счетов, возвратов, списаний, заказов, доступа после оплаты, оплаты без получения услуги.
- support — технические проблемы: ошибка сайта, баг, вход в аккаунт, неработающая функция, если проблема НЕ связана с оплатой.
- complaint — жалоба, сильное недовольство, претензия, угроза плохого отзыва, юридический тон, конфликтная ситуация.
- other — всё, что не подходит под остальные категории.

Приоритет категорий:
1. Если есть жалоба, претензия, угроза, сильное недовольство — выбирай complaint.
2. Если в тексте есть оплата, счет, возврат, деньги, заказ, списание или доступ не открылся после оплаты — выбирай billing.
3. Если проблема техническая и не связана с оплатой — выбирай support.
4. Если данных недостаточно — выбирай other, confidence=low, escalate=true.

Правила:
1. Отвечай строго по входному тексту. Не выдумывай факты, суммы, сроки, статусы заказов или обещания.
2. category должен быть одним из: billing, support, complaint, other.
3. confidence должен быть одним из: high, medium, low.
4. Если данных мало, текст неоднозначный, есть риск конфликта или нужна проверка человеком — ставь confidence=low и escalate=true.
5. Если confidence=low, escalate всегда должен быть true.
6. Если обращение похоже на жалобу, угрозу отзыва, юридическую претензию или сильное недовольство — ставь escalate=true.
7. draft_reply должен быть вежливым черновиком ответа на языке обращения, 1–6 предложений.
8. Верни только JSON по схеме. Без Markdown и без пояснений.
""".strip()


class LLMFormatError(Exception):
    """Raised when the model response does not match the expected schema."""


def fallback_result() -> TriageResult:
    return TriageResult(
        category="other",
        draft_reply="Ваше обращение передано оператору. Специалист проверит детали и ответит вам в ближайшее время.",
        confidence="low",
        escalate=True,
    )


def _fake_llm_result(request: TriageRequest) -> TriageResult:
    """Deterministic local demo mode for tests and video without paid API calls."""
    text = request.text.lower()

    billing_words = ("оплат", "счет", "счёт", "возврат", "деньг", "invoice", "payment", "refund")
    complaint_words = ("жалоб", "ужас", "недоволен", "претензи", "обман", "complaint", "angry", "terrible")
    support_words = ("не работает", "ошибка", "доступ", "помогите", "support", "error", "bug", "login")

    if any(word in text for word in complaint_words):
        return TriageResult(
            category="complaint",
            draft_reply="Здравствуйте! Нам жаль, что вы столкнулись с такой ситуацией. Мы передадим обращение специалисту, чтобы он проверил детали и помог решить вопрос.",
            confidence="high",
            escalate=True,
        )
    if any(word in text for word in billing_words):
        return TriageResult(
            category="billing",
            draft_reply="Здравствуйте! Спасибо за обращение. Мы проверим информацию по оплате и передадим вопрос специалисту, если потребуется уточнение.",
            confidence="high",
            escalate=False,
        )
    if any(word in text for word in support_words):
        return TriageResult(
            category="support",
            draft_reply="Здравствуйте! Спасибо за сообщение. Мы проверим техническую проблему и подскажем дальнейшие шаги для решения.",
            confidence="medium",
            escalate=False,
        )

    return TriageResult(
        category="other",
        draft_reply="Здравствуйте! Спасибо за обращение. Мы изучим ваш вопрос и вернемся с ответом после проверки деталей.",
        confidence="medium",
        escalate=False,
    )


def triage_with_llm(request: TriageRequest) -> TriageResult:
    if settings.llm_fake_mode:
        logger.info("LLM fake mode is enabled")
        return _fake_llm_result(request)

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)

    user_prompt = json.dumps(
        {
            "text": request.text,
            "channel": request.channel,
            "client_id": request.client_id,
        },
        ensure_ascii=False,
    )

    logger.info("Calling OpenAI model=%s", settings.openai_model)

    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "triage_result",
                "strict": True,
                "schema": TRIAGE_JSON_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content
    if not content:
        raise LLMFormatError("Model returned empty content")

    try:
        raw_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMFormatError(f"Model returned invalid JSON: {exc}") from exc

    try:
        result = TriageResult.model_validate(raw_data)
    except ValidationError as exc:
        raise LLMFormatError(f"Model JSON does not match API contract: {exc}") from exc

    logger.info(
        "OpenAI result validated: category=%s confidence=%s escalate=%s",
        result.category,
        result.confidence,
        result.escalate,
    )
    return result
