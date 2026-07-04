"""File-backed store for generated Insights Reports.

Each report is a plain JSON file under reports/ - no database needed for
what's essentially a handful of timestamped documents. Generation itself
(report_analysis.py) is classical/cheap; this module just orchestrates
pulling the two data sources together and persisting the result.
"""

import datetime
import json
import os

import app_db
import central_data
import pos_data
import report_analysis
import tn_categories

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def _ensure_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _report_path(report_id: str) -> str:
    safe_id = os.path.basename(report_id)  # defense in depth against path traversal via a crafted id
    return os.path.join(REPORTS_DIR, f"{safe_id}.json")


def _main_store_section() -> dict | None:
    try:
        products = pos_data.get_products()
    except FileNotFoundError:
        return None
    sale_items = pos_data.get_sale_items()
    if sale_items.empty:
        return None
    category_map = app_db.get_category_assignments()  # {} is fine - pareto/trend just skip category grouping
    analysis = report_analysis.analyze_dataset(sale_items, products, category_map)
    return {
        "title": "Main Store (USD)",
        "currency": "$",
        "analysis": analysis,
        "narrative": report_analysis.build_narrative("Main Store (USD)", "$", analysis),
    }


def _tn_network_section() -> dict | None:
    locations = central_data.get_locations()
    if locations.empty:
        return None
    products = central_data.get_products("all")
    sale_items = central_data.get_sale_items("all")
    category_map = tn_categories.build_category_map(sale_items["barcode"].dropna().unique())
    analysis = report_analysis.analyze_dataset(sale_items, products, category_map)
    return {
        "title": "Tamil Nadu Network (₹)",
        "currency": "₹",
        "analysis": analysis,
        "narrative": report_analysis.build_narrative("Tamil Nadu Network (₹)", "₹", analysis),
    }


def generate_report() -> dict:
    _ensure_dir()
    generated_at = datetime.datetime.now()
    report_id = f"report_{generated_at:%Y%m%d_%H%M%S}"

    sections = [s for s in (_main_store_section(), _tn_network_section()) if s is not None]

    if not sections:
        narrative = "# Insights Report\n\nNo sales data available yet."
    else:
        narrative = "# Insights Report\n\n" + "\n\n".join(s["narrative"] for s in sections)

    report = {
        "id": report_id,
        "generated_at": generated_at.isoformat(),
        "method": (
            "Classical statistics only (pandas group-bys, Pareto/ABC analysis, "
            "ordinary-least-squares trend line, Herfindahl-Hirschman concentration "
            "index, day-of-week seasonality). No LLM was used to produce this report."
        ),
        "sections": sections,
        "narrative": narrative,
    }

    with open(_report_path(report_id), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def list_reports() -> list[dict]:
    _ensure_dir()
    summaries = []
    for filename in sorted(os.listdir(REPORTS_DIR), reverse=True):
        if not filename.endswith(".json"):
            continue
        report_id = filename[: -len(".json")]
        try:
            with open(os.path.join(REPORTS_DIR, filename), encoding="utf-8") as f:
                report = json.load(f)
            summaries.append({
                "id": report_id,
                "generated_at": report.get("generated_at"),
                "section_titles": [s["title"] for s in report.get("sections", [])],
            })
        except (json.JSONDecodeError, OSError):
            continue  # skip a corrupt/partial file rather than fail the whole list
    return summaries


def get_report(report_id: str) -> dict | None:
    path = _report_path(report_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
