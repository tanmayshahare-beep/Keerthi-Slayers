import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import app_db
import auth
import categories_template
import pos_data
import segregation

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


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
