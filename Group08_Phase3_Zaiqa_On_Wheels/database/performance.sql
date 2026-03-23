-- ============================================================
-- QuickBite — Index & Performance Analysis
-- Engine: SQLite 3
-- Run this file to: (1) create indexes, (2) compare query plans
-- ============================================================

-- ============================================================
-- SECTION 1 — INDEX CREATION
-- (Also in schema.sql — safe to run again, uses IF NOT EXISTS)
-- ============================================================

-- Orders: most-queried table, filtered by customer, restaurant, status
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant  ON orders(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_orders_rider       ON orders(rider_id);
CREATE INDEX IF NOT EXISTS idx_orders_status      ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created     ON orders(created_at DESC);

-- Order items: always joined to orders
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);

-- Menu items: browsed by restaurant and filtered by availability
CREATE INDEX IF NOT EXISTS idx_menu_restaurant    ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_menu_category      ON menu_items(category_id);
CREATE INDEX IF NOT EXISTS idx_menu_available     ON menu_items(is_available);

-- Messages: fetched by sender+receiver pair, sorted by time
CREATE INDEX IF NOT EXISTS idx_messages_pair      ON messages(sender_id, receiver_id);
CREATE INDEX IF NOT EXISTS idx_messages_created   ON messages(created_at DESC);

-- Produce orders
CREATE INDEX IF NOT EXISTS idx_produce_orders_cid ON produce_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_produce_orders_rid ON produce_orders(rider_id);

-- Audit log: queried by user and action type
CREATE INDEX IF NOT EXISTS idx_audit_user         ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action       ON audit_log(action);

-- Loyalty: unique customer lookup
CREATE INDEX IF NOT EXISTS idx_loyalty_customer   ON loyalty_points(customer_id);

-- Restaurants: homepage filter (approved + open)
CREATE INDEX IF NOT EXISTS idx_restaurants_status ON restaurants(status, is_open);

-- Users: login lookup
CREATE INDEX IF NOT EXISTS idx_users_email        ON users(email);

-- Riders: user ↔ rider join
CREATE INDEX IF NOT EXISTS idx_riders_user        ON riders(user_id);


-- ============================================================
-- SECTION 2 — QUERY PLAN COMPARISON (EXPLAIN QUERY PLAN)
-- Run these BEFORE and AFTER index creation and compare output.
-- "SCAN TABLE" = full table scan (slow)
-- "SEARCH TABLE USING INDEX" = indexed lookup (fast)
-- ============================================================

-- ── Query 1: Fetch all orders for a customer ─────────────────
-- USE CASE: Customer dashboard — loads order history
-- WITHOUT index → SCAN orders (reads every row)
-- WITH    index → SEARCH orders USING INDEX idx_orders_customer
EXPLAIN QUERY PLAN
SELECT o.*, r.name as restaurant_name
FROM orders o
JOIN restaurants r ON o.restaurant_id = r.id
WHERE o.customer_id = 1
ORDER BY o.created_at DESC;

-- ── Query 2: Fetch available menu items for a restaurant ─────
-- USE CASE: Restaurant menu page
-- WITHOUT index → SCAN menu_items
-- WITH    index → SEARCH menu_items USING INDEX idx_menu_restaurant
EXPLAIN QUERY PLAN
SELECT * FROM menu_items
WHERE restaurant_id = 1
  AND is_available = 1;

-- ── Query 3: Fetch conversation between two users ────────────
-- USE CASE: Customer ↔ Rider chat polling (every 4 seconds)
-- WITHOUT index → SCAN messages
-- WITH    index → SEARCH messages USING INDEX idx_messages_pair
EXPLAIN QUERY PLAN
SELECT * FROM messages
WHERE (sender_id = 1 AND receiver_id = 5)
   OR (sender_id = 5 AND receiver_id = 1)
ORDER BY created_at ASC;

-- ── Query 4: Admin orders dashboard ──────────────────────────
-- USE CASE: Admin sees all pending orders
-- WITHOUT index → SCAN orders
-- WITH    index → SEARCH orders USING INDEX idx_orders_status
EXPLAIN QUERY PLAN
SELECT o.*, u.name as customer_name, r.name as restaurant_name
FROM orders o
JOIN users u ON o.customer_id = u.id
JOIN restaurants r ON o.restaurant_id = r.id
WHERE o.status = 'Pending'
ORDER BY o.created_at DESC;

-- ── Query 5: Homepage restaurant listing ─────────────────────
-- USE CASE: Homepage loads approved + open restaurants
-- WITHOUT index → SCAN restaurants
-- WITH    index → SEARCH restaurants USING INDEX idx_restaurants_status
EXPLAIN QUERY PLAN
SELECT * FROM restaurants
WHERE status = 'approved'
  AND is_open = 1
ORDER BY rating DESC;

-- ── Query 6: Rider available orders ──────────────────────────
-- USE CASE: Rider dashboard polls for unassigned pending orders
-- WITHOUT index → SCAN orders (full scan)
-- WITH    index → SEARCH orders USING INDEX idx_orders_status
EXPLAIN QUERY PLAN
SELECT o.*, r.name as restaurant_name, r.location
FROM orders o
JOIN restaurants r ON o.restaurant_id = r.id
WHERE o.status = 'Confirmed'
  AND o.rider_id IS NULL;

-- ── Query 7: Audit log per user ───────────────────────────────
-- USE CASE: Admin audit page filtered by user
-- WITHOUT index → SCAN audit_log
-- WITH    index → SEARCH audit_log USING INDEX idx_audit_user
EXPLAIN QUERY PLAN
SELECT * FROM audit_log
WHERE user_id = 1
ORDER BY timestamp DESC
LIMIT 50;

-- ── Query 8: Login lookup ─────────────────────────────────────
-- USE CASE: Every login request
-- WITHOUT index → SCAN users
-- WITH    index → SEARCH users USING INDEX idx_users_email
EXPLAIN QUERY PLAN
SELECT * FROM users WHERE email = 'admin@quickbite.com';


-- ============================================================
-- SECTION 3 — PERFORMANCE SUMMARY
-- ============================================================
-- Query                          | Before Index | After Index
-- -------------------------------|--------------|------------------
-- Customer order history         | SCAN (all)   | INDEX idx_orders_customer
-- Restaurant menu items          | SCAN (all)   | INDEX idx_menu_restaurant
-- Chat message history           | SCAN (all)   | INDEX idx_messages_pair
-- Admin pending orders           | SCAN (all)   | INDEX idx_orders_status
-- Homepage restaurants           | SCAN (all)   | INDEX idx_restaurants_status
-- Rider available orders         | SCAN (all)   | INDEX idx_orders_status
-- Audit log per user             | SCAN (all)   | INDEX idx_audit_user
-- Login by email                 | SCAN (all)   | INDEX idx_users_email
--
-- All 8 critical queries improve from O(n) full table scan
-- to O(log n) B-tree index lookup after index creation.
-- ============================================================
