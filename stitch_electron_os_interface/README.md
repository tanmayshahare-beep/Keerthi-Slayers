# AROS — Retail Insights (desktop app)

A local Electron app that reads this repo's real `pos-system/pos_system.db` and
turns it into an insights dashboard: which products/categories drive revenue
(Pareto 80/20 analysis) and which are trending up or down week over week. All
numbers are computed directly from real sales data — nothing here is mocked.

```
electron/main.js          spawns the backend, opens the window
aros_backend/app.py       FastAPI app: auth + categories + insights
aros_backend/static/      the dashboard UI (index.html + app.js)
```

`DESIGN.md` documents the visual design system the UI follows. `screen.png`
is a reference mockup of the original concept (superseded by the working app).

## Setup

1. **Backend dependencies** (Python 3.10+):

   ```
   cd aros_backend
   pip install -r requirements.txt
   ```

2. **Make sure `pos-system/pos_system.db` exists** with data. If it's missing:

   ```
   cd ../../pos-system
   python3 -c "from database import POSDatabase; POSDatabase()"
   python3 seed_data.py
   ```

3. **Electron dependencies** (Node.js 18+):

   ```
   cd ../stitch_electron_os_interface/electron
   npm install
   ```

## Run

```
cd electron
npm start
```

This spawns the FastAPI backend on `127.0.0.1:8000` and opens it in an
Electron window. First run: create a local username/password (stored only in
`aros_backend/aros_app.db`, PBKDF2-hashed — nothing leaves your machine), then
confirm or edit the suggested product categories. After that you land on the
Insights dashboard.

## Running the backend standalone (no Electron)

Useful for developing the API without rebuilding the Electron shell each time:

```
cd aros_backend
python3 -m uvicorn app:app --reload
```

Then open `http://127.0.0.1:8000` in a browser.
