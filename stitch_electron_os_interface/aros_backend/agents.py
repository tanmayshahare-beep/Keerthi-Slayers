"""Agent registry.

Structured as a registry rather than hardcoded prompts so more agents can be
added later (each just needs a name + system prompt here, plus a small
"build ... messages" helper) without reshaping the plumbing in app.py,
ollama_client.py, or chat_store.py. Two agents exist so far:

- report_explainer: plain-language walkthrough of a classical stats report.
- news_correlator: looks for plausible links between real local news
  headlines (aros_backend/news.py) and the same report's sales patterns.

Both write to the same per-report conversation slot (chat_store.py) - only
one "active" agent conversation per report at a time, whichever was started
most recently. That's a deliberate simplification, not a limitation of the
registry itself.
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
    "news_correlator": {
        "display_name": "News Correlator",
        "system_prompt": (
            "You are a retail market analyst. You're given a summary of a "
            "store's sales performance and a list of real, recent local news "
            "headlines. Look for plausible connections between the news and "
            "the sales patterns - a local event, economic news, weather, or "
            "industry trend that might explain a spike, decline, or notable "
            "shift. You are pattern-matching headlines against trends, not "
            "proving causation - say so plainly, and just as plainly say when "
            "nothing in the news seems related instead of forcing a "
            "connection. Keep your first answer concise (a few short "
            "paragraphs.) Answer follow-up questions the same way, grounded "
            "only in the sales data and headlines you were given."
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


def build_news_correlation_messages(report_narrative: str, articles: list[dict], location_label: str) -> list[dict]:
    agent = get_agent("news_correlator")
    if articles:
        headlines = "\n".join(
            f"- {a['title']} ({a.get('source') or 'unknown source'}, {a.get('published') or 'date unknown'})"
            for a in articles[:10]
        )
    else:
        headlines = "(no recent headlines were found)"

    return [
        {"role": "system", "content": agent["system_prompt"]},
        {
            "role": "user",
            "content": (
                f"Here is the sales data summary for {location_label}:\n\n"
                f"{report_narrative}\n\n"
                f"Here are recent local news headlines for {location_label}:\n{headlines}\n\n"
                "Do any of these headlines plausibly connect to the sales patterns above? "
                "What correlations, if any, do you see?"
            ),
        },
    ]
