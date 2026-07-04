# Store ↔ HQ Sync Setup

Connects the Store POS (sender) to the central HQ receiver so sales made offline
get pushed to a shared database once a network path exists.

```
Laptop B (Store POS)  --HTTP POST-->  Laptop A (HQ)
store_sync_agent.py                   HQ_Retail_OS/hq_receiver.py
pos_system.db                         HQ_Retail_OS/central_hq.db
```

Both scripts live in this same repo — copy the whole repo to each laptop (or
just the relevant piece: repo root + `pos-system/` for the store, `HQ_Retail_OS/`
for HQ).

Prerequisites: Python 3.7+, `pip install flask` (HQ machine), `pip install requests`
(Store machine). Both machines must be on the same network (same Wi-Fi/LAN).

## 1. Start the receiver (Laptop A / HQ)

```cmd
cd "HQ_Retail_OS"
python hq_receiver.py
```

You should see:

```
✅ Central HQ Database initialized (central_hq.db)
🚀 HQ Receiver is now running...
* Running on http://0.0.0.0:5000
```

Leave this window open — closing it stops the receiver.

Find this machine's IP address (needed by Laptop B):

```cmd
ipconfig
```

Note the **IPv4 Address** under your active Wi-Fi/Ethernet adapter (e.g. `192.168.1.100`).

## 2. Point the sender at the receiver (Laptop B / Store)

Edit `store_sync_agent.py` (repo root), line 11:

```python
HQ_API_URL = "http://192.168.1.100:5000/ingest"  # <- Laptop A's IPv4 address
```

Run it from the repo root (it opens `pos_system.db` via a relative path, so the
working directory must be the repo root, not `pos-system/`):

```cmd
python store_sync_agent.py
```

It polls for unsynced sales (`synced_to_cloud = 0`) every 30 seconds and marks
each one synced only after HQ confirms receipt. If HQ is unreachable it prints
a warning and retries — no sales data is lost.

## 3. Check the connection

**A. Health check** — from Laptop B (or any machine on the network), confirm
HQ is reachable before worrying about real data:

```cmd
python -c "import requests; print(requests.get('http://192.168.1.100:5000/health', timeout=5).json())"
```

Expect `{'status': 'HQ is alive'}`. A `ConnectionError` here means a network/
firewall/IP problem — fix this before touching the sync agent.

**B. End-to-end test** — on Laptop B, make one sale in the POS app (`python
main.py` inside `pos-system/`), then run the sync agent once. Confirm you see:

```
📤 Sending 1 sales to HQ...
   ✅ Sale #<id> synced.
```

and the matching line in Laptop A's terminal:

```
📥 Received Sale #<id> from STORE_001 | Total: $<amount>
```

**C. Verify it landed in HQ's database** — on Laptop A, in a second terminal:

```cmd
cd "HQ_Retail_OS"
python -c "import sqlite3; conn=sqlite3.connect('central_hq.db'); cursor=conn.cursor(); cursor.execute('SELECT store_id, sale_id, total_amount, timestamp FROM central_sales'); print(cursor.fetchall()); conn.close()"
```

**D. Verify the store side marked it synced** — on Laptop B, from the repo root:

```cmd
python -c "import sqlite3; conn=sqlite3.connect('pos_system.db'); cursor=conn.cursor(); cursor.execute('SELECT id, synced_to_cloud FROM sales ORDER BY id DESC LIMIT 5'); print(cursor.fetchall()); conn.close()"
```

The most recent sale should show `synced_to_cloud = 1`.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `⚠️ Cannot reach HQ` on Laptop B | HQ isn't running, wrong IP in `HQ_API_URL`, or Windows Firewall is blocking port 5000 on Laptop A |
| Health check hangs then times out | Machines aren't on the same network/subnet |
| Sale never shows `synced_to_cloud = 1` | Sync agent run from the wrong directory — it must run from the repo root (not `pos-system/`) so `pos_system.db` resolves to the real database |
| `Duplicate sale ignored` on every run | Expected if a sale already synced — the `UNIQUE(store_id, sale_id)` constraint prevents double-inserts on retries |
