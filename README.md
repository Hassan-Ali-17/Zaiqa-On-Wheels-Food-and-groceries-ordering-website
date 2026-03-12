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

## 🚀 Key Features

### 🔐 User Authentication
- Secure user registration and login
- JWT-based authentication
- Token expiration after 24 hours
- Protected API routes using Bearer tokens

### 🛒 Cart Management
Users can:
- Add items to their cart
- Remove items from cart
- Update item quantities
- View cart before checkout

### 🍔 Food & Grocery Browsing
The platform supports two types of ordering:

**Restaurant Ordering** — Users can:
- Browse restaurant menus
- Select menu items
- Apply promotions
- Place restaurant orders

**Produce / Grocery Ordering** — Users can:
- Browse available grocery items
- Add produce to cart
- Place grocery orders

### 📦 Order Management
Customers can:
- Place orders
- Track delivery status
- View previous order history
- Earn loyalty points from purchases

### 🗂️ Admin Panel
Admins have full system control including:
- Approving riders
- Approving restaurants
- Managing promotions
- Monitoring audit logs
- Managing platform users

### 👨‍🍳 Restaurant Manager Tools
Managers can:
- Manage their restaurant
- Add or edit menu items
- Create categories
- View order statistics

### 🚴 Rider Delivery System
Riders can:
- View available delivery orders
- Accept deliveries
- Mark deliveries as completed
- Chat with customers

### 📱 Responsive Design
The UI is optimized for:
- Desktop
- Tablets
- Mobile devices

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | SQLite |
| Authentication | JWT (JSON Web Tokens) |
| API Docs | OpenAPI / Swagger |

---

## ▶️ How to Run the Project

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Hassan-Ali-17/Zaiqa-On-Wheels-Food-and-groceries-ordering-website.git
```

### 2️⃣ Navigate to the Project Folder
```bash
cd "Group08_Phase2_QuickBite"
```

### 3️⃣ Go to the Backend Directory
```bash
cd backend
```

### 4️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 5️⃣ Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```
Edit `.env` and set secure values:
```
JWT_SECRET=your_long_random_secret
FLASK_SECRET=another_secure_secret
```

### 6️⃣ Run the Application
```bash
python app.py
```

The server will start at `http://127.0.0.1:5000`

Flask automatically serves the frontend. Open in your browser:
```
http://127.0.0.1:5000
```

---

## 🔑 Authentication System

All protected API endpoints require a JWT Bearer token.

**Header format:**
```
Authorization: Bearer <token>
```

**Tokens are obtained from:**
```
POST /api/v1/login
POST /api/v1/signup
```

**Token validity:** 24 hours

---

## 👥 User Roles & Access Control

| Role | Capabilities |
|---|---|
| **Customer** | Browse restaurants and produce, place orders, chat with riders, earn loyalty points |
| **Rider** | Accept deliveries, update order status, communicate with customers |
| **Manager** | Manage restaurant menus, categories, and monitor statistics |
| **Admin** | Full platform control including approvals, promotions, and system monitoring |

> Role-based access is implemented using **RBAC (Role Based Access Control)**.

---

## 🧾 Database Transaction Scenarios (DBMS Phase)

Two critical operations implement explicit transaction management using `BEGIN`, `COMMIT`, and `ROLLBACK` — ensuring data consistency and ACID compliance.

### Scenario 1 — Place Restaurant Order
**Endpoint:** `POST /api/v1/orders`

**Transaction flow:**
1. Insert new order
2. Insert order items
3. Validate promotion code
4. Award loyalty points
5. Commit transaction

**Rollback triggers** — The transaction rolls back if:
- Menu item is invalid
- Item is unavailable
- Promotion code is expired
- Loyalty points become negative
- Any database error occurs

### Scenario 2 — Place Produce Order
**Endpoint:** `POST /api/v1/produce/order`

**Transaction flow:**
1. Insert produce order
2. Validate produce availability
3. Apply promotion
4. Update loyalty points
5. Commit transaction

**Rollback occurs if:**
- Produce item unavailable
- Promotion invalid
- Loyalty underflow
- Database error

> Rollback proof is available in: `media/rollback_demo.log`

---

## 📂 Project Structure
```
zaiqa-on-wheels/
│
├── Group[08]_Phase2_QuickBite/
│   ├── backend/
│   │   ├── app.py               # Flask server (API routes, JWT auth, RBAC, transactions)
│   │   ├── requirements.txt
│   │   ├── schema.sql
│   │   ├── seed.sql
│   │   ├── swagger.yaml
│   │   └── Backend_Explanation.pdf
│   │
│   ├── frontend/
│   │   └── pages/               # HTML, CSS and JavaScript frontend
│   │
│   └── media/
│       └── rollback_demo.log
│
├── .env.example
└── README.md
```

---

## 🔗 API Versioning

The system supports both:
```
/api/v1/...
```
and a backward compatible alias:
```
/api/...
```

---

## 📘 Educational Purpose

This project demonstrates several core computer science concepts:

| Area | Concepts |
|---|---|
| **Full-Stack Development** | Frontend UI design, backend API development, client-server interaction |
| **Database Systems** | Schema design, SQL queries, transaction management |
| **Security** | JWT authentication, secure session handling |
| **Software Architecture** | REST API structure, role-based access control, modular backend design |

---

## 📄 Documentation

Additional documentation includes:
- Swagger API specification → `backend/swagger.yaml`
- Backend architecture explanation → `backend/Backend_Explanation.pdf`
- Transaction rollback demonstration → `media/rollback_demo.log`

---

## 👨‍💻 Contributors

| Name | ID |
|---|---|
| Hassan Ali Shah | BSCS24040 |
| Ahsen Ali | BSCS24056 |

---

## ✅ Conclusion

Zaiqa On Wheels demonstrates how a modern web application can combine frontend development, backend APIs, authentication systems, database management, and transaction handling to build a **secure, scalable, and interactive** food & grocery ordering platform.
