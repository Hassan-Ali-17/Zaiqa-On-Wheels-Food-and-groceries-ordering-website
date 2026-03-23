# Zaiqa On Wheels 🍽️🛒
### Food & Grocery Ordering Web Application

Zaiqa On Wheels is a full-stack food and grocery ordering platform that allows users to browse restaurant menus and grocery items, manage their cart, place orders, and track deliveries through a secure and responsive interface.

The system demonstrates a complete end-to-end web solution, integrating:
- Frontend user interface
- Backend API services
- Authentication and authorization
- Database management
- Transaction control

> Built using **Python (Flask)**, **HTML**, **CSS**, **JavaScript**, and **SQLite** — showcasing practical concepts from Web Development and Database Management Systems (DBMS).
---

## 👨‍💻 Contributors

| Name | ID |
|---|---|
| Hassan Ali Shah | BSCS24040 |
| Ahsen Ali | BSCS24056 |

---

## 🚀 Key Features

### 🔐 User Authentication
- Secure user registration and login
- JWT-based authentication with PBKDF2-HMAC-SHA256 password hashing
- Token expiration after 24 hours
- Protected API routes using Bearer tokens
- Role-Based Access Control (RBAC) enforced on both frontend and backend

### 🛒 Cart Management
Users can:
- Add items to their cart
- Remove items from cart
- Update item quantities
- View cart before checkout
- Apply promo codes and redeem loyalty points at checkout

### 🍔 Food & Grocery Browsing
The platform supports two types of ordering:

**Restaurant Ordering** — Users can:
- Browse restaurant menus with live search and cuisine filter
- Select menu items and manage cart
- Apply promotions and redeem loyalty points
- Place restaurant orders with atomic transactions

**Produce / Grocery Ordering** — Users can:
- Browse available fruits and vegetables
- Buy fresh produce by weight (kg)
- Place grocery orders with full transaction support

### 📦 Order Management
Customers can:
- Place orders with full ACID-compliant checkout
- Track delivery status in real-time (4-second polling)
- View previous order history
- Earn and redeem loyalty points from purchases
- Chat with riders during active deliveries

### 🗂️ Admin Panel
Admins have full system control including:
- Approving/rejecting riders and restaurants
- Managing promotions and promo codes
- Monitoring the complete audit log
- Viewing all user conversations
- Analytics dashboard with Chart.js visualizations

### 👨‍🍳 Restaurant Manager Tools
Managers can:
- Set up and manage their restaurant profile
- Full CRUD on menu categories and items
- Toggle item availability without deleting
- View incoming orders and revenue statistics

### 🚴 Rider Delivery System
Riders can:
- View and accept available delivery orders
- Update order status through the delivery lifecycle
- Chat with customers
- View total earnings

### 📱 Responsive Design
The UI is optimized for Desktop, Tablets, and Mobile devices with a built-in dark/light mode toggle.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript (ES2020+) |
| Backend | Python 3.11+, Flask 3.x |
| Database | SQLite 3 (WAL mode) |
| Authentication | JWT HS256 (stdlib hmac + hashlib) |
| Password Hashing | PBKDF2-HMAC-SHA256 — 310,000 iterations (NIST SP 800-132) |
| CORS | flask-cors |
| API Docs | OpenAPI 3.0 / Swagger |
| Charts | Chart.js (CDN) |

---

## 🏗️ System Architecture

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

The frontend is served **directly from Flask** at `/` — this eliminates all CORS issues.

---

## 📂 Project Structure

```
Zaiqa-On-Wheels/
│
├── frontend/
│   └── src/
│       ├── index.html                  ← Login / Register page
│       ├── css/main.css                ← All styles + dark mode
│       ├── js/shared.js                ← API helper, JWT, auth guards
│       └── pages/
│           ├── admin/                  ← dashboard, orders, users, riders, restaurants, promos, audit, chat
│           ├── customer/               ← home, orders, track, produce, loyalty, profile, chat
│           ├── manager/                ← dashboard, menu-manager, orders, setup, pending, profile
│           ├── rider/                  ← dashboard, pending, my-orders, profile
│           └── restaurant/             ← menu (customer-facing restaurant page)
│
├── backend/
│   ├── app.py                          ← Flask app (all routes, JWT auth, RBAC, transactions)
│   ├── requirements.txt
│   ├── .env.example
│   ├── food_delivery.db                ← SQLite database (auto-created on first run)
│   └── uploads/                        ← Restaurant & produce images
│
├── database/
│   ├── schema.sql                      ← Full table definitions + indexes
│   ├── seed.sql                        ← Admin user + promo codes
│   └── performance.sql                 ← Index benchmarks (EXPLAIN QUERY PLAN)
│
├── docs/
│   ├── swagger.yaml                    ← OpenAPI 3.0 — all endpoints
│   ├── ER_Diagram.drawio
│   ├── UML_ClassDiagram.drawio
│   └── Backend_Explanation.docx
│
├── media/
│   └── rollback_demo.log               ← Live rollback scenario proof
│
└── README.md
```

---

## ▶️ How to Run the Project

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| pip | any recent |
| Browser | Chrome / Firefox / Edge |

No Node.js or npm required.

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Hassan-Ali-17/Zaiqa-On-Wheels-Food-and-groceries-ordering-website.git
cd Zaiqa-On-Wheels-Food-and-groceries-ordering-website
```

### 2️⃣ Navigate to the Backend Directory
```bash
cd backend
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables
```bash
cp .env.example .env
```
Edit `.env` and set:
```env
FLASK_SECRET=your_random_secret_here_min_32_chars
JWT_SECRET=another_random_secret_here_min_32_chars
FLASK_ENV=development
PORT=5000
```
Generate secrets instantly:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5️⃣ Run the Application
```bash
python app.py
```

The server starts at `http://127.0.0.1:5000`. Flask serves the frontend automatically — open in your browser:
```
http://127.0.0.1:5000
```

---

## 👥 User Roles & Default Credentials

| Role | Email | Password | Capabilities |
|---|---|---|---|
| **Admin** | ahsen@gmail.com | hint**24040 name** | Full platform control — users, restaurants, riders, promos, analytics, audit log |
| **Customer** | customer@quickbite.com | test123 | Browse, order food & produce, track, chat, loyalty points |
| **Manager** | manager@quickbite.com | test123 | Manage own restaurant menu, categories, view orders and stats |
| **Rider** | rider@quickbite.com | test123 | Accept orders, update delivery status, chat, view earnings |

RBAC is enforced at two levels:
- **Backend:** `require_auth(*roles)` decorator returns 401/403 before any business logic runs
- **Frontend:** `requireAuth(role)` guard at the top of every page redirects to login on role mismatch

---

## 🔑 Authentication System

All protected API endpoints require a JWT Bearer token:
```
Authorization: Bearer <token>
```

Tokens are obtained from:
```
POST /api/login
POST /api/signup
```

**Token validity:** 24 hours

---

## 🧾 Database Transaction Scenarios (DBMS)

Two critical operations implement explicit transaction management using `BEGIN`, `COMMIT`, and `ROLLBACK` — ensuring full ACID compliance.

### Scenario 1 — Place Restaurant Order
**Endpoint:** `POST /api/orders`

**Atomic steps:**
1. Validate menu items are available and belong to the restaurant
2. Validate promo code is active and within usage limit
3. Validate sufficient loyalty points for redemption
4. INSERT orders row
5. INSERT order_items rows
6. UPDATE loyalty_points (award earned points)
7. UPDATE promo_codes (increment used_count)
8. UPDATE loyalty_points (deduct redeemed points)

**Rollback triggers:** Any `ValueError` or `Exception` → full `ROLLBACK` → specific error returned to user → zero partial state in DB

### Scenario 2 — Place Produce Order
**Endpoint:** `POST /api/produce/order`

Identical transaction structure for the fresh produce market.

**Rollback occurs if:** Produce item unavailable, promotion invalid, loyalty underflow, or any database error.

> Rollback proof is available in: `media/rollback_demo.log`

---

## ✅ ACID Compliance

| Property | Implementation |
|---|---|
| **Atomicity** | `BEGIN`/`COMMIT`/`ROLLBACK` in `place_order()` and `place_produce_order()`. Any exception triggers full rollback. |
| **Consistency** | CHECK constraints on price, rating, role/status ENUMs. UNIQUE on email. FOREIGN KEY constraints with CASCADE/SET NULL. |
| **Isolation** | SQLite WAL mode (`PRAGMA journal_mode=WAL`). Each request opens and closes its own connection. |
| **Durability** | `PRAGMA synchronous=NORMAL` flushes WAL to disk. All events logged to `audit_log` table. |

---

## 📊 Indexing & Performance

18 indexes defined in `database/schema.sql`, benchmarked in `database/performance.sql`.

| Index | Purpose |
|---|---|
| idx_orders_customer | Customer order history page |
| idx_orders_status | Rider polls for available orders |
| idx_menu_restaurant | Restaurant menu page load |
| idx_messages_pair | Chat history (polled every 4s) |
| idx_restaurants_status | Homepage approved + open filter |
| idx_users_email | Login lookup on every sign-in |

All critical queries improve from full table scan O(n) to indexed lookup O(log n).

---

## 🔗 API Reference

Full detail in `docs/swagger.yaml`. Quick reference:

| Method | Route | Auth | Purpose |
|---|---|---|---|
| POST | /api/signup | None | Register new user |
| POST | /api/login | None | Login, returns JWT |
| GET | /api/restaurants | None | List approved restaurants |
| POST | /api/orders | customer | Place order (atomic transaction) |
| GET | /api/orders/customer/:id | customer | Order history |
| POST | /api/produce/order | customer | Place produce order |
| POST | /api/messages | any | Send message |
| GET | /api/admin/stats | admin | Analytics & KPIs |
| PUT | /api/admin/riders/:id/approve | admin | Approve rider |
| POST | /api/manager/menu-item | manager | Add menu item |
| GET | /api/orders/available | rider | View available orders |

The system supports both `/api/...` and `/api/v1/...` (backward-compatible alias).

---

## 📘 Educational Purpose

This project demonstrates several core computer science concepts:

| Area | Concepts |
|---|---|
| **Full-Stack Development** | Frontend UI design, backend API development, client-server interaction |
| **Database Systems** | Schema design, SQL queries, transaction management, ACID compliance |
| **Security** | JWT authentication, PBKDF2 password hashing, RBAC |
| **Software Architecture** | REST API structure, modular backend design, role-based access control |
| **Performance** | Index design, query optimization, WAL concurrency |

---

## 📄 Documentation

| Document | Location |
|---|---|
| Swagger API specification | `docs/swagger.yaml` |
| Backend architecture explanation | `docs/Backend_Explanation.docx` |
| ER Diagram | `docs/ER_Diagram.drawio` |
| UML Class Diagram | `docs/UML_ClassDiagram.drawio` |
| Transaction rollback demonstration | `media/rollback_demo.log` |

---

## ⚠️ Known Limitations

| Issue | Notes |
|---|---|
| Legacy password hashing | SHA-256 accounts still work via fallback. New accounts use PBKDF2. |
| No JWT refresh tokens | Tokens expire after 24h; user must log in again. |
| SQLite concurrency | WAL handles moderate load. Not suitable for high-concurrency production. |
| Polling vs WebSockets | Real-time uses 4-second polling. Functional but less efficient than WebSockets. |
| Single-file backend | `app.py` contains all routes — documented deviation from MVC structure. |
