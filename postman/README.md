# KistBook Postman Collection

## Import

1. Open Postman → **Import** → select `KistBook_POC.postman_collection.json`
2. Set the `base_url` collection variable to your running instance (default: `http://localhost:8000`)
3. Generate a token and paste it into the `token` variable:

```bash
cd /path/to/rekist
python -c "
from kistbook.core.security import create_access_token
print(create_access_token({'sub': 'demo'}))
"
```

## First Run (in order)

1. **Create Retailer** — creates ShopHive, auto-saves `retailer_id` to collection variable
2. **Import CSV** — upload your installment book (see CSV format below)
3. **Trigger Scan** — runs the reminder engine, returns tasks enqueued
4. **Get Reminder Logs** — view the full audit trail

## Webhook Signature

The `/webhooks/whatsapp` endpoint requires `X-Hub-Signature-256: sha256=<hex>`. Compute it:

```python
import hashlib, hmac, json
secret = "your-WETARSEEL_WEBHOOK_SECRET"
body = json.dumps(your_payload, separators=(',', ':')).encode()
sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
print(f"sha256={sig}")
```

## CSV Format

```
customer_name,cnic,phone,guarantor_name,guarantor_phone,installment_amount,due_day_of_month,total_installments,installments_paid,last_payment_date
Ahmed Khan,3520212345671,+923001234567,,,5000,15,12,3,2026-05-15
```

- `phone` and `guarantor_phone`: E.164 format (`+923xxxxxxxxx`)
- `cnic`: 13 digits, no dashes
- `due_day_of_month`: 1–28
- `last_payment_date`: ISO format `YYYY-MM-DD` or empty
