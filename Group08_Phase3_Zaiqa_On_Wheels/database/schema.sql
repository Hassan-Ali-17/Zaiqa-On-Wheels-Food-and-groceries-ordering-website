-- ============================================================
-- QuickBite — Database Schema
-- Engine : SQLite 3
-- Encoding: UTF-8
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;   -- Write-Ahead Logging for concurrency
PRAGMA synchronous  = NORMAL;

-- ── users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    phone         TEXT    DEFAULT '',
    password_hash TEXT    NOT NULL,          -- PBKDF2-HMAC-SHA256
    role          TEXT    NOT NULL CHECK(role IN ('customer','rider','admin','manager')),
    created_at    TEXT    DEFAULT (datetime('now'))
);

-- ── riders ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS riders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vehicle_type    TEXT    DEFAULT 'Bike',
    license_plate   TEXT    DEFAULT '',
    status          TEXT    DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
    total_earnings  REAL    DEFAULT 0
);

-- ── restaurants ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurants (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    cuisine      TEXT    DEFAULT '',
    location     TEXT    DEFAULT '',
    address      TEXT    DEFAULT '',
    phone        TEXT    DEFAULT '',
    manager_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    rating       REAL    DEFAULT 0,
    image_url    TEXT    DEFAULT '',
    status       TEXT    DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
    is_open      INTEGER DEFAULT 1,
    created_at   TEXT    DEFAULT (datetime('now'))
);

-- ── categories ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL
);

-- ── menu_items ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS menu_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    category_id     INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name            TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    price           REAL    NOT NULL CHECK(price >= 0),
    image_filename  TEXT    DEFAULT '',
    is_available    INTEGER DEFAULT 1,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ── orders ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id           INTEGER NOT NULL REFERENCES users(id),
    restaurant_id         INTEGER NOT NULL REFERENCES restaurants(id),
    rider_id              INTEGER REFERENCES riders(id) ON DELETE SET NULL,
    status                TEXT    DEFAULT 'Pending',
    total_amount          REAL    NOT NULL CHECK(total_amount >= 0),
    delivery_fee          REAL    DEFAULT 50,
    platform_fee          REAL    DEFAULT 0,
    rider_tip             REAL    DEFAULT 0,
    promo_discount        REAL    DEFAULT 0,
    loyalty_discount      REAL    DEFAULT 0,
    payment_method        TEXT    DEFAULT 'Cash on Delivery',
    delivery_address      TEXT    DEFAULT '',
    special_instructions  TEXT    DEFAULT '',
    estimated_time        INTEGER DEFAULT 35,
    created_at            TEXT    DEFAULT (datetime('now')),
    updated_at            TEXT    DEFAULT (datetime('now'))
);

-- ── order_items ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id     INTEGER NOT NULL REFERENCES menu_items(id),
    quantity    INTEGER NOT NULL CHECK(quantity > 0),
    unit_price  REAL    NOT NULL CHECK(unit_price >= 0)
);

-- ── messages ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL REFERENCES users(id),
    receiver_id INTEGER NOT NULL REFERENCES users(id),
    order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    message     TEXT    NOT NULL,
    is_read     INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- ── reviews ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   INTEGER NOT NULL REFERENCES users(id),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    order_id      INTEGER REFERENCES orders(id),
    rating        INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment       TEXT    DEFAULT '',
    created_at    TEXT    DEFAULT (datetime('now'))
);

-- ── audit_log ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT    NOT NULL,
    details    TEXT    DEFAULT '',
    timestamp  TEXT    DEFAULT (datetime('now'))
);

-- ── produce_items ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produce_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    category        TEXT    DEFAULT 'vegetable' CHECK(category IN ('fruit','vegetable')),
    price_per_kg    REAL    NOT NULL CHECK(price_per_kg >= 0),
    image_filename  TEXT    DEFAULT '',
    is_available    INTEGER DEFAULT 1,
    stock_kg        REAL    DEFAULT 100
);

-- ── produce_orders ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produce_orders (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id          INTEGER NOT NULL REFERENCES users(id),
    rider_id             INTEGER REFERENCES riders(id) ON DELETE SET NULL,
    total_amount         REAL    NOT NULL CHECK(total_amount >= 0),
    delivery_fee         REAL    DEFAULT 50,
    promo_discount       REAL    DEFAULT 0,
    loyalty_discount     REAL    DEFAULT 0,
    payment_method       TEXT    DEFAULT 'Cash on Delivery',
    delivery_address     TEXT    DEFAULT '',
    special_instructions TEXT    DEFAULT '',
    status               TEXT    DEFAULT 'Pending',
    created_at           TEXT    DEFAULT (datetime('now')),
    updated_at           TEXT    DEFAULT (datetime('now'))
);

-- ── produce_order_items ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS produce_order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES produce_orders(id) ON DELETE CASCADE,
    produce_id  INTEGER NOT NULL REFERENCES produce_items(id),
    quantity_kg REAL    NOT NULL CHECK(quantity_kg > 0),
    unit_price  REAL    NOT NULL CHECK(unit_price >= 0)
);

-- ── promo_codes ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS promo_codes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT    NOT NULL UNIQUE,
    discount_type  TEXT    NOT NULL CHECK(discount_type IN ('percentage','fixed')),
    discount_value REAL    NOT NULL CHECK(discount_value > 0),
    min_order      REAL    DEFAULT 0,
    max_uses       INTEGER DEFAULT 100,
    used_count     INTEGER DEFAULT 0,
    is_active      INTEGER DEFAULT 1,
    created_at     TEXT    DEFAULT (datetime('now'))
);

-- ── loyalty_points ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loyalty_points (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id      INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    total_points     INTEGER DEFAULT 0,
    lifetime_points  INTEGER DEFAULT 0,
    updated_at       TEXT    DEFAULT (datetime('now'))
);

-- ── loyalty_transactions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL REFERENCES users(id),
    order_id     INTEGER,
    points       INTEGER NOT NULL,
    type         TEXT    NOT NULL CHECK(type IN ('earn','redeem')),
    description  TEXT    DEFAULT '',
    created_at   TEXT    DEFAULT (datetime('now'))
);

-- ============================================================
-- INDEXES — see performance.sql for benchmarks
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant  ON orders(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_orders_rider       ON orders(rider_id);
CREATE INDEX IF NOT EXISTS idx_orders_status      ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created     ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_menu_restaurant    ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_menu_category      ON menu_items(category_id);
CREATE INDEX IF NOT EXISTS idx_menu_available     ON menu_items(is_available);
CREATE INDEX IF NOT EXISTS idx_messages_pair      ON messages(sender_id, receiver_id);
CREATE INDEX IF NOT EXISTS idx_messages_created   ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_produce_orders_cid ON produce_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_produce_orders_rid ON produce_orders(rider_id);
CREATE INDEX IF NOT EXISTS idx_audit_user         ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action       ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_loyalty_customer   ON loyalty_points(customer_id);
CREATE INDEX IF NOT EXISTS idx_restaurants_status ON restaurants(status, is_open);
CREATE INDEX IF NOT EXISTS idx_users_email        ON users(email);
CREATE INDEX IF NOT EXISTS idx_riders_user        ON riders(user_id);
