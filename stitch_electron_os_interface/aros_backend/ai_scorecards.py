"""File-backed cache for the AI half of the Business Scorecard (Lead Score,
Market Readiness, AI Recommendations, Executive Summary - see
scorecard_advisor in agents.py).

Unlike Reports/Plans this isn't a growing history of timestamped documents -
there's only ever one "current" AI scorecard per location, so a location is
the cache key and regenerating overwrites it. This exists so opening
Insights doesn't lose the last AI read just because you navigated away, and
so GENERATE AI INSIGHTS is a real local-model call you make on purpose
(first time, or explicitly regenerating) rather than something re-run on
every page visit.
"""

import datetime
import json
import os

import agents
import ollama_client
import reports

AI_SCORECARDS_DIR = os.path.join(os.path.dirname(__file__), "ai_scorecards")


def _ensure_dir():
    os.makedirs(AI_SCORECARDS_DIR, exist_ok=True)


def _path(location: str) -> str:
    safe = os.path.basename(location)  # defense in depth against path traversal via a crafted location
    return os.path.join(AI_SCORECARDS_DIR, f"{safe}.json")


def get_cached(location: str) -> dict | None:
    path = _path(location)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate(location: str) -> dict:
    """Runs scorecard_advisor and caches the result for this location,
    overwriting whatever was cached before. Raises ValueError if there's no
    sales data for this location, or ollama_client.OllamaUnavailableError if
    the local model can't be reached - callers (app.py) turn each into the
    right HTTP status."""
    section = reports.main_store_section() if location == "main" else reports.tn_network_section(location)
    if section is None:
        raise ValueError("No sales data available for this location.")

    scorecard = section["analysis"]["scorecard"]
    messages = agents.build_scorecard_messages(section["narrative"], scorecard, section["title"], section["currency"])
    reply = ollama_client.chat(messages, num_predict=600)

    _ensure_dir()
    result = {
        "location": location,
        "location_label": section["title"],
        "generated_at": datetime.datetime.now().isoformat(),
        "sections": agents.split_scorecard_response(reply),
    }
    with open(_path(location), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result
