from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3, hashlib, os, datetime, base64, uuid, hmac, json
import hashlib as _hl

# ── JWT / PBKDF2 (stdlib only, no extra deps) ─────────────────────────────────
import secrets, struct, functools

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'foodapp_secret_2024_change_me')

JWT_SECRET = os.environ.get('JWT_SECRET', 'quickbite_jwt_secret_change_in_production')

# ── PBKDF2-HMAC-SHA256 password hashing (NIST SP 800-132) ────────────────────
def hash_password(pw):
    """PBKDF2-HMAC-SHA256 with 310000 iterations + random salt."""
    import hashlib as _h
    salt = secrets.token_bytes(16)
    dk = _h.pbkdf2_hmac('sha256', pw.encode(), salt, 310_000)
    return f"pbkdf2:sha256:310000${salt.hex()}${dk.hex()}"

def check_password(pw, stored):
    """Verify password — handles PBKDF2, legacy SHA-256 hex, and any other format."""
    import hashlib as _h
    if not stored:
        return False
    # PBKDF2 format (new): pbkdf2:sha256:iters$salt$dk
    if stored.startswith('pbkdf2:sha256:'):
        try:
            _, _, rest = stored.split(':', 2)
            iters_str, salt_hex, dk_hex = rest.split('$')
            dk = _h.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(salt_hex), int(iters_str))
            return hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False
    # Legacy SHA-256 hex (64 chars)
    if len(stored) == 64:
        return hmac.compare_digest(stored, _h.sha256(pw.encode()).hexdigest())
    # Legacy SHA-256 with prefix
    if stored.startswith('sha256:'):
        return hmac.compare_digest(stored[7:], _h.sha256(pw.encode()).hexdigest())
    # Last resort: direct compare
    return hmac.compare_digest(stored, pw)

# ── JWT helpers ───────────────────────────────────────────────────────────────
def _b64url(data):
    if isinstance(data, str): data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def _b64url_decode(s):
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + '=' * (pad % 4))

def issue_jwt(user_id, role):
    """Issue HS256 JWT valid for 24 hours."""
    header  = _b64url(json.dumps({'alg':'HS256','typ':'JWT'}))
    payload = _b64url(json.dumps({
        'sub': str(user_id),
        'role': role,
        'iat': int(datetime.datetime.utcnow().timestamp()),
        'exp': int((datetime.datetime.utcnow() + datetime.timedelta(hours=24)).timestamp())
    }))
    sig = _b64url(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), _hl.sha256).digest())
    return f"{header}.{payload}.{sig}"

def decode_jwt(token):
    """Decode and verify JWT. Returns payload dict or None."""
    try:
        parts = token.split('.')
        if len(parts) != 3: return None
        header, payload, sig = parts
        expected = _b64url(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), _hl.sha256).digest())
        if not hmac.compare_digest(sig, expected): return None
        data = json.loads(_b64url_decode(payload))
        if data.get('exp', 0) < int(datetime.datetime.utcnow().timestamp()): return None
        return data
    except Exception:
        return None

# ── RBAC decorator ────────────────────────────────────────────────────────────
def require_auth(*roles):
    """Decorator: require valid JWT + optional role check.
    Usage: @require_auth('admin') or @require_auth('admin','manager') or @require_auth()
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get('Authorization', '')
            token = auth.removeprefix('Bearer ').strip() if auth.startswith('Bearer ') else None
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            payload = decode_jwt(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            if roles and payload.get('role') not in roles:
                return jsonify({'error': f'Access denied. Required: {roles}'}), 403
            kwargs['_auth_uid']  = int(payload['sub'])
            kwargs['_auth_role'] = payload['role']
            return fn(*args, **kwargs)
        return wrapper
    return decorator

require_admin    = require_auth('admin')
require_manager  = require_auth('manager')
require_rider    = require_auth('rider')
require_customer = require_auth('customer')
require_any      = require_auth()
CORS(app)

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

@app.route('/api/<path:path>',    methods=['OPTIONS'])
@app.route('/api/v1/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    from flask import Response
    r = Response()
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return r

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'food_delivery.db')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=10000')
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def log_audit(user_id, action, details=''):
    try:
        db = get_db()
        db.execute('INSERT INTO audit_log (user_id, action, details, timestamp) VALUES (?,?,?,?)',
                   (user_id, action, details, datetime.datetime.now().isoformat()))
        db.commit()
        db.close()
    except: pass

def save_image(b64_data, prefix='img'):
    """Save base64 image to disk, return filename"""
    if not b64_data or not b64_data.startswith('data:'):
        return None
    try:
        header, data = b64_data.split(',', 1)
        ext = 'jpg' if 'jpeg' in header else ('png' if 'png' in header else 'jpg')
        fname = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
        with open(os.path.join(UPLOAD_DIR, fname), 'wb') as f:
            f.write(base64.b64decode(data))
        return fname
    except Exception as e:
        print('Image save error:', e)
        return None

@app.route('/api/test', methods=['GET','POST'])
def test_endpoint():
    return jsonify({'ok': True, 'method': request.method, 'msg': 'Backend is working!'})


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ── Serve frontend from Flask (eliminates all CORS issues) ───────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'src')

@app.route('/')
def serve_root():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    full_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer','rider','admin','manager')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS riders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            vehicle_type TEXT,
            license_plate TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
            is_available INTEGER DEFAULT 1,
            total_earnings REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cuisine TEXT,
            location TEXT,
            phone TEXT,
            image_filename TEXT,
            rating REAL DEFAULT 4.0,
            delivery_time INTEGER DEFAULT 30,
            is_open INTEGER DEFAULT 1,
            status TEXT DEFAULT 'approved' CHECK(status IN ('pending','approved','rejected')),
            manager_id INTEGER,
            added_by INTEGER,
            description TEXT,
            min_order REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image_filename TEXT,
            is_available INTEGER DEFAULT 1,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            rider_id INTEGER,
            status TEXT DEFAULT 'Pending',
            total_amount REAL NOT NULL,
            delivery_fee REAL DEFAULT 50,
            platform_fee REAL DEFAULT 0,
            rider_tip REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'Cash on Delivery',
            delivery_address TEXT,
            special_instructions TEXT,
            estimated_time INTEGER DEFAULT 35,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            order_id INTEGER,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            order_id INTEGER,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS produce_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price_per_kg REAL NOT NULL,
            image_filename TEXT,
            description TEXT,
            is_available INTEGER DEFAULT 1,
            stock_kg REAL DEFAULT 50.0
        );
        CREATE TABLE IF NOT EXISTS produce_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            rider_id INTEGER,
            total_amount REAL NOT NULL,
            delivery_fee REAL DEFAULT 50,
            payment_method TEXT DEFAULT 'Cash on Delivery',
            delivery_address TEXT,
            status TEXT DEFAULT 'Pending',
            special_instructions TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS produce_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            produce_id INTEGER NOT NULL,
            quantity_kg REAL NOT NULL,
            unit_price REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT DEFAULT 'percent',
            discount_value REAL NOT NULL,
            min_order REAL DEFAULT 0,
            max_uses INTEGER DEFAULT 100,
            used_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS loyalty_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER UNIQUE NOT NULL,
            total_points INTEGER DEFAULT 0,
            lifetime_points INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS loyalty_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            order_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Seed admin
    ph = hash_password('hassan')
    db.execute('INSERT OR IGNORE INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)',
               ('Admin Ahsen','ahsen@gmail.com','03001234567',ph,'admin'))

    # Seed 20 famous restaurants with full data
    # (id, name, cuisine, location, phone, rating, dtime, slug, image_filename)
    restaurants = [
        (1,'McDonald\'s','Fast Food','DHA Lahore','0311-0000001',4.3,20,'mcdonalds','rest_mcdonalds.png'),
        (2,'KFC','Fast Food','Gulberg Lahore','0311-0000002',4.4,25,'kfc','rest_kfc.png'),
        (3,'Pizza Hut','Italian','Model Town Lahore','0311-0000003',4.2,35,'pizzahut','rest_pizzahut.png'),
        (4,'Domino\'s Pizza','Italian','Johar Town Lahore','0311-0000004',4.1,30,'dominos','rest_dominos.png'),
        (5,'Subway','Sandwiches','Bahria Town Lahore','0311-0000005',4.0,20,'subway','rest_subway.png'),
        (6,'Hardee\'s','Fast Food','DHA Phase 6 Lahore','0311-0000006',4.2,25,'hardees','rest_hardees.png'),
        (7,'Burger King','Fast Food','MM Alam Road Lahore','0311-0000007',4.3,25,'burgerking','rest_burgerking.jpg'),
        (8,'Biryani Pot','Pakistani','Anarkali Lahore','0311-0000008',4.8,40,'biryanipot','rest_biryanipot.png'),
        (9,'Ravi Restaurant','Pakistani','Davis Road Lahore','0311-0000009',4.6,35,'ravi','rest_ravi.png'),
        (10,'Café Aylanto','Continental','Gulberg III Lahore','0311-0000010',4.7,45,'aylanto','rest_aylanto.jpg'),
        (11,'Sakura','Japanese','Liberty Market Lahore','0311-0000011',4.5,50,'sakura','rest_sakura.png'),
        (12,'Chinese Palace','Chinese','Cavalry Ground Lahore','0311-0000012',4.2,40,'chinesepalace','rest_chinesepalace.png'),
        (13,'Cosa Nostra','Italian','Hussain Chowk Lahore','0311-0000013',4.6,40,'cosanostra','rest_cosanostra.png'),
        (14,'Andaaz','Pakistani','Township Lahore','0311-0000014',4.7,40,'andaaz','rest_andaaz.jpg'),
        (15,'BBQ Tonight','BBQ','Ferozepur Road Lahore','0311-0000015',4.5,45,'bbqtonight','rest_bbqtonight.png'),
        (16,'Ginyaki','Japanese','DHA Y-Block Lahore','0311-0000016',4.4,50,'ginyaki','rest_ginyaki.jpg'),
        (17,'Nando\'s','Grilled','Emporium Mall Lahore','0311-0000017',4.3,30,'nandos','rest_nandos.png'),
        (18,'Thai Cuisine','Thai','Gulberg V Lahore','0311-0000018',4.4,45,'thai','rest_thai.png'),
        (19,'Johnny & Jugnu','Burgers','Packages Mall Lahore','0311-0000019',4.6,30,'jj','rest_jj.jpg'),
        (20,'Hot Spot','Fast Food','Canal Road Lahore','0311-0000020',4.1,25,'hotspot','rest_hotspot.jpg'),
    ]

    menu_data = {
        1: [  # McDonald's
            ('Burgers',[("Big Mac","Two beef patties, special sauce, lettuce, cheese",550),
                        ("Quarter Pounder","Quarter pound beef with cheese",620),
                        ("McChicken","Crispy chicken fillet burger",480),
                        ("Filet-O-Fish","Fish fillet with tartar sauce",520),
                        ("Double Cheeseburger","Two beef patties, double cheese",490)]),
            ('Sides',[("Large Fries","Golden crispy fries",250),
                      ("Nuggets 9pc","Crispy chicken nuggets with dips",490),
                      ("Onion Rings","Beer battered onion rings",220),
                      ("Coleslaw","Creamy coleslaw salad",150)]),
            ('Drinks',[("Coke Large","Refreshing Coca-Cola",180),
                       ("McFlurry","Ice cream with Oreo topping",320),
                       ("Chocolate Shake","Thick chocolate milkshake",380),
                       ("Mineral Water","500ml mineral water",100)]),
            ('Meals',[("Big Mac Meal","Big Mac + fries + drink",850),
                      ("McNuggets Meal","9 nuggets + fries + drink",750)])
        ],
        2: [  # KFC
            ('Burgers',[("Zinger Burger","Spicy crispy chicken fillet",580),
                        ("Tower Burger","Double stacked zinger",750),
                        ("Chick'n Share","Grilled chicken burger",520),
                        ("Fillet Burger","Classic chicken fillet",480)]),
            ('Chicken',[("2pc Chicken","Original recipe 2 pieces",420),
                        ("4pc Chicken","Original recipe 4 pieces",780),
                        ("Mighty Bucket","Mix of 8 pieces",1400),
                        ("Crispy Strips 3pc","Crispy chicken tenders",480),
                        ("Hot Wings 6pc","Spicy crispy wings",550)]),
            ('Sides',[("Mashed Potato","Creamy mashed potatoes",180),
                      ("Coleslaw","KFC signature coleslaw",150),
                      ("Fries","Seasoned crispy fries",220),
                      ("Rice","Steamed basmati rice",150)]),
            ('Deals',[("Zinger Meal","Zinger + fries + drink",900),
                      ("Family Feast","8pc chicken + 2 fries + 2 drinks",2800),
                      ("Student Deal","Zinger + rice + drink",750)])
        ],
        3: [  # Pizza Hut
            ('Pizzas',[("Margherita 9""","Classic tomato & mozzarella",750),
                       ("Pepperoni 9""","Loaded pepperoni pizza",950),
                       ("BBQ Chicken 9""","BBQ sauce with grilled chicken",1050),
                       ("Veggie Supreme 9""","Fresh garden vegetables",850),
                       ("Meat Lovers 9""","Triple meat topping",1100),
                       ("Cheese Lover 12""","Extra cheese loaded",1350)]),
            ('Pasta',[("Bolognese","Classic meat pasta",650),
                      ("Arrabiata","Spicy tomato pasta",580),
                      ("Alfredo","Creamy white sauce pasta",620)]),
            ('Sides',[("Garlic Bread","Buttery garlic bread",280),
                      ("Wings 6pc","Spicy chicken wings",580),
                      ("Chicken Strips","Crispy strips with dip",480)]),
            ('Desserts',[("Chocolate Brownie","Warm fudge brownie",380),
                         ("Garlic Ice Cream","Unique Pizza Hut dessert",250)])
        ],
        4: [  # Domino's
            ('Pizzas',[("Philly Cheese Steak","Beef with peppers & cheese",950),
                       ("Chicken Tikka","Spiced chicken tikka pizza",900),
                       ("Beef Sensation","Loaded beef pizza",1000),
                       ("Veggie Fiesta","Garden fresh vegetables",800),
                       ("ExtravaganZZa","Everything on one pizza",1200),
                       ("Pacific Veggie","Roasted veggies",850)]),
            ('Sides',[("Bread Twists","Garlic butter bread twists",320),
                      ("Chicken Kickers","Spicy chicken pieces",520),
                      ("Stuffed Cheesy Bites","Cheese stuffed bites",480)]),
            ('Dips & Extras',[("Ranch Dip","Creamy ranch dipping sauce",80),
                               ("BBQ Sauce","Sweet BBQ dip",80),
                               ("Extra Cheese","Add extra cheese",150)]),
            ('Drinks',[("Pepsi 1.5L","Chilled Pepsi",180),
                       ("7UP 1.5L","Chilled 7UP",180),
                       ("Mountain Dew","Green energy drink",150)])
        ],
        5: [  # Subway
            ('Footlongs',[("Chicken Teriyaki","Teriyaki glazed chicken sub",850),
                          ("BMT","Beef, mortadella & turkey",950),
                          ("Veggie Delite","Fresh garden vegetables",700),
                          ("Club","Turkey, ham & roast beef",900),
                          ("Tuna","Classic tuna with mayo",800)]),
            ('6-inch',[("Egg & Cheese","Scrambled eggs with cheese",480),
                       ("Chicken & Bacon Ranch","Grilled chicken with bacon",650),
                       ("Italian BMT 6""","Classic Italian meats",620)]),
            ('Salads',[("Garden Fresh","Mixed green salad",450),
                       ("Chicken Caesar","Grilled chicken caesar",550)]),
            ('Drinks & Extras',[("Fountain Drink","Any soft drink",150),
                                 ("Cookies 3pc","Freshly baked cookies",280),
                                 ("Chips","Any chips bag",120)])
        ],
        6: [  # Hardee's
            ('Burgers',[("Thickburger 1/3","Charbroiled beef thickburger",680),
                        ("Monster Burger","Double patty monster burger",950),
                        ("Mushroom Swiss","Beef with mushrooms and swiss",720),
                        ("BBQ Thickburger","BBQ beef with onion rings",750),
                        ("Spicy Chicken","Nashville hot chicken burger",620)]),
            ('Sides',[("Natural Cut Fries","Real potato cut fries",250),
                      ("Onion Rings","Crispy onion rings",220),
                      ("Mac & Cheese Bites","Fried mac & cheese",320)]),
            ('Breakfast',[("Biscuit & Gravy","Southern style breakfast",450),
                          ("Loaded Breakfast Burrito","Eggs bacon cheese",520),
                          ("Pancakes","Fluffy buttermilk pancakes",380)]),
            ('Drinks',[("Milkshake","Thick hand-scooped shake",450),
                       ("Orange Juice","Fresh squeezed OJ",200),
                       ("Iced Tea","Sweet iced tea",150)])
        ],
        7: [  # Burger King
            ('Burgers',[("Whopper","Flame-grilled beef with veggies",720),
                        ("Double Whopper","Double beef whopper",950),
                        ("Whopper Jr.","Smaller whopper version",520),
                        ("Crispy Chicken","Crispy fried chicken burger",580),
                        ("Veggie Burger","Plant-based patty burger",550)]),
            ('Chicken',[("Chicken Fries","Fry-shaped chicken strips",450),
                        ("Nuggets 10pc","Crispy nuggets",480),
                        ("Chicken Royale","Premium chicken sandwich",650)]),
            ('Sides',[("King Fries","Large seasoned fries",250),
                      ("Onion Rings","Classic onion rings",220),
                      ("Mozzarella Sticks","Fried cheese sticks",320)]),
            ('Desserts',[("Sundae","Soft serve with toppings",250),
                         ("Apple Pie","Warm baked apple pie",200),
                         ("Hershey's Pie","Chocolate pie slice",320)])
        ],
        8: [  # Biryani Pot
            ('Biryani',[("Chicken Biryani","Fragrant basmati with spiced chicken",380),
                        ("Mutton Biryani","Tender mutton in aromatic rice",480),
                        ("Beef Biryani","Slow-cooked beef biryani",450),
                        ("Prawn Biryani","Fresh prawns in spiced rice",550),
                        ("Vegetable Biryani","Garden vegetables biryani",280)]),
            ('Karahi',[("Chicken Karahi","Classic tomato karahi",850),
                       ("Mutton Karahi","Rich mutton karahi",1100),
                       ("Shinwari Karahi","Peshawar style karahi",950)]),
            ('Starters',[("Seekh Kebab","Grilled minced meat kebabs",320),
                         ("Samosa 3pc","Crispy potato samosas",120),
                         ("Dahi Bhalla","Yogurt with lentil dumplings",180)]),
            ('Breads',[("Naan","Freshly baked clay oven naan",60),
                       ("Paratha","Layered whole wheat paratha",70),
                       ("Puri","Fried wheat bread",50)])
        ],
        9: [  # Ravi Restaurant
            ('Mains',[("Paye","Slow cooked trotters",350),
                      ("Nihari","Braised beef shank stew",380),
                      ("Siri Paye","Head and feet curry",380),
                      ("Haleem","Lentils with slow-cooked meat",320),
                      ("Daal Makhni","Black lentils in butter",280)]),
            ('BBQ',[("Beef Tikka","Marinated grilled beef",450),
                    ("Chicken Tikka","Tandoor grilled chicken",400),
                    ("Boti","Spiced grilled lamb pieces",480),
                    ("Seekh Kebab","Minced meat kebabs",320)]),
            ('Breads',[("Roti","Thin wheat roti",40),
                       ("Naan","Clay oven naan",60),
                       ("Peshwari Naan","Sweet coconut filled naan",120)]),
            ('Extras',[("Raita","Yogurt with cucumber",80),
                       ("Chutney","Fresh mint chutney",60),
                       ("Lassi Sweet","Sweet yogurt drink",150)])
        ],
        10: [  # Café Aylanto
            ('Starters',[("Bruschetta","Toasted bread with tomatoes",480),
                         ("Soup of the Day","Chef's daily special soup",380),
                         ("Shrimp Cocktail","Chilled shrimp with sauce",750),
                         ("Calamari","Crispy fried squid rings",680)]),
            ('Mains',[("Grilled Salmon","Atlantic salmon with herbs",2200),
                      ("Beef Tenderloin","200g grilled tenderloin",2800),
                      ("Chicken Supreme","Stuffed chicken with mushroom",1800),
                      ("Pasta Primavera","Fresh garden vegetable pasta",1200),
                      ("Seafood Risotto","Creamy seafood risotto",1900)]),
            ('Pizzas',[("Truffle Mushroom","Black truffle & mushroom",1400),
                       ("Prawn & Pesto","Fresh prawns with basil pesto",1500)]),
            ('Desserts',[("Tiramisu","Italian coffee dessert",680),
                         ("Crème Brûlée","Classic French custard",620),
                         ("Chocolate Fondant","Warm chocolate lava cake",750)])
        ],
        11: [  # Sakura
            ('Sushi Rolls',[("California Roll 8pc","Crab, avocado, cucumber",850),
                            ("Salmon Roll 8pc","Fresh Atlantic salmon",1100),
                            ("Dragon Roll 8pc","Shrimp tempura & avocado",1200),
                            ("Rainbow Roll 8pc","Mixed fish on California",1300),
                            ("Spicy Tuna Roll","Tuna with spicy mayo",1050)]),
            ('Ramen',[("Tonkotsu Ramen","Rich creamy pork broth",850),
                      ("Miso Ramen","Traditional miso soup base",780),
                      ("Shoyu Ramen","Soy sauce based broth",780),
                      ("Spicy Ramen","Fiery chili oil ramen",850)]),
            ('Starters',[("Edamame","Steamed salted soybeans",350),
                         ("Gyoza 6pc","Pan-fried dumplings",480),
                         ("Miso Soup","Traditional miso soup",280)]),
            ('Mains',[("Chicken Katsu","Panko breaded chicken",950),
                      ("Teriyaki Bowl","Glazed chicken rice bowl",850),
                      ("Tempura Platter","Assorted tempura",1100)])
        ],
        12: [  # Chinese Palace
            ('Starters',[("Spring Rolls 4pc","Crispy vegetable rolls",320),
                         ("Wonton Soup","Clear broth with wontons",380),
                         ("Dim Sum Basket","Assorted steamed dumplings",580),
                         ("Crispy Corn","Crunchy masala corn",280)]),
            ('Mains',[("Kung Pao Chicken","Spicy peanut chicken",850),
                      ("Beef & Broccoli","Stir fried beef with veggies",950),
                      ("Sweet Sour Pork","Classic sweet and sour",900),
                      ("Mapo Tofu","Spicy tofu with minced pork",750),
                      ("Mongolian Beef","Caramelized beef strips",980)]),
            ('Rice & Noodles',[("Fried Rice","Wok fried rice with egg",380),
                               ("Chow Mein","Stir fried noodles",420),
                               ("Lo Mein","Soft noodles in sauce",400)]),
            ('Desserts',[("Mango Pudding","Chilled mango dessert",250),
                         ("Sesame Balls","Fried glutinous rice balls",280),
                         ("Fortune Cookie","Sweet cookie with message",80)])
        ],
        13: [  # Cosa Nostra
            ('Antipasti',[("Caprese Salad","Fresh mozzarella & tomato",750),
                          ("Prosciutto & Melon","Cured ham with sweet melon",850),
                          ("Arancini 4pc","Fried risotto balls",620),
                          ("Antipasto Platter","Selection of Italian starters",1200)]),
            ('Pasta',[("Spaghetti Carbonara","Egg, pecorino, guanciale",1100),
                      ("Pasta all\'Amatriciana","Tomato, guanciale, pecorino",1050),
                      ("Linguine Vongole","Clams in white wine",1400),
                      ("Gnocchi al Pesto","Potato gnocchi with basil",950)]),
            ('Pizzas',[("Margherita DOC","San Marzano tomato, buffalo mozzarella",1200),
                       ("Diavola","Spicy salami & chili",1300),
                       ("Quattro Stagioni","Four seasons pizza",1400)]),
            ('Dolci',[("Panna Cotta","Vanilla cream dessert",580),
                      ("Cannoli","Sicilian pastry with ricotta",520),
                      ("Affogato","Espresso over gelato",450)])
        ],
        14: [  # Andaaz
            ('Karahi',[("Chicken Karahi","Lahori style tomato karahi",900),
                       ("Mutton Karahi","Tender mutton karahi",1200),
                       ("White Karahi","Creamy yogurt based karahi",950),
                       ("Chilli Chicken","Spicy dry chilli chicken",850)]),
            ('Biryani',[("Andaaz Special Biryani","House special recipe",450),
                        ("Chicken Tikka Biryani","Tikka pieces in biryani",480)]),
            ('Starters',[("Reshmi Kebab","Silky smooth chicken kebab",350),
                         ("Chicken Tikka","Tandoor grilled chicken",420),
                         ("Boti Kebab","Spiced lamb on skewer",480),
                         ("Dahi Ke Kebab","Yogurt and lentil kebab",320)]),
            ('Breads & Rice',[("Butter Naan","Tandoor naan with butter",80),
                              ("Laccha Paratha","Layered flaky paratha",90),
                              ("Steamed Rice","Plain basmati rice",150),
                              ("Khichri","Lentils and rice mix",200)])
        ],
        15: [  # BBQ Tonight
            ('BBQ',[("Mixed BBQ Platter","Assorted BBQ for 2",1800),
                    ("Chicken BBQ Platter","Full chicken BBQ",1400),
                    ("Beef Seekh Platter","8 beef seekh kebabs",1200),
                    ("Lamb Chops","Grilled marinated chops",1600),
                    ("Prawn BBQ","Jumbo prawns on grill",1800)]),
            ('Tikka',[("Chicken Tikka Half","Tandoor tikka half",650),
                      ("Beef Tikka","Marinated beef chunks",750),
                      ("Boti Tikka","Spiced lamb pieces",800)]),
            ('Karahi',[("Karahi Chicken","BBQ style karahi",950),
                       ("Handi Mutton","Slow cooked clay pot mutton",1300)]),
            ('Sides',[("Naan","Fresh tandoor naan",70),
                      ("Raita","Mint yogurt",100),
                      ("Salad","Fresh garden salad",150),
                      ("Chutney Platter","3 varieties of chutney",120)])
        ],
        16: [  # Ginyaki
            ('Sushi',[("Nigiri Salmon 2pc","Hand-pressed salmon sushi",480),
                      ("Nigiri Tuna 2pc","Hand-pressed tuna sushi",520),
                      ("Salmon Sashimi 5pc","Fresh sliced salmon",750),
                      ("Sashimi Platter","Chef selection sashimi",1800),
                      ("Temaki Hand Roll","Cone-shaped hand roll",580)]),
            ('Hot Dishes',[("Ebi Tempura","Crispy shrimp tempura",850),
                           ("Karaage Chicken","Japanese fried chicken",750),
                           ("Takoyaki 6pc","Octopus balls",480),
                           ("Agedashi Tofu","Lightly fried tofu in dashi",420)]),
            ('Rice & Noodles',[("Yakitori Bowl","Grilled chicken rice bowl",750),
                               ("Udon Soup","Thick wheat noodles in broth",650),
                               ("Soba Noodles","Buckwheat noodles cold/hot",600)]),
            ('Desserts',[("Mochi Ice Cream","Rice cake with ice cream",350),
                         ("Matcha Lava Cake","Green tea lava cake",480),
                         ("Dorayaki","Red bean pancake sandwich",280)])
        ],
        17: [  # Nando's
            ('Chicken',[("1/4 Chicken","Peri-peri marinated chicken",650),
                        ("1/2 Chicken","Half flame-grilled chicken",1100),
                        ("Whole Chicken","Full peri-peri chicken",2000),
                        ("Spicy Wings 6pc","Peri-peri glazed wings",680)]),
            ('Burgers',[("Chicken Burger","Grilled fillet peri-peri burger",680),
                        ("Double Chicken","Double fillet burger",850)]),
            ('Sides',[("Spicy Rice","Peri-peri spiced rice",280),
                      ("Corn on the Cob","Grilled sweet corn",250),
                      ("Peri Peri Chips","Seasoned cut chips",280),
                      ("Creamy Mash","Buttery mashed potato",250),
                      ("Garlic Bread","Toasted garlic bread",200)]),
            ('Desserts',[("Natas","Portuguese custard tarts",250),
                         ("Churros","Cinnamon sugar churros",380)])
        ],
        18: [  # Thai Cuisine
            ('Starters',[("Tom Yum Soup","Spicy lemongrass shrimp soup",480),
                         ("Tom Kha Gai","Coconut milk chicken soup",520),
                         ("Satay 4pc","Grilled chicken skewers + peanut",480),
                         ("Spring Rolls","Crispy Thai spring rolls",350)]),
            ('Mains',[("Pad Thai","Stir-fried rice noodles",750),
                      ("Green Curry","Aromatic green curry",850),
                      ("Red Curry","Rich spicy red curry",850),
                      ("Massaman Curry","Mild peanut curry",900),
                      ("Basil Fried Rice","Thai holy basil rice",700)]),
            ('Noodles',[("Pad See Ew","Wide noodles in soy sauce",700),
                        ("Khao Soi","Northern Thai noodle soup",800)]),
            ('Desserts',[("Mango Sticky Rice","Sweet mango with glutinous rice",380),
                         ("Thai Iced Tea","Sweetened milk tea",250),
                         ("Coconut Ice Cream","Fresh coconut ice cream",280)])
        ],
        19: [  # Johnny & Jugnu
            ('Burgers',[("OG Burger","Classic smash burger",650),
                        ("Double Stack","Double smashed patty",850),
                        ("Johnny Special","House signature burger",750),
                        ("Crispy Chicken","Buttermilk fried chicken",680),
                        ("Mushroom Truffle","Truffle mayo mushroom burger",850)]),
            ('Sides',[("Crinkle Fries","Crispy crinkle cut fries",280),
                      ("Sweet Potato Fries","Seasoned sweet potato fries",320),
                      ("Onion Rings","Beer battered rings",280),
                      ("Mac & Cheese","Creamy mac and cheese",380)]),
            ('Shakes',[("Classic Vanilla","Thick vanilla milkshake",380),
                       ("Chocolate Overload","Double chocolate shake",420),
                       ("Strawberry Fields","Fresh strawberry shake",400)]),
            ('Extras',[("Add Egg","Fried egg topping",80),
                       ("Add Bacon","Crispy turkey bacon",120),
                       ("Add Cheese","Extra cheese slice",80)])
        ],
        20: [  # Hot Spot
            ('Burgers',[("Smash Burger","Smashed beef patty",550),
                        ("Chicken Crunch","Crunchy chicken burger",520),
                        ("BBQ Special","BBQ sauce beef burger",600),
                        ("Veggie Delight","Plant-based burger",480)]),
            ('Wraps',[("Chicken Tikka Wrap","Spiced chicken in flour wrap",450),
                      ("BBQ Beef Wrap","BBQ beef with veggies",480),
                      ("Falafel Wrap","Crispy falafel wrap",380)]),
            ('Sides',[("Hot Spot Fries","Seasoned signature fries",220),
                      ("Coleslaw","Creamy homemade coleslaw",150),
                      ("Corn Salad","Spiced corn with herbs",180)]),
            ('Drinks',[("Lemonade","Fresh squeezed lemonade",200),
                       ("Iced Coffee","Cold brew iced coffee",250),
                       ("Pakola","Classic Pakistani soda",120),
                       ("Lassi","Thick yogurt drink",200)])
        ],
    }


    # Seed produce items only if table is empty (prevents duplicates on restart)
    if db.execute('SELECT COUNT(*) FROM produce_items').fetchone()[0] == 0:
        produce = [
            ('Apple','fruit',280,'fruit_apple.jpg','Fresh crisp red apples, sweet and juicy'),
            ('Banana','fruit',120,'fruit_banana.jpg','Ripe yellow bananas, naturally sweet'),
            ('Grapes','fruit',350,'fruit_grapes.jpg','Sweet dark purple grapes, seedless'),
            ('Guava','fruit',150,'fruit_guava.jpg','Fresh guava, rich in Vitamin C'),
            ('Lychee','fruit',450,'fruit_lychee.jpg','Sweet and fragrant lychee'),
            ('Mango','fruit',320,'fruit_mango.jpg','Premium Sindhri mangoes, king of fruits'),
            ('Orange','fruit',180,'fruit_orange.jpg','Juicy Valencia oranges, Vitamin C rich'),
            ('Peach','fruit',400,'fruit_peach.jpg','Soft and sweet peaches'),
            ('Pineapple','fruit',200,'fruit_pineapple.jpg','Tropical pineapple, sweet and tangy'),
            ('Strawberry','fruit',500,'fruit_strawberry.jpg','Fresh red strawberries, perfectly sweet'),
            ('Watermelon','fruit',80,'fruit_watermelon.jpg','Chilled watermelon, refreshing summer fruit'),
            ('Sweet Potato','vegetable',120,'veg_sweet_potato.jpg','Naturally sweet yam, rich in vitamins'),
            ('Brinjal (Eggplant)','vegetable',100,'veg_brinjal.jpg','Tender purple brinjal, great for karahi'),
            ('Carrot','vegetable',90,'veg_carrot.jpg','Crunchy fresh carrots, locally grown'),
            ('Lettuce','vegetable',180,'veg_lettuce.jpg','Crisp fresh lettuce leaves for salads'),
            ('Red Chilli','vegetable',200,'veg_chilli.jpg','Hot red chillies, freshly picked'),
            ('Corn','vegetable',150,'veg_corn.jpg','Sweet golden corn on the cob'),
            ('Cucumber','vegetable',80,'veg_cucumber.jpg','Cool and fresh cucumbers'),
            ('Garlic','vegetable',600,'veg_garlic.jpg','Aromatic garlic bulbs, locally grown'),
            ('Avocado','vegetable',800,'veg_avocado.jpg','Creamy ripe avocados, premium quality'),
            ('Lady Finger (Okra)','vegetable',130,'veg_ladyfinger.jpg','Fresh tender bhindi / okra'),
            ('Lemon','vegetable',250,'veg_lemon.jpg','Zesty yellow lemons, fresh and tangy'),
            ('Onion','vegetable',70,'veg_onion.jpg','Fresh yellow onions, kitchen essential'),
            ('Peas','vegetable',220,'veg_pea.jpg','Sweet green peas in pod'),
            ('Potato','vegetable',60,'veg_potato.jpg','Fresh potatoes, perfect for any dish'),
            ('Tomato','vegetable',110,'veg_tomato.jpg','Ripe red tomatoes, farm fresh'),
        ]
        for p in produce:
            db.execute('INSERT INTO produce_items (name,category,price_per_kg,image_filename,description) VALUES (?,?,?,?,?)', p)


    # Seed default promo codes only if none exist (preserves admin-created codes)
    existing_count = db.execute("SELECT COUNT(*) FROM promo_codes").fetchone()[0]
    if existing_count == 0:
        promos = [
            ('HASSAN',  'percent', 10, 0, 1000),
            ('AHSEN',   'percent', 20, 0, 1000),
            ('DBMS',    'percent', 30, 0, 1000),
            ('LADLAY',  'percent', 15, 0, 1000),
            ('SPECIAL', 'percent', 35, 0, 1000),
        ]
        for p in promos:
            db.execute('INSERT INTO promo_codes (code,discount_type,discount_value,min_order,max_uses) VALUES (?,?,?,?,?)', p)

    cat_id = 100
    item_id = 100

    for rid, rname, cuisine, location, phone, rating, dtime, slug, img in restaurants:
        db.execute("INSERT OR IGNORE INTO restaurants (id,name,cuisine,location,phone,rating,delivery_time,status,image_filename) VALUES (?,?,?,?,?,?,?,'approved',?)",
                   (rid, rname, cuisine, location, phone, rating, dtime, img))
        # Patch any existing row that has no image (e.g. from older DB)
        db.execute('UPDATE restaurants SET image_filename=? WHERE id=? AND (image_filename IS NULL OR image_filename="")',
                   (img, rid))

        if rid in menu_data:
            for cat_name, items in menu_data[rid]:
                db.execute("INSERT OR IGNORE INTO categories (id,restaurant_id,name) VALUES (?,?,?)", (cat_id, rid, cat_name))
                for item_name, item_desc, item_price in items:
                    db.execute("INSERT OR IGNORE INTO menu_items (id,category_id,restaurant_id,name,description,price) VALUES (?,?,?,?,?,?)",
                               (item_id, cat_id, rid, item_name, item_desc, item_price))
                    item_id += 1
                cat_id += 1

    # Migration: add rider_id to produce_orders if missing
    try:
        db.execute('ALTER TABLE produce_orders ADD COLUMN rider_id INTEGER')
    except: pass
    try:
        db.execute('ALTER TABLE produce_orders ADD COLUMN special_instructions TEXT')
    except: pass

    db.commit()
    db.close()

# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route('/api/signup',    methods=['POST'])
@app.route('/api/v1/signup', methods=['POST'])
def signup():
    data = request.json
    db = get_db()
    ph = hash_password(data['password'])          # PBKDF2-HMAC-SHA256
    try:
        cur = db.execute('INSERT INTO users (name,email,phone,password_hash,role) VALUES (?,?,?,?,?)',
                         (data['name'], data['email'], data.get('phone',''), ph, data['role']))
        user_id = cur.lastrowid
        if data['role'] == 'rider':
            db.execute('INSERT INTO riders (user_id,vehicle_type,license_plate) VALUES (?,?,?)',
                       (user_id, data.get('vehicle_type','Bike'), data.get('license_plate','')))
        db.commit()
        token = issue_jwt(user_id, data['role'])
        log_audit(user_id, 'SIGNUP', f"New {data['role']} registered: {data['email']}")
        return jsonify({'success': True, 'token': token, 'user_id': user_id, 'role': data['role'],
                        'name': data['name'], 'email': data['email'], 'phone': data.get('phone','')})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    finally:
        db.close()

@app.route('/api/login',    methods=['POST'])
@app.route('/api/v1/login', methods=['POST'])
def login():
    data = request.json
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email=?', (data['email'],)).fetchone()
    if not user or not check_password(data['password'], user['password_hash']):
        db.close()
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    token = issue_jwt(user['id'], user['role'])
    result = {
        'success': True,
        'token': token,
        'user_id': user['id'],
        'role': user['role'],
        'name': user['name'],
        'email': user['email'],
        'phone': user['phone'] or ''    # needed for JazzCash/EasyPaisa validation
    }
    if user['role'] == 'rider':
        rider = db.execute('SELECT * FROM riders WHERE user_id=?', (user['id'],)).fetchone()
        if rider:
            result['rider_status'] = rider['status']
            result['rider_id'] = rider['id']
    if user['role'] == 'manager':
        rest = db.execute('SELECT id,name,status FROM restaurants WHERE manager_id=?', (user['id'],)).fetchone()
        if rest:
            result['restaurant_id'] = rest['id']
            result['restaurant_name'] = rest['name']
            result['restaurant_status'] = rest['status']
    db.close()
    log_audit(user['id'], 'LOGIN', f"{user['role']} logged in")
    return jsonify(result)

@app.route('/api/logout',    methods=['POST'])
@app.route('/api/v1/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})

# ─── RESTAURANTS ─────────────────────────────────────────────────────────────

@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    db = get_db()
    # ?all=1 lets manager/admin see pending restaurants too
    show_all = request.args.get('all') == '1'
    manager_id = request.args.get('manager_id')

    if manager_id:
        # Manager sees their own restaurant regardless of status
        rows = db.execute(
            'SELECT * FROM restaurants WHERE manager_id=? ORDER BY created_at DESC',
            (manager_id,)
        ).fetchall()
    elif show_all:
        rows = db.execute('SELECT * FROM restaurants ORDER BY rating DESC').fetchall()
    else:
        # Customers only see approved + open
        rows = db.execute(
            "SELECT * FROM restaurants WHERE status='approved' AND is_open=1 ORDER BY rating DESC"
        ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/restaurants/<int:rid>', methods=['GET'])
def get_restaurant(rid):
    db = get_db()
    r = db.execute('SELECT * FROM restaurants WHERE id=?', (rid,)).fetchone()
    if not r:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    result = dict(r)

    # ── Fetch categorised items ──────────────────────────────────────────────
    cats = db.execute('SELECT * FROM categories WHERE restaurant_id=?', (rid,)).fetchall()
    categories = []
    categorised_ids = set()
    for cat in cats:
        items = db.execute(
            'SELECT * FROM menu_items WHERE category_id=? AND restaurant_id=? AND is_available=1',
            (cat['id'], rid)
        ).fetchall()
        item_list = [dict(i) for i in items]
        for i in item_list:
            categorised_ids.add(i['id'])
        categories.append({'id': cat['id'], 'name': cat['name'], 'items': item_list})

    # ── Fetch uncategorised items (no category_id or NULL) ───────────────────
    uncategorised = db.execute(
        'SELECT * FROM menu_items WHERE restaurant_id=? AND is_available=1 AND (category_id IS NULL OR category_id=0)',
        (rid,)
    ).fetchall()
    uncategorised = [dict(i) for i in uncategorised if i['id'] not in categorised_ids]
    if uncategorised:
        categories.append({'id': None, 'name': 'Menu', 'items': uncategorised})

    # ── If NO categories at all, try fetching ALL items for this restaurant ──
    if not categories:
        all_items = db.execute(
            'SELECT * FROM menu_items WHERE restaurant_id=? AND is_available=1',
            (rid,)
        ).fetchall()
        if all_items:
            categories.append({'id': None, 'name': 'Menu', 'items': [dict(i) for i in all_items]})

    result['categories'] = categories
    db.close()
    return jsonify(result)

@app.route('/api/manager/restaurant', methods=['POST'])
def manager_create_restaurant():
    data = request.json
    db = get_db()
    img = save_image(data.get('image'), 'rest')
    cur = db.execute('''INSERT INTO restaurants (name,cuisine,location,phone,image_filename,delivery_time,description,min_order,status,manager_id)
                        VALUES (?,?,?,?,?,?,?,?,'pending',?)''',
                     (data['name'], data.get('cuisine',''), data.get('location',''), data.get('phone',''),
                      img, data.get('delivery_time',30), data.get('description',''), data.get('min_order',0),
                      data['manager_id']))
    rid = cur.lastrowid
    db.commit()
    log_audit(data['manager_id'], 'CREATE_RESTAURANT', f"Restaurant '{data['name']}' submitted for approval")
    db.close()
    return jsonify({'success': True, 'restaurant_id': rid})

@app.route('/api/manager/restaurant/<int:rid>', methods=['PUT'])
def manager_update_restaurant(rid):
    data = request.json
    db = get_db()
    img = save_image(data.get('image'), 'rest')
    if img:
        db.execute('UPDATE restaurants SET name=?,cuisine=?,location=?,phone=?,image_filename=?,delivery_time=?,description=?,min_order=? WHERE id=? AND manager_id=?',
                   (data['name'],data.get('cuisine'),data.get('location'),data.get('phone'),img,data.get('delivery_time',30),data.get('description'),data.get('min_order',0),rid,data['manager_id']))
    else:
        db.execute('UPDATE restaurants SET name=?,cuisine=?,location=?,phone=?,delivery_time=?,description=?,min_order=? WHERE id=? AND manager_id=?',
                   (data['name'],data.get('cuisine'),data.get('location'),data.get('phone'),data.get('delivery_time',30),data.get('description'),data.get('min_order',0),rid,data['manager_id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/manager/menu-item', methods=['POST'])
def manager_add_item():
    data = request.json
    db = get_db()
    img = save_image(data.get('image'), 'item')
    cur = db.execute('INSERT INTO menu_items (category_id,restaurant_id,name,description,price,image_filename) VALUES (?,?,?,?,?,?)',
                     (data.get('category_id'), data['restaurant_id'], data['name'], data.get('description',''), data['price'], img))
    db.commit()
    item_id = cur.lastrowid
    log_audit(data.get('manager_id'), 'ADD_MENU_ITEM', f"Item '{data['name']}' added to restaurant {data['restaurant_id']}")
    db.close()
    return jsonify({'success': True, 'item_id': item_id})

@app.route('/api/manager/menu-item/<int:iid>', methods=['PUT'])
def manager_update_item(iid):
    data = request.json
    db   = get_db()

    # Toggle-only call — just flip is_available, don't touch name/price
    if data.get('_toggle'):
        db.execute('UPDATE menu_items SET is_available=? WHERE id=?',
                   (1 if data.get('is_available') else 0, iid))
        db.commit()
        db.close()
        return jsonify({'success': True})

    # Full update
    img = save_image(data.get('image'), 'item')
    name  = data.get('name','').strip()
    price = data.get('price', 0)
    desc  = data.get('description', '')
    avail = data.get('is_available', 1)

    if not name or not price:
        db.close()
        return jsonify({'success': False, 'error': 'Name and price are required'}), 400

    if img:
        db.execute('UPDATE menu_items SET name=?,description=?,price=?,image_filename=?,is_available=? WHERE id=?',
                   (name, desc, price, img, avail, iid))
    else:
        db.execute('UPDATE menu_items SET name=?,description=?,price=?,is_available=? WHERE id=?',
                   (name, desc, price, avail, iid))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/manager/menu-item/<int:iid>', methods=['DELETE'])
def manager_delete_item(iid):
    db = get_db()
    db.execute('DELETE FROM menu_items WHERE id=?', (iid,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/manager/category', methods=['POST'])
def manager_add_category():
    data = request.json
    db = get_db()
    cur = db.execute('INSERT INTO categories (restaurant_id,name) VALUES (?,?)', (data['restaurant_id'], data['name']))
    db.commit()
    cat_id = cur.lastrowid
    db.close()
    return jsonify({'success': True, 'id': cat_id, 'category_id': cat_id})

@app.route('/api/manager/restaurant/<int:rid>/menu', methods=['GET'])
def manager_get_menu(rid):
    """Manager view: ALL categories (including empty) + ALL items (including unavailable)."""
    db  = get_db()
    r   = db.execute('SELECT * FROM restaurants WHERE id=?', (rid,)).fetchone()
    if not r:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    result = dict(r)
    cats = db.execute('SELECT * FROM categories WHERE restaurant_id=? ORDER BY id', (rid,)).fetchall()
    categories = []
    categorised_ids = set()
    for cat in cats:
        items = db.execute(
            'SELECT * FROM menu_items WHERE category_id=? AND restaurant_id=? ORDER BY id',
            (cat['id'], rid)
        ).fetchall()
        item_list = [dict(i) for i in items]
        for i in item_list:
            categorised_ids.add(i['id'])
        categories.append({'id': cat['id'], 'name': cat['name'], 'items': item_list})
    # Also get uncategorised items
    uncategorised = db.execute(
        'SELECT * FROM menu_items WHERE restaurant_id=? AND (category_id IS NULL OR category_id=0) ORDER BY id',
        (rid,)
    ).fetchall()
    uncategorised = [dict(i) for i in uncategorised if i['id'] not in categorised_ids]
    if uncategorised:
        categories.append({'id': None, 'name': 'Uncategorised', 'items': uncategorised})
    result['categories'] = categories
    db.close()
    return jsonify(result)

@app.route('/api/manager/restaurant/<int:rid>/orders', methods=['GET'])
def manager_orders(rid):
    db = get_db()
    orders = db.execute('''SELECT o.*, u.name as customer_name FROM orders o JOIN users u ON o.customer_id=u.id
                           WHERE o.restaurant_id=? ORDER BY o.created_at DESC''', (rid,)).fetchall()
    result = []
    for o in orders:
        od = dict(o)
        items = db.execute('SELECT oi.*,mi.name FROM order_items oi JOIN menu_items mi ON oi.item_id=mi.id WHERE oi.order_id=?',(o['id'],)).fetchall()
        od['items'] = [dict(i) for i in items]
        result.append(od)
    db.close()
    return jsonify(result)

@app.route('/api/manager/restaurant/<int:rid>/stats', methods=['GET'])
def manager_stats(rid):
    db = get_db()
    total = db.execute('SELECT COUNT(*) as c FROM orders WHERE restaurant_id=?',(rid,)).fetchone()['c']
    revenue = db.execute("SELECT COALESCE(SUM(total_amount),0) as s FROM orders WHERE restaurant_id=? AND status='Delivered'",(rid,)).fetchone()['s']
    platform_cut = revenue * 0.05
    db.close()
    return jsonify({'total_orders':total,'revenue':revenue,'platform_fee':platform_cut,'net_revenue':revenue-platform_cut})

# ─── ORDERS ──────────────────────────────────────────────────────────────────

@app.route('/api/orders',    methods=['POST'])
@app.route('/api/v1/orders', methods=['POST'])
def place_order():
    """ATOMIC order placement — BEGIN/COMMIT/ROLLBACK transaction."""
    data = request.json
    db = get_db()
    try:
        db.execute('BEGIN')
        sub           = float(data['subtotal'])
        delivery_fee  = float(data.get('delivery_fee', 50))
        platform_fee  = round(sub * 0.05, 2)
        tip           = round(sub * 0.10, 2)
        promo_discount   = float(data.get('promo_discount', 0))
        loyalty_discount = float(data.get('loyalty_discount', 0))
        total = round(max(0, sub + delivery_fee + platform_fee - promo_discount - loyalty_discount), 2)
        cid   = data['customer_id']

        # ── Step 1: validate every menu item belongs to this restaurant & is available ──
        for item in data['items']:
            row = db.execute(
                'SELECT id,name,is_available,restaurant_id FROM menu_items WHERE id=?',
                (item['item_id'],)
            ).fetchone()
            if not row:
                raise ValueError(f"Menu item {item['item_id']} not found")
            if row['restaurant_id'] != data['restaurant_id']:
                raise ValueError(f"Menu item {row['name']} does not belong to selected restaurant")
            if not row['is_available']:
                raise ValueError(f"Menu item {row['name']} is currently unavailable")

        # ── Step 2: validate promo code if provided ──
        if data.get('promo_code'):
            promo = db.execute(
                'SELECT * FROM promo_codes WHERE code=? AND is_active=1',
                (data['promo_code'],)
            ).fetchone()
            if not promo:
                raise ValueError(f"Promo code '{data['promo_code']}' is invalid or inactive")
            if promo['used_count'] >= promo['max_uses']:
                raise ValueError(f"Promo code '{data['promo_code']}' has reached its usage limit ({promo['max_uses']}/{promo['max_uses']})")

        # ── Step 3: validate loyalty redemption ──
        if loyalty_discount > 0:
            lp = db.execute('SELECT total_points FROM loyalty_points WHERE customer_id=?', (cid,)).fetchone()
            available = lp['total_points'] if lp else 0
            if available < int(loyalty_discount):
                raise ValueError(f"Insufficient loyalty points (have {available}, need {int(loyalty_discount)})")

        # ── Step 4: insert order ──
        cur = db.execute(
            '''INSERT INTO orders (customer_id,restaurant_id,total_amount,delivery_fee,platform_fee,
               rider_tip,payment_method,delivery_address,special_instructions,estimated_time)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (cid, data['restaurant_id'], total, delivery_fee, platform_fee, tip,
             data.get('payment_method','Cash on Delivery'),
             data.get('delivery_address',''),
             data.get('special_instructions',''),
             data.get('estimated_time', 35))
        )
        order_id = cur.lastrowid

        # ── Step 5: insert order items ──
        for item in data['items']:
            db.execute(
                'INSERT INTO order_items (order_id,item_id,quantity,unit_price) VALUES (?,?,?,?)',
                (order_id, item['item_id'], item['quantity'], item['unit_price'])
            )

        # ── Step 6: award loyalty points ──
        db.execute('INSERT OR IGNORE INTO loyalty_points (customer_id,total_points,lifetime_points) VALUES (?,0,0)', (cid,))
        points_earned = int(total / 100)
        if points_earned > 0:
            db.execute('UPDATE loyalty_points SET total_points=total_points+?, lifetime_points=lifetime_points+? WHERE customer_id=?',
                       (points_earned, points_earned, cid))
            db.execute('INSERT INTO loyalty_transactions (customer_id,points,type,description,order_id) VALUES (?,?,?,?,?)',
                       (cid, points_earned, 'earn', f'Earned from order PKR {int(total)}', order_id))

        # ── Step 7: mark promo used ──
        if data.get('promo_code'):
            db.execute('UPDATE promo_codes SET used_count=used_count+1 WHERE code=?', (data['promo_code'],))

        # ── Step 8: deduct redeemed loyalty ──
        if loyalty_discount > 0:
            pts = int(loyalty_discount)
            db.execute('UPDATE loyalty_points SET total_points=MAX(0,total_points-?) WHERE customer_id=?', (pts, cid))
            db.execute('INSERT INTO loyalty_transactions (customer_id,points,type,description,order_id) VALUES (?,?,?,?,?)',
                       (cid, -pts, 'redeem', f'Redeemed for PKR {pts} discount', order_id))

        db.execute('COMMIT')
        log_audit(cid, 'PLACE_ORDER', f"Order #{order_id} PKR {total} promo={data.get('promo_code','none')} pts={points_earned}")
        db.close()
        return jsonify({'success': True, 'order_id': order_id, 'total': total, 'points_earned': points_earned})

    except ValueError as e:
        db.execute('ROLLBACK')
        log_audit(data.get('customer_id'), 'ORDER_ROLLBACK', str(e))
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.execute('ROLLBACK')
        log_audit(data.get('customer_id'), 'ORDER_ROLLBACK', f'Unexpected: {e}')
        db.close()
        return jsonify({'success': False, 'error': 'Order failed — transaction rolled back'}), 500

@app.route('/api/orders/customer/<int:cid>', methods=['GET'])
def customer_orders(cid):
    db = get_db()
    orders = db.execute('''SELECT o.*, r.name as restaurant_name FROM orders o JOIN restaurants r ON o.restaurant_id=r.id
                           WHERE o.customer_id=? ORDER BY o.created_at DESC''', (cid,)).fetchall()
    result = []
    for o in orders:
        od = dict(o)
        items = db.execute('SELECT oi.*,mi.name FROM order_items oi JOIN menu_items mi ON oi.item_id=mi.id WHERE oi.order_id=?',(o['id'],)).fetchall()
        od['items'] = [dict(i) for i in items]
        result.append(od)
    # Include produce orders
    produce = db.execute('''SELECT po.*, 'Fresh Produce Market' as restaurant_name
                              FROM produce_orders po WHERE po.customer_id=? ORDER BY po.created_at DESC''', (cid,)).fetchall()
    for p in produce:
        pd = dict(p)
        pd['order_type'] = 'produce'
        items = db.execute('''SELECT poi.*, pi.name FROM produce_order_items poi
                               JOIN produce_items pi ON poi.produce_id=pi.id WHERE poi.order_id=?''', (p['id'],)).fetchall()
        pd['items'] = [dict(i) for i in items]
        result.append(pd)
    result.sort(key=lambda x: x.get('created_at',''), reverse=True)
    db.close()
    return jsonify(result)

@app.route('/api/orders/<int:oid>', methods=['GET'])
def get_order(oid):
    db = get_db()
    o = db.execute('SELECT o.*,r.name as restaurant_name FROM orders o JOIN restaurants r ON o.restaurant_id=r.id WHERE o.id=?',(oid,)).fetchone()
    items = db.execute('SELECT oi.*,mi.name FROM order_items oi JOIN menu_items mi ON oi.item_id=mi.id WHERE oi.order_id=?',(oid,)).fetchall()
    result = dict(o)
    result['items'] = [dict(i) for i in items]
    db.close()
    return jsonify(result)

@app.route('/api/orders/<int:oid>/status', methods=['PUT'])
def update_order_status(oid):
    data = request.json
    db = get_db()
    try:
        db.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',
                   (data['status'], datetime.datetime.now().isoformat(), oid))
        db.commit()
        log_audit(data.get('user_id'), 'UPDATE_ORDER_STATUS', f"Order #{oid} -> {data['status']}")
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
    return jsonify({'success': True})

@app.route('/api/orders/available', methods=['GET'])
def available_orders():
    db = get_db()
    orders = db.execute('''SELECT o.*,r.name as restaurant_name,r.location as pickup_location,u.name as customer_name
                           FROM orders o JOIN restaurants r ON o.restaurant_id=r.id JOIN users u ON o.customer_id=u.id
                           WHERE o.status='Confirmed' AND o.rider_id IS NULL''').fetchall()
    result = [dict(o) for o in orders]
    # Include produce orders confirmed but no rider
    produce = db.execute('''SELECT po.*, 'Fresh Produce Market' as restaurant_name,
                              'Produce Warehouse, Lahore' as pickup_location, u.name as customer_name
                              FROM produce_orders po JOIN users u ON po.customer_id=u.id
                              WHERE po.status='Confirmed' AND (po.rider_id IS NULL OR po.rider_id=0)
                              ''').fetchall()
    for p in produce:
        pd = dict(p)
        pd['order_type'] = 'produce'
        result.append(pd)
    db.close()
    return jsonify(result)

@app.route('/api/orders/<int:oid>/assign', methods=['PUT'])
def assign_rider(oid):
    data = request.json
    db = get_db()
    db.execute("UPDATE orders SET rider_id=?,status='Out for Delivery',updated_at=? WHERE id=?",
               (data['rider_id'], datetime.datetime.now().isoformat(), oid))
    db.commit()
    log_audit(data.get('user_id'), 'ASSIGN_RIDER', f"Rider {data['rider_id']} accepted order #{oid}")
    db.close()
    return jsonify({'success': True})

@app.route('/api/orders/rider/<int:rid>', methods=['GET'])
def rider_orders(rid):
    db = get_db()
    orders = db.execute('''SELECT o.*,r.name as restaurant_name,r.location as pickup_location,
                           u.name as customer_name,u.phone as customer_phone,u.id as customer_user_id
                           FROM orders o JOIN restaurants r ON o.restaurant_id=r.id JOIN users u ON o.customer_id=u.id
                           WHERE o.rider_id=? ORDER BY o.created_at DESC''', (rid,)).fetchall()
    result = [dict(o) for o in orders]
    produce = db.execute('''SELECT po.*, 'Fresh Produce Market' as restaurant_name,
                              'Produce Warehouse, Lahore' as pickup_location,
                              u.name as customer_name, u.phone as customer_phone
                              FROM produce_orders po JOIN users u ON po.customer_id=u.id
                              WHERE po.rider_id=? ORDER BY po.created_at DESC''', (rid,)).fetchall()
    for p in produce:
        pd = dict(p)
        pd['order_type'] = 'produce'
        result.append(pd)
    result.sort(key=lambda x: x.get('created_at',''), reverse=True)
    db.close()
    return jsonify(result)

# ─── RIDERS ──────────────────────────────────────────────────────────────────

@app.route('/api/admin/riders', methods=['GET'])
def admin_riders():
    db = get_db()
    riders = db.execute('SELECT r.*,u.name,u.email,u.phone FROM riders r JOIN users u ON r.user_id=u.id').fetchall()
    db.close()
    return jsonify([dict(r) for r in riders])

@app.route('/api/admin/riders/<int:rid>/approve', methods=['PUT'])
def approve_rider(rid):
    data = request.json
    status = data.get('status','approved')
    db = get_db()
    db.execute('UPDATE riders SET status=? WHERE id=?', (status, rid))
    db.commit()
    log_audit(data.get('admin_id'), 'RIDER_APPROVAL', f"Rider {rid} -> {status}")
    db.close()
    return jsonify({'success': True})

@app.route('/api/rider/status/<int:uid>', methods=['GET'])
def rider_status(uid):
    db = get_db()
    r = db.execute('SELECT * FROM riders WHERE user_id=?', (uid,)).fetchone()
    db.close()
    if r: return jsonify(dict(r))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/rider/<int:rid>/earnings', methods=['POST'])
def update_earnings(rid):
    data = request.json
    db = get_db()
    db.execute('UPDATE riders SET total_earnings=total_earnings+? WHERE id=?',(data['amount'],rid))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ─── MESSAGES ─────────────────────────────────────────────────────────────────

@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO messages (sender_id,receiver_id,order_id,message) VALUES (?,?,?,?)',
               (data['sender_id'], data['receiver_id'], data.get('order_id'), data['message']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/messages/<int:uid1>/<int:uid2>', methods=['GET'])
def get_messages(uid1, uid2):
    db = get_db()
    msgs = db.execute('''SELECT m.*,u.name as sender_name FROM messages m JOIN users u ON m.sender_id=u.id
                         WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?)
                         ORDER BY m.created_at ASC''', (uid1,uid2,uid2,uid1)).fetchall()
    db.execute('UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?',(uid2,uid1))
    db.commit()
    db.close()
    return jsonify([dict(m) for m in msgs])

@app.route('/api/messages/admin/<int:uid>', methods=['GET'])
def get_admin_messages(uid):
    db = get_db()
    admin = db.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not admin: return jsonify({'messages':[],'admin_id':None})
    msgs = db.execute('''SELECT m.*,u.name as sender_name FROM messages m JOIN users u ON m.sender_id=u.id
                         WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?)
                         ORDER BY m.created_at ASC''', (uid,admin['id'],admin['id'],uid)).fetchall()
    db.close()
    return jsonify({'messages':[dict(m) for m in msgs],'admin_id':admin['id']})

# ─── REVIEWS ─────────────────────────────────────────────────────────────────

@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO reviews (customer_id,restaurant_id,order_id,rating,comment) VALUES (?,?,?,?,?)',
               (data['customer_id'],data['restaurant_id'],data.get('order_id'),data['rating'],data.get('comment','')))
    avg = db.execute('SELECT AVG(rating) as a FROM reviews WHERE restaurant_id=?',(data['restaurant_id'],)).fetchone()['a']
    db.execute('UPDATE restaurants SET rating=? WHERE id=?',(round(avg,1),data['restaurant_id']))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/reviews/restaurant/<int:rid>', methods=['GET'])
def restaurant_reviews(rid):
    db = get_db()
    revs = db.execute('SELECT rv.*,u.name as customer_name FROM reviews rv JOIN users u ON rv.customer_id=u.id WHERE rv.restaurant_id=? ORDER BY rv.created_at DESC',(rid,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in revs])

# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    db = get_db()
    total_orders = db.execute('SELECT COUNT(*) as c FROM orders').fetchone()['c']
    total_users = db.execute("SELECT COUNT(*) as c FROM users WHERE role='customer'").fetchone()['c']
    total_riders = db.execute('SELECT COUNT(*) as c FROM riders').fetchone()['c']
    pending_riders = db.execute("SELECT COUNT(*) as c FROM riders WHERE status='pending'").fetchone()['c']
    total_restaurants = db.execute("SELECT COUNT(*) as c FROM restaurants WHERE is_open=1 AND status='approved'").fetchone()['c']
    pending_restaurants = db.execute("SELECT COUNT(*) as c FROM restaurants WHERE status='pending'").fetchone()['c']
    delivered_revenue = db.execute("SELECT COALESCE(SUM(total_amount),0) as s FROM orders WHERE status='Delivered'").fetchone()['s']
    platform_revenue = db.execute("SELECT COALESCE(SUM(platform_fee),0) as s FROM orders WHERE status='Delivered'").fetchone()['s']
    total_platform_cut = db.execute("SELECT COALESCE(SUM(platform_fee),0) as s FROM orders").fetchone()['s']
    db.close()
    return jsonify({'total_orders':total_orders,'total_users':total_users,'total_riders':total_riders,
                    'pending_riders':pending_riders,'total_restaurants':total_restaurants,
                    'pending_restaurants':pending_restaurants,'revenue':delivered_revenue,
                    'platform_revenue':platform_revenue,'total_platform_cut':total_platform_cut})

@app.route('/api/admin/orders', methods=['GET'])
def admin_orders():
    db = get_db()
    orders = db.execute('''SELECT o.*,r.name as restaurant_name,u.name as customer_name
                           FROM orders o JOIN restaurants r ON o.restaurant_id=r.id JOIN users u ON o.customer_id=u.id
                           ORDER BY o.created_at DESC LIMIT 200''').fetchall()
    result = [dict(o) for o in orders]
    # Include produce orders
    produce = db.execute('''SELECT po.*, u.name as customer_name, 'Fresh Produce Market' as restaurant_name
                             FROM produce_orders po JOIN users u ON po.customer_id=u.id
                             ORDER BY po.created_at DESC LIMIT 100''').fetchall()
    for p in produce:
        pd = dict(p)
        pd['order_type'] = 'produce'
        items = db.execute('''SELECT poi.*, pi.name FROM produce_order_items poi
                               JOIN produce_items pi ON poi.produce_id=pi.id WHERE poi.order_id=?''', (p['id'],)).fetchall()
        pd['items'] = [dict(i) for i in items]
        result.append(pd)
    result.sort(key=lambda x: x.get('created_at',''), reverse=True)
    db.close()
    return jsonify(result)

@app.route('/api/admin/restaurants', methods=['GET'])
def admin_restaurants():
    db = get_db()
    rows = db.execute('SELECT r.*,u.name as manager_name FROM restaurants r LEFT JOIN users u ON r.manager_id=u.id ORDER BY r.created_at DESC').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/restaurants', methods=['POST'])
def admin_add_restaurant():
    data = request.json
    db = get_db()
    cur = db.execute("INSERT INTO restaurants (name,cuisine,location,phone,rating,delivery_time,status,is_open,added_by) VALUES (?,?,?,?,?,?,'approved',1,?)",
                     (data['name'],data.get('cuisine',''),data.get('location',''),data.get('phone',''),
                      data.get('rating',4.0),data.get('delivery_time',30),data.get('admin_id')))
    db.commit()
    log_audit(data.get('admin_id'), 'ADD_RESTAURANT', f"Restaurant '{data['name']}' added by admin")
    db.close()
    return jsonify({'success': True, 'id': cur.lastrowid})

@app.route('/api/admin/restaurants/<int:rid>/approve', methods=['PUT'])
def admin_approve_restaurant(rid):
    data   = request.json
    status = data.get('status','approved')
    db     = get_db()
    if status == 'approved':
        # Also set is_open=1 so customers can see it immediately
        db.execute('UPDATE restaurants SET status=?, is_open=1 WHERE id=?', (status, rid))
    else:
        db.execute('UPDATE restaurants SET status=? WHERE id=?', (status, rid))
    db.commit()
    log_audit(data.get('admin_id'), 'RESTAURANT_APPROVAL', f"Restaurant {rid} -> {status}")
    db.close()
    return jsonify({'success': True})

@app.route('/api/admin/restaurants/<int:rid>', methods=['DELETE'])
def admin_delete_restaurant(rid):
    db = get_db()
    db.execute('DELETE FROM restaurants WHERE id=?',(rid,))
    db.commit()
    log_audit(request.json.get('admin_id') if request.json else None, 'REMOVE_RESTAURANT', f"Restaurant {rid} removed")
    db.close()
    return jsonify({'success': True})

@app.route('/api/admin/restaurants/<int:rid>', methods=['PUT'])
def admin_update_restaurant(rid):
    data = request.json
    db = get_db()
    db.execute('UPDATE restaurants SET name=?,cuisine=?,location=?,phone=?,delivery_time=? WHERE id=?',
               (data['name'],data['cuisine'],data['location'],data['phone'],data['delivery_time'],rid))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    db = get_db()
    users = db.execute('SELECT id,name,email,phone,role,created_at FROM users ORDER BY created_at DESC').fetchall()
    db.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/admin/audit', methods=['GET'])
def admin_audit():
    db = get_db()
    logs = db.execute('SELECT al.*,u.name as user_name FROM audit_log al LEFT JOIN users u ON al.user_id=u.id ORDER BY al.timestamp DESC LIMIT 100').fetchall()
    db.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/admin/conversations', methods=['GET'])
def admin_conversations():
    db = get_db()
    admin = db.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not admin: return jsonify([])
    aid = admin['id']
    convs = db.execute(f'''
        SELECT DISTINCT u.id, u.name, u.role,
        (SELECT message FROM messages WHERE (sender_id=u.id AND receiver_id={aid}) OR (sender_id={aid} AND receiver_id=u.id) ORDER BY created_at DESC LIMIT 1) as last_message,
        (SELECT COUNT(*) FROM messages WHERE sender_id=u.id AND receiver_id={aid} AND is_read=0) as unread
        FROM users u
        WHERE u.id IN (
            SELECT sender_id FROM messages WHERE receiver_id={aid}
            UNION SELECT receiver_id FROM messages WHERE sender_id={aid}
        ) AND u.role != 'admin'
    ''').fetchall()
    db.close()
    return jsonify([dict(c) for c in convs])


@app.route('/api/orders/detail/<int:oid>', methods=['GET'])
def get_order_detail(oid):
    db = get_db()
    o = db.execute('''
        SELECT o.*, r.name as restaurant_name, r.location as restaurant_location,
               u.name as rider_name, ri.vehicle_type as rider_vehicle
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.id
        LEFT JOIN riders ri ON o.rider_id = ri.id
        LEFT JOIN users u ON ri.user_id = u.id
        WHERE o.id = ?
    ''', (oid,)).fetchone()
    if not o:
        db.close()
        return jsonify({'error': 'Order not found'}), 404
    result = dict(o)
    items = db.execute('''SELECT oi.*, mi.name as item_name FROM order_items oi
                         JOIN menu_items mi ON oi.item_id = mi.id WHERE oi.order_id = ?''', (oid,)).fetchall()
    result['items'] = [dict(i) for i in items]
    db.close()
    return jsonify(result)

# ─── PRODUCE (Fruits & Vegetables) ───────────────────────────────────────────

@app.route('/api/produce',    methods=['GET'])
@app.route('/api/v1/produce', methods=['GET'])
def get_produce():
    """Returns ALL produce for customers — including stock_kg so UI can show levels."""
    category = request.args.get('category')
    db = get_db()
    if category:
        rows = db.execute(
            'SELECT * FROM produce_items WHERE category=? ORDER BY is_available DESC, name',
            (category,)
        ).fetchall()
    else:
        rows = db.execute(
            'SELECT * FROM produce_items ORDER BY is_available DESC, category, name'
        ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/produce/order',    methods=['POST'])
@app.route('/api/v1/produce/order', methods=['POST'])
def place_produce_order():
    """ATOMIC produce order placement — BEGIN/COMMIT/ROLLBACK transaction."""
    data = request.json
    db   = get_db()
    try:
        db.execute('BEGIN')
        subtotal         = float(data['total_amount'])
        delivery_fee     = float(data.get('delivery_fee', 50))
        promo_discount   = float(data.get('promo_discount', 0))
        loyalty_discount = float(data.get('loyalty_discount', 0))
        total = round(max(0, subtotal + delivery_fee - promo_discount - loyalty_discount), 2)
        cid   = data['customer_id']

        # ── Step 1: validate each produce item is available and has enough stock ──
        for item in data['items']:
            row = db.execute('SELECT id,name,is_available,stock_kg FROM produce_items WHERE id=?', (item['produce_id'],)).fetchone()
            if not row:
                raise ValueError(f"Produce item {item['produce_id']} not found")
            if not row['is_available'] or row['stock_kg'] <= 0:
                raise ValueError(f"Produce item '{row['name']}' is currently out of stock")
            qty_requested = float(item['quantity_kg'])
            if qty_requested > row['stock_kg']:
                raise ValueError(f"Not enough stock for '{row['name']}' — requested {qty_requested}kg, only {row['stock_kg']}kg available")

        # ── Step 2: validate promo code ──
        if data.get('promo_code'):
            promo = db.execute('SELECT * FROM promo_codes WHERE code=? AND is_active=1', (data['promo_code'],)).fetchone()
            if not promo:
                raise ValueError(f"Promo code '{data['promo_code']}' is invalid or inactive")
            if promo['used_count'] >= promo['max_uses']:
                raise ValueError(f"Promo code '{data['promo_code']}' has reached its usage limit ({promo['max_uses']}/{promo['max_uses']})")

        # ── Step 3: validate loyalty points ──
        if loyalty_discount > 0:
            lp = db.execute('SELECT total_points FROM loyalty_points WHERE customer_id=?', (cid,)).fetchone()
            available = lp['total_points'] if lp else 0
            if available < int(loyalty_discount):
                raise ValueError(f"Insufficient loyalty points (have {available}, need {int(loyalty_discount)})")

        # ── Step 4: insert produce order ──
        cur = db.execute(
            'INSERT INTO produce_orders (customer_id,total_amount,delivery_fee,payment_method,delivery_address,special_instructions) VALUES (?,?,?,?,?,?)',
            (cid, total, delivery_fee, data.get('payment_method','Cash on Delivery'),
             data.get('delivery_address',''), data.get('special_instructions',''))
        )
        order_id = cur.lastrowid

        # ── Step 5: insert line items ──
        for item in data['items']:
            db.execute('INSERT INTO produce_order_items (order_id,produce_id,quantity_kg,unit_price) VALUES (?,?,?,?)',
                       (order_id, item['produce_id'], item['quantity_kg'], item['unit_price']))

        # ── Step 5b: deduct stock_kg for each purchased item ──
        for item in data['items']:
            qty_kg = float(item['quantity_kg'])
            db.execute(
                '''UPDATE produce_items
                   SET stock_kg = MAX(0, stock_kg - ?),
                       is_available = CASE WHEN MAX(0, stock_kg - ?) <= 0 THEN 0 ELSE is_available END
                   WHERE id = ?''',
                (qty_kg, qty_kg, item['produce_id'])
            )

        # ── Step 6: award loyalty points ──
        db.execute('INSERT OR IGNORE INTO loyalty_points (customer_id,total_points,lifetime_points) VALUES (?,0,0)', (cid,))
        points_earned = int(total / 100)
        if points_earned > 0:
            db.execute('UPDATE loyalty_points SET total_points=total_points+?, lifetime_points=lifetime_points+? WHERE customer_id=?',
                       (points_earned, points_earned, cid))
            db.execute('INSERT INTO loyalty_transactions (customer_id,points,type,description,order_id) VALUES (?,?,?,?,?)',
                       (cid, points_earned, 'earn', f'Earned from produce order PKR {int(total)}', order_id))

        # ── Step 7: mark promo used ──
        if data.get('promo_code'):
            db.execute('UPDATE promo_codes SET used_count=used_count+1 WHERE code=?', (data['promo_code'],))

        # ── Step 8: deduct loyalty redemption ──
        if loyalty_discount > 0:
            pts = int(loyalty_discount)
            db.execute('UPDATE loyalty_points SET total_points=MAX(0,total_points-?) WHERE customer_id=?', (pts, cid))
            db.execute('INSERT INTO loyalty_transactions (customer_id,points,type,description,order_id) VALUES (?,?,?,?,?)',
                       (cid, -pts, 'redeem', f'Redeemed PKR {pts} on produce order', order_id))

        db.execute('COMMIT')
        log_audit(cid, 'PRODUCE_ORDER', f"Produce order #{order_id} PKR {total} pts={points_earned}")
        db.close()
        return jsonify({'success': True, 'order_id': order_id, 'total': total, 'points_earned': points_earned})

    except ValueError as e:
        db.execute('ROLLBACK')
        log_audit(data.get('customer_id'), 'PRODUCE_ORDER_ROLLBACK', str(e))
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.execute('ROLLBACK')
        log_audit(data.get('customer_id'), 'PRODUCE_ORDER_ROLLBACK', f'Unexpected: {e}')
        db.close()
        return jsonify({'success': False, 'error': 'Order failed — transaction rolled back'}), 500

@app.route('/api/produce/orders/<int:cid>', methods=['GET'])
def customer_produce_orders(cid):
    db = get_db()
    orders = db.execute('SELECT * FROM produce_orders WHERE customer_id=? ORDER BY created_at DESC', (cid,)).fetchall()
    result = []
    for o in orders:
        od = dict(o)
        items = db.execute('SELECT poi.*, pi.name, pi.image_filename, pi.category FROM produce_order_items poi JOIN produce_items pi ON poi.produce_id=pi.id WHERE poi.order_id=?', (o['id'],)).fetchall()
        od['items'] = [dict(i) for i in items]
        result.append(od)
    db.close()
    return jsonify(result)

@app.route('/api/produce/order/<int:oid>/status', methods=['PUT'])
def update_produce_order_status(oid):
    data = request.json
    # Map restaurant-style statuses to valid produce order statuses
    status_map = {'Preparing': 'Confirmed'}
    raw_status = data.get('status', '')
    status = status_map.get(raw_status, raw_status)
    # Validate against allowed values
    allowed = ('Pending', 'Confirmed', 'Out for Delivery', 'Delivered', 'Cancelled')
    if status not in allowed:
        return jsonify({'error': f'Invalid status: {raw_status}'}), 400
    db = get_db()
    try:
        update_fields = 'status=?,updated_at=?'
        params = [status, datetime.datetime.now().isoformat()]
        if 'rider_id' in data and data['rider_id']:
            update_fields = 'status=?,rider_id=?,updated_at=?'
            params = [status, data['rider_id'], datetime.datetime.now().isoformat()]
        params.append(oid)
        db.execute(f'UPDATE produce_orders SET {update_fields} WHERE id=?', params)
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
    return jsonify({'success': True})



@app.route('/api/produce/order/<int:oid>', methods=['GET'])
def get_produce_order_detail(oid):
    db = get_db()
    o = db.execute('''SELECT po.*, u.name as customer_name,
                      ru.name as rider_name, r.vehicle_type as rider_vehicle
                      FROM produce_orders po
                      JOIN users u ON po.customer_id=u.id
                      LEFT JOIN riders r ON po.rider_id=r.id
                      LEFT JOIN users ru ON r.user_id=ru.id
                      WHERE po.id=?''', (oid,)).fetchone()
    if not o:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    result = dict(o)
    items = db.execute('''SELECT poi.*, pi.name, pi.image_filename
                          FROM produce_order_items poi
                          JOIN produce_items pi ON poi.produce_id=pi.id
                          WHERE poi.order_id=?''', (oid,)).fetchall()
    result['items'] = [dict(i) for i in items]
    result['restaurant_name'] = 'Fresh Produce Market'
    result['order_type'] = 'produce'
    db.close()
    return jsonify(result)


@app.route('/api/produce/order/<int:oid>/assign', methods=['PUT'])
def assign_produce_rider(oid):
    data = request.json
    db = get_db()
    db.execute("UPDATE produce_orders SET rider_id=?,status='Out for Delivery',updated_at=? WHERE id=?",
               (data['rider_id'], datetime.datetime.now().isoformat(), oid))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ─── PROMO CODES ─────────────────────────────────────────────────────────────


# ─── ADMIN PRODUCE MANAGEMENT ─────────────────────────────────────────────────

@app.route('/api/admin/produce', methods=['GET'])
def admin_get_all_produce():
    """Get ALL produce items (including out-of-stock) for admin management."""
    db = get_db()
    rows = db.execute(
        'SELECT * FROM produce_items ORDER BY category, name'
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/produce/<int:pid>/restock', methods=['PUT'])
def restock_produce(pid):
    """Admin restocks a produce item — set stock_kg and mark available."""
    data = request.json
    db   = get_db()
    stock_kg = float(data.get('stock_kg', 50))
    db.execute(
        'UPDATE produce_items SET stock_kg=?, is_available=1 WHERE id=?',
        (stock_kg, pid)
    )
    db.commit()
    item = db.execute('SELECT name FROM produce_items WHERE id=?', (pid,)).fetchone()
    db.close()
    log_audit(None, 'PRODUCE_RESTOCK', f"Item #{pid} ({item['name'] if item else ''}) restocked to {stock_kg}kg")
    return jsonify({'success': True, 'stock_kg': stock_kg})

@app.route('/api/admin/produce/<int:pid>/toggle', methods=['PUT'])
def toggle_produce_availability(pid):
    """Admin marks a produce item as available or unavailable."""
    data = request.json
    db   = get_db()
    is_available = int(data.get('is_available', 1))
    db.execute('UPDATE produce_items SET is_available=? WHERE id=?', (is_available, pid))
    db.commit()
    item = db.execute('SELECT name FROM produce_items WHERE id=?', (pid,)).fetchone()
    db.close()
    status = 'available' if is_available else 'unavailable'
    log_audit(None, 'PRODUCE_TOGGLE', f"Item #{pid} ({item['name'] if item else ''}) marked {status}")
    return jsonify({'success': True})

@app.route('/api/admin/produce/<int:pid>/price', methods=['PUT'])
def update_produce_price(pid):
    """Admin updates a produce item's price per kg."""
    data = request.json
    db   = get_db()
    price = float(data.get('price_per_kg', 0))
    if price <= 0:
        db.close()
        return jsonify({'success': False, 'error': 'Price must be greater than 0'}), 400
    db.execute('UPDATE produce_items SET price_per_kg=? WHERE id=?', (price, pid))
    db.commit()
    db.close()
    return jsonify({'success': True, 'price_per_kg': price})


@app.route('/api/promo/validate', methods=['POST'])
def validate_promo():
    # NOTE: Always return HTTP 200 even for errors - browsers block reading 4xx CORS response bodies
    try:
        data = request.json or {}
        code = data.get('code', '').upper().strip()
        if not code:
            return jsonify({'valid': False, 'error': 'Please enter a promo code'})
        db = get_db()
        promo = db.execute("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code,)).fetchone()
        if not promo:
            db.close()
            return jsonify({'valid': False, 'error': f'"{code}" is not a valid promo code'})
        if promo['used_count'] >= promo['max_uses']:
            db.close()
            return jsonify({'valid': False, 'error': 'This promo code has reached its usage limit'})
        order_total = float(data.get('order_total', 0))
        if order_total < float(promo['min_order']):
            db.close()
            return jsonify({'valid': False, 'error': f'Minimum order of PKR {int(promo["min_order"])} required'})
        if promo['discount_type'] == 'percent':
            discount = round(order_total * promo['discount_value'] / 100, 2)
        else:
            discount = float(promo['discount_value'])
        discount = min(discount, order_total)
        discount = round(discount, 0)
        label = '{}% off'.format(int(promo['discount_value'])) if promo['discount_type'] == 'percent' else 'PKR {} off'.format(int(promo['discount_value']))
        db.close()
        return jsonify({'valid': True, 'code': code, 'discount_type': promo['discount_type'],
                        'discount_value': float(promo['discount_value']), 'discount_amount': float(discount),
                        'message': f'🎉 {label} applied! You save PKR {int(discount)}'})
    except Exception as e:
        print(f'[validate_promo error] {e}')
        return jsonify({'valid': False, 'error': 'Server error. Please try again.'})

@app.route('/api/promo/use', methods=['POST'])
def use_promo():
    data = request.json
    db = get_db()
    db.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (data['code'],))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/admin/promos', methods=['GET'])
def admin_promos():
    db = get_db()
    rows = db.execute('SELECT * FROM promo_codes ORDER BY created_at DESC').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/promos', methods=['POST'])
def admin_create_promo():
    data = request.json
    db = get_db()
    try:
        db.execute('INSERT INTO promo_codes (code,discount_type,discount_value,min_order,max_uses) VALUES (?,?,?,?,?)',
                   (data['code'].upper(), data.get('discount_type','percent'), data['discount_value'],
                    data.get('min_order',0), data.get('max_uses',100)))
        db.commit()
        log_audit(data.get('admin_id'), 'CREATE_PROMO', f"Promo code {data['code']} created")
        db.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({'success': False, 'error': 'Code already exists'}), 400

@app.route('/api/admin/promos/<int:pid>', methods=['PUT'])
def admin_toggle_promo(pid):
    data = request.json
    db = get_db()
    db.execute('UPDATE promo_codes SET is_active=? WHERE id=?', (data['is_active'], pid))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/admin/promos/<int:pid>', methods=['DELETE'])
def admin_delete_promo(pid):
    db = get_db()
    db.execute('DELETE FROM promo_codes WHERE id=?', (pid,))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ─── LOYALTY POINTS ───────────────────────────────────────────────────────────

@app.route('/api/loyalty/<int:cid>', methods=['GET'])
def get_loyalty(cid):
    db = get_db()
    row = db.execute('SELECT * FROM loyalty_points WHERE customer_id=?', (cid,)).fetchone()
    if not row:
        db.execute('INSERT OR IGNORE INTO loyalty_points (customer_id,total_points,lifetime_points) VALUES (?,0,0)', (cid,))
        db.commit()
        row = db.execute('SELECT * FROM loyalty_points WHERE customer_id=?', (cid,)).fetchone()
    txns = db.execute('SELECT * FROM loyalty_transactions WHERE customer_id=? ORDER BY created_at DESC LIMIT 20', (cid,)).fetchall()
    result = dict(row)
    result['transactions'] = [dict(t) for t in txns]
    db.close()
    return jsonify(result)

@app.route('/api/loyalty/earn', methods=['POST'])
def earn_points():
    data = request.json
    cid = data['customer_id']
    amount = data['order_amount']
    points = int(amount / 100)  # 1 point per PKR 100
    db = get_db()
    db.execute('INSERT OR IGNORE INTO loyalty_points (customer_id,total_points,lifetime_points) VALUES (?,0,0)', (cid,))
    db.execute('UPDATE loyalty_points SET total_points=total_points+?, lifetime_points=lifetime_points+? WHERE customer_id=?', (points, points, cid))
    db.execute('INSERT INTO loyalty_transactions (customer_id,points,type,description,order_id) VALUES (?,?,?,?,?)',
               (cid, points, 'earn', f'Earned from order PKR {int(amount)}', data.get('order_id')))
    db.commit()
    db.close()
    return jsonify({'success': True, 'points_earned': points})

@app.route('/api/loyalty/redeem', methods=['POST'])
def redeem_points():
    data = request.json
    cid = data['customer_id']
    points = data['points']
    discount = points  # 1 point = PKR 1
    db = get_db()
    row = db.execute('SELECT total_points FROM loyalty_points WHERE customer_id=?', (cid,)).fetchone()
    if not row or row['total_points'] < points:
        db.close()
        return jsonify({'success': False, 'error': 'Insufficient points'}), 400
    db.execute('UPDATE loyalty_points SET total_points=total_points-? WHERE customer_id=?', (points, cid))
    db.execute('INSERT INTO loyalty_transactions (customer_id,points,type,description,order_id) VALUES (?,?,?,?,?)',
               (cid, -points, 'redeem', f'Redeemed for PKR {discount} discount', data.get('order_id')))
    db.commit()
    db.close()
    return jsonify({'success': True, 'discount': discount})

# ─── RIDER LOCATION (Simulated) ───────────────────────────────────────────────

@app.route('/api/rider/location/<int:order_id>', methods=['GET'])
def get_rider_location(order_id):
    import math, time
    db = get_db()
    order = db.execute('SELECT o.*, r.location as pickup_location FROM orders o JOIN restaurants r ON o.restaurant_id=r.id WHERE o.id=?', (order_id,)).fetchone()
    db.close()
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    # Simulate rider movement based on time elapsed
    t = (time.time() % 120) / 120  # 0 to 1 over 2 minutes cycle
    # Lahore coordinates base
    base_lat, base_lng = 31.5204, 74.3587
    # Simulate path from restaurant to customer
    rider_lat = base_lat + (math.sin(t * math.pi) * 0.015)
    rider_lng = base_lng + (t * 0.02)
    progress = min(int(t * 100), 99) if order['status'] == 'Out for Delivery' else (100 if order['status'] == 'Delivered' else 0)
    return jsonify({
        'order_id': order_id,
        'status': order['status'],
        'rider_lat': rider_lat,
        'rider_lng': rider_lng,
        'restaurant_lat': base_lat - 0.01,
        'restaurant_lng': base_lng - 0.01,
        'customer_lat': base_lat + 0.01,
        'customer_lng': base_lng + 0.02,
        'progress': progress,
        'eta_minutes': max(1, int((1 - t) * 20))
    })



def run_migrations():
    """Safely add columns that may be missing in older databases."""
    db = get_db()
    migrations = [
        "ALTER TABLE produce_items ADD COLUMN stock_kg REAL DEFAULT 50.0",
        "ALTER TABLE produce_items ADD COLUMN description TEXT DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN updated_at TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE produce_orders ADD COLUMN updated_at TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE restaurants ADD COLUMN delivery_time INTEGER DEFAULT 35",
        "ALTER TABLE restaurants ADD COLUMN address TEXT DEFAULT ''",
        "ALTER TABLE restaurants ADD COLUMN phone TEXT DEFAULT ''",
        "ALTER TABLE menu_items ADD COLUMN image_filename TEXT DEFAULT ''",
        "ALTER TABLE menu_items ADD COLUMN description TEXT DEFAULT ''",
    ]
    for sql in migrations:
        try:
            db.execute(sql)
            db.commit()
        except Exception:
            pass  # column already exists — safe to ignore

    # Ensure all produce items have stock set
    db.execute("UPDATE produce_items SET stock_kg = 50.0 WHERE stock_kg IS NULL OR stock_kg = 0")
    db.execute("UPDATE produce_items SET is_available = 1 WHERE is_available IS NULL")
    db.commit()
    db.close()

if __name__ == '__main__':
    init_db()
    run_migrations()
    app.run(debug=True, port=5000)
