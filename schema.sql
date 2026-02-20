-- ============================================================
-- schema.sql
-- Food Delivery System — Complete Database Schema
-- Tables · Constraints · Indexes · Triggers · Views
-- ============================================================

-- ------------------------------------------------------------
-- 0. Setup
-- ------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS Review;
DROP TABLE IF EXISTS Payment;
DROP TABLE IF EXISTS OrderItem;
DROP TABLE IF EXISTS `Order`;
DROP TABLE IF EXISTS MenuItem;
DROP TABLE IF EXISTS Category;
DROP TABLE IF EXISTS Rider;
DROP TABLE IF EXISTS Address;
DROP TABLE IF EXISTS Restaurant;
DROP TABLE IF EXISTS Customer;

SET FOREIGN_KEY_CHECKS = 1;


-- ------------------------------------------------------------
-- 1. Tables
-- ------------------------------------------------------------

CREATE TABLE Customer (
    customer_id   INT           AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(100)  NOT NULL,
    phone         VARCHAR(15)   NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_customer_email UNIQUE (email),
    CONSTRAINT chk_customer_phone CHECK (LENGTH(phone) >= 10)
);

CREATE TABLE Address (
    address_id  INT           AUTO_INCREMENT PRIMARY KEY,
    customer_id INT           NOT NULL,
    street      VARCHAR(255)  NOT NULL,
    city        VARCHAR(100)  NOT NULL,
    postal_code VARCHAR(10)   NOT NULL,
    country     VARCHAR(50)   NOT NULL DEFAULT 'Pakistan',
    is_default  TINYINT(1)    NOT NULL DEFAULT 0,
    CONSTRAINT fk_address_customer
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Restaurant (
    restaurant_id INT           AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    location      VARCHAR(255)  NOT NULL,
    phone         VARCHAR(15)   NOT NULL,
    email         VARCHAR(100)  NOT NULL,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    CONSTRAINT uq_restaurant_email UNIQUE (email)
);

CREATE TABLE Rider (
    rider_id     INT          AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(100) NOT NULL,
    phone        VARCHAR(15)  NOT NULL,
    vehicle_type ENUM('Bike', 'Car', 'Scooter') NOT NULL,
    is_available TINYINT(1)   NOT NULL DEFAULT 1,
    CONSTRAINT uq_rider_email UNIQUE (email),
    CONSTRAINT chk_rider_phone CHECK (LENGTH(phone) >= 10)
);

CREATE TABLE Category (
    category_id   INT          AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT          NOT NULL,
    name          VARCHAR(50)  NOT NULL,
    CONSTRAINT fk_category_restaurant
        FOREIGN KEY (restaurant_id) REFERENCES Restaurant(restaurant_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE MenuItem (
    item_id     INT            AUTO_INCREMENT PRIMARY KEY,
    category_id INT            NOT NULL,
    name        VARCHAR(100)   NOT NULL,
    description TEXT,
    price       DECIMAL(10,2)  NOT NULL,
    is_available TINYINT(1)    NOT NULL DEFAULT 1,
    CONSTRAINT fk_menuitem_category
        FOREIGN KEY (category_id) REFERENCES Category(category_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_menuitem_price CHECK (price > 0)
);

CREATE TABLE `Order` (
    order_id      INT            AUTO_INCREMENT PRIMARY KEY,
    customer_id   INT            NOT NULL,
    restaurant_id INT            NOT NULL,
    address_id    INT            NOT NULL,
    rider_id      INT            DEFAULT NULL,
    order_date    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status        ENUM('Pending','Preparing','Out for Delivery','Delivered','Cancelled')
                                 NOT NULL DEFAULT 'Pending',
    total_amount  DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)   REFERENCES Customer(customer_id),
    CONSTRAINT fk_order_restaurant
        FOREIGN KEY (restaurant_id) REFERENCES Restaurant(restaurant_id),
    CONSTRAINT fk_order_address
        FOREIGN KEY (address_id)    REFERENCES Address(address_id),
    CONSTRAINT fk_order_rider
        FOREIGN KEY (rider_id)      REFERENCES Rider(rider_id),
    CONSTRAINT chk_order_total CHECK (total_amount >= 0)
);

CREATE TABLE OrderItem (
    orderitem_id  INT            AUTO_INCREMENT PRIMARY KEY,
    order_id      INT            NOT NULL,
    item_id       INT            NOT NULL,
    quantity      INT            NOT NULL,
    subunit_price DECIMAL(10,2)  NOT NULL,
    CONSTRAINT fk_orderitem_order
        FOREIGN KEY (order_id) REFERENCES `Order`(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_orderitem_menuitem
        FOREIGN KEY (item_id) REFERENCES MenuItem(item_id),
    CONSTRAINT chk_orderitem_qty   CHECK (quantity > 0),
    CONSTRAINT chk_orderitem_price CHECK (subunit_price > 0)
);

CREATE TABLE Payment (
    payment_id   INT            AUTO_INCREMENT PRIMARY KEY,
    order_id     INT            NOT NULL,
    amount       DECIMAL(10,2)  NOT NULL,
    payment_date DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    method       ENUM('Credit Card','Cash on Delivery','PayPal','JazzCash','EasyPaisa') NOT NULL,
    status       ENUM('Paid','Failed','Refunded') NOT NULL DEFAULT 'Paid',
    CONSTRAINT uq_payment_order UNIQUE (order_id),
    CONSTRAINT fk_payment_order
        FOREIGN KEY (order_id) REFERENCES `Order`(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_payment_amount CHECK (amount > 0)
);

CREATE TABLE Review (
    review_id     INT   AUTO_INCREMENT PRIMARY KEY,
    customer_id   INT   NOT NULL,
    restaurant_id INT   NOT NULL,
    rating        INT   NOT NULL,
    comment       TEXT,
    review_date   DATE  NOT NULL DEFAULT (CURDATE()),
    CONSTRAINT fk_review_customer
        FOREIGN KEY (customer_id)   REFERENCES Customer(customer_id),
    CONSTRAINT fk_review_restaurant
        FOREIGN KEY (restaurant_id) REFERENCES Restaurant(restaurant_id),
    CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 5)
);


-- ------------------------------------------------------------
-- 2. Indexes
-- ------------------------------------------------------------

-- Customer lookup by email (login)
CREATE INDEX idx_customer_email       ON Customer(email);

-- Order queries by customer (order history page)
CREATE INDEX idx_order_customer       ON `Order`(customer_id);

-- Order queries by restaurant (restaurant dashboard)
CREATE INDEX idx_order_restaurant     ON `Order`(restaurant_id);

-- Order queries by status (admin/ops dashboards)
CREATE INDEX idx_order_status         ON `Order`(status);

-- Order queries by rider (rider app)
CREATE INDEX idx_order_rider          ON `Order`(rider_id);

-- Menu item listing per category
CREATE INDEX idx_menuitem_category    ON MenuItem(category_id);

-- Category listing per restaurant (menu page load)
CREATE INDEX idx_category_restaurant  ON Category(restaurant_id);

-- Order line items per order (receipt building)
CREATE INDEX idx_orderitem_order      ON OrderItem(order_id);

-- Reviews per restaurant (rating calculation)
CREATE INDEX idx_review_restaurant    ON Review(restaurant_id);

-- Reviews per customer (customer profile page)
CREATE INDEX idx_review_customer      ON Review(customer_id);


-- ------------------------------------------------------------
-- 3. Triggers
-- ------------------------------------------------------------

DELIMITER //

-- Trigger 1: Auto-update order total when an item is added
CREATE TRIGGER trg_order_total_after_insert
AFTER INSERT ON OrderItem
FOR EACH ROW
BEGIN
    UPDATE `Order`
    SET total_amount = total_amount + (NEW.quantity * NEW.subunit_price)
    WHERE order_id = NEW.order_id;
END;
//

-- Trigger 2: Auto-update order total when an item is removed
CREATE TRIGGER trg_order_total_after_delete
AFTER DELETE ON OrderItem
FOR EACH ROW
BEGIN
    UPDATE `Order`
    SET total_amount = total_amount - (OLD.quantity * OLD.subunit_price)
    WHERE order_id = OLD.order_id;
END;
//

-- Trigger 3: Auto-update order total when an item quantity/price changes
CREATE TRIGGER trg_order_total_after_update
AFTER UPDATE ON OrderItem
FOR EACH ROW
BEGIN
    UPDATE `Order`
    SET total_amount = total_amount
                       - (OLD.quantity * OLD.subunit_price)
                       + (NEW.quantity * NEW.subunit_price)
    WHERE order_id = NEW.order_id;
END;
//

-- Trigger 4: Prevent invalid order status transitions
--   Rules: Delivered orders cannot revert; Cancelled orders cannot reopen
CREATE TRIGGER trg_prevent_invalid_status
BEFORE UPDATE ON `Order`
FOR EACH ROW
BEGIN
    IF OLD.status = 'Delivered' AND NEW.status != 'Delivered' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot change status of a Delivered order.';
    END IF;

    IF OLD.status = 'Cancelled' AND NEW.status != 'Cancelled' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot reopen a Cancelled order.';
    END IF;
END;
//

-- Trigger 5: Set rider as unavailable when assigned to an order
CREATE TRIGGER trg_rider_unavailable_on_assign
AFTER UPDATE ON `Order`
FOR EACH ROW
BEGIN
    -- Mark rider busy when assigned
    IF NEW.rider_id IS NOT NULL AND OLD.rider_id IS NULL THEN
        UPDATE Rider SET is_available = 0 WHERE rider_id = NEW.rider_id;
    END IF;

    -- Mark rider available again when order is delivered or cancelled
    IF OLD.rider_id IS NOT NULL
       AND NEW.status IN ('Delivered', 'Cancelled')
       AND OLD.status NOT IN ('Delivered', 'Cancelled') THEN
        UPDATE Rider SET is_available = 1 WHERE rider_id = OLD.rider_id;
    END IF;
END;
//

DELIMITER ;


-- ------------------------------------------------------------
-- 4. Views
-- ------------------------------------------------------------

-- View 1: Full order summary — joins Customer, Restaurant, Rider
CREATE OR REPLACE VIEW v_order_summary AS
SELECT
    o.order_id,
    o.order_date,
    o.status,
    o.total_amount,
    c.name          AS customer_name,
    c.email         AS customer_email,
    r.name          AS restaurant_name,
    r.location      AS restaurant_location,
    rd.name         AS rider_name,
    rd.vehicle_type AS rider_vehicle,
    a.city          AS delivery_city,
    a.street        AS delivery_street
FROM `Order` o
JOIN Customer    c  ON o.customer_id   = c.customer_id
JOIN Restaurant  r  ON o.restaurant_id = r.restaurant_id
JOIN Address     a  ON o.address_id    = a.address_id
LEFT JOIN Rider  rd ON o.rider_id      = rd.rider_id;


-- View 2: Top 10 most ordered menu items
CREATE OR REPLACE VIEW v_popular_items AS
SELECT
    mi.item_id,
    mi.name                     AS item_name,
    cat.name                    AS category,
    res.name                    AS restaurant,
    SUM(oi.quantity)            AS total_units_sold,
    COUNT(DISTINCT oi.order_id) AS times_ordered,
    ROUND(AVG(oi.subunit_price), 2) AS avg_price
FROM MenuItem  mi
JOIN OrderItem oi  ON mi.item_id      = oi.item_id
JOIN Category  cat ON mi.category_id  = cat.category_id
JOIN Restaurant res ON cat.restaurant_id = res.restaurant_id
GROUP BY mi.item_id, mi.name, cat.name, res.name
ORDER BY total_units_sold DESC
LIMIT 10;


-- View 3: Restaurant ratings dashboard
CREATE OR REPLACE VIEW v_restaurant_ratings AS
SELECT
    res.restaurant_id,
    res.name                        AS restaurant_name,
    res.location,
    COUNT(rev.review_id)            AS review_count,
    ROUND(AVG(rev.rating), 2)       AS average_rating,
    SUM(CASE WHEN rev.rating = 5 THEN 1 ELSE 0 END) AS five_star_count,
    SUM(CASE WHEN rev.rating <= 2 THEN 1 ELSE 0 END) AS low_rating_count
FROM Restaurant res
LEFT JOIN Review rev ON res.restaurant_id = rev.restaurant_id
GROUP BY res.restaurant_id, res.name, res.location
ORDER BY average_rating DESC;


-- View 4: Revenue report per restaurant
CREATE OR REPLACE VIEW v_restaurant_revenue AS
SELECT
    res.restaurant_id,
    res.name                            AS restaurant_name,
    COUNT(DISTINCT o.order_id)          AS total_orders,
    SUM(o.total_amount)                 AS gross_revenue,
    COUNT(DISTINCT o.customer_id)       AS unique_customers,
    ROUND(AVG(o.total_amount), 2)       AS avg_order_value,
    SUM(CASE WHEN o.status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_orders
FROM Restaurant res
LEFT JOIN `Order` o ON res.restaurant_id = o.restaurant_id
GROUP BY res.restaurant_id, res.name;
