"""Agent registry.

Structured as a registry rather than hardcoded prompts so more agents can be
added later (each just needs a name + system prompt here, plus a small
"build ... messages" helper) without reshaping the plumbing in app.py,
ollama_client.py, or chat_store.py.

Report agents (report_explainer, news_correlator) both write to the same
per-report conversation slot (chat_store.py) - only one "active" agent
conversation per report at a time, whichever was started most recently.
That's a deliberate simplification, not a limitation of the registry itself.

Plan engines (strategy_engine ... customer_success_engine, see plans.py) are
a sequential pipeline: each one's build_engine_messages() call includes
every earlier engine's narrative as context, so the six read as one
coherent plan instead of independent opinions. All six are instructed to be
upfront about the limits of what the data actually supports rather than
inventing specifics the business hasn't provided.
"""

import re

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
    "strategy_engine": {
        "display_name": "Strategy Engine",
        "system_prompt": (
            "You are a retail strategy consultant covering market positioning, "
            "brand positioning, and pricing. Given a business's goal, "
            "timeframe, budget, and its real sales data, write a concise "
            "strategic plan: how the business should position itself, any "
            "pricing moves worth considering, and the overall approach to hit "
            "the stated goal within the stated timeframe and budget. Be "
            "specific and actionable - tie every recommendation back to the "
            "actual numbers you were given, and say plainly when the budget or "
            "timeframe looks unrealistic for the goal rather than pretending "
            "otherwise."
        ),
    },
    "marketing_engine": {
        "display_name": "Marketing Engine",
        "system_prompt": (
            "You are a 360-degree marketing strategist. You're given a "
            "business's goal/timeframe/budget and the Strategy Engine's plan "
            "for it. Design a marketing strategy that fits within the budget: "
            "which channels to use (digital, social, in-store, local/print), "
            "core messaging, and a rough sense of how the budget should be "
            "split across them. Be specific and actionable, and build "
            "directly on the strategy you were given rather than repeating it."
        ),
    },
    "leadgen_engine": {
        "display_name": "Lead Gen Engine",
        "system_prompt": (
            "You are a lead-generation specialist for small retail "
            "businesses. You're given the goal/timeframe/budget and the "
            "strategy and marketing plans already drafted for it. Suggest "
            "concrete tactics to bring in and start converting leads - "
            "specific digital ad ideas, a WhatsApp/SMS campaign concept, and "
            "physical/local marketing ideas (in-store promotions, local "
            "partnerships, flyers, events) as fit the budget. Be specific and "
            "actionable, and note roughly how much of the budget each tactic "
            "might reasonably need."
        ),
    },
    "sales_engine": {
        "display_name": "Sale Engine",
        "system_prompt": (
            "You are a sales operations consultant. You're given the "
            "goal/timeframe/budget and the strategy, marketing, and lead-gen "
            "plans already drafted for it. Design how leads actually become "
            "customers: the sales funnel stages, what happens at each stage, "
            "and how to measure conversion. Be specific and actionable, and "
            "make sure your funnel actually matches the leads the Lead Gen "
            "Engine's tactics would bring in."
        ),
    },
    "analytics_engine": {
        "display_name": "Analytics Engine",
        "system_prompt": (
            "You are a retail data analyst. You're given a business's "
            "goal/timeframe/budget, the strategy/marketing/lead-gen/sales "
            "plans already drafted for it, and a real classical statistics "
            "summary of its actual sales data (Pareto analysis, trend line, "
            "seasonality, concentration). Write a short forecasting and "
            "competitive-insight commentary: what the numbers suggest about "
            "the odds of hitting the stated goal in the stated timeframe, "
            "what risks to watch, and what to track going forward. Be honest "
            "about the limits of forecasting from historical data alone, and "
            "ground every comment in the actual numbers you were given - "
            "never invent a statistic that wasn't provided to you."
        ),
    },
    "customer_success_engine": {
        "display_name": "Customer Success Engine",
        "system_prompt": (
            "You are a customer success and retention strategist. You're "
            "given a business's goal/timeframe/budget, the plans already "
            "drafted for it, and a real summary of its recent transaction "
            "activity. Suggest a customer support and retention approach - "
            "how to keep new customers (brought in by the plans above) "
            "coming back, and what a lightweight CRM or support process could "
            "look like at this business's current scale. If the transaction "
            "data shows no individual customer identities are being tracked "
            "yet, say so plainly and suggest whether starting something "
            "simple (like a loyalty signup at checkout) would actually help "
            "given the stated goal - don't invent customer segments or "
            "behavior the data doesn't support."
        ),
    },
    "plan_advisor": {
        "display_name": "Plan Advisor",
        "system_prompt": (
            "You are a helpful, plain-spoken business advisor. A retail store "
            "owner has just gone through a full planning pipeline - strategy, "
            "marketing, lead generation, sales, analytics, and customer "
            "success - for a specific goal. You have their complete plan "
            "below. Answer their follow-up questions using only what's in the "
            "plan and the real data referenced in it - if they ask about "
            "something the plan doesn't cover, say so plainly instead of "
            "guessing."
        ),
    },
    "scorecard_advisor": {
        "display_name": "Scorecard Advisor",
        "system_prompt": (
            "You are a retail business analyst producing a concise executive "
            "scorecard. You're given real classical statistics about a "
            "store's performance: a Business Health Score, a Growth Score, a "
            "Revenue Opportunity estimate, a Customer Health proxy, and a "
            "list of Risk Alerts - all computed directly from real sales "
            "data, not by you. This business has no lead-generation or "
            "market-research data on file, so you must ESTIMATE two "
            "additional readiness scores using sound judgment from the real "
            "numbers you were given:\n"
            "- Lead Score (0-100): how well-positioned this business looks "
            "right now to generate and convert new leads.\n"
            "- Market Readiness (0-100): how ready this business looks to "
            "grow, expand, or take on more demand.\n"
            "Be explicit that these two are qualitative estimates, not "
            "measured data. Then give 3-5 concrete AI Recommendations, and a "
            "short Executive Summary (2-3 sentences) tying everything "
            "together. Format your entire answer with exactly these four "
            "section headers, in this order, each on its own line: "
            "'## Lead Score', '## Market Readiness', '## AI Recommendations', "
            "'## Executive Summary'. Do not add any other headers or "
            "commentary outside these four sections."
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


def build_engine_messages(engine_name: str, plan: dict, prior_context: str, real_data_narrative: str | None) -> list[dict]:
    """One step of the plan pipeline (see plans.py). prior_context is every
    earlier engine's narrative, already labeled and joined - empty string
    for the first engine in the sequence."""
    agent = get_agent(engine_name)

    header = (
        f"Business goal: {plan['goal']}\n"
        f"Timeframe: {plan['timeframe']}\n"
        f"Budget: {plan['currency']}{plan['budget']:,.2f}\n"
        f"Location: {plan['location_label']}"
    )

    blocks = [header]
    if prior_context:
        blocks.append(f"Here's what previous planning steps have already recommended:\n\n{prior_context}")
    if real_data_narrative:
        blocks.append(f"Real data for this business:\n{real_data_narrative}")
    blocks.append(f"Based on all of this, provide your {agent['display_name']} recommendations.")

    return [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": "\n\n".join(blocks)},
    ]


def build_plan_chat_seed_messages(plan: dict) -> list[dict]:
    """Seeds a plan-wide chat conversation with the full pipeline output as
    context. The greeting is a canned line, not a real model call - there's
    nothing data-bearing in it, so it's not worth the extra latency."""
    agent = get_agent("plan_advisor")
    header = (
        f"Business goal: {plan['goal']}\n"
        f"Timeframe: {plan['timeframe']}\n"
        f"Budget: {plan['currency']}{plan['budget']:,.2f}\n"
        f"Location: {plan['location_label']}"
    )
    engine_sections = "\n\n".join(
        f"### {plan['engines'][name]['display_name']}\n{plan['engines'][name]['narrative']}"
        for name in plan["engine_order"]
        if name in plan["engines"]
    )
    return [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": f"{header}\n\n{engine_sections}"},
        {"role": "assistant", "content": "Got it — I've reviewed your full plan. What would you like to know?"},
    ]


SCORECARD_SECTIONS = ["Lead Score", "Market Readiness", "AI Recommendations", "Executive Summary"]


def build_scorecard_messages(narrative: str, scorecard: dict, location_label: str, currency: str) -> list[dict]:
    agent = get_agent("scorecard_advisor")
    alerts_text = "\n".join(f"- [{a['severity'].upper()}] {a['text']}" for a in scorecard["risk_alerts"])
    bh, gr, ro, ch = scorecard["business_health"], scorecard["growth"], scorecard["revenue_opportunity"], scorecard["customer_health"]

    header = (
        f"Location: {location_label}\n"
        f"Business Health Score: {bh['score']}/100 ({bh['level']})\n"
        f"Growth Score: {gr['score']}/100 ({gr.get('trending_up', 0)} of {gr.get('tracked', 0)} tracked items trending up week-over-week)\n"
        f"Revenue Opportunity: {currency}{ro['estimated_monthly_value']:,.2f}/month recoverable from {ro['products_affected']} out-of-stock product(s)\n"
        f"Customer Health (visit-frequency proxy): {ch['score']}/100 ({ch['visit_frequency_trend']}, {ch['avg_daily_transactions']} avg daily transactions)\n"
        f"Risk Alerts:\n{alerts_text}"
    )

    return [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": f"{header}\n\nSales data summary:\n{narrative}\n\nProduce the scorecard."},
    ]


def split_scorecard_response(text: str) -> dict:
    """Splits the scorecard_advisor's '## Header' formatted reply into named
    sections. Falls back to putting the whole reply under Executive Summary
    if the model didn't follow the format - still shows something useful
    rather than dropping the response."""
    pattern = "|".join(re.escape(h) for h in SCORECARD_SECTIONS)
    matches = list(re.finditer(rf"##\s*({pattern})\s*\n", text))
    if not matches:
        return {"Lead Score": "", "Market Readiness": "", "AI Recommendations": "", "Executive Summary": text.strip()}

    sections = {}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip()
    for name in SCORECARD_SECTIONS:
        sections.setdefault(name, "")
    return sections
