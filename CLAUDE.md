<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at `specs/001-reminder-engine-poc/plan.md`
<!-- SPECKIT END -->

# KistBook — Development Guidelines

Full product spec: `spec.md`. Full PRD: `kistbook_prd_v2.md`.

---

## Project Context

KistBook is a WhatsApp-based installment reminder engine for Pakistani retail. The POC is a backend-only system: FastAPI + Celery + PostgreSQL + Redis, deployed on Railway. No frontend in scope yet.

The core constraint: **the reminder engine must never send a duplicate message**. Idempotency is the most important correctness property in this codebase.

---

## Tech Stack

- **Python 3.11+**, FastAPI, SQLAlchemy 2.x (async), Alembic
- **PostgreSQL 15** via Railway — primary store
- **Redis** via Railway — Celery broker and result backend
- **Celery 5** + Celery Beat — task queue and daily scheduler
- **WeTarseel BSP** — WhatsApp Cloud API wrapper (Meta)

---

## Code Style

- **Type-annotate everything** — all function signatures, all model fields. Use `from __future__ import annotations` at the top of every file.
- **Pydantic v2** for request/response schemas and config. No raw dicts crossing API boundaries.
- **No comments explaining what the code does.** Only comment when the *why* is non-obvious: a hidden constraint, a workaround, a subtle invariant.
- **No docstrings** unless the function is a public API surface that a consumer needs to understand without reading the body.
- Prefer flat over nested. If a function needs more than two levels of indentation, break it up.
- No `print()` statements. Use Python's `logging` module with structured log lines.

---

## Project Structure

```
kistbook/
├── api/
│   ├── main.py           # FastAPI app, router registration
│   ├── routes/
│   │   ├── retailers.py
│   │   ├── customers.py
│   │   ├── webhooks.py   # WeTarseel inbound webhook
│   │   └── admin.py      # dev/test endpoints (trigger-scan, etc.)
│   └── deps.py           # shared FastAPI dependencies (DB session, auth)
├── core/
│   ├── config.py         # settings via pydantic-settings (env vars)
│   ├── security.py       # JWT encode/decode
│   └── logging.py        # structured logging setup
├── db/
│   ├── models.py         # SQLAlchemy ORM models
│   ├── session.py        # async engine + session factory
│   └── migrations/       # Alembic
├── engine/
│   ├── scanner.py        # daily scan logic — reads csv_customers, enqueues tasks
│   ├── branch.py         # branch classification (A/B/C) and step resolution
│   ├── tasks.py          # Celery tasks: SendReminderTask
│   └── templates.py      # message template selection and variable rendering
├── integrations/
│   ├── wetarseel.py      # WeTarseel API client (send message, verify webhook sig)
│   └── whatsapp_types.py # typed dicts / Pydantic models for WeTarseel payloads
├── celery_app.py         # Celery app and Beat schedule definition
└── tests/
    ├── test_branch.py
    ├── test_scanner.py
    ├── test_tasks.py
    └── test_webhooks.py
```

---

## Database

- Use **async SQLAlchemy** (`asyncpg` driver). All DB calls must be async.
- All schema changes via **Alembic migrations** — never modify the DB directly.
- The idempotency constraint on `reminder_logs` is a database-level `UNIQUE` constraint on `(customer_id, step, channel)`. Never rely solely on application-level checks.
- Encrypt `retailer_connections.credentials` at the application layer before writing to the DB. Use Fernet (from `cryptography`) with a key from env.

---

## Celery

- The Beat job (`scanner.py`) runs **once every 24 hours**. It only enqueues tasks — it does no I/O to WeTarseel.
- `SendReminderTask` must be **idempotent**: re-check `reminder_logs` for the idempotency key before calling WeTarseel. A task that has already been sent must return cleanly, not raise.
- Use `task_acks_late = True` on `SendReminderTask` so a worker crash does not silently drop a task.
- Do not use `apply_async(countdown=...)` for scheduling across days — that is Beat's job. Workers only process what Beat enqueues today.

---

## WhatsApp / WeTarseel

- **Never call WeTarseel outside of a Celery task.** The webhook handler and scanner are not allowed to send messages directly — they enqueue tasks.
- Verify the WeTarseel webhook HMAC-SHA256 signature on every inbound request before processing. Reject with 401 if invalid.
- All customer-facing messages must use a Meta-approved template. Template names live in `engine/templates.py` as constants, not magic strings scattered through the code.
- Log every API call to WeTarseel: request payload, HTTP status, response body, and timestamp. Store the provider message ID in `reminder_logs.provider_msg_id`.

---

## Error Handling

- **Do not swallow exceptions silently.** Every `except` block must either re-raise or log at `ERROR` level with full context.
- Celery task failures should log the error and set `reminder_logs.status = 'failed'`. Do not auto-retry for POC — failed rows are reviewed manually.
- FastAPI exception handlers: return structured JSON `{"error": "...", "detail": "..."}` for all 4xx/5xx responses.

---

## Environment Variables

All config via environment variables using `pydantic-settings`. Required vars:

```
DATABASE_URL          # PostgreSQL connection string (asyncpg)
REDIS_URL             # Redis connection string
SECRET_KEY            # JWT signing key
CREDENTIALS_ENC_KEY   # Fernet key for encrypting retailer credentials
WETARSEEL_API_KEY     # WeTarseel API key
WETARSEEL_WEBHOOK_SECRET  # HMAC secret for webhook verification
```

Never hardcode credentials. Never commit a `.env` file.

---

## Testing

- **Unit test** `engine/branch.py` exhaustively — every branch classification case and every step trigger day. This logic is the product.
- **Unit test** the idempotency check in `SendReminderTask` — confirm a task that finds an existing `reminder_logs` row exits without calling WeTarseel.
- **Integration tests** hit a real PostgreSQL instance (use `pytest-asyncio` + a test DB). Do not mock the database.
- Mock WeTarseel HTTP calls with `respx` (async-compatible httpx mock).
- Test the webhook handler with a valid and an invalid HMAC signature.

---

## Git

- Branch from `main`. One branch per feature or fix.
- Commit messages: imperative mood, present tense. `Add branch C guarantor step` not `Added guarantor step`.
- Do not commit `.env`, `*.pyc`, or migration files generated against a local DB with non-standard data.
