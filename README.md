# Zaiqa-On-Wheels-Food-and-groceries-ordering-website
# ---------------Zaiqa-On-Wheels 🍽️🛒----------------

Food & Grocery Ordering Web Application

Zaiqa On Wheels is a full-stack food and grocery ordering platform that allows users to browse restaurant menus and grocery items, manage their cart, place orders, and track deliveries through a secure and responsive interface.

The system demonstrates a complete end-to-end web solution, integrating:

Frontend user interface

Backend API services

Authentication and authorization

Database management

Transaction control

The project is built using Python (Flask), HTML, CSS, JavaScript, and SQLite, and showcases practical concepts from Web Development and Database Management Systems (DBMS).

🚀 Key Features
🔐 User Authentication

Secure user registration and login

JWT-based authentication

Token expiration after 24 hours

Protected API routes using Bearer tokens

🛒 Cart Management

Users can:

Add items to their cart

Remove items from cart

Update item quantities

View cart before checkout

🍔 Food & Grocery Browsing

The platform supports two types of ordering:

Restaurant Ordering

Users can:

Browse restaurant menus

Select menu items

Apply promotions

Place restaurant orders

Produce / Grocery Ordering

Users can:

Browse available grocery items

Add produce to cart

Place grocery orders

📦 Order Management

Customers can:

Place orders

Track delivery status

View previous order history

Earn loyalty points from purchases

🗂️ Admin Panel

Admins have full system control including:

Approving riders

Approving restaurants

Managing promotions

Monitoring audit logs

Managing platform users

👨‍🍳 Restaurant Manager Tools

Managers can:

Manage their restaurant

Add or edit menu items

Create categories

View order statistics

🚴 Rider Delivery System

Riders can:

View available delivery orders

Accept deliveries

Mark deliveries as completed

Chat with customers

📱 Responsive Design

The UI is optimized for:

Desktop

Tablets

Mobile devices

🛠️ Technology Stack
Frontend

HTML

CSS

JavaScript

Backend

Python

Flask

Database

SQLite

Authentication

JWT (JSON Web Tokens)

API Documentation

OpenAPI / Swagger specification

⚙️ Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/Hassan-Ali-17/Zaiqa-On-Wheels-Food-and-groceries-ordering-website.git
cd zaiqa-on-wheels
2️⃣ Install Backend Dependencies
cd backend
pip install -r requirements.txt
3️⃣ Configure Environment Variables

Copy the example environment file:

cp .env.example .env

Edit .env and set secure values:

JWT_SECRET=your_long_random_secret
FLASK_SECRET=another_secure_secret
4️⃣ Start the Server
cd backend
python app.py

The server will start at:

http://127.0.0.1:5000

Flask automatically serves the frontend.

Open in browser:

http://127.0.0.1:5000
🔑 Authentication System

All protected API endpoints require a JWT Bearer token.

Header format:

Authorization: Bearer <token>

Tokens are obtained from:

POST /api/v1/login
POST /api/v1/signup

Token validity:

24 hours
👥 User Roles & Access Control
Role	Capabilities
Customer	Browse restaurants and produce, place orders, chat with riders, earn loyalty points
Rider	Accept deliveries, update order status, communicate with customers
Manager	Manage restaurant menus, categories, and monitor statistics
Admin	Full platform control including approvals, promotions, and system monitoring

Role-based access is implemented using RBAC (Role Based Access Control).

🧾 Database Transaction Scenarios (DBMS Phase)

Two critical operations implement explicit transaction management using:

BEGIN
COMMIT
ROLLBACK

This ensures data consistency and ACID compliance.

Scenario 1 — Place Restaurant Order

Endpoint:

POST /api/v1/orders

Transaction flow:

Insert new order

Insert order items

Validate promotion code

Award loyalty points

Commit transaction

Rollback triggers

The transaction rolls back if:

Menu item is invalid

Item is unavailable

Promotion code is expired

Loyalty points become negative

Any database error occurs

Scenario 2 — Place Produce Order

Endpoint:

POST /api/v1/produce/order

Transaction flow:

Insert produce order

Validate produce availability

Apply promotion

Update loyalty points

Commit transaction

Rollback occurs if:

Produce item unavailable

Promotion invalid

Loyalty underflow

Database error

Rollback proof is available in:

media/rollback_demo.log
📂 Project Structure
zaiqa-on-wheels/
│
├── backend/
│   ├── app.py
│   │   Flask server containing:
│   │   - API routes
│   │   - JWT authentication
│   │   - Role based access
│   │   - transaction logic
│   │
│   ├── requirements.txt
│   ├── schema.sql
│   ├── seed.sql
│   ├── swagger.yaml
│   └── Backend_Explanation.pdf
│
├── frontend/
│   └── pages/
│       HTML, CSS and JavaScript frontend
│
├── media/
│   └── rollback_demo.log
│
├── .env.example
└── README.md
🔗 API Versioning

The system supports both:

/api/v1/...

and a backward compatible alias:

/api/...
📘 Educational Purpose

This project demonstrates several core computer science concepts, including:

Full-Stack Development

Frontend UI design

Backend API development

Client-server interaction

Database Systems

Schema design

SQL queries

Transaction management

Security

JWT authentication

Secure session handling

Software Architecture

REST API structure

Role-based access control

Modular backend design

📄 Documentation

Additional documentation includes:

Swagger API specification

Backend architecture explanation

Transaction rollback demonstration

Located in:

backend/swagger.yaml
backend/Backend_Explanation.pdf
media/rollback_demo.log
👨‍💻 Contributors

Hassan Ali Shah
BSCS24040

Ahsen Ali
BSCS24056

✅ Conclusion

Zaiqa On Wheels demonstrates how a modern web application can combine:

frontend development

backend APIs

authentication systems

database management

transaction handling

to build a secure, scalable, and interactive food & grocery ordering platform.
