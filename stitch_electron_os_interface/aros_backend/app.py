import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agents
import app_db
import auth
import categories_template
import central_data
import chat_store
import news
import ollama_client
import pos_data
import reports
import segregation
import tn_categories

app_db.init_db()

app = FastAPI(title="AROS Backend")


class Credentials(BaseModel):
    username: str
    password: str


class CategoryAssignments(BaseModel):
    assignments: dict[str, str]  # barcode -> category_name


class ChatMessage(BaseModel):
    message: str


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


def _news_label_for(location: str) -> str | None:
    return central_data.label_for_store(location) if location not in ("main", "all") else None


@app.get("/api/news")
def news_for_location(location: str = "main", _user: str = Depends(auth.require_session)):
    return news.fetch_news(location, _news_label_for(location))


@app.post("/api/reports/generate")
def reports_generate(location: str = "main", _user: str = Depends(auth.require_session)):
    return reports.generate_report(location)


@app.get("/api/reports")
def reports_list(_user: str = Depends(auth.require_session)):
    return reports.list_reports()


@app.get("/api/reports/{report_id}")
def reports_get(report_id: str, _user: str = Depends(auth.require_session)):
    report = reports.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/llm/status")
def llm_status(_user: str = Depends(auth.require_session)):
    return {"available": ollama_client.is_available(), "model": ollama_client.DEFAULT_MODEL}


@app.post("/api/reports/{report_id}/send-to-llm")
def reports_send_to_llm(report_id: str, _user: str = Depends(auth.require_session)):
    """Kicks off a chat conversation with the local LLM (via Ollama - see
    ollama_client.py) about this report: the "report_explainer" agent
    (agents.py) explains it in plain language, which seeds the conversation
    that /api/reports/{report_id}/chat continues."""
    report = reports.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    messages = agents.build_explainer_messages(report["narrative"])
    try:
        reply = ollama_client.chat(messages, num_predict=600)
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    messages.append({"role": "assistant", "content": reply})
    chat_store.start_conversation(report_id, messages)
    return {"explanation": reply}


@app.post("/api/reports/{report_id}/correlate-news")
def reports_correlate_news(report_id: str, _user: str = Depends(auth.require_session)):
    """Second agent (news_correlator, agents.py): fetches real headlines for
    this report's own location (news.py - same free Google News RSS the News
    tab uses) and asks the local LLM whether they plausibly relate to the
    report's sales patterns. Starts/replaces this report's conversation the
    same way send-to-llm does - see agents.py's module docstring for why."""
    report = reports.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    location = report.get("location", "main")
    news_result = news.fetch_news(location, _news_label_for(location))
    messages = agents.build_news_correlation_messages(
        report["narrative"], news_result["articles"], report.get("location_label", location)
    )
    try:
        reply = ollama_client.chat(messages, num_predict=600)
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    messages.append({"role": "assistant", "content": reply})
    chat_store.start_conversation(report_id, messages)
    return {"explanation": reply, "articles_used": news_result["articles"]}


@app.get("/api/reports/{report_id}/chat")
def reports_chat_history(report_id: str, _user: str = Depends(auth.require_session)):
    history = chat_store.get_conversation(report_id) or []
    return {"messages": [m for m in history if m["role"] != "system"]}


@app.post("/api/reports/{report_id}/chat")
def reports_chat(report_id: str, body: ChatMessage, _user: str = Depends(auth.require_session)):
    if chat_store.get_conversation(report_id) is None:
        raise HTTPException(status_code=409, detail="Start with Send to LLM or Correlate with News first.")

    chat_store.append_message(report_id, "user", body.message)
    try:
        reply = ollama_client.chat(chat_store.get_conversation(report_id))
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    chat_store.append_message(report_id, "assistant", reply)
    return {"reply": reply}


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
