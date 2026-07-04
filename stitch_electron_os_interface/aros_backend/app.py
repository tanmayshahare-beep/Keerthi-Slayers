import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import app_db
import auth
import categories_template
import central_data
import news
import pos_data
import segregation
import tn_categories

app_db.init_db()

app = FastAPI(title="AROS Backend")


class Credentials(BaseModel):
    username: str
    password: str


class CategoryAssignments(BaseModel):
    assignments: dict[str, str]  # barcode -> category_name


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/status")
def auth_status():
    user = app_db.get_user()
    return {"has_user": user is not None}


@app.post("/api/auth/setup")
def setup(credentials: Credentials):
    if app_db.get_user():
        raise HTTPException(status_code=409, detail="A user already exists")
    if not credentials.username.strip() or not credentials.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    password_hash, salt = auth.hash_password(credentials.password)
    app_db.create_user(credentials.username.strip(), password_hash, salt)
    token = auth.issue_session(credentials.username.strip())
    return {"token": token}


@app.post("/api/auth/login")
def login(credentials: Credentials):
    user = app_db.get_user()
    if not user:
        raise HTTPException(status_code=404, detail="No user set up yet")
    _id, username, password_hash, salt = user
    # Match setup()'s username.strip() so a stray leading/trailing space
    # (autofill, a stray keystroke) doesn't silently fail the username check.
    if username != credentials.username.strip():
        raise HTTPException(status_code=401, detail=f'No account found with username "{credentials.username.strip()}".')
    if not auth.verify_password(credentials.password, salt, password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    token = auth.issue_session(username)
    return {"token": token}


@app.get("/api/products")
def products(_user: str = Depends(auth.require_session)):
    return pos_data.get_products().to_dict(orient="records")


@app.get("/api/categories/template")
def categories_suggested_template(_user: str = Depends(auth.require_session)):
    return {"assignments": categories_template.suggested_assignments()}


@app.get("/api/categories")
def categories_get(_user: str = Depends(auth.require_session)):
    assignments = app_db.get_category_assignments()
    if not assignments:
        raise HTTPException(status_code=404, detail="Onboarding not completed yet")
    return {"assignments": assignments}


@app.post("/api/categories")
def categories_save(body: CategoryAssignments, _user: str = Depends(auth.require_session)):
    if not body.assignments:
        raise HTTPException(status_code=400, detail="No category assignments provided")
    app_db.save_category_assignments(body.assignments)
    return {"saved": len(body.assignments)}


@app.get("/api/insights")
def insights(_user: str = Depends(auth.require_session)):
    category_map = app_db.get_category_assignments()
    if not category_map:
        raise HTTPException(status_code=409, detail="Onboarding not completed yet")
    sale_items = pos_data.get_sale_items()
    return {
        "pareto": segregation.pareto(sale_items, category_map),
        "trend_shifts": segregation.trend_shifts(sale_items, category_map),
    }


@app.get("/api/locations")
def locations(_user: str = Depends(auth.require_session)):
    """Tamil Nadu shop network (see pos-system/tamil_nadu_local_simulator.py).
    Empty list until that simulator has been run at least once."""
    df = central_data.get_locations()
    records = df.to_dict(orient="records")
    for r in records:
        r["label"] = central_data.label_for_store(r["store_id"])
    return records


def _empty_location_insights():
    return {
        "stats": {"revenue": 0.0, "transactions": 0, "products_tracked": 0, "stockouts": 0},
        "pareto": {"by_category": [], "by_product": []},
        "trend_shifts": {"recent_window_days": segregation.RECENT_WINDOW_DAYS, "by_category": [], "by_product": []},
    }


@app.get("/api/location-insights")
def location_insights(location: str = "all", _user: str = Depends(auth.require_session)):
    sale_items = central_data.get_sale_items(location)
    products = central_data.get_products(location)

    if sale_items.empty and products.empty:
        return _empty_location_insights()

    # sale_id only increments per-store (each store's counter starts at 1),
    # so counting nunique("sale_id") across combined stores would collide -
    # count distinct (store_id, sale_id) pairs instead.
    transactions = (
        len(sale_items.drop_duplicates(subset=["store_id", "sale_id"])) if not sale_items.empty else 0
    )
    stats = {
        "revenue": round(float(sale_items["subtotal"].sum()), 2) if not sale_items.empty else 0.0,
        "transactions": transactions,
        "products_tracked": int(products["barcode"].nunique()) if not products.empty else 0,
        "stockouts": int((products["stock"] == 0).sum()) if not products.empty else 0,
    }

    if sale_items.empty:
        pareto = {"by_category": [], "by_product": []}
        trend_shifts = {"recent_window_days": segregation.RECENT_WINDOW_DAYS, "by_category": [], "by_product": []}
    else:
        category_map = tn_categories.build_category_map(sale_items["barcode"].dropna().unique())
        pareto = segregation.pareto(sale_items, category_map)
        trend_shifts = segregation.trend_shifts(sale_items, category_map)

    return {"stats": stats, "pareto": pareto, "trend_shifts": trend_shifts}


@app.get("/api/news")
def news_for_location(location: str = "main", _user: str = Depends(auth.require_session)):
    label = central_data.label_for_store(location) if location not in ("main", "all") else None
    return news.fetch_news(location, label)


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
