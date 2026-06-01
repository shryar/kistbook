# KistBook — Installment Reminder Engine (POC)

WhatsApp-based automated installment reminder engine for Pakistani retail. Replaces manual follow-up with branched, idempotent reminders dispatched via WeTarseel BSP.

## What It Does

1. Retailer uploads an installment book CSV
2. Daily scan classifies customers into Branch A / B / C by payment behaviour
3. Throttled WhatsApp reminders are dispatched; guarantor and manager alerts trigger at escalation thresholds
4. Inbound customer replies pause the sequence and notify the ops manager
5. Zero duplicate messages — enforced by a `UNIQUE(customer_id, step, channel)` DB constraint

## Architecture

```
CSV Upload → FastAPI → PostgreSQL
                ↓
Celery Beat (daily 06:00 PKT)
   → scanner.py  →  SendReminderTask (Celery worker)
                           ↓
                    WeTarseel BSP → WhatsApp

WhatsApp reply → WeTarseel webhook → FastAPI → reply_handler.py
                                                    ↓
                                             pause sequence + alert manager
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.11+) |
| Task queue | Celery 5 + Celery Beat |
| Database | PostgreSQL 15 (Railway) |
| Broker / cache | Redis (Railway) |
| WhatsApp | WeTarseel BSP (Meta Cloud API) |
| ORM | SQLAlchemy 2.x async |
| Auth | JWT (python-jose) |
| Encryption | Fernet (cryptography) |

## Local Development Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15 running locally or via Railway
- Redis running locally or via Railway

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/kistbook
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-min-32-chars
CREDENTIALS_ENC_KEY=<Fernet key — generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
WETARSEEL_API_KEY=your-wetarseel-api-key
WETARSEEL_WEBHOOK_SECRET=your-webhook-secret
ENVIRONMENT=development
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start Services

```bash
# Terminal 1 — FastAPI
uvicorn kistbook.api.main:app --reload

# Terminal 2 — Celery worker
celery -A kistbook.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat (daily scheduler)
celery -A kistbook.celery_app beat --loglevel=info
```

### 6. Generate a JWT Token

```bash
python -c "
from kistbook.core.security import create_access_token
print(create_access_token({'sub': 'demo'}))
"
```

## First Run

### Option A — Web UI (easiest)

Open `http://localhost:8000` in a browser. The demo UI walks through all 4 steps: create retailer → upload CSV → trigger scan → view logs.

### Option B — Postman

Import `postman/KistBook_POC.postman_collection.json`. See `postman/README.md` for instructions.

### Option C — cURL

```bash
BASE=http://localhost:8000
TOKEN=<your-jwt-token>

# Create retailer
curl -X POST $BASE/retailers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"ShopHive","whatsapp_number":"+923001234567","manager_phone":"+923007654321"}'

# Import CSV
curl -X POST $BASE/retailers/<id>/import-csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@installment_book.csv"

# Trigger scan (dev only)
curl -X POST $BASE/admin/trigger-scan \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"retailer_id":"<id>"}'

# View logs
curl $BASE/retailers/<id>/reminder-logs \
  -H "Authorization: Bearer $TOKEN"
```

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/retailers` | JWT | Create retailer + default config |
| `POST` | `/retailers/{id}/import-csv` | JWT | Upload CSV installment book |
| `GET` | `/retailers/{id}/customers` | JWT | List customers with filters |
| `PATCH` | `/retailers/{id}/customers/{cid}` | JWT | Pause / resume sequence |
| `GET` | `/retailers/{id}/reminder-logs` | JWT | Audit log with filters |
| `GET` | `/retailers/{id}/config` | JWT | Get reminder config |
| `PATCH` | `/retailers/{id}/config` | JWT | Update reminder config |
| `POST` | `/webhooks/whatsapp` | HMAC | WeTarseel inbound webhook |
| `POST` | `/admin/trigger-scan` | JWT | Manual scan (dev only) |

## Running Tests

```bash
# Set test DB URL
export TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/kistbook_test

pytest kistbook/tests/ -v
```

## Design Documents

Full specification, data model, API contracts, and research decisions:

```
specs/001-reminder-engine-poc/
├── spec.md          # Business specification, user stories, FRs
├── plan.md          # Implementation plan, tech stack
├── data-model.md    # Entity relationships, DB schema
├── research.md      # Key design decisions with rationale
└── contracts/api.md # REST endpoint contracts
```

## Branch Classification

| Branch | Condition | Steps |
|--------|-----------|-------|
| A | Standard (days ≤ 3 or first overdue) | T−3, T0, T+1, T+3 |
| B | Partial payer, overdue > 3 days | T+7, T+10, T+14 (manager) |
| C | Never paid, overdue > 0 | T+3, T+5 (guarantor), T+7 (manager) |
