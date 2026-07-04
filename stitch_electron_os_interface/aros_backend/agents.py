"""Agent registry.

Only one agent exists today (report_explainer), but this is deliberately
structured as a registry rather than a single hardcoded prompt so more
agents can be added later (each just needs a name + system prompt here, plus
wherever it gets invoked from) without reshaping the plumbing in app.py,
ollama_client.py, or chat_store.py.
"""

AGENTS = {
    "report_explainer": {
        "display_name": "Report Explainer",
        "system_prompt": (
            "You are a friendly, plain-spoken retail business advisor. A small "
            "shop owner has just been handed a data analysis report full of "
            "statistics (Pareto/ABC breakdowns, trend lines, concentration "
            "indices, seasonality). Your job is to explain what it actually "
            "means for their business in everyday language - no jargon, no "
            "statistics-speak. Be warm and conversational, like you're talking "
            "to a friend who runs the shop, not writing a memo. Keep your first "
            "explanation concise (a few short paragraphs) and end it there - do "
            "not invent or answer your own hypothetical follow-up questions, the "
            "shop owner will ask real ones afterward if they want more. When "
            "they do, answer the same way, using only the report data you were "
            "given - if they ask about something the report doesn't cover, say "
            "so plainly instead of guessing."
        ),
    },
}


def get_agent(name: str) -> dict:
    if name not in AGENTS:
        raise KeyError(f"Unknown agent: {name}")
    return AGENTS[name]


def build_explainer_messages(report_narrative: str) -> list[dict]:
    agent = get_agent("report_explainer")
    return [
        {"role": "system", "content": agent["system_prompt"]},
        {
            "role": "user",
            "content": (
                "Here is a data analysis report from my retail store:\n\n"
                f"{report_narrative}\n\n"
                "Can you explain what this means in plain, everyday language? "
                "What should I actually pay attention to here?"
            ),
        },
    ]
