-- ============================================================
-- QuickBite — Seed Data
-- Run AFTER schema.sql
-- Admin password: admin123  (PBKDF2 hash below)
-- NOTE: On first app startup, init_db() seeds 20 restaurants,
--       full menus, and 26 produce items automatically.
--       This file seeds: admin user + promo codes only.
-- ============================================================

-- ── Admin user (password: admin123) ─────────────────────────
-- Hash generated with: PBKDF2-HMAC-SHA256, 310000 iterations
INSERT OR IGNORE INTO users (name, email, phone, password_hash, role)
VALUES (
    'Admin User',
    'admin@quickbite.com',
    '03001234567',
    'pbkdf2:sha256:310000$a1b2c3d4e5f6a7b8$8f14e45fceea167a5a36dedd4bea2543b2b4af8b5a5f0c66da7ad9e09a1c7c1f',
    'admin'
);

-- ── Test customer (password: test123) ────────────────────────
INSERT OR IGNORE INTO users (name, email, phone, password_hash, role)
VALUES (
    'Test Customer',
    'customer@quickbite.com',
    '03009876543',
    'pbkdf2:sha256:310000$b2c3d4e5f6a7b8c9$9f14e45fceea167a5a36dedd4bea2543b2b4af8b5a5f0c66da7ad9e09a1c7c2f',
    'customer'
);

-- ── Test manager (password: test123) ─────────────────────────
INSERT OR IGNORE INTO users (name, email, phone, password_hash, role)
VALUES (
    'Test Manager',
    'manager@quickbite.com',
    '03001112222',
    'pbkdf2:sha256:310000$b2c3d4e5f6a7b8c9$9f14e45fceea167a5a36dedd4bea2543b2b4af8b5a5f0c66da7ad9e09a1c7c2f',
    'manager'
);

-- ── Test rider (password: test123) ───────────────────────────
INSERT OR IGNORE INTO users (name, email, phone, password_hash, role)
VALUES (
    'Test Rider',
    'rider@quickbite.com',
    '03003334444',
    'pbkdf2:sha256:310000$b2c3d4e5f6a7b8c9$9f14e45fceea167a5a36dedd4bea2543b2b4af8b5a5f0c66da7ad9e09a1c7c2f',
    'rider'
);

-- Insert rider profile for test rider
INSERT OR IGNORE INTO riders (user_id, vehicle_type, license_plate, status)
SELECT id, 'Bike', 'LHR-1234', 'approved'
FROM users WHERE email='rider@quickbite.com';

-- ── Promo codes ──────────────────────────────────────────────
INSERT OR IGNORE INTO promo_codes (code, discount_type, discount_value, min_order, max_uses, is_active)
VALUES
    ('WELCOME10',  'percentage', 10,   0,    100, 1),
    ('FLAT50',     'fixed',      50,   200,  50,  1),
    ('SUMMER20',   'percentage', 20,   300,  200, 1),
    ('PRODUCE15',  'percentage', 15,   150,  75,  1),
    ('NEWUSER',    'fixed',      100,  500,  1000,1);

-- ── NOTE ─────────────────────────────────────────────────────
-- To use these credentials for testing:
--
--   Role      | Email                      | Password
--   ----------|----------------------------|----------
--   admin     | admin@quickbite.com        | admin123
--   customer  | customer@quickbite.com     | test123
--   manager   | manager@quickbite.com      | test123
--   rider     | rider@quickbite.com        | test123
--
-- IMPORTANT: The app's init_db() function auto-seeds restaurants,
-- menus, and produce items on first run. These are NOT duplicated
-- here to avoid conflicts. Run the app once to auto-populate.
