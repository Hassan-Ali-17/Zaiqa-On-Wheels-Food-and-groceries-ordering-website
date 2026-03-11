-- QuickBite Food Delivery Platform — seed.sql
-- Inserts default admin, promo codes, and sample produce items for testing.
-- Run AFTER schema.sql: sqlite3 food_delivery.db < seed.sql

-- ── Admin user (PBKDF2 hash of 'hassan') ─────────────────────────────────────
-- NOTE: To regenerate hash: python3 -c "import hashlib,secrets; s=secrets.token_hex(16); dk=hashlib.pbkdf2_hmac('sha256',b'hassan',s.encode(),310000); print(f'pbkdf2:sha256:310000\${s}\${dk.hex()}')"
INSERT OR IGNORE INTO users (name,email,phone,password_hash,role)
VALUES ('Admin Ahsen','ahsen@gmail.com','03001234567',
        'pbkdf2:sha256:310000$placeholder_run_app_to_seed$placeholder','admin');

-- ── Default promo codes ───────────────────────────────────────────────────────
INSERT OR IGNORE INTO promo_codes (code,discount_type,discount_value,min_order,max_uses)
VALUES
    ('HASSAN',  'percent', 10, 0, 1000),
    ('AHSEN',   'percent', 20, 0, 1000),
    ('DBMS',    'percent', 30, 0, 1000),
    ('LADLAY',  'percent', 15, 0, 1000),
    ('SPECIAL', 'percent', 35, 0, 1000);

-- Note: Restaurant, menu, and produce data is seeded automatically by app.py init_db()
-- on first server start to avoid duplicating the large menu dataset here.
