-- ============================================================
-- performance.sql
-- Food Delivery System — Query Performance Analysis
-- EXPLAIN ANALYZE: Before and After Indexing
-- ============================================================
-- HOW TO USE:
--   1. Run schema.sql (includes indexes already).
--   2. Run seed.sql.
--   3. To test "before" results, DROP each index first (shown
--      inline below), run the EXPLAIN, then recreate the index
--      and run the EXPLAIN again to compare.
-- ============================================================


-- ============================================================
-- Query 1: Customer Order History
-- Use case: Customer taps "My Orders" — fetch all orders for
--           a specific customer, newest first.
-- ============================================================

-- ── BEFORE INDEXING ──────────────────────────────────────────
-- Drop the index to simulate a table without it
DROP INDEX IF EXISTS idx_order_customer ON `Order`;

EXPLAIN ANALYZE
SELECT
    o.order_id,
    o.order_date,
    o.status,
    o.total_amount,
    r.name AS restaurant_name
FROM `Order` o
JOIN Restaurant r ON o.restaurant_id = r.restaurant_id
WHERE o.customer_id = 5
ORDER BY o.order_date DESC;

/*
  Expected BEFORE result (no index on customer_id):
  ┌──────────────────────────────────────────────────────────────────┐
  │ id │ select_type │ table │ type │ key  │ rows │ Extra            │
  ├────┼─────────────┼───────┼──────┼──────┼──────┼──────────────────┤
  │  1 │ SIMPLE      │ o     │ ALL  │ NULL │  50  │ Using where;     │
  │    │             │       │      │      │      │ Using filesort   │
  │  1 │ SIMPLE      │ r     │ eq_  │ PRI  │   1  │ NULL             │
  └──────────────────────────────────────────────────────────────────┘
  type=ALL means MySQL scans all 50 rows in Order.
  With 10,000+ orders this becomes a serious bottleneck.
*/


-- ── AFTER INDEXING ───────────────────────────────────────────
CREATE INDEX idx_order_customer ON `Order`(customer_id);

EXPLAIN ANALYZE
SELECT
    o.order_id,
    o.order_date,
    o.status,
    o.total_amount,
    r.name AS restaurant_name
FROM `Order` o
JOIN Restaurant r ON o.restaurant_id = r.restaurant_id
WHERE o.customer_id = 5
ORDER BY o.order_date DESC;

/*
  Expected AFTER result (idx_order_customer active):
  ┌──────────────────────────────────────────────────────────────────┐
  │ id │ select_type │ table │ type │ key                 │ rows     │
  ├────┼─────────────┼───────┼──────┼─────────────────────┼──────────┤
  │  1 │ SIMPLE      │ o     │ ref  │ idx_order_customer  │   2-3    │
  │  1 │ SIMPLE      │ r     │ eq_  │ PRIMARY             │   1      │
  └──────────────────────────────────────────────────────────────────┘
  type=ref means MySQL uses the index to jump directly to matching
  rows. Rows examined drops from 50 → ~2-3.
  Performance gain: O(n) → O(log n) lookup.
  At 100,000 orders: ~1 ms vs ~200 ms.
*/


-- ============================================================
-- Query 2: Menu Items for a Category (Menu Browsing)
-- Use case: Customer browses a restaurant category page —
--           list all available items in a given category.
-- ============================================================

-- ── BEFORE INDEXING ──────────────────────────────────────────
DROP INDEX IF EXISTS idx_menuitem_category ON MenuItem;

EXPLAIN ANALYZE
SELECT
    item_id,
    name,
    description,
    price
FROM MenuItem
WHERE category_id = 8
  AND is_available = 1
ORDER BY price ASC;

/*
  Expected BEFORE result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table    │ type │ key  │ rows │ Extra                            │
  ├──────────┼──────┼──────┼──────┼──────────────────────────────────┤
  │ MenuItem │ ALL  │ NULL │ 150  │ Using where; Using filesort      │
  └──────────────────────────────────────────────────────────────────┘
  Full table scan across all 150 menu items for each category page
  load. At a restaurant chain with 5,000+ items this is very slow.
*/


-- ── AFTER INDEXING ───────────────────────────────────────────
CREATE INDEX idx_menuitem_category ON MenuItem(category_id);

EXPLAIN ANALYZE
SELECT
    item_id,
    name,
    description,
    price
FROM MenuItem
WHERE category_id = 8
  AND is_available = 1
ORDER BY price ASC;

/*
  Expected AFTER result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table    │ type │ key                   │ rows │ Extra           │
  ├──────────┼──────┼───────────────────────┼──────┼─────────────────┤
  │ MenuItem │ ref  │ idx_menuitem_category │ 3-5  │ Using where;    │
  │          │      │                       │      │ Using filesort  │
  └──────────────────────────────────────────────────────────────────┘
  Rows examined: 150 → ~3-5. MySQL uses the index to narrow results
  to only items in category 8, then filters by is_available.
  For a composite improvement, consider: INDEX(category_id, is_available).
*/


-- ============================================================
-- Query 3: Restaurant Ratings Aggregation
-- Use case: Homepage / listing page showing star ratings for
--           each restaurant, sorted by best rated.
-- ============================================================

-- ── BEFORE INDEXING ──────────────────────────────────────────
DROP INDEX IF EXISTS idx_review_restaurant ON Review;

EXPLAIN ANALYZE
SELECT
    restaurant_id,
    COUNT(*)           AS review_count,
    ROUND(AVG(rating), 2) AS average_rating
FROM Review
GROUP BY restaurant_id
ORDER BY average_rating DESC;

/*
  Expected BEFORE result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table  │ type │ key  │ rows │ Extra                              │
  ├────────┼──────┼──────┼──────┼────────────────────────────────────┤
  │ Review │ ALL  │ NULL │  30  │ Using temporary; Using filesort    │
  └──────────────────────────────────────────────────────────────────┘
  MySQL reads every row in Review, builds a temporary table to
  compute the GROUP BY, then sorts it. At 100,000 reviews this
  causes major latency on every page load.
*/


-- ── AFTER INDEXING ───────────────────────────────────────────
CREATE INDEX idx_review_restaurant ON Review(restaurant_id);

EXPLAIN ANALYZE
SELECT
    restaurant_id,
    COUNT(*)           AS review_count,
    ROUND(AVG(rating), 2) AS average_rating
FROM Review
GROUP BY restaurant_id
ORDER BY average_rating DESC;

/*
  Expected AFTER result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table  │ type  │ key                    │ rows │ Extra           │
  ├────────┼───────┼────────────────────────┼──────┼─────────────────┤
  │ Review │ index │ idx_review_restaurant  │  30  │ Using index     │
  └──────────────────────────────────────────────────────────────────┘
  MySQL uses the index to group rows by restaurant_id without a
  temporary table. "Using index" means the query is satisfied
  entirely from the index (covering index scan) — no row lookups.
  Performance gain scales significantly with review volume.
*/


-- ============================================================
-- Query 4: Active Orders for a Rider (Rider App Dashboard)
-- Use case: Rider opens the app to see their current and
--           recent deliveries filtered by status.
-- ============================================================

-- ── BEFORE INDEXING ──────────────────────────────────────────
DROP INDEX IF EXISTS idx_order_rider   ON `Order`;
DROP INDEX IF EXISTS idx_order_status  ON `Order`;

EXPLAIN ANALYZE
SELECT
    o.order_id,
    o.status,
    o.order_date,
    o.total_amount,
    a.street,
    a.city,
    c.name AS customer_name,
    c.phone AS customer_phone
FROM `Order` o
JOIN Address  a ON o.address_id  = a.address_id
JOIN Customer c ON o.customer_id = c.customer_id
WHERE o.rider_id = 2
  AND o.status IN ('Out for Delivery', 'Preparing')
ORDER BY o.order_date DESC;

/*
  Expected BEFORE result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table    │ type │ key  │ rows │ Extra                            │
  ├──────────┼──────┼──────┼──────┼──────────────────────────────────┤
  │ o        │ ALL  │ NULL │  50  │ Using where; Using filesort      │
  │ a        │ eq_  │ PRI  │   1  │                                  │
  │ c        │ eq_  │ PRI  │   1  │                                  │
  └──────────────────────────────────────────────────────────────────┘
  Full scan on Order to find rows matching rider_id and status.
  Every rider dashboard refresh scans the entire orders table.
*/


-- ── AFTER INDEXING ───────────────────────────────────────────
CREATE INDEX idx_order_rider  ON `Order`(rider_id);
CREATE INDEX idx_order_status ON `Order`(status);

EXPLAIN ANALYZE
SELECT
    o.order_id,
    o.status,
    o.order_date,
    o.total_amount,
    a.street,
    a.city,
    c.name AS customer_name,
    c.phone AS customer_phone
FROM `Order` o
JOIN Address  a ON o.address_id  = a.address_id
JOIN Customer c ON o.customer_id = c.customer_id
WHERE o.rider_id = 2
  AND o.status IN ('Out for Delivery', 'Preparing')
ORDER BY o.order_date DESC;

/*
  Expected AFTER result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table    │ type │ key              │ rows │ Extra                │
  ├──────────┼──────┼──────────────────┼──────┼──────────────────────┤
  │ o        │ ref  │ idx_order_rider  │  3-5 │ Using where;         │
  │          │      │                  │      │ Using filesort       │
  │ a        │ eq_  │ PRIMARY          │    1 │                      │
  │ c        │ eq_  │ PRIMARY          │    1 │                      │
  └──────────────────────────────────────────────────────────────────┘
  MySQL uses idx_order_rider to restrict the scan to only the rows
  for rider_id = 2 (typically 2-5 rows), then filters on status.
  Advanced optimisation: Composite index (rider_id, status) would
  eliminate the post-index status filter entirely.
*/


-- ============================================================
-- Query 5: Revenue Report Per Restaurant
-- Use case: Admin dashboard — total revenue and order count
--           for each restaurant this month, sorted by revenue.
-- ============================================================

-- ── BEFORE INDEXING ──────────────────────────────────────────
DROP INDEX IF EXISTS idx_order_restaurant ON `Order`;

EXPLAIN ANALYZE
SELECT
    r.restaurant_id,
    r.name                               AS restaurant_name,
    r.location,
    COUNT(o.order_id)                    AS total_orders,
    SUM(o.total_amount)                  AS gross_revenue,
    ROUND(AVG(o.total_amount), 2)        AS avg_order_value,
    SUM(CASE WHEN o.status = 'Cancelled'
             THEN 1 ELSE 0 END)          AS cancelled_count
FROM Restaurant r
LEFT JOIN `Order` o
       ON r.restaurant_id = o.restaurant_id
      AND o.order_date >= '2026-01-01'
      AND o.order_date <  '2026-03-01'
GROUP BY r.restaurant_id, r.name, r.location
ORDER BY gross_revenue DESC;

/*
  Expected BEFORE result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table │ type │ key  │ rows │ Extra                               │
  ├───────┼──────┼──────┼──────┼─────────────────────────────────────┤
  │ r     │ ALL  │ NULL │  15  │                                     │
  │ o     │ ALL  │ NULL │  50  │ Using where; Using join buffer      │
  └──────────────────────────────────────────────────────────────────┘
  Both tables are fully scanned. For each of 15 restaurants MySQL
  examines all 50 orders to find matches (15 × 50 = 750 row checks).
  At 1,000 restaurants × 1,000,000 orders this is catastrophic.
*/


-- ── AFTER INDEXING ───────────────────────────────────────────
CREATE INDEX idx_order_restaurant ON `Order`(restaurant_id);

EXPLAIN ANALYZE
SELECT
    r.restaurant_id,
    r.name                               AS restaurant_name,
    r.location,
    COUNT(o.order_id)                    AS total_orders,
    SUM(o.total_amount)                  AS gross_revenue,
    ROUND(AVG(o.total_amount), 2)        AS avg_order_value,
    SUM(CASE WHEN o.status = 'Cancelled'
             THEN 1 ELSE 0 END)          AS cancelled_count
FROM Restaurant r
LEFT JOIN `Order` o
       ON r.restaurant_id = o.restaurant_id
      AND o.order_date >= '2026-01-01'
      AND o.order_date <  '2026-03-01'
GROUP BY r.restaurant_id, r.name, r.location
ORDER BY gross_revenue DESC;

/*
  Expected AFTER result:
  ┌──────────────────────────────────────────────────────────────────┐
  │ table │ type │ key                  │ rows │ Extra               │
  ├───────┼──────┼──────────────────────┼──────┼─────────────────────┤
  │ r     │ ALL  │ NULL                 │  15  │ Using temporary     │
  │ o     │ ref  │ idx_order_restaurant │  3-4 │ Using where         │
  └──────────────────────────────────────────────────────────────────┘
  For each restaurant MySQL now uses idx_order_restaurant to retrieve
  only its matching orders (~3-4 rows each) rather than scanning all
  50. Total row checks: 15 × ~3 = ~45 instead of 750.
  At scale (1M orders): index reduces join cost by 99%+.
  Further optimisation: Add order_date to the index as
  (restaurant_id, order_date) to push the date filter into the index.
*/
/*
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ Query                   │ Without Index         │ With Index                 │
  ├─────────────────────────┼───────────────────────┼────────────────────────────┤
  │ 1. Customer Orders      │ type=ALL, 50 rows      │ type=ref, ~2 rows         │
  │ 2. Category Menu Items  │ type=ALL, 150 rows     │ type=ref, ~3 rows         │
  │ 3. Restaurant Ratings   │ temp table + filesort  │ index scan, no temp table │
  │ 4. Rider Active Orders  │ type=ALL, 50 rows      │ type=ref, ~3 rows         │
  │ 5. Revenue Report       │ nested ALL scans       │ ref join, ~45 row checks  │
  └──────────────────────────────────────────────────────────────────────────────┘
  */

