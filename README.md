# AI Triage Service — MVP сервиса обработки обращений

Портфолио-проект: API-сервис для первичной обработки клиентских обращений.

Сервис принимает обращение, классифицирует его через LLM, формирует черновик ответа, определяет необходимость эскалации и сохраняет историю обработки в SQLite.

## Что реализовано

- `POST /triage` — основной endpoint обработки обращений.
- Валидация входного JSON:
  - `text`: обязательный текст 1–2000 символов;
  - `channel`: `email`, `form` или `chat`;
  - `client_id`: обязательный идентификатор клиента.
- LLM-обработка через OpenAI API.
- Структурированный JSON-ответ:
  - `category`: `billing`, `support`, `complaint`, `other`;
  - `draft_reply`: черновик ответа 1–6 предложений;
  - `confidence`: `high`, `medium`, `low`;
  - `escalate`: `true` / `false`.
- SQLite-журнал `tickets`.
- Лимитирование запросов на `client_id`.
- Fallback-сценарий: если LLM недоступна или вернула некорректный формат, обращение передается оператору.
- Guardrail Layer: дополнительная проверка JSON-ответа модели через Pydantic.
- Логирование ключевых этапов обработки.
- Docker / docker-compose.

> Примечание: в исходном описании сдачи встречается `POST /lead`, но в основном контракте задания указан `POST /triage`. В проекте реализован корректный endpoint `POST /triage`.

---

## Архитектура

```text
Client / Postman / curl
        |
        v
FastAPI POST /triage
        |
        v
Input validation + rate limit by client_id
        |
        v
LLM Client -> OpenAI API
        |
        v
Guardrail Layer -> strict JSON validation
        |
        v
SQLite tickets + logs
        |
        v
JSON response to client
```

При ошибке LLM:

```text
LLM error / invalid JSON / missing API key
        |
        v
Fallback response:
category=other
confidence=low
escalate=true
draft_reply="Ваше обращение передано оператору..."
        |
        v
Save ticket with error field
```

---

## Быстрый запуск за 5–10 минут

### 1. Клонировать репозиторий

```bash
git clone <your-repository-url>
cd ai-triage-service
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
```

Активация на Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Активация на macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Создать `.env`

```bash
cp .env.example .env
```

Для быстрой локальной демонстрации без платного API-ключа включите:

```env
LLM_FAKE_MODE=true
```

Для реальной LLM-обработки укажите ключ:

```env
OPENAI_API_KEY=sk-your-real-key
LLM_FAKE_MODE=false
```

Важно: реальный `.env` не должен попадать в GitHub.

### 5. Запустить сервис

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "service": "AI Triage Service",
  "environment": "local"
}
```

---

## Пример запроса к POST /triage

```bash
curl -X POST "http://127.0.0.1:8000/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Здравствуйте, я оплатил заказ, но доступ к курсу не открылся.",
    "channel": "email",
    "client_id": "client_001"
  }'
```

Пример ответа:

```json
{
  "category": "billing",
  "draft_reply": "Здравствуйте! Спасибо за обращение. Мы проверим информацию по оплате и передадим вопрос специалисту, если потребуется уточнение.",
  "confidence": "high",
  "escalate": false
}
```

---

## Где смотреть SQLite

База создается автоматически:

```text
data/tickets.db
```

Посмотреть последние записи можно командой:

```bash
python scripts/query_tickets.py
```

Или напрямую через SQLite:

```bash
sqlite3 data/tickets.db "SELECT id, created_at, client_id, channel, category, confidence, escalate, error FROM tickets ORDER BY id DESC LIMIT 10;"
```

Структура таблицы `tickets`:

```text
id
created_at
client_id
channel
text
category
confidence
escalate
draft_reply
error
```

---

## Где смотреть логи

Логи пишутся в файл:

```text
logs/app.log
```

Пример просмотра:

```bash
tail -n 50 logs/app.log
```

В Windows PowerShell:

```powershell
Get-Content logs/app.log -Tail 50
```

---

## Демо-команды

Запустить несколько демо-запросов и вывести последние записи из SQLite:

```bash
bash scripts/demo_requests.sh
```

Проверить лимитирование:

```bash
bash scripts/check_rate_limit.sh
```

По умолчанию лимит задается в `.env`:

```env
REQUESTS_PER_MINUTE=10
```

---

## Docker-запуск

### 1. Подготовить `.env`

```bash
cp .env.example .env
```

Для локального демо можно поставить:

```env
LLM_FAKE_MODE=true
```

### 2. Собрать и запустить

```bash
docker compose up --build
```

Сервис будет доступен:

```text
http://127.0.0.1:8000
```

Остановка:

```bash
docker compose down
```

---

## Переменные окружения

| Переменная | Назначение | Пример |
|---|---|---|
| `OPENAI_API_KEY` | ключ OpenAI API | `sk-...` |
| `OPENAI_MODEL` | модель LLM | `gpt-4.1-mini` |
| `OPENAI_TEMPERATURE` | температура модели | `0.2` |
| `LLM_FAKE_MODE` | локальный демо-режим без API | `true` / `false` |
| `REQUESTS_PER_MINUTE` | лимит запросов на client_id | `10` |
| `DB_PATH` | путь к SQLite | `data/tickets.db` |
| `LOG_FILE` | путь к лог-файлу | `logs/app.log` |

---

## Контракт API

### POST /triage

Вход:

```json
{
  "text": "string, 1..2000 symbols",
  "channel": "email | form | chat",
  "client_id": "string"
}
```

Выход:

```json
{
  "category": "billing | support | complaint | other",
  "draft_reply": "string, 1-6 sentences",
  "confidence": "high | medium | low",
  "escalate": true
}
```

Ошибки:

- `422` — некорректный входной JSON;
- `429` — превышен лимит запросов по `client_id`;
- при ошибке LLM сервис возвращает `200` с безопасной эскалацией и сохраняет ошибку в SQLite.

---

## Guardrail Layer

Фича проекта: сервис не доверяет ответу LLM напрямую.

После ответа модели выполняется проверка:

- результат должен быть валидным JSON;
- поля должны соответствовать контракту;
- запрещены лишние поля;
- `category` и `confidence` должны быть только из разрешенных значений;
- `draft_reply` должен содержать 1–6 предложений;
- если `confidence=low`, то `escalate` автоматически становится `true`.

Если проверка не пройдена, включается fallback.

---

## Тесты

Запуск:

```bash
pytest -q
```

Что проверяется:

- успешная обработка обращения;
- запись в SQLite;
- валидация обязательного поля `text`;
- лимитирование по `client_id`;
- безопасный fallback-ответ.

---

## Что показать в демо-видео 2–3 минуты

1. Открыть проект и `.env` без реального ключа.
2. Показать `LLM_FAKE_MODE=true` для локальной демонстрации.
3. Запустить `uvicorn app.main:app --reload`.
4. Отправить POST-запрос на `/triage` через curl/Postman.
5. Показать JSON-ответ.
6. Открыть SQLite через `python scripts/query_tickets.py`.
7. Показать `logs/app.log`.
8. Коротко объяснить fallback и guardrail.

Подробный сценарий: `DEMO_VIDEO_SCRIPT.md`.

---

## Что улучшить в v2

- заменить in-memory rate limiter на Redis;
- добавить RAG / базу знаний компании;
- добавить админку для просмотра tickets;
- добавить экспорт в CSV;
- добавить интеграции с email, формой сайта и чатом;
- добавить метрики Prometheus/Grafana;
- добавить авторизацию для API;
- добавить асинхронную очередь обработки.
