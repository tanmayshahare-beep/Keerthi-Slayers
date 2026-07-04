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

        # Grab sales that haven't been sent yet
        cursor.execute("""
            SELECT id, timestamp, total_amount 
            FROM sales 
            WHERE synced_to_cloud = 0 
            ORDER BY timestamp
        """)
        pending_sales = cursor.fetchall()

        if not pending_sales:
            return  # Nothing to do

        print(f"📤 Sending {len(pending_sales)} sales to HQ...")

        for sale in pending_sales:
            sale_id = sale[0]
            payload = {
                "store_id": STORE_ID,
                "sale_id": sale_id,
                "timestamp": sale[1],
                "total_amount": sale[2]
            }

            # Send to Laptop A (HQ)
            response = requests.post(HQ_API_URL, json=payload, timeout=5)

            if response.status_code == 200:
                # Mark as synced so we never send it again
                cursor.execute("""
                    UPDATE sales 
                    SET synced_to_cloud = 1 
                    WHERE id = ?
                """, (sale_id,))
                conn.commit()
                print(f"   ✅ Sale #{sale_id} synced.")
            else:
                print(f"   ❌ HQ Error {response.status_code}. Stopping for now.")
                break  # Stop trying if HQ is down

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
        time.sleep(30)  # Wait 30 seconds before checking again