import sqlite3
import random
import datetime
import time
import os
import sys

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# CONFIGURATION
# ==========================================

# This simulator represents a CHAIN of shops across Tamil Nadu, so it writes
# straight into the HQ rollup database (which has a store_id on every table)
# instead of the single-till pos_system.db used by the real POS app.
CENTRAL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "HQ_Retail_OS", "central_hq.db")

# Historical generation
GENERATE_HISTORICAL = True
HISTORICAL_DAYS = 45  # 45 days of past sales, per store

HISTORICAL_SALES_PER_STORE_PER_DAY_MIN = 15
HISTORICAL_SALES_PER_STORE_PER_DAY_MAX = 35

# Live simulation
LIVE_SLEEP_INTERVAL = 3   # Seconds between batches
LIVE_BATCH_SIZE = 5       # Number of sales per batch (across all stores combined)
LIVE_ITEMS_PER_SALE_MIN = 1
LIVE_ITEMS_PER_SALE_MAX = 7
LIVE_QTY_PER_ITEM_MIN = 1
LIVE_QTY_PER_ITEM_MAX = 3

# ==========================================
# STORE NETWORK (Tamil Nadu)
# ==========================================
#
# category_weights key = the 4th digit of the barcode (see PRODUCTS below),
# which is what identifies a product's category:
#   1 = Staples & Grains, 2 = Vegetables & Fruits, 3 = Dairy & Beverages,
#   4 = Masalas & Spices, 5 = Snacks & Packaged Foods, 6 = Household & Personal Care
# Weights bias which categories sell more in that city, so each location's
# insights genuinely differ instead of being identically-shaped noise.

STORES = [
    {
        "store_id": "DINDIGUL_001", "city": "Dindigul", "price_multiplier": 1.00,
        "category_weights": {"1": 1.3, "2": 1.2, "3": 1.0, "4": 1.1, "5": 0.8, "6": 0.9},
    },
    {
        "store_id": "MADURAI_001", "city": "Madurai", "price_multiplier": 1.05,
        "category_weights": {"1": 1.0, "2": 1.0, "3": 1.1, "4": 1.3, "5": 1.0, "6": 0.9},
    },
    {
        "store_id": "COIMBATORE_001", "city": "Coimbatore", "price_multiplier": 1.15,
        "category_weights": {"1": 0.9, "2": 0.9, "3": 1.2, "4": 0.9, "5": 1.3, "6": 1.2},
    },
    {
        "store_id": "TRICHY_001", "city": "Tiruchirappalli", "price_multiplier": 1.02,
        "category_weights": {"1": 1.1, "2": 1.1, "3": 1.0, "4": 1.2, "5": 0.9, "6": 1.0},
    },
    {
        "store_id": "CHENNAI_001", "city": "Chennai", "price_multiplier": 1.25,
        "category_weights": {"1": 0.8, "2": 0.9, "3": 1.1, "4": 0.9, "5": 1.4, "6": 1.3},
    },
]

# ==========================================
# PRODUCT CATALOG (50+ South Indian Grocery Items)
# ==========================================
# Barcode shape: 89 0 <category digit> <item number>. The category digit
# (index 3) is what tn_categories.py in the AROS backend uses to bucket
# these products - keep new items within this numbering scheme.

PRODUCTS = [
    # Staples (Rice, Dhal, Oil) - category digit 1
    {"barcode": "8901001", "name": "Ponni Rice (1kg)", "price": 55.0},
    {"barcode": "8901002", "name": "Basmati Rice (1kg)", "price": 120.0},
    {"barcode": "8901003", "name": "Idly Rice (1kg)", "price": 48.0},
    {"barcode": "8901004", "name": "Toor Dhal (1kg)", "price": 180.0},
    {"barcode": "8901005", "name": "Moong Dhal (1kg)", "price": 150.0},
    {"barcode": "8901006", "name": "Urad Dhal (1kg)", "price": 160.0},
    {"barcode": "8901007", "name": "Sunflower Oil (1L)", "price": 200.0},
    {"barcode": "8901008", "name": "Coconut Oil (1L)", "price": 350.0},
    {"barcode": "8901009", "name": "Gingelly Oil (1L)", "price": 280.0},
    {"barcode": "8901010", "name": "Sugar (1kg)", "price": 42.0},
    {"barcode": "8901011", "name": "Salt (1kg)", "price": 20.0},
    {"barcode": "8901012", "name": "Wheat Flour (1kg)", "price": 35.0},
    {"barcode": "8901013", "name": "Rava (Sooji) (500g)", "price": 30.0},

    # Vegetables & Fruits (Per kg unless specified) - category digit 2
    {"barcode": "8902001", "name": "Onion (1kg)", "price": 30.0},
    {"barcode": "8902002", "name": "Tomato (1kg)", "price": 40.0},
    {"barcode": "8902003", "name": "Potato (1kg)", "price": 50.0},
    {"barcode": "8902004", "name": "Brinjal (1kg)", "price": 45.0},
    {"barcode": "8902005", "name": "Drumstick (250g)", "price": 25.0},
    {"barcode": "8902006", "name": "Banana (dozen)", "price": 40.0},
    {"barcode": "8902007", "name": "Apple (1kg)", "price": 180.0},
    {"barcode": "8902008", "name": "Orange (1kg)", "price": 120.0},
    {"barcode": "8902009", "name": "Mango (1kg)", "price": 80.0},
    {"barcode": "8902010", "name": "Coconut (each)", "price": 45.0},
    {"barcode": "8902011", "name": "Grapes (500g)", "price": 60.0},
    {"barcode": "8902012", "name": "Pomegranate (each)", "price": 70.0},

    # Dairy & Beverages - category digit 3
    {"barcode": "8903001", "name": "Milk (1L)", "price": 56.0},
    {"barcode": "8903002", "name": "Curd (500ml)", "price": 40.0},
    {"barcode": "8903003", "name": "Buttermilk (500ml)", "price": 25.0},
    {"barcode": "8903004", "name": "Tea Powder (1kg)", "price": 250.0},
    {"barcode": "8903005", "name": "Coffee Powder (500g)", "price": 150.0},
    {"barcode": "8903006", "name": "Horlicks (500g)", "price": 180.0},
    {"barcode": "8903007", "name": "Boost (500g)", "price": 190.0},

    # Masalas & Spices - category digit 4
    {"barcode": "8904001", "name": "Sambar Powder (200g)", "price": 45.0},
    {"barcode": "8904002", "name": "Rasam Powder (200g)", "price": 40.0},
    {"barcode": "8904003", "name": "Chilli Powder (200g)", "price": 60.0},
    {"barcode": "8904004", "name": "Turmeric Powder (100g)", "price": 30.0},
    {"barcode": "8904005", "name": "Coriander Powder (200g)", "price": 35.0},
    {"barcode": "8904006", "name": "Garam Masala (100g)", "price": 50.0},

    # Snacks & Packaged Foods - category digit 5
    {"barcode": "8905001", "name": "Parle Biscuits (pack)", "price": 10.0},
    {"barcode": "8905002", "name": "Britannia Biscuits (pack)", "price": 20.0},
    {"barcode": "8905003", "name": "Murukku (200g)", "price": 30.0},
    {"barcode": "8905004", "name": "Banana Chips (200g)", "price": 45.0},
    {"barcode": "8905005", "name": "Mixture (200g)", "price": 35.0},
    {"barcode": "8905006", "name": "Pasta (500g)", "price": 55.0},
    {"barcode": "8905007", "name": "Noodles (pack)", "price": 25.0},
    {"barcode": "8905008", "name": "Cooking Soda (pack)", "price": 15.0},

    # Household & Personal Care - category digit 6
    {"barcode": "8906001", "name": "Bathing Soap (each)", "price": 45.0},
    {"barcode": "8906002", "name": "Shampoo (200ml)", "price": 150.0},
    {"barcode": "8906003", "name": "Detergent Powder (1kg)", "price": 80.0},
    {"barcode": "8906004", "name": "Dish Wash (500ml)", "price": 60.0},
    {"barcode": "8906005", "name": "Toothpaste (100g)", "price": 85.0},
    {"barcode": "8906006", "name": "Toilet Paper (4 rolls)", "price": 120.0},
]

# ==========================================
# DATABASE HELPERS
# ==========================================

def connect():
    return sqlite3.connect(CENTRAL_DB_PATH)


def init_central_tables(conn):
    """Same schema HQ_Retail_OS/hq_receiver.py creates - safe to call even
    if hq_receiver.py already initialized this file."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS central_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            sale_id INTEGER,
            timestamp TEXT,
            total_amount REAL,
            received_at TEXT,
            UNIQUE(store_id, sale_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS central_sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            sale_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            subtotal REAL,
            received_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS central_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            product_id INTEGER,
            barcode TEXT,
            name TEXT,
            price REAL,
            stock INTEGER,
            updated_at TEXT,
            UNIQUE(store_id, product_id)
        )
    """)
    conn.commit()


def ensure_products_exist(conn, store):
    """Injects this store's catalog (with its own price multiplier) if missing."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM central_products WHERE store_id = ?", (store["store_id"],))
    count = cursor.fetchone()[0]

    if count == 0:
        now = datetime.datetime.now().isoformat()
        for product_id, p in enumerate(PRODUCTS, start=1):
            price = round(p["price"] * store["price_multiplier"], 2)
            cursor.execute("""
                INSERT INTO central_products (store_id, product_id, barcode, name, price, stock, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (store["store_id"], product_id, p["barcode"], p["name"], price, 99999, now))
        conn.commit()
        print(f"   📦 Injected {len(PRODUCTS)} products for {store['city']} ({store['store_id']})")
    else:
        print(f"   ✅ {store['city']} ({store['store_id']}) already has {count} products")


def next_sale_id(conn, store_id):
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(sale_id), 0) FROM central_sales WHERE store_id = ?", (store_id,))
    return cursor.fetchone()[0] + 1


# ==========================================
# WEIGHTED PRODUCT SELECTION (per-city category bias)
# ==========================================

def pick_weighted_products(products, category_weights, num_items):
    """products: list of (product_id, barcode, price, stock).
    Weighted sample without replacement, biased by each city's category_weights."""
    pool = list(products)
    weights = [category_weights.get(p[1][3], 1.0) if len(p[1]) > 3 else 1.0 for p in pool]
    chosen = []
    for _ in range(min(num_items, len(pool))):
        total = sum(weights)
        if total <= 0:
            break
        r = random.uniform(0, total)
        upto = 0.0
        for i, w in enumerate(weights):
            upto += w
            if upto >= r:
                chosen.append(pool.pop(i))
                weights.pop(i)
                break
    return chosen


# ==========================================
# GENERATE A SINGLE SALE FOR ONE STORE
# ==========================================

def generate_sale(conn, store, sale_id, timestamp=None):
    """Generates a single sale transaction for one store. Reuses the given
    connection/sale_id rather than reconnecting per sale (this runs across
    thousands of historical rows)."""
    if timestamp is None:
        timestamp = datetime.datetime.now()

    cursor = conn.cursor()
    cursor.execute(
        "SELECT product_id, barcode, price, stock FROM central_products WHERE store_id = ?",
        (store["store_id"],),
    )
    all_products = cursor.fetchall()
    if not all_products:
        return None

    num_items = random.randint(LIVE_ITEMS_PER_SALE_MIN, LIVE_ITEMS_PER_SALE_MAX)
    selected = pick_weighted_products(all_products, store["category_weights"], num_items)

    total_amount = 0.0
    items_data = []
    for product_id, barcode, price, stock in selected:
        qty = random.randint(LIVE_QTY_PER_ITEM_MIN, LIVE_QTY_PER_ITEM_MAX)
        if stock < qty:
            qty = stock
            if qty == 0:
                continue
        subtotal = round(price * qty, 2)
        total_amount += subtotal
        items_data.append((product_id, qty, subtotal))

    if not items_data:
        return None

    total_amount = round(total_amount, 2)
    timestamp_str = timestamp.isoformat()
    received_at = datetime.datetime.now().isoformat()

    try:
        cursor.execute("""
            INSERT INTO central_sales (store_id, sale_id, timestamp, total_amount, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (store["store_id"], sale_id, timestamp_str, total_amount, received_at))

        for product_id, qty, subtotal in items_data:
            cursor.execute("""
                INSERT INTO central_sale_items (store_id, sale_id, product_id, quantity, subtotal, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (store["store_id"], sale_id, product_id, qty, subtotal, received_at))
            cursor.execute("""
                UPDATE central_products SET stock = stock - ? WHERE store_id = ? AND product_id = ?
            """, (qty, store["store_id"], product_id))

        conn.commit()
        return {"sale_id": sale_id, "total": total_amount, "items": len(items_data)}

    except Exception as e:
        conn.rollback()
        print(f"❌ Error generating sale for {store['store_id']}: {e}")
        return None


# ==========================================
# HISTORICAL DATA GENERATOR
# ==========================================

def generate_historical_data(conn, store, days=45):
    print(f"\n📜 Generating {days} days of historical sales for {store['city']}...")
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days)

    sale_id = next_sale_id(conn, store["store_id"])
    total_sales = 0
    total_revenue = 0.0

    for day_offset in range(days):
        current_day = start_date + datetime.timedelta(days=day_offset)
        hour = random.randint(8, 21)
        minute = random.randint(0, 59)
        current_day = current_day.replace(hour=hour, minute=minute, second=0, microsecond=0)

        num_sales = random.randint(
            HISTORICAL_SALES_PER_STORE_PER_DAY_MIN,
            HISTORICAL_SALES_PER_STORE_PER_DAY_MAX,
        )

        for _ in range(num_sales):
            current_day += datetime.timedelta(minutes=random.randint(1, 15))
            result = generate_sale(conn, store, sale_id, timestamp=current_day)
            if result:
                total_sales += 1
                total_revenue += result["total"]
                sale_id += 1

        if (day_offset + 1) % 10 == 0:
            print(f"   📅 {store['city']}: processed {day_offset + 1}/{days} days...")

    print(f"✅ {store['city']} historical generation complete.")
    print(f"   📊 Total sales: {total_sales}")
    print(f"   💰 Total revenue: ₹{total_revenue:,.2f}")
    return total_sales, total_revenue


# ==========================================
# LIVE SIMULATION (Runs Forever, cycles through all stores)
# ==========================================

def run_live_simulation(conn):
    print("\n" + "=" * 60)
    print("🏪 TAMIL NADU MULTI-SHOP SIMULATOR — LIVE MODE")
    print("=" * 60)
    print(f"🏙️  Stores: {', '.join(s['city'] for s in STORES)}")
    print(f"⏱️  Batch interval: {LIVE_SLEEP_INTERVAL}s")
    print(f"📦 Sales per batch: up to {LIVE_BATCH_SIZE}")
    print("=" * 60)
    print("🚀 Press Ctrl+C to stop.\n")

    sale_counters = {s["store_id"]: next_sale_id(conn, s["store_id"]) for s in STORES}
    total_sales = 0
    total_revenue = 0.0

    try:
        while True:
            batch_count = random.randint(1, LIVE_BATCH_SIZE)
            for _ in range(batch_count):
                store = random.choice(STORES)
                result = generate_sale(conn, store, sale_counters[store["store_id"]])
                if result:
                    sale_counters[store["store_id"]] += 1
                    total_sales += 1
                    total_revenue += result["total"]
                    print(f"💰 [{store['city']}] Sale #{result['sale_id']:06d} | ₹{result['total']:.2f} | {result['items']} items")

            if total_sales % 50 == 0 and total_sales > 0:
                print(f"\n📊 STATS: {total_sales} sales across {len(STORES)} stores | Revenue: ₹{total_revenue:,.2f}\n")

            time.sleep(LIVE_SLEEP_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n🛑 Stopped by user.")
        print(f"📊 Final Stats: {total_sales} sales | Revenue: ₹{total_revenue:,.2f}")


# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print("=" * 60)
    print("🇮🇳 TAMIL NADU MULTI-SHOP POS SIMULATOR")
    print("=" * 60)
    print(f"📂 Database: {os.path.abspath(CENTRAL_DB_PATH)}")
    print(f"🏙️  Stores ({len(STORES)}): {', '.join(s['city'] for s in STORES)}")

    conn = connect()
    init_central_tables(conn)

    print("\n📦 Checking product catalogs...")
    for store in STORES:
        ensure_products_exist(conn, store)

    if GENERATE_HISTORICAL:
        for store in STORES:
            generate_historical_data(conn, store, HISTORICAL_DAYS)

    if "--no-live" in sys.argv:
        print("\n✅ Historical seeding complete. Skipping live simulation (--no-live).")
        conn.close()
    else:
        run_live_simulation(conn)
        conn.close()
