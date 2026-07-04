import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agents
import ai_scorecards
import app_db
import auth
import categories_template
import central_data
import chat_store
import news
import ollama_client
import plans
import pos_data
import report_analysis
import reports
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


class PlanCreate(BaseModel):
    location: str = "main"
    goal: str
    timeframe: str
    budget: float


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
    products = pos_data.get_products()
    analysis = report_analysis.analyze_dataset(sale_items, products, category_map, currency="$")
    return {
        "pareto": analysis["pareto"],
        "trend_shifts": analysis["trend_shifts"],
        "scorecard": analysis["scorecard"],
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


@app.get("/api/location-insights")
def location_insights(location: str = "all", _user: str = Depends(auth.require_session)):
    sale_items = central_data.get_sale_items(location)
    products = central_data.get_products(location)
    category_map = tn_categories.build_category_map(sale_items["barcode"].dropna().unique()) if not sale_items.empty else {}
    analysis = report_analysis.analyze_dataset(sale_items, products, category_map, currency="₹")
    return {
        "stats": analysis["summary"],
        "pareto": analysis["pareto"],
        "trend_shifts": analysis["trend_shifts"],
        "scorecard": analysis["scorecard"],
    }


@app.get("/api/scorecard/ai")
def scorecard_ai_get(location: str = "main", _user: str = Depends(auth.require_session)):
    """Returns whatever AI scorecard was last generated for this location,
    if any - lets the UI show it immediately on load instead of always
    starting from a blank "click to generate" state."""
    cached = ai_scorecards.get_cached(location)
    if cached is None:
        raise HTTPException(status_code=404, detail="No AI scorecard generated yet for this location.")
    return cached


@app.post("/api/scorecard/ai")
def scorecard_ai_generate(location: str = "main", _user: str = Depends(auth.require_session)):
    """The four qualitative scorecard fields (Lead Score, Market Readiness,
    AI Recommendations, Executive Summary) that classical stats alone can't
    produce - scorecard_advisor (agents.py) estimates them from the same
    real numbers the dashboard already shows, on demand rather than on
    every page load. Overwrites this location's previously cached result."""
    try:
        return ai_scorecards.generate(location)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


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


@app.post("/api/plans")
def plans_create(body: PlanCreate, _user: str = Depends(auth.require_session)):
    return plans.create_plan(body.location, body.goal, body.timeframe, body.budget)


@app.get("/api/plans")
def plans_list(_user: str = Depends(auth.require_session)):
    return plans.list_plans()


@app.get("/api/plans/{plan_id}")
def plans_get(plan_id: str, _user: str = Depends(auth.require_session)):
    plan = plans.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.post("/api/plans/{plan_id}/run/{engine_name}")
def plans_run_engine(plan_id: str, engine_name: str, _user: str = Depends(auth.require_session)):
    """Runs exactly one step of the sequential engine pipeline (plans.py).
    The frontend calls this once per engine, in order, so it can show
    progress and render each section as it completes rather than waiting
    for all six local-LLM calls to finish silently."""
    try:
        return plans.run_engine(plan_id, engine_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plan not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/plans/{plan_id}/chat")
def plans_chat_history(plan_id: str, _user: str = Depends(auth.require_session)):
    history = chat_store.get_conversation(plan_id) or []
    return {"messages": [m for m in history if m["role"] != "system"]}


@app.post("/api/plans/{plan_id}/chat")
def plans_chat(plan_id: str, body: ChatMessage, _user: str = Depends(auth.require_session)):
    if chat_store.get_conversation(plan_id) is None:
        plan = plans.get_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        chat_store.start_conversation(plan_id, agents.build_plan_chat_seed_messages(plan))

    chat_store.append_message(plan_id, "user", body.message)
    try:
        reply = ollama_client.chat(chat_store.get_conversation(plan_id))
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    chat_store.append_message(plan_id, "assistant", reply)
    return {"reply": reply}


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
