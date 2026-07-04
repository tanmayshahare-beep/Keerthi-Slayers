# Multi-Store POS Data Connectivity Pipeline

A lightweight, reliable, and offline-capable data pipeline for aggregating sales and inventory data from multiple retail store POS terminals to a centralized HQ database.

---

## Overview

This system simulates a real-world retail architecture using a **Hub-and-Spoke** model.

- **Store Laptops (Spokes)**: Run a local POS system (Hegxib) and a lightweight Python agent that automatically pushes new sales to HQ.
- **HQ Server (Hub)**: Runs a Flask API receiver that ingests data from all stores and stores it in a unified SQLite database.

**Key Features:**

- ✅ Offline-first: Stores continue working if HQ goes offline.
- ✅ Automatic retry: Unsold sales are queued locally until HQ is reachable.
- ✅ Zero duplicate data: Uses `synced_to_cloud` flags and unique constraints.
- ✅ Minimal setup: Runs entirely on Python with no external cloud dependencies.

---

## Architecture Diagram

```mermaid
flowchart LR
    subgraph Store_Laptop [Store POS Laptop]
        POS[Hegxib POS\nSQLite DB] --> Agent[store_sync_agent.py\n(Sync Agent)]
    end

    subgraph Network [Local Network / WiFi]
        Agent -->|HTTP POST (JSON)| API[Flask API Receiver\nPort 5000]
    end

    subgraph HQ_Laptop [HQ Server Laptop]
        API --> Central_DB[(central_hq.db\nUnified Sales DB)]
    end

    style Store_Laptop fill:#f9f9f9,stroke:#333,stroke-width:2px
    style HQ_Laptop fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Network fill:#fff3e0,stroke:#e65100,stroke-width:1px
```

---

## System Components

### 1. Store POS Laptop (Edge / Spoke)

| Component | Description |
| :--- | :--- |
| **Hegxib POS** | Open-source POS software running locally. Stores sales in `pos_system.db`. |
| **Database Patch** | Adds a `synced_to_cloud` column to the `sales` table to track upload status. |
| **Sync Agent** | Python script (`store_sync_agent.py`) that runs in the background, polls for unsynced sales every 30 seconds, and pushes them to HQ. |

### 2. HQ Server Laptop (Hub)

| Component | Description |
| :--- | :--- |
| **Flask Receiver** | Python web server (`hq_receiver.py`) that listens for incoming `POST` requests on port `5000`. |
| **Central Database** | SQLite database (`central_hq.db`) that stores all sales from all stores with a `store_id` identifier. |
| **Deduplication Logic** | Uses `INSERT OR IGNORE` to safely handle duplicate transmissions. |

---

## Prerequisites

### On Both Laptops

- Python 3.7+ installed.
- Basic network connectivity (both laptops on the same local network or VPN).

### On Store POS Laptop (Laptop B)

- Hegxib POS installed and running.
- Python library: `requests`
  ```bash
  pip install requests
  ```

### On HQ Server Laptop (Laptop A)

- Python library: `flask`
  ```bash
  pip install flask
  ```

---

## Setup Guide

### Part A: HQ Server Laptop (Laptop A - The Receiver)

#### Step 1: Find Your IP Address

- Open Command Prompt and run: `ipconfig`
- Note the **IPv4 Address** (e.g., `192.168.1.100`). You will give this to the store laptops.

#### Step 2: Create the Receiver Script

- Create a folder (e.g., `C:\HQ_Retail_OS`).
- Save the following file as `hq_receiver.py`:

```python
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
            UNIQUE(store_id, sale_id)
        )
    """)

    # Stores the line items of each sale
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

        if not all([store_id, sale_id, timestamp, total_amount is not None]):
            return jsonify({"error": "Missing required fields"}), 400

        received_at = datetime.datetime.now().isoformat()

        conn = sqlite3.connect('central_hq.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO central_sales
            (store_id, sale_id, timestamp, total_amount, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (store_id, sale_id, timestamp, total_amount, received_at))

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

# --- 4. Health Check ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "HQ is alive"}), 200

# --- 5. Start the Server ---
if __name__ == '__main__':
    init_database()
    print("🚀 HQ Receiver is now running...")
    print(f"📡 Listening on all network interfaces (0.0.0.0:5000)")
    print(f"👀 Waiting for data from Store POS laptops...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
```

#### Step 3: Initialize and Run

```bash
cd C:\HQ_Retail_OS
python hq_receiver.py
```

Keep this terminal **open and running**. You should see:

```
✅ Central HQ Database initialized
🚀 HQ Receiver is running on http://0.0.0.0:5000
```

#### Step 4: Give Your IP Address to Laptop B

Tell the store laptop operator to use your IPv4 address in their configuration.

---

### Part B: Store POS Laptop (Laptop B - The Sender)

#### Step 1: Patch the Local POS Database

- Navigate to your Hegxib folder (in this repo, that's `pos-system/` — the same folder as `main.py` and `pos_system.db`).
- Run this command to add the `synced_to_cloud` column:

```bash
python -c "import sqlite3; conn=sqlite3.connect('pos_system.db'); cursor=conn.cursor(); cursor.execute('ALTER TABLE sales ADD COLUMN synced_to_cloud INTEGER DEFAULT 0'); conn.commit(); conn.close(); print('✅ DB Patched.')"
```

#### Step 2: Verify the Column Was Added

```bash
python -c "import sqlite3; conn=sqlite3.connect('pos_system.db'); cursor=conn.cursor(); cursor.execute('PRAGMA table_info(sales)'); print([col[1] for col in cursor.fetchall()])"
```

You should see: `['id', 'timestamp', 'total_amount', 'customer_name', 'synced_to_cloud']`

#### Step 3: Create the Sync Agent Script

Save the following file as `store_sync_agent.py` in your Hegxib folder — **it must live in the same folder as `pos_system.db`** (in this repo, that's `pos-system/`), since it opens the database via a relative path. Running it from any other folder (e.g. the repo root) will silently connect to a different, empty `pos_system.db` and never find any sales to sync.

```python
import sqlite3
import requests
import time
import os
import sys

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# !!! IMPORTANT: CHANGE THIS IP ADDRESS !!!
# ==========================================
# Replace 192.168.1.100 with the ACTUAL IP address of Laptop A (HQ).
# To find Laptop A's IP, run 'ipconfig' on Laptop A and look for IPv4.
HQ_API_URL = "http://192.168.1.100:5000/ingest"  # <--- CHANGE THIS

# Give this store a unique name (use different names if you have multiple stores)
STORE_ID = "STORE_001"

# Path to your Hegxib database (keep it as-is if the script is in the same folder)
DB_PATH = "pos_system.db"

# ------------------------------------------
# DO NOT CHANGE ANYTHING BELOW THIS LINE
# ------------------------------------------

def sync_pending_sales():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, total_amount 
            FROM sales 
            WHERE synced_to_cloud = 0 
            ORDER BY timestamp
        """)
        pending_sales = cursor.fetchall()

        if not pending_sales:
            return

        print(f"📤 Sending {len(pending_sales)} sales to HQ...")

        for sale in pending_sales:
            sale_id = sale[0]
            payload = {
                "store_id": STORE_ID,
                "sale_id": sale_id,
                "timestamp": sale[1],
                "total_amount": sale[2]
            }

            response = requests.post(HQ_API_URL, json=payload, timeout=5)

            if response.status_code == 200:
                cursor.execute("""
                    UPDATE sales 
                    SET synced_to_cloud = 1 
                    WHERE id = ?
                """, (sale_id,))
                conn.commit()
                print(f"   ✅ Sale #{sale_id} synced.")
            else:
                print(f"   ❌ HQ Error {response.status_code}. Stopping for now.")
                break

        conn.close()

    except requests.exceptions.ConnectionError:
        print("⚠️  Cannot reach HQ. Is Laptop A running the Flask server?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

# --- Run forever ---
if __name__ == "__main__":
    print(f"🚀 POS Sync Agent started for {STORE_ID}")
    print(f"📡 Target HQ: {HQ_API_URL}")
    while True:
        sync_pending_sales()
        time.sleep(30)
```

#### Step 4: Test the Agent Manually

1. Open Hegxib POS (`python main.py`), log in with `admin123`, and sell 1 item.
2. Close Hegxib (or leave it open).
3. Run the agent once:

```bash
python store_sync_agent.py
```

**Expected Output:**

```
🚀 POS Sync Agent started for STORE_001
📡 Target HQ: http://192.168.1.100:5000/ingest
📤 Sending 1 sales to HQ...
   ✅ Sale #1 synced.
```

#### Step 5: Automate the Agent (Boot Startup)

1. Press `Win + R`, type `taskschd.msc`, and press Enter.
2. In the right-hand panel, click **"Create Basic Task"**.
3. **Name:** `POS Cloud Sync`
4. **Trigger:** Select **"When the computer starts"**.
5. **Action:** Select **"Start a program"**.
6. **Program/script:** Browse to your `python.exe`.
   - Find the path by running `where python` in CMD.
7. **Add arguments:** Full path to `store_sync_agent.py` (e.g., `C:\Hegxib\store_sync_agent.py`).
8. **Start in:** Folder containing the script (e.g., `C:\Hegxib`).
9. Click **Finish**.

The agent will now run silently every time the POS laptop boots.

---

## Configuration Reference

| Variable | Location | Description |
| :--- | :--- | :--- |
| `HQ_API_URL` | `pos-system/store_sync_agent.py` (Line 15) | Full URL of the HQ Flask server. |
| `STORE_ID` | `pos-system/store_sync_agent.py` (Line 18) | Unique identifier for this store (e.g., "STORE_001"). |
| `DB_PATH` | `pos-system/store_sync_agent.py` (Line 21) | Path to the local `pos_system.db`. Defaults to current folder — the script must be run from `pos-system/` (the same folder as `main.py` and `pos_system.db`), not the repo root. |
| `PORT` | `HQ_Retail_OS/hq_receiver.py` (Line 125) | Port the Flask server listens on (default: `5000`). |

---

## Data Flow Explanation

1.  **Local Sale**: Cashier rings up a customer. Hegxib writes the sale to `sales` table with `synced_to_cloud = 0`.
2.  **Polling**: The `store_sync_agent.py` wakes up every 30 seconds and queries for records where `synced_to_cloud = 0`.
3.  **Transmission**: For each pending sale, the agent builds a JSON payload and sends an HTTP `POST` to the HQ server.
4.  **Ingestion**: The Flask receiver validates the JSON, writes it to `central_hq.db`, and returns a `200 OK`.
5.  **Acknowledgment**: Upon receiving the `200 OK`, the agent updates the local record to `synced_to_cloud = 1`, ensuring it is never sent again.
6.  **Centralization**: Your future optimization OS will query `central_hq.db` to view sales from all stores combined.

---

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **`⚠️ Cannot reach HQ`** | 1. Verify Laptop A's IP address hasn't changed (use `ipconfig`).<br>2. Ensure Laptop A is running `hq_receiver.py`.<br>3. Check firewalls (temporarily disable Windows Defender Firewall to test). |
| **`sqlite3.OperationalError: no such column: synced_to_cloud`** | You forgot to patch the database. Run the `ALTER TABLE` command from Part B, Step 1. |
| **Duplicate sales in central DB** | The script uses `INSERT OR IGNORE` based on `(store_id, sale_id)`. Duplicates are silently ignored. |
| **Agent stops sending after one sale** | Check if the `synced_to_cloud` flag is updating. If not, check file permissions on `pos_system.db`. |
| **Flask server isn't accessible from other laptops** | Ensure you are using `host='0.0.0.0'` in `app.run()` (already included). Also check if port `5000` is blocked by the firewall. |
| **ImportError: No module named 'flask'** | Run `pip install flask` on Laptop A. |
| **ImportError: No module named 'requests'** | Run `pip install requests` on Laptop B. |

---

## File Structure Summary

### On Store POS Laptop (Laptop B)

```
C:\Hegxib_POS\
├── main.py                 (Hegxib executable)
├── pos_system.db           (Local SQLite DB)
├── store_sync_agent.py     (Your sync script)
└── seed_data.py            (Optional: Simulate test inventory)
```

### On HQ Server Laptop (Laptop A)

```
C:\HQ_Retail_OS\
├── hq_receiver.py          (Flask ingestion server)
└── central_hq.db           (Centralized SQLite DB - auto-created)
```

---

## Roadmap / Next Steps

This completes the **Connectivity Layer**. The next phase involves building the **Optimization OS** that will:

- Query `central_hq.db` to run analytics.
- Detect spoilage risks and stockouts.
- Suggest inter-store transfers.
- **(Future)** Integrate an LLM-based reasoning layer for natural language business insights.

---

## License & Disclaimer

This project is intended for **simulation and development purposes only**. Use in production environments requires proper security hardening (HTTPS, authentication, database backups) which are not implemented in this demo.