# QuickBite — Food & Grocery Delivery Platform

> **Course:** Advanced Database Management — CS 4th Semester (A & B)
> **Phase:** 3 — Frontend & Final Submission
> **Deadline:** 25 March 2026

---

## Team Members

| Name | Roll Number |
|------|-------------|
| Hassan Ali | BSCS23-___ |
| _(add members)_ | BSCS23-___ |

**Group Number:** `[YOUR GROUP NUMBER]`

---

## Project Overview

**QuickBite** is a full-stack food and fresh-produce delivery platform targeting the Pakistani urban market. It solves the problem of fragmented local delivery by offering a single platform for:

- **Restaurant food ordering** with real-time order tracking
- **Fresh produce (fruits & vegetables)** sold by weight (kg)
- **Multi-role management** — customers, restaurant managers, delivery riders, and an admin
- **Loyalty rewards** and **promo code discounts** on every order

The backend is a Flask REST API backed by SQLite with full ACID-compliant transactions, JWT authentication, and PBKDF2-HMAC-SHA256 password hashing. The frontend is a role-gated multi-page HTML/CSS/JS application.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML5 / CSS3 / JavaScript (ES2020+) |
| Backend | Python 3.11+ / Flask 3.x |
| Database | SQLite 3 (WAL mode) |
| Auth | JWT HS256 (stdlib hmac + hashlib, no extra deps) |
| Password hashing | PBKDF2-HMAC-SHA256 — 310,000 iterations (NIST SP 800-132) |
| CORS | flask-cors |
| API Docs | OpenAPI 3.0 (swagger.yaml) |
| Styling | Custom CSS with dark/light mode toggle |
| Charts | Chart.js (CDN) — admin analytics dashboard |

---

## System Architecture

```
Browser (HTML/JS)
      |  Authorization: Bearer <JWT>
      |  Content-Type: application/json
      v
Flask Backend  (backend/app.py — port 5000)
      |  SQLite parameterized queries
      |  BEGIN / COMMIT / ROLLBACK transactions
      v
SQLite Database  (backend/food_delivery.db)
      |
      +-- users, riders, restaurants
      +-- orders, order_items
      +-- produce_items, produce_orders, produce_order_items
      +-- messages, reviews, audit_log
      +-- promo_codes, loyalty_points, loyalty_transactions
      +-- (18 indexes — see database/performance.sql)
```

The frontend is served **directly from Flask** at `/` — this eliminates all CORS issues. All API calls attach a JWT Bearer token stored in `localStorage`.

---

## Directory Structure

```
Group[Number]_Phase3_QuickBite/
|
+-- frontend/
|   +-- src/
|   |   +-- index.html              <- Login / Register page
|   |   +-- css/main.css            <- All styles + dark mode
|   |   +-- js/shared.js            <- API helper, JWT, auth guards
|   |   +-- pages/
|   |       +-- admin/              <- dashboard, orders, users, riders, restaurants, promos, audit, chat
|   |       +-- customer/           <- home, orders, track, produce, loyalty, profile, chat
|   |       +-- manager/            <- dashboard, menu-manager, orders, setup, pending, profile
|   |       +-- rider/              <- dashboard, pending, my-orders, profile
|   +-- public/index.html
|   +-- package.json
|   +-- .env.example
|
+-- backend/
|   +-- app.py                      <- Flask app (all-in-one)
|   +-- requirements.txt
|   +-- .env.example
|   +-- food_delivery.db            <- SQLite database (auto-created on first run)
|   +-- uploads/                    <- Restaurant & produce images
|
+-- database/
|   +-- schema.sql                  <- Full table definitions + indexes
|   +-- seed.sql                    <- Admin user + promo codes
|   +-- performance.sql             <- Index benchmarks (EXPLAIN QUERY PLAN)
|
+-- docs/
|   +-- ER_Diagram.pdf
|   +-- Schema_Documentation.pdf
|   +-- ACID_Documentation.pdf
|   +-- swagger.yaml                <- OpenAPI 3.0 — all 61 endpoints
|   +-- Backend_Explanation.pdf
|
+-- media/
|   +-- rollback_demo.log           <- Live rollback scenario proof
|
+-- README.md
```

> **Deviation from rubric structure:** The backend is a single `app.py` rather than split into routes/controllers/models folders. This was chosen to keep SQLite transactions atomic within a single module scope. All functions are clearly commented by domain section.

---

## UI Examples

### 1. Customer Home — Restaurant Browsing
The homepage lets customers browse approved and open restaurants with a live search bar. Each card shows rating, cuisine, and Open/Closed badge. This is the core customer-facing entry point to the ordering flow.

### 2. Checkout — Atomic Transaction Demo
The checkout shows a live fee breakdown (subtotal, delivery PKR 50, platform fee 5%, rider tip 10%), promo code validation, and loyalty point redemption. On submit, the backend performs a full BEGIN/COMMIT/ROLLBACK transaction. If any item is unavailable or the promo is exhausted, the user sees a specific error and NO partial order is created.

### 3. Admin Analytics Dashboard
The admin dashboard renders Chart.js bar and doughnut charts of orders and revenue. It also shows live KPI stats (total users, orders, revenue, pending riders). This satisfies the "analytics dashboard with charts" complex feature requirement.

---

## Setup & Installation

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| pip | any recent |
| Browser | Chrome / Firefox / Edge |

No Node.js or npm required for the frontend (static HTML).

### Step 1 — Clone the repository

```bash
git clone https://github.com/Hassan-Ali-17/Zaiqa-On-Wheels-Food-and-groceries-ordering-website.git
cd Zaiqa-On-Wheels-Food-and-groceries-ordering-website
```

### Step 2 — Set up backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set JWT_SECRET and FLASK_SECRET to random strings
```

### Step 3 — Configure .env

```env
FLASK_SECRET=your_random_secret_here_min_32_chars
JWT_SECRET=another_random_secret_here_min_32_chars
FLASK_ENV=development
PORT=5000
```

Generate secrets:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4 — Start the backend (auto-initializes DB)

```bash
python3 app.py
# Running on http://127.0.0.1:5000
```

### Step 5 — Open the app

```
http://127.0.0.1:5000
```

Flask serves the frontend directly. No separate server needed.

---

## User Roles

| Role | Email | Password | Can Do |
|------|-------|----------|--------|
| admin | admin@quickbite.com | admin123 | Everything: users, restaurants, riders, promos, analytics, audit log |
| customer | customer@quickbite.com | test123 | Browse, order food, order produce, track, chat, loyalty |
| manager | manager@quickbite.com | test123 | Manage own restaurant menu, view orders and stats |
| rider | rider@quickbite.com | test123 | Accept orders, update delivery status, chat, view earnings |

RBAC is enforced at both levels:
- **Backend:** `require_auth(*roles)` decorator returns 401/403 before any business logic
- **Frontend:** `requireAuth(role)` guard at top of every page redirects to login on mismatch

---

## Feature Walkthrough

### Authentication
- Login/Register — `POST /api/login` — JWT issued on success, stored in localStorage
- Logout — `POST /api/logout` — clears localStorage
- All pages redirect to login if no valid token present

### Customer
- Browse restaurants with live search and cuisine filter
- Add items to cart, apply promo codes, redeem loyalty points
- Checkout with atomic transaction (BEGIN/COMMIT/ROLLBACK)
- Real-time order tracking with 4-second polling
- Bidirectional chat with rider
- Fresh produce market — buy fruits & vegetables by kg
- View loyalty points balance and transaction history

### Admin
- Analytics dashboard with Chart.js visualizations
- Full CRUD on restaurants, promo codes
- Approve/reject rider and restaurant applications
- View complete audit log of all system events
- Monitor all user conversations

### Manager
- Set up restaurant profile and menu
- Full CRUD on menu categories and items
- Toggle item availability without editing
- View incoming orders and revenue stats

### Rider
- View and accept available delivery orders
- Update order status through delivery lifecycle
- Chat with customers
- View total earnings

---

## Complex Features

### 1. Analytics Dashboard with Charts
`admin/dashboard.html` uses Chart.js (loaded from CDN) to render:
- Bar chart of top restaurants by order volume
- Doughnut chart of revenue breakdown
- KPI cards with live platform statistics

### 2. Real-Time Updates via Polling
Order tracking (`customer/track.html`) and chat pages use `setInterval` with 4-second polling to provide near-real-time order status and message updates without WebSockets.

---

## Transaction Scenarios

### Food Order — `place_order()` in `backend/app.py`

**Trigger:** Customer submits cart checkout

**Atomic steps:**
1. Validate menu items available and belong to restaurant
2. Validate promo code active and within usage limit
3. Validate sufficient loyalty points for redemption
4. INSERT orders row
5. INSERT order_items rows
6. UPDATE loyalty_points (award earned)
7. UPDATE promo_codes (increment used_count)
8. UPDATE loyalty_points (deduct redeemed)

**Rollback triggers:** Any ValueError or Exception → ROLLBACK → error returned to user → no partial state in DB

### Produce Order — `place_produce_order()` in `backend/app.py`

Identical structure for produce market orders.

---

## ACID Compliance

| Property | Implementation |
|----------|---------------|
| Atomicity | BEGIN/COMMIT/ROLLBACK in place_order() and place_produce_order(). Any exception triggers full ROLLBACK. |
| Consistency | CHECK constraints on price, rating, role/status ENUMs. UNIQUE on email, loyalty customer. FOREIGN KEY constraints with CASCADE/SET NULL. |
| Isolation | SQLite WAL mode (PRAGMA journal_mode=WAL). Each request opens and closes its own connection. |
| Durability | PRAGMA synchronous=NORMAL flushes WAL to disk. All events logged to audit_log table. |

---

## Indexing & Performance

18 indexes defined in `database/schema.sql`, benchmarked in `database/performance.sql`.

| Index | Purpose |
|-------|---------|
| idx_orders_customer | Customer order history page |
| idx_orders_status | Rider polls for available orders |
| idx_menu_restaurant | Restaurant menu page load |
| idx_messages_pair | Chat history (polled every 4s) |
| idx_restaurants_status | Homepage approved+open filter |
| idx_users_email | Login lookup on every sign-in |

All 8 critical queries improve from SCAN TABLE (O(n)) to SEARCH USING INDEX (O(log n)).

---

## API Reference

Full detail in `docs/swagger.yaml`. Quick reference:

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| POST | /api/signup | None | Register |
| POST | /api/login | None | Login, returns JWT |
| GET | /api/restaurants | None | List restaurants |
| POST | /api/orders | customer | Place order (atomic) |
| GET | /api/orders/customer/:id | customer | Order history |
| POST | /api/produce/order | customer | Place produce order |
| POST | /api/messages | any | Send message |
| GET | /api/admin/stats | admin | Analytics |
| PUT | /api/admin/riders/:id/approve | admin | Approve rider |
| POST | /api/manager/menu-item | manager | Add menu item |
| GET | /api/orders/available | rider | Available orders |

---

## Known Issues & Limitations

| Issue | Notes |
|-------|-------|
| Legacy password hashing | SHA-256 accounts still work via fallback. New accounts use PBKDF2. |
| No JWT refresh tokens | Tokens expire after 24h; user must log in again. |
| SQLite concurrency | WAL handles moderate load. Not for high-concurrency production. |
| Polling vs WebSockets | Real-time uses 4s polling. Functional but less efficient than WebSockets. |
| Backend structure | Single app.py instead of routes/controllers/models — documented deviation. |

---

## Contact

**TAs:** Jalal Ahmed (bscs23134@itu.edu.pk) | Khadijah Farooqi (bscs23128@itu.edu.pk)
**Office Hours:** Monday & Thursday 11:30 AM – 2:30 PM
