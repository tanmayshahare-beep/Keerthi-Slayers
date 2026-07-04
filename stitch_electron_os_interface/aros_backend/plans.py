"""File-backed store for AI Business Plans.

A plan captures a goal/timeframe/budget for one location (see app.py's
/api/plans), then runs a sequential 6-agent pipeline (agents.py's engine
personas): strategy -> marketing -> lead gen -> sales -> analytics ->
customer success. Each engine sees the plan AND every prior engine's
narrative, so the pipeline reads as one coherent plan rather than six
disconnected opinions.

Two engines also get a real, non-LLM data snapshot alongside their AI
narrative - analytics_engine reuses reports.py's exact same classical
analysis, and customer_success_engine reuses real recent transactions from
pos_data.py. Neither fabricates numbers the underlying data doesn't have.
"""

import datetime
import json
import os

import agents
import ollama_client
import pos_data
import reports

PLANS_DIR = os.path.join(os.path.dirname(__file__), "plans")

ENGINE_ORDER = [
    "strategy_engine",
    "marketing_engine",
    "leadgen_engine",
    "sales_engine",
    "analytics_engine",
    "customer_success_engine",
]


def _ensure_dir():
    os.makedirs(PLANS_DIR, exist_ok=True)


def _plan_path(plan_id: str) -> str:
    safe_id = os.path.basename(plan_id)  # defense in depth against path traversal via a crafted id
    return os.path.join(PLANS_DIR, f"{safe_id}.json")


def _save(plan: dict) -> None:
    with open(_plan_path(plan["id"]), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)


def create_plan(location: str, goal: str, timeframe: str, budget: float) -> dict:
    _ensure_dir()
    created_at = datetime.datetime.now()
    plan_id = f"plan_{created_at:%Y%m%d_%H%M%S}"

    plan = {
        "id": plan_id,
        "created_at": created_at.isoformat(),
        "location": location,
        "location_label": reports.location_label(location),
        "currency": "$" if location == "main" else "₹",
        "goal": goal,
        "timeframe": timeframe,
        "budget": budget,
        "engine_order": ENGINE_ORDER,
        "engines": {},  # engine_name -> {display_name, narrative, real_data?}
    }
    _save(plan)
    return plan


def get_plan(plan_id: str) -> dict | None:
    path = _plan_path(plan_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_plans() -> list[dict]:
    _ensure_dir()
    summaries = []
    for filename in sorted(os.listdir(PLANS_DIR), reverse=True):
        if not filename.endswith(".json"):
            continue
        plan_id = filename[: -len(".json")]
        try:
            with open(os.path.join(PLANS_DIR, filename), encoding="utf-8") as f:
                plan = json.load(f)
            summaries.append({
                "id": plan_id,
                "created_at": plan.get("created_at"),
                "location_label": plan.get("location_label"),
                "goal": plan.get("goal"),
                "engines_completed": len(plan.get("engines", {})),
                "engines_total": len(plan.get("engine_order", ENGINE_ORDER)),
            })
        except (json.JSONDecodeError, OSError):
            continue  # skip a corrupt/partial file rather than fail the whole list
    return summaries


def _prior_context(plan: dict) -> str:
    parts = []
    for engine_name in plan["engine_order"]:
        entry = plan["engines"].get(engine_name)
        if entry:
            parts.append(f"### {entry['display_name']}\n{entry['narrative']}")
    return "\n\n".join(parts)


def _real_data_for(engine_name: str, plan: dict) -> dict | None:
    location = plan["location"]

    if engine_name == "analytics_engine":
        section = reports.main_store_section() if location == "main" else reports.tn_network_section(location)
        return {"type": "analytics", "section": section}

    if engine_name == "customer_success_engine":
        if location != "main":
            return {
                "type": "customer_activity",
                "available": False,
                "reason": (
                    "Per-transaction customer activity is only tracked for the Main "
                    "Store POS - the Tamil Nadu network doesn't record individual "
                    "transactions at this level of detail."
                ),
            }
        try:
            recent = pos_data.get_recent_sales(limit=15)
        except FileNotFoundError:
            return {"type": "customer_activity", "available": False, "reason": "pos_system.db not found."}
        distinct_names = set(recent["customer_name"].unique()) if not recent.empty else set()
        return {
            "type": "customer_activity",
            "available": True,
            "has_named_customers": bool(distinct_names) and distinct_names != {"Guest"},
            "recent_transactions": [
                {
                    "id": int(r["id"]),
                    "timestamp": r["timestamp"].isoformat(),
                    "total_amount": round(float(r["total_amount"]), 2),
                    "customer_name": r["customer_name"],
                    "item_count": int(r["item_count"]),
                }
                for _, r in recent.iterrows()
            ],
        }

    return None


def _real_data_narrative(real_data: dict | None) -> str | None:
    """Turns a real_data snapshot into plain text so the LLM narrative for
    that engine is actually grounded in it, not just the plan's goal/budget."""
    if real_data is None:
        return None

    if real_data["type"] == "analytics":
        section = real_data["section"]
        return section["narrative"] if section else "No sales data available for this location yet."

    if real_data["type"] == "customer_activity":
        if not real_data["available"]:
            return real_data["reason"]
        txns = real_data["recent_transactions"]
        if not txns:
            return "No transactions recorded yet."
        avg_ticket = sum(t["total_amount"] for t in txns) / len(txns)
        identity_note = (
            "Some transactions have named customers."
            if real_data["has_named_customers"]
            else "Every transaction is logged under a generic 'Guest' customer - there's no loyalty/customer-ID system in place yet, so individual customers can't be distinguished."
        )
        return (
            f"Most recent {len(txns)} transactions: average ticket ${avg_ticket:,.2f}. "
            f"{identity_note}"
        )

    return None


def run_engine(plan_id: str, engine_name: str) -> dict:
    """Runs exactly one engine and persists its output. Raises ValueError for
    an unknown engine, FileNotFoundError if the plan doesn't exist,
    PermissionError if an earlier engine in the sequence hasn't run yet, or
    ollama_client.OllamaUnavailableError if the local model can't be reached
    - callers (app.py) turn each into the right HTTP status."""
    if engine_name not in ENGINE_ORDER:
        raise ValueError(f"Unknown engine: {engine_name}")

    plan = get_plan(plan_id)
    if plan is None:
        raise FileNotFoundError(f"Plan not found: {plan_id}")

    idx = ENGINE_ORDER.index(engine_name)
    for earlier in ENGINE_ORDER[:idx]:
        if earlier not in plan["engines"]:
            raise PermissionError(f"Run {earlier} before {engine_name} - this pipeline is sequential.")

    real_data = _real_data_for(engine_name, plan)
    messages = agents.build_engine_messages(engine_name, plan, _prior_context(plan), _real_data_narrative(real_data))
    reply = ollama_client.chat(messages, num_predict=500)

    entry = {"display_name": agents.get_agent(engine_name)["display_name"], "narrative": reply}
    if real_data is not None:
        entry["real_data"] = real_data

    plan["engines"][engine_name] = entry
    _save(plan)
    return entry
