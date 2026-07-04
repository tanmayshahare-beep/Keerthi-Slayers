# Open-Source Point of Sale System

A real, offline-first POS system, an optional multi-store sync layer, and a
desktop analytics app that reads the actual sales data — no mocked numbers
anywhere in this repo.

## What's here

| Folder | What it is |
| :--- | :--- |
| [`pos-system/`](pos-system/README.md) | **Hegxib POS** — the actual point-of-sale app. Offline, SQLite-backed, phone-as-barcode-scanner, inventory management. This is what a cashier runs. |
| [`HQ_Retail_OS/`](SYNC_SETUP.md) | Optional receiver for a central "HQ" database, so multiple store laptops can push their sales to one place over the local network. |
| [`stitch_electron_os_interface/`](stitch_electron_os_interface/README.md) | **AROS** — a separate Electron desktop app that reads the POS/HQ databases (read-only) and turns them into an insights dashboard: Pareto/trend analysis, live retail news, multi-location comparison, and a local-LLM chat (via [Ollama](https://ollama.com)) that explains a generated report and answers follow-up questions. |

Each folder's own README has the real setup/run instructions for that piece —
this file is just the map.

## Quick start

**Just want to ring up sales?**
```bash
cd pos-system
python main.py
```
See [`pos-system/README.md`](pos-system/README.md) — default admin password `admin123`.

**Want the analytics dashboard?**
```bash
cd stitch_electron_os_interface/electron
npm install
npm start
```
See [`stitch_electron_os_interface/README.md`](stitch_electron_os_interface/README.md)
and `instructions.txt` in that folder for the full walkthrough (multi-location
demo data, News tab, and the local-LLM report chat are all optional add-ons
documented there).

**Syncing multiple stores to one HQ database?** See [`SYNC_SETUP.md`](SYNC_SETUP.md).

## How the pieces fit together

```
pos-system/pos_system.db  ──┐
                             ├─→ stitch_electron_os_interface (AROS dashboard, read-only)
HQ_Retail_OS/central_hq.db ─┘
       ▲
       │ (optional, over LAN)
pos-system/store_sync_agent.py  →  HQ_Retail_OS/hq_receiver.py
```

The POS app is the source of truth and never depends on AROS or the HQ
sync layer to function — both of those are optional, additive, and strictly
read from (or receive pushes from) the POS side, never the reverse.

## License

[`pos-system/LICENSE`](pos-system/LICENSE) — GNU GPLv3.

## Contributing

Pull requests and forks welcome — see [`pos-system/README.md`](pos-system/README.md#contributing)
for contact details.
