import sqlite3
import json
import datetime
import sys
from flask import Flask, request, jsonify

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

app = Flask(__name__)

# --- 1. Setup Central Database (Runs automatically on startup) ---
def init_database():
    conn = sqlite3.connect('central_hq.db')
    cursor = conn.cursor()

    # Stores the header of each sale
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS central_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            sale_id INTEGER,
            timestamp TEXT,
            total_amount REAL,
            received_at TEXT,
            UNIQUE(store_id, sale_id)  -- Prevents duplicate uploads
        )
    """)

    # Stores the line items of each sale (we will extend this later)
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

    # Stores current inventory snapshots from each store
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
    conn.close()
    print("✅ Central HQ Database initialized (central_hq.db)")

# --- 2. The Ingestion Endpoint (Where Laptop B sends data) ---
@app.route('/ingest', methods=['POST'])
def ingest_sale():
    try:
        data = request.get_json()
        store_id = data.get('store_id')
        sale_id = data.get('sale_id')
        timestamp = data.get('timestamp')
        total_amount = data.get('total_amount')

        # Basic validation
        if not all([store_id, sale_id, timestamp, total_amount is not None]):
            return jsonify({"error": "Missing required fields"}), 400

        received_at = datetime.datetime.now().isoformat()

        # Connect to the central database
        conn = sqlite3.connect('central_hq.db')
        cursor = conn.cursor()

        # Insert the sale (ignore if already exists to handle retries)
        cursor.execute("""
            INSERT OR IGNORE INTO central_sales
            (store_id, sale_id, timestamp, total_amount, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (store_id, sale_id, timestamp, total_amount, received_at))

        # Check if this was a new insertion or a duplicate
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Duplicate sale ignored"}), 200

        conn.commit()
        conn.close()

        print(f"📥 Received Sale #{sale_id} from {store_id} | Total: ${total_amount}")
        return jsonify({"status": "success", "sale_id": sale_id}), 200

    except Exception as e:
        print(f"❌ Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

# --- 3. Optional: Inventory Sync Endpoint (for future expansion) ---
@app.route('/ingest/inventory', methods=['POST'])
def ingest_inventory():
    """
    Future endpoint: Laptop B can send its full product list here.
    Not required for Phase 1, but good to have the skeleton.
    """
    return jsonify({"message": "Inventory sync not yet implemented"}), 501

# --- 4. Health Check (So Laptop B knows you are alive) ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "HQ is alive"}), 200

# --- 5. Start the Server ---
if __name__ == '__main__':
    init_database()
    print("🚀 HQ Receiver is now running...")
    print(f"📡 Listening on all network interfaces (0.0.0.0:5000)")
    print(f"👀 Waiting for data from Store POS laptops...")
    # host='0.0.0.0' makes it accessible from other laptops on the same network
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
