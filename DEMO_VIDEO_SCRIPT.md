# Сценарий демо-видео 2–3 минуты

## Цель видео

Показать цепочку: запрос → ответ сервиса → запись в SQLite → логи.

## Подготовка перед записью

1. Открыть проект в VS Code.
2. Создать `.env` из `.env.example`.
3. Для демонстрации без API-ключа поставить:

```env
LLM_FAKE_MODE=true
```

4. Установить зависимости:

```bash
pip install -r requirements.txt
```

## Сценарий записи

### 0:00–0:20 — Вступление

Текст:

> Это MVP AI-сервиса для первичной обработки клиентских обращений. Он принимает обращение через API, классифицирует его, формирует черновик ответа, определяет необходимость эскалации и сохраняет историю в SQLite.

### 0:20–0:45 — Структура проекта

Показать файлы:

- `app/main.py`
- `app/llm_client.py`
- `app/schemas.py`
- `app/database.py`
- `.env.example`
- `README.md`

Текст:

> Сервис сделан на FastAPI. Секреты вынесены в переменные окружения. Для демонстрации есть локальный fake mode, а для реальной работы используется OpenAI API.

### 0:45–1:10 — Запуск API

Команда:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Показать `/health`:

```bash
curl http://127.0.0.1:8000/health
```

### 1:10–1:45 — Запрос на POST /triage

Команда:

```bash
curl -X POST "http://127.0.0.1:8000/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Здравствуйте, я оплатил заказ, но доступ к курсу не открылся.",
    "channel": "email",
    "client_id": "client_001"
  }'
```

Показать ответ:

```json
{
  "category": "billing",
  "draft_reply": "...",
  "confidence": "high",
  "escalate": false
}
```

### 1:45–2:10 — SQLite

Команда:

```bash
python scripts/query_tickets.py
```

Текст:

> Видно, что запрос и результат сохранены в таблицу tickets: client_id, channel, category, confidence, escalate и error.

### 2:10–2:30 — Логи

Команда:

```bash
tail -n 30 logs/app.log
```

Windows PowerShell:

```powershell
Get-Content logs/app.log -Tail 30
```

Текст:

> Логи показывают основные этапы обработки: входящий запрос, результат LLM или fake mode, сохранение записи в SQLite.

### 2:30–3:00 — Надежность

Текст:

> В проект добавлен guardrail layer: ответ модели проверяется как строгий JSON. Если LLM недоступна или формат ответа неправильный, сервис не падает, а возвращает безопасный fallback: обращение передано оператору, confidence low, escalate true.

## Что важно не забыть показать

- endpoint `/triage`;
- JSON-ответ;
- SQLite-запись;
- логи;
- `.env.example`, где видно, что ключ не хранится в коде;
- guardrail/fallback как портфолио-фичу.
