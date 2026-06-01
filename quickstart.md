# KistBook — Local Testing Quickstart

Assumes `docker compose up --build` is already running and all five services are healthy.

---

## Step 1 — Generate a JWT token

```bash
docker compose exec api python -c "
from kistbook.core.security import create_access_token
print(create_access_token({'sub': 'demo'}))
"
```

Copy the printed token — you'll paste it into the UI in the next step.

---

## Step 2 — Open the demo UI

Go to **http://localhost:8000**

Paste the token into the **API Token** field at the top of the page.

---

## Step 3 — Create a test CSV

Save this as `test_customers.csv` on your machine:

```
customer_name,cnic,phone,guarantor_name,guarantor_phone,installment_amount,due_day_of_month,total_installments,installments_paid,last_payment_date
Ahmed Khan,3520212345671,+923001234567,,,5000,1,12,3,2026-05-01
Sara Malik,3520212345672,+923001234568,,,8000,1,6,0,
Bilal Ahmed,3520212345673,+923001234569,Ali Ahmed,+923009999999,3000,1,24,1,2026-05-01
```

Or create it from the terminal:

```bash
cat > /tmp/test_customers.csv << 'EOF'
customer_name,cnic,phone,guarantor_name,guarantor_phone,installment_amount,due_day_of_month,total_installments,installments_paid,last_payment_date
Ahmed Khan,3520212345671,+923001234567,,,5000,1,12,3,2026-05-01
Sara Malik,3520212345672,+923001234568,,,8000,1,6,0,
Bilal Ahmed,3520212345673,+923001234569,Ali Ahmed,+923009999999,3000,1,24,1,2026-05-01
EOF
```

**What each customer exercises:**

| Customer | installments_paid | Branch | Why |
|----------|------------------|--------|-----|
| Ahmed Khan | 3 | A | Partial payer, within standard window |
| Sara Malik | 0 | C | Never paid — hard escalation track |
| Bilal Ahmed | 1 (with guarantor) | A | Partial payer, standard window |

---

## Step 4 — Run through the UI

Work through all four steps in the browser:

1. **Create Retailer** — fills in ShopHive details, click the button. The retailer ID is saved automatically.
2. **Upload CSV** — pick your `test_customers.csv` file, click Import.
3. **Trigger Scan** — click Run Scan. You'll see `tasks_enqueued` and `customers_scanned` in the response.
4. **View Logs** — click Load Logs. You'll see one `reminder_logs` row per triggered step.

---

## What to expect

With `WETARSEEL_API_KEY=dev-placeholder` in `.env`, the Celery tasks run the full engine path but WeTarseel API calls fail. Each customer step appears in the logs with `status=failed`. This is expected — the full pipeline (classify → enqueue → idempotency check → attempt send → log result) executes correctly.

To confirm the **idempotency guarantee**, click **Trigger Scan** a second time. The log count must not increase — each `(customer_id, step, channel)` combination is already recorded and the tasks exit cleanly without re-sending.

---

## Switching to a real WeTarseel key

Update `.env`:

```
WETARSEEL_API_KEY=your-real-key
WETARSEEL_WEBHOOK_SECRET=your-real-secret
```

Then restart without rebuilding:

```bash
docker compose restart api worker beat
```

Trigger the scan again — reminders will now actually dispatch to WhatsApp.

---

## Useful commands

```bash
# Watch live logs from all services
docker compose logs -f

# Watch only the Celery worker (task execution)
docker compose logs -f worker

# Open a Python shell inside the running API container
docker compose exec api python

# Reset everything (wipes the database)
docker compose down -v && docker compose up
```
