# QuickBite — Food Delivery Platform  
### DBMS Phase 2 | Group [Number]

---

## Setup & Run

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and set JWT_SECRET and FLASK_SECRET to long random strings
```

### 3. Start the server
```bash
cd backend
python app.py
```
Server runs at `http://127.0.0.1:5000`  
Frontend is served automatically by Flask — open `http://127.0.0.1:5000` in your browser.

---

## Authentication

All protected endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The token is returned by `POST /api/v1/login` and `POST /api/v1/signup`.  
Tokens expire after 24 hours.

---

## Test Credentials

| Role     | Email            | Password |
|----------|------------------|----------|
| Admin    | ahsen@gmail.com  | hassan   |
| Customer | Sign up via UI   | —        |
| Rider    | Sign up + admin approval | —  |
| Manager  | Created by admin | —        |

---

## Roles & Access

| Role     | Can Do |
|----------|--------|
| customer | Browse restaurants/produce, place orders, chat rider, loyalty |
| rider    | View available orders, accept & deliver, chat customer |
| manager  | Manage own restaurant, menu items, categories, view stats |
| admin    | Full platform control: approve riders/restaurants, manage promos, view audit log |

---

## Transaction Scenarios (Phase 2)

Two critical operations use explicit `BEGIN / COMMIT / ROLLBACK`:

**Scenario 1 — Place Restaurant Order** (`POST /api/v1/orders`):  
Atomic across: INSERT order → INSERT order_items (validated) → validate promo → award loyalty → COMMIT  
Rolls back on: invalid/unavailable item, expired promo, insufficient loyalty points, any DB error.

**Scenario 2 — Place Produce Order** (`POST /api/v1/produce/order`):  
Same pattern for produce items. Rolls back on unavailable produce, bad promo, loyalty underflow.

Rollback evidence: `media/rollback_demo.log`

---

## File Structure

```
quickbite/
├── backend/
│   ├── app.py                   # Flask server — all routes, JWT auth, RBAC, transactions
│   ├── requirements.txt         # Python dependencies
│   ├── schema.sql               # Full database schema
│   ├── seed.sql                 # Default data (admin, promos)
│   ├── swagger.yaml             # OpenAPI 3.0 spec
│   └── Backend_Explanation.pdf  # Architecture & design document
├── frontend/
│   └── pages/                   # HTML/CSS/JS frontend
├── media/
│   └── rollback_demo.log        # Transaction rollback demonstration
├── .env.example                 # Environment variable template
└── README.md
```

---

## API Versioning

All endpoints are available at both:
- `/api/v1/...` — versioned (current)
- `/api/...` — legacy alias (backward compatible)

Contact: Jalal Ahmed (bscs23134@itu.edu.pk) | Khadijah Farooqi (bscs23128@itu.edu.pk)
