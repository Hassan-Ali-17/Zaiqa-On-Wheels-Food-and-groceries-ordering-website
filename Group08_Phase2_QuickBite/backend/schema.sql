-- QuickBite Food Delivery Platform — Phase 2
-- schema.sql  (updated from Phase 1 — see comments for changes)
-- Run: sqlite3 food_delivery.db < schema.sql

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;   -- enables concurrent reads + serialised writes

-- ── users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    phone         TEXT,
    password_hash TEXT    NOT NULL,   -- PBKDF2-HMAC-SHA256 format: pbkdf2:sha256:<iters>$<salt>$<dk>
    role          TEXT    NOT NULL CHECK(role IN ('customer','rider','admin','manager')),
    created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── riders ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS riders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER UNIQUE NOT NULL REFERENCES users(id),
    vehicle_type  TEXT,
    license_plate TEXT,
    status        TEXT    DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
    is_available  INTEGER DEFAULT 1,
    total_earnings REAL   DEFAULT 0
);

-- ── restaurants ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurants (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    cuisine        TEXT,
    location       TEXT,
    phone          TEXT,
    image_filename TEXT,
    rating         REAL    DEFAULT 4.0,
    delivery_time  INTEGER DEFAULT 30,
    is_open        INTEGER DEFAULT 1,
    status         TEXT    DEFAULT 'approved' CHECK(status IN ('pending','approved','rejected')),
    manager_id     INTEGER REFERENCES users(id),
    added_by       INTEGER REFERENCES users(id),
    description    TEXT,
    min_order      REAL    DEFAULT 0,
    created_at     TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── categories ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    name          TEXT    NOT NULL
);

-- ── menu_items ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS menu_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id    INTEGER REFERENCES categories(id),
    restaurant_id  INTEGER NOT NULL REFERENCES restaurants(id),
    name           TEXT    NOT NULL,
    description    TEXT,
    price          REAL    NOT NULL CHECK(price >= 0),
    image_filename TEXT,
    is_available   INTEGER DEFAULT 1
);

-- ── orders ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id          INTEGER NOT NULL REFERENCES users(id),
    restaurant_id        INTEGER NOT NULL REFERENCES restaurants(id),
    rider_id             INTEGER REFERENCES riders(id),
    status               TEXT    DEFAULT 'Pending',
    total_amount         REAL    NOT NULL CHECK(total_amount >= 0),
    delivery_fee         REAL    DEFAULT 50,
    platform_fee         REAL    DEFAULT 0,
    rider_tip            REAL    DEFAULT 0,
    payment_method       TEXT    DEFAULT 'Cash on Delivery',
    delivery_address     TEXT,
    special_instructions TEXT,
    estimated_time       INTEGER DEFAULT 35,
    created_at           TEXT    DEFAULT CURRENT_TIMESTAMP,
    updated_at           TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── order_items ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id),
    item_id    INTEGER NOT NULL REFERENCES menu_items(id),
    quantity   INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL    NOT NULL CHECK(unit_price >= 0)
);

-- ── messages ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL REFERENCES users(id),
    receiver_id INTEGER NOT NULL REFERENCES users(id),
    order_id    INTEGER,
    message     TEXT    NOT NULL,
    is_read     INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── reviews ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   INTEGER NOT NULL REFERENCES users(id),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    order_id      INTEGER,
    rating        INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment       TEXT,
    created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── audit_log ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER,
    action    TEXT    NOT NULL,
    details   TEXT,
    timestamp TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── produce_items ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produce_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    category       TEXT    NOT NULL,
    price_per_kg   REAL    NOT NULL CHECK(price_per_kg >= 0),
    image_filename TEXT,
    description    TEXT,
    is_available   INTEGER DEFAULT 1,
    stock_kg       REAL    DEFAULT 50.0
);

-- ── produce_orders ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produce_orders (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id          INTEGER NOT NULL REFERENCES users(id),
    rider_id             INTEGER REFERENCES riders(id),
    total_amount         REAL    NOT NULL CHECK(total_amount >= 0),
    delivery_fee         REAL    DEFAULT 50,
    payment_method       TEXT    DEFAULT 'Cash on Delivery',
    delivery_address     TEXT,
    status               TEXT    DEFAULT 'Pending',
    special_instructions TEXT,
    created_at           TEXT    DEFAULT CURRENT_TIMESTAMP,
    updated_at           TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── produce_order_items ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produce_order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES produce_orders(id),
    produce_id  INTEGER NOT NULL REFERENCES produce_items(id),
    quantity_kg REAL    NOT NULL CHECK(quantity_kg > 0),
    unit_price  REAL    NOT NULL CHECK(unit_price >= 0)
);

-- ── promo_codes ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS promo_codes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT    UNIQUE NOT NULL,
    discount_type  TEXT    DEFAULT 'percent',
    discount_value REAL    NOT NULL CHECK(discount_value > 0),
    min_order      REAL    DEFAULT 0,
    max_uses       INTEGER DEFAULT 100,
    used_count     INTEGER DEFAULT 0,
    is_active      INTEGER DEFAULT 1,
    created_at     TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── loyalty_points ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loyalty_points (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id      INTEGER UNIQUE NOT NULL REFERENCES users(id),
    total_points     INTEGER DEFAULT 0,
    lifetime_points  INTEGER DEFAULT 0
);

-- ── loyalty_transactions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    points      INTEGER NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('earn','redeem')),
    description TEXT,
    order_id    INTEGER,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- ── Indexes for query performance ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_orders_customer      ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant    ON orders(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_orders_rider         ON orders(rider_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_rest      ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender      ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_receiver    ON messages(receiver_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user       ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_loyalty_customer     ON loyalty_points(customer_id);
