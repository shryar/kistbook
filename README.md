# KistBook — Installment Reminder Engine (POC)

WhatsApp-based automated installment reminder engine for Pakistani retail. Replaces manual follow-up with branched, idempotent reminders dispatched via the WeTarseel BSP.

## What It Does

1. Retailer uploads an installment book CSV
2. Daily scan classifies customers into Branch A / B / C by payment behaviour
3. Throttled WhatsApp reminders are dispatched; guarantor and manager alerts trigger at escalation thresholds
4. Inbound customer replies pause the sequence and notify the ops manager
5. Zero duplicate messages — enforced by a `UNIQUE(customer_id, step, channel)` DB constraint

## Architecture

```
CSV Upload ──► FastAPI ──► PostgreSQL
                  │
         Celery Beat (daily 06:00 PKT)
              │
         scanner.py ──► SendReminderTask (Celery worker)
                              │
                       WeTarseel BSP ──► WhatsApp

WhatsApp reply ──► WeTarseel webhook ──► FastAPI ──► reply_handler.py
                                                         │
                                               pause sequence + manager alert
```

## Running Locally with Docker

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Create your `.env` file

Copy the example and fill in your WeTarseel credentials:

```bash
cp .env.example .env
```

The only values you **must** change before first run are:

| Variable | How to get it |
|----------|---------------|
| `WETARSEEL_API_KEY` | Your WeTarseel dashboard API key |
| `WETARSEEL_WEBHOOK_SECRET` | Set in your WeTarseel webhook config |
| `SECRET_KEY` | Any random 32+ character string |
| `CREDENTIALS_ENC_KEY` | Run: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

`DATABASE_URL` and `REDIS_URL` are pre-filled in `.env.example` to match the Docker Compose services — leave them as-is.

### 2. Start everything

```bash
docker compose up --build
```

This starts five services in the right order:

| Service | What it does |
|---------|-------------|
| `db` | PostgreSQL 15 |
| `redis` | Redis 7 (Celery broker) |
| `migrate` | Runs `alembic upgrade head`, then exits |
| `api` | FastAPI on `localhost:8000` |
| `worker` | Celery worker (processes reminder tasks) |
| `beat` | Celery Beat (triggers daily scan at 06:00 UTC) |

### 3. Generate a JWT token

The API requires a bearer token on every request except the webhook endpoint.

```bash
docker compose exec api python -c "
from kistbook.core.security import create_access_token
print(create_access_token({'sub': 'demo'}))
"
```

### 4. Open the demo UI

Go to **http://localhost:8000** — a 4-step form walks through the full POC flow:

1. **Create Retailer** — registers ShopHive, saves the retailer ID
2. **Upload CSV** — imports the installment book
3. **Trigger Scan** — runs the reminder engine immediately
4. **View Logs** — shows the full audit trail

Paste the token from step 3 into the token field at the top.

### Stopping

```bash
docker compose down          # stop containers, keep DB data
docker compose down -v       # stop + delete the DB volume (clean slate)
```

---

## CSV Format

```
customer_name,cnic,phone,guarantor_name,guarantor_phone,installment_amount,due_day_of_month,total_installments,installments_paid,last_payment_date
Ahmed Khan,3520212345671,+923001234567,,,5000,15,12,3,2026-05-15
```

- `phone` / `guarantor_phone`: E.164 format (`+923xxxxxxxxx`)
- `cnic`: 13 digits, no dashes
- `due_day_of_month`: 1–28 (capped to last day of month for short months)
- `last_payment_date`: `YYYY-MM-DD` or empty
- `guarantor_name` / `guarantor_phone`: optional — leave empty if not on file

---

## API Reference

All endpoints require `Authorization: Bearer <token>` except the webhook.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/retailers` | Create retailer + default config |
| `POST` | `/retailers/{id}/import-csv` | Upload CSV installment book |
| `GET` | `/retailers/{id}/customers` | List customers (filters: `paused`, `completed`) |
| `PATCH` | `/retailers/{id}/customers/{cid}` | Pause / resume sequence |
| `GET` | `/retailers/{id}/reminder-logs` | Audit log (filters: `direction`, `status`, `from`, `to`) |
| `GET` | `/retailers/{id}/config` | Get reminder config |
| `PATCH` | `/retailers/{id}/config` | Update tone, VIP list, branch toggles |
| `POST` | `/webhooks/whatsapp` | WeTarseel inbound webhook (HMAC verified, no JWT) |
| `POST` | `/admin/trigger-scan` | Manual scan trigger (dev environment only) |

Interactive docs: **http://localhost:8000/docs**

A Postman collection is in `postman/` — see `postman/README.md` for import instructions.

---

## Branch Classification

| Branch | When | Steps |
|--------|------|-------|
| A | Standard (0 days overdue or first 3 days) | T−3, T0, T+1, T+3 → customer |
| B | Partial payer, > 3 days overdue | T+7, T+10 → customer; T+14 → manager |
| C | Never paid, any days overdue | T+3 → customer; T+5 → guarantor; T+7 → manager |

Customers who complete all installments are auto-marked `is_completed=TRUE` and excluded from all future scans.

---

## Running Tests

Requires a running PostgreSQL instance (the Docker Compose `db` service works):

```bash
# With the db service already running via docker compose up db
docker compose exec api pytest kistbook/tests/ -v
```

Or against a local Postgres:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://kistbook:kistbook@localhost:5432/kistbook_test \
  .venv/bin/pytest kistbook/tests/ -v
```
