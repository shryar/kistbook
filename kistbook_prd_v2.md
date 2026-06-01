# KistBook — Product Requirements Document
**Version 2.0 | June 2026 | Confidential**

---

## Changelog from v1.0

| Area | v1.0 | v2.0 |
|---|---|---|
| WhatsApp strategy | Flagged API as uncertain; WhatsApp Web as fallback | Official API confirmed available in Pakistan via local BSPs, live in 1 day. WhatsApp Web approach removed entirely. |
| Default rate framing | 5–10% treated as credit risk problem | Reframed as friction/forgetting problem. True bad debt is ~0.3% (1 in 300 over 4 years). The 5–10% is recoverable drifters. |
| Phase 1 scope | Ledger + reminders + basic KishtScore | Narrowed to ledger + reminder engine only. KishtScore moved to Phase 2 (needs data to train on). |
| Reminder logic | Single escalation sequence | Split into two branches: soft re-engagement (partial payers) vs. hard escalation (total no-shows). |
| Network score framing | Catch bad borrowers | Reframed as geography/drift detection — flags CNICs going unresponsive across multiple retailers simultaneously. |

---

## Executive Summary

KistBook is a B2B SaaS platform that serves as the **credit collections OS for mid-size ecommerce retailers in Pakistan** — and eventually across South Asia and MENA. It replaces the WhatsApp-group-and-gut-feel system that governs informal installment credit today with a structured, automated reminder engine, a customer credit ledger, and — once sufficient repayment data exists — an AI-driven network credit score built from real behaviour.

**The founding insight:** Pakistan's installment credit market is already massive and deeply functional. It runs on trust, paper, and personal relationships. The retailer's credit instincts are largely correct (true default rate is near zero). What breaks down is the follow-up system. Payments slip not because customers won't pay — but because nobody is consistently, professionally nudging them. KistBook fixes the follow-up, not the credit decision.

**Target customer (v1):** Mid-size ecommerce retailers in Pakistan (10–50 staff, tech-savvy, selling electronics or high-ticket goods on credit, ~100–2,000 installment customers, avg ticket PKR 50K–150K).

**Business model:** Transaction fee — a % of each installment successfully collected through the platform.

---

## Problem Statement

### The retailer's reality

A retailer like ShopHive extends credit to hundreds of customers across Lahore. The average ticket is PKR 50K–150K. Customers pay in installments over 3–12 months. The entire system is managed via WhatsApp threads and memory.

When a payment is due, someone manually sends a reminder — if they remember. When a payment is missed, the retailer finds out days or weeks later. At any given time, 5–10% of the portfolio is "late" — money that is mostly recoverable but sitting in friction.

### What the problem actually is

Validated from ShopHive's own 4-year portfolio:

- **True bad debt (no payment after deposit):** ~0.3% — 1 customer in 300 over 4 years
- **The 5–10% "bad debt":** Almost entirely partial payers who've gone quiet, or customers who've left the city

**This is not a credit risk problem. It is a friction and forgetting problem.**

Customers who've paid 4 of 6 installments are not defaulters — they are drifters. They can pay. They intend to pay. They just need a consistent, professional, escalating nudge. The current WhatsApp-based system delivers inconsistent nudges at best and none at worst. KistBook automates the nudge.

### Why this problem is unsolved

Existing tools in Pakistan (Moneypex, UR QistPro, DigitalManager, DigiKhata) solve the **ledger problem** — they track who owes what. They do not solve the **collections problem**. They are record-keeping tools, not collections engines.

The specific gap:

| Layer | Who solves it today | Status |
|---|---|---|
| Ledger / record-keeping | Moneypex, DigiKhata | Solved |
| Automated WhatsApp reminders | UR QistPro (basic, one-way) | Partially — no escalation logic, no branching, no two-way |
| Branched collections workflow | Nobody in Pakistan | **Unsolved** |
| Partial-payer re-engagement flow | Nobody in Pakistan | **Unsolved** |
| Cross-retailer drift detection | Nobody in Pakistan | **Unsolved** |
| Field recovery coordination | Manual / ad hoc | **Unsolved** |

---

## Market Opportunity

### Pakistan (immediate)
- Informal installment credit in electronics alone runs into hundreds of billions PKR annually
- ~500,000+ small and mid-size retailers across Pakistan extend some form of credit
- Credit card penetration: <3% of the population — informal credit is the only game in town
- 5–10% late payment rate across portfolios = enormous recoverable value sitting in friction

### Regional (3–5 year horizon)
- Bangladesh, Egypt, Nigeria share identical market dynamics: large informal credit ecosystems, low credit card penetration, high mobile penetration, rapidly digitising retail
- Indonesia's BNPL market projected to reach $13.59B by 2030 — collections infrastructure layer still nascent
- MENA's consumer lending market is $500B — ClearGrid (Dubai) raised $10M in 2025 purely to automate collections for banks and BNPL providers. KistBook is the SME-retail version of this thesis, at 1/10th the complexity

### Comparable companies
| Company | Market | What they do | Funding |
|---|---|---|---|
| ClearGrid | UAE/KSA | AI collections automation for banks & BNPL | $10M (2025) |
| Credgenics | India | Digital collections for NBFCs & fintechs | $50M+ |
| Kredivo | Indonesia | BNPL + credit scoring for underbanked | $270M+ |
| UR QistPro | Pakistan | Basic ledger + one-way WhatsApp reminders | Bootstrapped |
| Moneypex | Pakistan | Ledger + guarantor tracking, no reminders | Bootstrapped |

**KistBook's white space:** Collections intelligence for retailer-run informal credit — a category none of the above serve.

---

## Product Vision

> "KistBook is the collections backbone of Pakistan's informal retail economy — the system that makes sure every rupee owed gets paid, without a single manual WhatsApp from the retailer."

---

## User Personas

### Primary: The Retail Operations Manager ("Bilal")
- Works at a mid-size ecommerce retailer
- Manages 200–800 installment customers
- Currently uses WhatsApp + memory to track and chase payments
- Spends 2–3 hours/day on manual follow-ups
- Goal: recover more payments with zero manual effort per customer

### Secondary: The Recovery Agent ("Asif")
- Field staff who visits customers who've gone unreachable
- Currently gets a WhatsApp message with an address and no other context
- Has no app, no route optimisation, no status reporting mechanism
- Goal: clear daily task list, efficient route, easy status updates back to manager

### Tertiary: The Retail Owner / CEO ("Kamran")
- Wants portfolio-level visibility without daily ops involvement
- Needs to know: total exposure, default rate trend, which categories/products default most
- Goal: strategic credit policy decisions, not WhatsApp threads

---

## Core Product: MVP (v1)

### WhatsApp Infrastructure — Official API via Pakistani BSP

**This is a resolved question, not a risk.** The official WhatsApp Business API is available in Pakistan through local BSPs with PKR billing and same-day onboarding.

**Recommended BSP:** WeTarseel (Pakistan-based, PKR billing, pre-approved Urdu templates, 1-day onboarding) or Intellicon (enterprise-grade, strong local support).

**Why NOT WhatsApp Web automation:**
- Meta's detection systems flagged and banned 6.8M accounts in the first half of 2025 alone for unofficial automation
- Standard WhatsApp Business App triggers restrictions after just 20–30 messages/day to new contacts
- Building a B2B SaaS product on top of a ban-prone, ToS-violating foundation is not viable — one ban kills every retailer using the platform simultaneously
- Official API takes 1–2 business days to set up via a local BSP and costs PKR, not dollars

**Message requirements:**
- All outbound business-initiated messages must use Meta-approved templates
- Templates are approved once and reused with dynamic variables (customer name, amount, due date)
- Two-way responses (customer replies "PAID" or requests a callback) are fully supported within the 24-hour service window

---

### Module 1 — Customer Credit Ledger

**What it does:** Single source of truth for every customer's credit account.

**Key features:**
- Customer onboarding: name, CNIC, phone, address, guarantor name + phone
- Installment plan creation: product, total amount, down payment, installment amount, frequency (weekly/monthly), duration
- Payment recording: manual entry (MVP) → payment gateway link (Phase 2)
- Outstanding balance calculation in real time
- Customer status: Current / Late (1–7 days) / Late (8–30 days) / Drifted / Paid Off

**Design principles:**
- Mobile-first — ops manager is not at a desktop
- Urdu language support from day one
- Offline-capable with sync on reconnect

---

### Module 2 — Branched Collections Engine *(Core Differentiator)*

**What it does:** Replaces the manual WhatsApp follow-up loop with an intelligent, branched reminder and escalation workflow. Critically, it treats partial payers differently from total no-shows — because they are fundamentally different situations.

#### Branch A — Standard reminder sequence (all customers)

| Timing | Channel | Tone | Content |
|---|---|---|---|
| T-3 days | WhatsApp | Friendly | "Aapki agli kisht PKR X, [Date] ko due hai. JazzCash: [link]" |
| T-0 | WhatsApp + SMS | Neutral | "Aaj aapki kisht due hai — PKR X. Abhi pay karein: [link]" |
| T+1 | WhatsApp | Gentle | "Koi masla? Hum madad karne ke liye yahan hain. Ya aaj pay karein: [link]" |
| T+3 | WhatsApp | Firm | "Aapka account late ho gaya. Manager ko notify kar diya gaya. Please contact karein." |

After T+3, the sequence **branches** based on customer payment history:

#### Branch B — Soft re-engagement (partial payer: has paid ≥1 installment before)

*Assumption: this person can pay, has paid before, and has drifted. Tone stays warm.*

| Timing | Channel | Tone | Content |
|---|---|---|---|
| T+7 | WhatsApp | Warm/personal | "Aap ne pehle X installments on time diye thay — hum aapki madad karna chahte hain. Kya aap kal pay kar sakte hain?" |
| T+10 | WhatsApp | Collaborative | Offer: "Kya aap partial payment de sakte hain abhi?" Two-tap reply options: PKR amount choices |
| T+14 | Manager alert | — | Ops manager notified: "Soft recovery required — [name], [amount], [last paid date]" |
| T+21 | Field task | — | Recovery visit task auto-created, assigned to recovery agent |

#### Branch C — Hard escalation (total no-show: no payment since deposit)

*Assumption: something is wrong — either fraud, relocation, or genuine hardship.*

| Timing | Channel | Tone | Content |
|---|---|---|---|
| T+3 | WhatsApp + SMS | Firm | Standard escalation |
| T+5 | Guarantor WhatsApp | Formal | Automated message to guarantor on file |
| T+7 | Manager alert | — | Immediate ops manager notification |
| T+10 | Field task | — | Recovery visit task created with priority flag |

**Two-way WhatsApp capability:**
- Customer replies "PAID" → ledger auto-updated, receipt sent, sequence paused
- Customer replies "HELP" or any message → ops manager notified immediately for human handoff
- Customer replies with a date → system notes it and sends a confirmation, then resumes sequence from that date

**Configuration options per retailer:**
- Enable/disable any step in the sequence
- Set tone (formal/informal) per customer segment
- Set reminder frequency (aggressive / standard / light)
- Whitelist VIP customers for manager-only contact (no automated messages)

---

### Module 3 — Recovery Task Manager

**What it does:** Converts escalated accounts into structured field recovery tasks.

**Key features:**
- Auto-generates recovery task when Branch B hits T+21 or Branch C hits T+10
- Assigns to named recovery agent
- Daily route-optimised task list (Google Maps integration)
- Task card shows: customer name, address, amount owed, last payment date, notes from WhatsApp thread
- Agent updates via mobile: Visited / Promised to pay [date] / Partial payment collected / Unreachable / Address incorrect
- Manager sees real-time recovery pipeline

---

### Module 4 — Portfolio Dashboard

**What it does:** Real-time credit health view for owners/CEOs.

**Key metrics:**
- Total credit deployed (PKR)
- Current / Late / Drifted / In recovery breakdown with PKR values
- Monthly collections vs. expected (trend line)
- Default rate trend (rolling 6 months)
- Top 10 at-risk accounts
- Reminder response rate (% of customers who pay within 24 hours of first reminder)

---

## KishtScore — Phase 2 Feature *(moved from Phase 1)*

**Why it moves to Phase 2:** A credit score is only as good as the data behind it. With zero historical repayment behaviour data in the system on Day 1, any score generated would be noise. After 6–9 months of reminder sequences running, response patterns, payment timing, and partial-pay behaviour accumulate into a genuinely predictive dataset. That's when KishtScore becomes useful.

### Phase 2A — Intra-retailer score (Months 7–12)
Built from:
- Payment punctuality (days early / on time / days late, per installment)
- Reminder response rate (opens, replies, ignores — per message)
- Historical pattern: did this customer drift and recover, or drift and disappear?
- Guarantor responsiveness when contacted
- Ticket size relative to payment consistency

Output: 1–5 star score shown when creating a new credit account for a returning customer. "This customer has a KishtScore of 4.2 — they've paid 11 of 12 installments, average 1.2 days late."

### Phase 2B — Network score (Months 13–18)
When multiple retailers are on the platform, repayment behaviour is pooled (with retailer consent and customer disclosure at point of credit application).

**Critical reframe from v1.0:** The network score's primary value is not catching "bad" borrowers — your true default rate shows those are vanishingly rare. The real value is **drift detection**: a customer who has gone unresponsive across 3 retailers simultaneously in the past 60 days is almost certainly a relocation or hardship case. Knowing this early — before sending a recovery agent on a wasted visit — is the actionable insight.

Use case: "This CNIC has active accounts at 2 other KistBook retailers and has missed the last 3 reminders at both. Likely relocated. Recommend: guarantor contact before field visit."

**Data governance:**
- CNIC is the matching key (not name — too many collisions in Pakistani data)
- Retailers opt in to data sharing; they receive reciprocal access only if they share
- Customers are informed at point of credit application
- Network score is shown to retailers, not to customers or third parties

---

## WhatsApp API: Vendor Recommendation

| BSP | Pricing | Setup time | Urdu templates | PKR billing | Recommendation |
|---|---|---|---|---|---|
| WeTarseel | SME-friendly, PKR | 1 business day | Pre-built library | Yes | **Start here for MVP** |
| Intellicon | Enterprise, PKR | 2–3 days | Yes | Yes | Consider at scale |
| Interakt (India) | USD | 2–7 days | Limited | No | Avoid for MVP |

**Setup requirements for KistBook (applies to any BSP):**
- SECP business registration
- NTN certificate
- Company website (ShopHive.com qualifies)
- Dedicated phone number not previously registered on WhatsApp
- Meta Business Manager account

**Message template requirements:**
- All outbound templates submitted to Meta for approval (usually 24 hours)
- Templates use dynamic variables: `{{customer_name}}`, `{{amount}}`, `{{due_date}}`, `{{payment_link}}`
- Urdu templates supported natively
- One-time approval — reused indefinitely with variable substitution

---

## Product Roadmap

### Phase 1 — Collections Foundation (Months 1–6)
**Goal:** Prove that automated reminders materially reduce late payments vs. manual WhatsApp.

Deliverables:
- Customer credit ledger (Module 1)
- Branched collections engine — WhatsApp API via WeTarseel (Module 2)
- Basic portfolio dashboard (Module 4)
- Urdu + English message templates (pre-approved with Meta)
- Manual payment recording (no payment gateway integration yet)

Pilot: 10–15 Lahore electronics retailers, onboarded personally by founder.

**Success metrics:**
- Days Sales Outstanding (DSO) reduction vs. baseline (target: 30%+ improvement)
- % of overdue accounts resolved without field visit (target: >60%)
- Retailer NPS > 50
- Reminder-to-payment conversion rate (% who pay within 48 hours of first reminder)

### Phase 2 — Intelligence Layer (Months 7–12)
**Goal:** Add recovery coordination and the first version of KishtScore. Expand geography.

Deliverables:
- Recovery Task Manager with agent mobile app (Module 3)
- KishtScore — intra-retailer (Phase 2A)
- JazzCash / EasyPaisa payment link embedded in reminder messages
- Two-way WhatsApp (customer self-service: reply to confirm, reschedule, or report issue)
- Expand to Karachi and Islamabad

**Success metrics:**
- KishtScore predicts late payment with >70% accuracy vs. baseline
- Field visit efficiency: recovery agent closes >50% of visits (vs. estimated <20% today)
- 50+ active retailers on platform
- Monthly transaction fee revenue: PKR 2M+

### Phase 3 — Network and Platform (Months 13–24)
**Goal:** Build the network effect that makes KistBook irreplaceable.

Deliverables:
- Network KishtScore (Phase 2B) — cross-retailer drift detection
- KishtScore API for BNPL providers and NBFCs (new revenue stream)
- eCommerce platform integrations (WooCommerce, Shopify Pakistan)
- Embedded receivables financing (partner NBFC advances against KistBook-verified installment book)
- International expansion: Bangladesh, then Egypt

---

## Business Model

### Core: Transaction fee on collections
- KistBook takes **1.5–2.5% of each installment collected through the platform**
- Incentive alignment: KistBook only earns when the retailer recovers money
- Fee is only charged on installments where a KistBook-sent reminder or workflow was active — retailers are not charged for installments customers pay spontaneously before any reminder fires

### Secondary (Phase 2+): KishtScore API
- Charge fintechs, BNPL providers, NBFCs for network credit score access via API
- Price: PKR 50–200 per credit inquiry
- High margin, zero incremental cost once network data exists

### Tertiary (Phase 3): Embedded financing spread
- Advance retailers against their verified installment receivables
- KistBook's repayment data makes underwriting dramatically cheaper than any bank
- Revenue: spread between cost of capital and advance rate

### Unit economics (illustrative, per retailer)

| Metric | Value |
|---|---|
| Active installment customers | 300 |
| Average ticket | PKR 100,000 |
| Average plan duration | 10 months |
| Monthly collections per retailer | ~PKR 2,500,000 |
| KistBook fee at 2% | **PKR 50,000/month** |

**Portfolio:**

| Retailers | Monthly Revenue |
|---|---|
| 50 | PKR 2.5M (~$9K USD) |
| 100 | PKR 5M (~$18K USD) |
| 500 | PKR 25M (~$90K USD) |

At 500 retailers KistBook is generating ~$1M+ ARR in transaction fees alone, before the KishtScore API revenue layer.

---

## Go-to-Market Strategy

### Beachhead: Lahore electronics corridor
ShopHive's CEO network is the unfair advantage. The initial GTM:
1. ShopHive uses KistBook first (dogfooding) — generates the case study with real DSO and recovery numbers
2. CEO personally onboards 5–10 adjacent Lahore electronics retailers in Months 1–2
3. Each retailer's measurable improvement becomes the sales asset for the next conversation

### The demo that sells itself
Show a retailer their current reality: a WhatsApp thread with 200 customers, no structure, payments going untracked. Then show KistBook's dashboard with every account, status, last reminder, and next action clearly visible. The contrast closes deals without a pitch.

### Sales motion
- Direct sales, founder-led in Phase 1
- Free 30-day trial with white-glove onboarding (CEO personally migrates their first 50 customers)
- No setup fee — transaction fee only
- Onboarding SLA: retailer is live with first automated reminders running within 48 hours of signup

### Retention moat
After 12 months, a retailer's entire customer payment history, reminder response patterns, and collections workflow live in KistBook. Switching cost is near-infinite — they lose their data, their KishtScores, and their automation. Churn risk drops precipitously after Month 6.

---

## Technical Architecture

### Stack
- **Backend:** Python (FastAPI) — REST API; clean, fast, well-supported in Pakistan's developer market
- **Database:** PostgreSQL (installment schedules, payment records, reminder logs) + Redis (reminder queue and scheduling)
- **Mobile:** React Native — single codebase for iOS and Android (ops managers + recovery agents)
- **Web dashboard:** React.js
- **WhatsApp:** Meta Cloud API via WeTarseel BSP
- **SMS fallback:** Telenor or Jazz bulk SMS API (for customers who don't use WhatsApp)
- **Hosting:** AWS ap-south-1 (Mumbai) or Google Cloud asia-south1 — lowest latency to Pakistan, acceptable data residency posture

### Integrations (Phase 1)
| Integration | Purpose | Priority |
|---|---|---|
| WhatsApp Business API (via WeTarseel) | Core reminder channel | P0 |
| SMS gateway (Telenor/Jazz) | Fallback for non-WhatsApp users | P0 |
| Google Maps API | Recovery agent route optimisation | P1 |
| JazzCash payment link API | Embedded payment in reminder messages | P1 |
| EasyPaisa payment link API | Same as above | P1 |

### Data model (simplified)
- `Retailers` — B2B customers
- `Customers` — end borrowers (CNIC as unique identifier)
- `CreditAccounts` — one per customer × retailer relationship
- `InstallmentSchedule` — one row per expected payment date/amount
- `Payments` — actual payments received (amount, date, method, channel)
- `ReminderLogs` — every outbound message (channel, timestamp, template, delivery status) + inbound response
- `RecoveryTasks` — field visit assignments with status
- `KishtScores` — computed scores per customer per retailer + network aggregate (Phase 2)

### Reminder queue architecture
The reminder engine is the most critical system in the product. It must:
- Run scheduled jobs reliably (cron + Redis queue)
- Handle WhatsApp API rate limits gracefully (Meta enforces per-phone-number messaging limits that increase with business tier)
- Retry failed messages via SMS fallback automatically
- Be auditable: every message sent, delivered, read, or failed is logged with timestamp
- Be idempotent: a server restart or duplicate job execution must never send a reminder twice

---

## Regulatory Considerations

- **KistBook is not a lender.** It is a SaaS collections tool for retailers extending their own credit. This keeps KistBook outside SECP NBFC licensing at launch — critical.
- **KishtScore is a proprietary business intelligence score**, not a formal credit bureau report. Formal credit bureau registration (SECP-regulated) is a Phase 3 option, not a requirement.
- **Data sharing (Phase 2):** Pakistan's Personal Data Protection Act (2023) applies. Customer CNIC data must be encrypted at rest and in transit. Network score data sharing requires documented retailer consent and customer disclosure at point of credit application.
- **WhatsApp compliance:** All message templates must include an opt-out mechanism. Retailer must have prior relationship with the customer (which they do — by definition, they extended credit to them).

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| WhatsApp API account quality issues (low delivery rates if customers block messages) | Medium | High | Use pre-approved Urdu templates with personalisation to maximise relevance. Monitor account health score in Meta dashboard daily. Add SMS as automatic fallback. |
| Retailers unwilling to share customer CNIC data for network score | Low (founder confirms not an issue) | High | Validated. Start sharing from Phase 2 with clear reciprocal benefit framing. |
| Competitor (Moneypex, UR QistPro) copies branched reminder logic | Medium | Medium | First-mover network data. A copied reminder engine without 12 months of repayment data behind the KishtScore is just a reminder tool — commoditised. |
| Low GMV on platform in Phase 1 = low transaction fee revenue | Medium | Medium | Acceptable. Phase 1 is validation, not scale. 15 retailers × PKR 50K/month = PKR 750K/month — enough to fund operations. |
| SECP reclassifies KishtScore as a credit bureau | Low | High | Engage SECP proactively from Year 1. Structure network data sharing as "retailer consortia tool" not "credit bureau." Legal counsel engaged before Phase 2B launch. |

---

## Success Metrics (North Star KPIs)

### Retailer outcomes
- **DSO reduction:** Days Sales Outstanding vs. pre-KistBook baseline (target: >30% reduction in 90 days)
- **Recovery rate:** % of late accounts resolved without field visit (target: >60%)
- **Reminder conversion:** % of customers who pay within 48 hours of first automated reminder

### Platform growth
- Monthly Active Retailers (MAR)
- Total installment GMV on platform (PKR)
- Unique CNICs in network (Phase 2+)

### Revenue
- Monthly transaction fee revenue (PKR)
- Revenue per retailer (should increase over time as retailers migrate more of their book to the platform)
- Net Revenue Retention (target: >110%)

### Product quality
- WhatsApp message delivery rate (target: >95%)
- Reminder response rate (customers engaging with automated messages)
- KishtScore predictive accuracy vs. actual default/drift rate (Phase 2+)

---

## Appendix A: Competitive Positioning Map

```
                        HIGH INTELLIGENCE
                               |
             ClearGrid          |          KistBook ←
             (banks/BNPL,       |          (SME retail,
              MENA, $10M)       |           Pakistan)
                               |
LARGE ——————————————————————————————————————————— SME
ENTERPRISE                     |
                               |
             Core banking       |     Moneypex / UR QistPro
             systems            |     (ledger + basic reminders,
                               |      no intelligence)
                               |
                        LOW INTELLIGENCE
```

KistBook occupies an uncontested quadrant: **SME-focused, high intelligence**. Enterprise intelligence tools (ClearGrid, Credgenics) are too expensive and complex for Pakistani SME retailers. Existing Pakistani tools are ledgers, not collections engines. KistBook is the gap.

---

## Appendix B: Recommended First 90 Days

| Week | Action |
|---|---|
| 1–2 | Register WhatsApp Business API via WeTarseel. Set up Meta Business Manager. Submit Urdu message templates for approval. |
| 2–3 | Build MVP ledger and manual payment recording. Internal test with ShopHive's own 300-customer book. |
| 3–4 | Activate reminder sequences on ShopHive's overdue accounts. Measure DSO before and after. |
| 4–6 | Onboard first 3 external pilot retailers. White-glove data migration. |
| 6–8 | Measure DSO improvement across pilots. Document 2–3 case studies with specific PKR recovered. |
| 8–12 | Use case studies to close next 10 retailers. Begin building recovery task manager. |

---

*Document prepared for internal strategy use. Not for external distribution.*
*Version 2.0 reflects validated answers from ShopHive CEO on: WhatsApp API feasibility in Pakistan, true portfolio default rate, and nature of late-payment problem.*
