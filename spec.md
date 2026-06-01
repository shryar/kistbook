# KistBook — Technical Specification
**v1.1 | June 2026 | Internal**

---

## What This Document Is

This spec defines the POC build scope for KistBook's reminder engine. It is the source of truth for implementation decisions. The full product vision and market context live in `kistbook_prd_v2.md`.

---

## POC Goal

Prove one hypothesis: **automated, branched WhatsApp reminders materially reduce late installment payments versus manual WhatsApp follow-up.**

Validation target: ShopHive's existing overdue installment book. Success metric: DSO reduction vs. pre-KistBook baseline.

---

## Architecture Overview

KistBook is **not a ledger**. For the POC, it is a collections layer that sits on top of CSV data exported from the retailer's existing CRM.

```
ShopHive exports customer + installment data from Daftra
        │
        │  one-time or periodic manual CSV upload
        ▼
KistBook CSV Import
        │
        ▼
KistBook Reminder Engine
  ├── Celery Beat (daily job at 06:00 PKT: scan due dates, enqueue reminders)
  ├── Celery Worker (fire WhatsApp messages, log results)
  └── Webhook Handler (receive WeTarseel delivery events + customer replies)
        │
        ▼
KistBook Store (PostgreSQL — lightweight)
  ├── csv_customers    ← imported installment book
  ├── reminder_logs    ← idempotency + audit trail
  ├── retailers        ← retailer account
  └── reminder_config  ← per-retailer sequence settings

Outbound channel
  └── WhatsApp only (WeTarseel BSP → Meta Cloud API)
```

**What KistBook owns:** imported customer data (from CSV), reminder logs, reminder config.

**What KistBook does not touch:** Daftra. No live API connection to Daftra in the POC. Payment confirmations received via WhatsApp reply are flagged for manual ops manager action — not written back to Daftra.

**Phase 2 note:** Once the POC is validated, replace CSV import with a live Daftra API connector and eventually a generic `CRMConnector` interface (Moneypex, DigiKhata, WooCommerce).

---

## Data Model

### `retailers`
```sql
id               UUID PRIMARY KEY
name             TEXT NOT NULL
whatsapp_number  TEXT NOT NULL  -- ShopHive's dedicated number, registered via WeTarseel
manager_phone    TEXT NOT NULL  -- ops manager's WhatsApp number for escalation alerts
created_at       TIMESTAMPTZ
```

### `reminder_config`
```sql
id                  UUID PRIMARY KEY
retailer_id         UUID REFERENCES retailers(id)
branch_a_enabled    BOOLEAN DEFAULT TRUE
branch_b_enabled    BOOLEAN DEFAULT TRUE
branch_c_enabled    BOOLEAN DEFAULT TRUE
tone                TEXT DEFAULT 'standard'  -- 'formal' | 'standard' | 'light'
vip_cnic_list       TEXT[]  -- CNICs that skip automation entirely
scan_time_utc       TEXT DEFAULT '01:00'     -- 06:00 PKT = 01:00 UTC
updated_at          TIMESTAMPTZ
```

### `csv_customers`
The installment book. One row per active installment plan. Updated by re-importing an updated CSV.

```sql
id                  UUID PRIMARY KEY
retailer_id         UUID REFERENCES retailers(id)
customer_name       TEXT NOT NULL
cnic                TEXT NOT NULL          -- unique identifier across the network (Phase 2)
phone               TEXT NOT NULL          -- WhatsApp-capable phone number
guarantor_name      TEXT
guarantor_phone     TEXT
installment_amount  NUMERIC NOT NULL       -- PKR amount per installment
due_day_of_month    INT NOT NULL           -- day of month the installment is due (1–28)
total_installments  INT NOT NULL
installments_paid   INT NOT NULL DEFAULT 0
last_payment_date   DATE
sequence_paused     BOOLEAN DEFAULT FALSE  -- set TRUE when customer replies PAID or HELP
imported_at         TIMESTAMPTZ
```

**CSV import schema (column headers must match exactly):**
```
customer_name, cnic, phone, guarantor_name, guarantor_phone,
installment_amount, due_day_of_month, total_installments,
installments_paid, last_payment_date
```

`last_payment_date` may be empty for no-show accounts. `guarantor_name` and `guarantor_phone` may be empty if not on file.

### `reminder_logs`
Every outbound message and every inbound customer reply gets a row. This is the audit trail and the idempotency store.

```sql
id                UUID PRIMARY KEY
retailer_id       UUID REFERENCES retailers(id)
customer_id       UUID REFERENCES csv_customers(id)
customer_cnic     TEXT NOT NULL
step              TEXT NOT NULL       -- e.g. 'branch_a_t-3', 'branch_b_t+7', 'manager_alert_b_t+14'
channel           TEXT NOT NULL       -- 'whatsapp' | 'manager_whatsapp'
direction         TEXT NOT NULL       -- 'outbound' | 'inbound'
template_id       TEXT                -- Meta-approved template name used (outbound only)
message_body      TEXT                -- rendered message text
status            TEXT NOT NULL       -- 'queued' | 'sent' | 'delivered' | 'read' | 'failed' | 'replied'
provider_msg_id   TEXT                -- WeTarseel message ID
inbound_text      TEXT                -- customer's reply text (inbound rows only)
sent_at           TIMESTAMPTZ
status_updated_at TIMESTAMPTZ
```

**Idempotency constraint:** `UNIQUE (customer_id, step, channel)` — prevents duplicate sends if the daily job runs twice or a task is retried.

---

## Reminder Engine

### Celery Beat — daily scan

Runs **once every 24 hours** at 06:00 PKT (01:00 UTC). Configurable per retailer via `reminder_config.scan_time_utc`.

```
for each active retailer:
  load reminder_config
  for each csv_customer where sequence_paused = FALSE:
    compute today's due installment (due_day_of_month vs today's date)
    determine days_since_due (negative = days until due)
    classify branch: A, B, or C (see Branch Logic below)
    for each step whose trigger day matches days_since_due:
      if reminder_logs already has a row for (customer_id, step, channel): skip
      else: enqueue SendReminderTask(retailer_id, customer_id, step)
```

### Celery Worker — SendReminderTask

```
1. Re-check idempotency against reminder_logs (cheap guard against duplicate queue entries)
2. Load csv_customers row: name, phone, installment_amount, due date
3. Select template for (step, tone from reminder_config)
4. Send WhatsApp message via WeTarseel API with rendered variables
5. Insert row into reminder_logs with status='sent' and provider_msg_id
6. On WeTarseel API failure: insert row with status='failed', do not retry automatically
   (failed rows are visible in logs; retry is manual for POC)
```

### Webhook Handler — inbound events (FastAPI)

Receives POST events from WeTarseel at `/webhooks/whatsapp`.

**Delivery status update** (WeTarseel notifies when a message is delivered / read / failed):
- Find `reminder_logs` row by `provider_msg_id`
- Update `status` and `status_updated_at`

**Inbound customer reply** (customer sends a WhatsApp message back):
- Insert row in `reminder_logs` with `direction='inbound'`, `inbound_text=<reply>`
- Classify reply:
  - Reply contains "paid" / "pay kar diya" / "ho gaya" (case-insensitive) → set `csv_customers.sequence_paused = TRUE`; send manager alert via WhatsApp: "Customer [name] replied PAID — please verify and update Daftra. Amount: PKR [X]"
  - Reply contains "help" / "problem" / "masla" / any unrecognised text → set `sequence_paused = TRUE`; send manager alert: "Customer [name] sent a message — human handoff needed. Reply: [text]"
  - Reply contains a date or "kal" / "parso" → log as promise-to-pay; do not pause sequence; manager alert: "Customer [name] promised to pay [date/text]"

---

## Branch Logic

### Classification (computed each scan, based on csv_customers row)

```
days_since_due = today - current installment due date

if installments_paid == 0 and days_since_due > 0:
    branch = C  (hard escalation — no payment at all since deposit)
elif installments_paid >= 1 and days_since_due > 3:
    branch = B  (soft re-engagement — partial payer, drifted past T+3)
elif days_since_due <= 3:
    branch = A  (standard — upcoming or early overdue)
```

### Branch A — Standard (all customers)

| Step key | Trigger (days_since_due) | Channel | Tone |
|---|---|---|---|
| `branch_a_t-3` | −3 (3 days before due) | WhatsApp → customer | Friendly |
| `branch_a_t0` | 0 (due date) | WhatsApp → customer | Neutral |
| `branch_a_t+1` | +1 | WhatsApp → customer | Gentle |
| `branch_a_t+3` | +3 | WhatsApp → customer | Firm |

### Branch B — Soft re-engagement (partial payer: installments_paid ≥ 1)

| Step key | Trigger (days_since_due) | Channel | Action |
|---|---|---|---|
| `branch_b_t+7` | +7 | WhatsApp → customer | Warm/personal |
| `branch_b_t+10` | +10 | WhatsApp → customer | Partial payment offer |
| `branch_b_t+14` | +14 | WhatsApp → manager | Ops manager alert |
| `branch_b_t+21` | +21 | *(Phase 2)* | Recovery task — out of scope for POC |

### Branch C — Hard escalation (no-show: installments_paid == 0)

| Step key | Trigger (days_since_due) | Channel | Action |
|---|---|---|---|
| `branch_c_t+3` | +3 | WhatsApp → customer | Firm |
| `branch_c_t+5` | +5 | WhatsApp → guarantor | Formal notice to guarantor on file |
| `branch_c_t+7` | +7 | WhatsApp → manager | Immediate ops manager alert |
| `branch_c_t+10` | +10 | *(Phase 2)* | Recovery task — out of scope for POC |

**Guarantor step:** If `guarantor_phone` is empty, skip `branch_c_t+5` silently and log as `status='skipped_no_guarantor'`.

**Manager alerts** (Branch B T+14, Branch C T+7): Sent as a WhatsApp message from KistBook's BSP number to `retailers.manager_phone`. Same WeTarseel API, no template approval required for manager-to-manager messages within the 24-hour session window.

---

## WhatsApp Integration

**BSP:** WeTarseel (Pakistan-based, PKR billing, 1-day onboarding).
**Registered entity for POC:** ShopHive (using ShopHive's SECP registration and NTN).

### Meta-approved templates required before go-live

All customer-facing outbound messages must use pre-approved templates. Submit these to WeTarseel before testing:

| Template name | Step | Variables |
|---|---|---|
| `kisht_reminder_friendly` | Branch A, T-3 | `{{name}}`, `{{amount}}`, `{{due_date}}` |
| `kisht_reminder_due` | Branch A, T-0 | `{{name}}`, `{{amount}}` |
| `kisht_reminder_gentle` | Branch A, T+1 | `{{name}}`, `{{amount}}` |
| `kisht_reminder_firm` | Branch A, T+3 | `{{name}}`, `{{amount}}` |
| `kisht_soft_warm` | Branch B, T+7 | `{{name}}`, `{{amount}}`, `{{installments_paid}}` |
| `kisht_soft_partial_offer` | Branch B, T+10 | `{{name}}`, `{{amount}}` |
| `kisht_hard_firm` | Branch C, T+3 | `{{name}}`, `{{amount}}` |
| `kisht_guarantor_notice` | Branch C, T+5 | `{{guarantor_name}}`, `{{customer_name}}`, `{{amount}}` |

Each template needs both an **Urdu** and **English** version. 16 templates total.

**Opt-out:** Every template must include a footer with opt-out instruction (Meta requirement): "Is message ko band karne ke liye STOP reply karein."

---

## API Endpoints (FastAPI)

```
POST   /webhooks/whatsapp              # WeTarseel inbound webhook (no auth — verified by signature)
POST   /retailers                      # create retailer account
POST   /retailers/{id}/import-csv      # upload CSV to populate csv_customers
GET    /retailers/{id}/customers       # list customers and their sequence status
PATCH  /retailers/{id}/customers/{cid} # manually pause/resume a customer's sequence
GET    /retailers/{id}/reminder-logs   # audit log (for dashboard, Phase 1.5)
POST   /admin/trigger-scan             # manually trigger the daily scan (dev/test only)
```

Authentication: JWT bearer token on all routes except `/webhooks/whatsapp`.

Webhook signature verification: WeTarseel signs webhook payloads with HMAC-SHA256. Verify on every inbound request before processing.

---

## Tech Stack

| Component | Choice |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| ORM + migrations | SQLAlchemy 2.x + Alembic |
| Database | PostgreSQL 15 (Railway managed) |
| Task queue + scheduler | Celery 5 + Celery Beat + Redis (Railway managed) |
| Beat schedule | Daily at 06:00 PKT (01:00 UTC) |
| WhatsApp | WeTarseel BSP → Meta Cloud API |
| SMS | Not in POC scope |
| Backend hosting | Railway |
| Frontend | Next.js on Vercel — built after engine is validated (Phase 1.5) |

---

## Out of Scope for POC

- Frontend dashboard
- Live Daftra API integration (replaced by CSV import for POC)
- SMS fallback
- Payment gateway (JazzCash / EasyPaisa)
- Recovery Task Manager (Phase 2)
- KishtScore (Phase 2)
- React Native mobile app (Phase 2)
- Multi-retailer support (POC is ShopHive only — single retailer row)
