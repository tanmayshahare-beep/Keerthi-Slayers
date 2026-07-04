"""Classical (non-LLM) analysis for the Insights Report feature.

Everything here is plain aggregation/arithmetic on top of pandas - group-bys,
ordinary-least-squares on a handful of points, a Herfindahl-Hirschman
concentration index. No model calls, no external services, negligible CPU.
segregation.py's Pareto/trend-shift logic is reused rather than duplicated.

The "narrative" builders below produce plain text via string templates from
already-computed numbers - not natural-language generation - so they stay on
the classical side of the line too. That narrative is also the payload a
future "send to LLM" step would forward, so it's written to read reasonably
as prose, not just a numbers dump.
"""

import pandas as pd

import segregation

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def weekday_seasonality(sale_items: pd.DataFrame) -> list[dict]:
    if sale_items.empty:
        return []
    df = sale_items.copy()
    df["weekday"] = df["timestamp"].dt.day_name()
    by_day = df.groupby("weekday")["subtotal"].sum()
    distinct_weeks = {}
    for day in WEEKDAY_ORDER:
        count = df.loc[df["weekday"] == day, "timestamp"].dt.date.nunique() or 1
        distinct_weeks[day] = count
    return [
        {
            "weekday": day,
            "avg_revenue": round(float(by_day.get(day, 0.0)) / distinct_weeks[day], 2),
        }
        for day in WEEKDAY_ORDER
        if day in by_day.index
    ]


def linear_trend(sale_items: pd.DataFrame) -> dict:
    """Ordinary least squares of daily revenue vs. day index - a slope, not a
    forecast. Cheap (a handful of sums over at most a few dozen points)."""
    if sale_items.empty:
        return {"slope_per_day": 0.0, "direction": "flat", "r_squared": 0.0}

    daily = sale_items.groupby(sale_items["timestamp"].dt.date)["subtotal"].sum().sort_index()
    if len(daily) < 2:
        return {"slope_per_day": 0.0, "direction": "flat", "r_squared": 0.0}

    x = pd.Series(range(len(daily)), dtype=float)
    y = daily.reset_index(drop=True).astype(float)
    x_mean, y_mean = x.mean(), y.mean()
    covariance = ((x - x_mean) * (y - y_mean)).sum()
    variance = ((x - x_mean) ** 2).sum()
    slope = covariance / variance if variance else 0.0
    intercept = y_mean - slope * x_mean

    predicted = intercept + slope * x
    ss_res = ((y - predicted) ** 2).sum()
    ss_tot = ((y - y_mean) ** 2).sum()
    r_squared = 1 - (ss_res / ss_tot) if ss_tot else 0.0

    avg_daily = y_mean or 1
    relative_slope = slope / avg_daily
    if relative_slope > 0.01:
        direction = "growing"
    elif relative_slope < -0.01:
        direction = "declining"
    else:
        direction = "flat"

    return {
        "slope_per_day": round(float(slope), 2),
        "direction": direction,
        "r_squared": round(float(r_squared), 3),
    }


def concentration_index(ranked_revenue: list[dict]) -> dict:
    """Herfindahl-Hirschman Index on revenue share - a standard classical
    concentration metric (sum of squared market shares), reusing whatever
    Pareto ranking was already computed rather than re-aggregating."""
    total = sum(r["revenue"] for r in ranked_revenue)
    if not total:
        return {"hhi": 0.0, "level": "n/a"}
    hhi = sum((r["revenue"] / total) ** 2 for r in ranked_revenue)
    if hhi < 0.15:
        level = "low (revenue spread broadly across many items)"
    elif hhi < 0.25:
        level = "moderate"
    else:
        level = "high (revenue concentrated in a few items)"
    return {"hhi": round(hhi, 3), "level": level}


def _score_level(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 50:
        return "moderate"
    if score >= 25:
        return "weak"
    return "critical"


def transaction_frequency_trend(sale_items: pd.DataFrame) -> dict:
    """Daily distinct-transaction count, split into two halves and compared -
    a proxy for how often people are visiting/buying, used as the Customer
    Health signal since no customer identity exists to measure retention or
    repeat-visit rate directly."""
    if sale_items.empty:
        return {"direction": "flat", "avg_daily_transactions": 0.0}

    key_cols = ["store_id", "sale_id"] if "store_id" in sale_items.columns else ["sale_id"]
    unique_txns = sale_items.drop_duplicates(subset=key_cols)
    daily_counts = unique_txns.groupby(unique_txns["timestamp"].dt.date).size().sort_index()
    avg_daily = float(daily_counts.mean())

    if len(daily_counts) < 4:
        return {"direction": "flat", "avg_daily_transactions": round(avg_daily, 1)}

    midpoint = len(daily_counts) // 2
    first_half_avg = daily_counts.iloc[:midpoint].mean()
    second_half_avg = daily_counts.iloc[midpoint:].mean()
    change = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg else 0.0

    if change > 0.05:
        direction = "growing"
    elif change < -0.05:
        direction = "declining"
    else:
        direction = "flat"

    return {"direction": direction, "avg_daily_transactions": round(avg_daily, 1), "pct_change": round(change * 100, 1)}


def business_health_score(analysis: dict) -> dict:
    """0-100 composite: revenue trend (40pts), stockout ratio (30pts),
    category concentration risk (30pts). Weights are a judgment call, not a
    standard formula - the point is a quick, defensible read of the same
    numbers already shown elsewhere, not a precise instrument."""
    summary = analysis["summary"]
    trend = analysis["trend"]
    cat_conc = analysis["concentration"]["by_category"]

    trend_score = {"growing": 40, "flat": 25, "declining": 10}[trend["direction"]]

    stockout_ratio = (summary["stockouts"] / summary["products_tracked"]) if summary["products_tracked"] else 0
    stockout_score = max(0.0, 30 * (1 - stockout_ratio))

    hhi = cat_conc["hhi"] if cat_conc["level"] != "n/a" else 0.2
    concentration_score = max(0.0, 30 * (1 - min(hhi, 1)))

    total = round(trend_score + stockout_score + concentration_score)
    return {"score": total, "level": _score_level(total)}


def growth_score(analysis: dict) -> dict:
    """0-100 based on the share of tracked categories+products whose recent
    week-over-week average beat their baseline - real momentum, not a
    forecast."""
    shifts = analysis["trend_shifts"]["by_category"] + analysis["trend_shifts"]["by_product"]
    if not shifts:
        return {"score": 50, "level": _score_level(50), "trending_up": 0, "tracked": 0}
    up = sum(1 for s in shifts if s["pct_change"] > 0)
    score = round((up / len(shifts)) * 100)
    return {"score": score, "level": _score_level(score), "trending_up": up, "tracked": len(shifts)}


def revenue_opportunity_estimate(analysis: dict) -> dict:
    """Estimated monthly revenue if currently-out-of-stock products (which
    have real historical sales, proving demand) were restocked - uses each
    product's own pre-stockout daily rate from trend_shifts, not a guess."""
    stockouts = set(analysis["stockouts"])
    shifts_by_product = {s["name"]: s for s in analysis["trend_shifts"]["by_product"]}
    monthly_value = 0.0
    affected = 0
    for name in stockouts:
        shift = shifts_by_product.get(name)
        if shift:
            daily_rate = max(shift["baseline_avg_daily_revenue"], shift["recent_avg_daily_revenue"])
            monthly_value += daily_rate * 30
            affected += 1
    return {"estimated_monthly_value": round(monthly_value, 2), "products_affected": affected}


def customer_health_score(freq_trend: dict) -> dict:
    score = {"growing": 75, "flat": 55, "declining": 35}[freq_trend["direction"]]
    return {
        "score": score,
        "level": _score_level(score),
        "visit_frequency_trend": freq_trend["direction"],
        "avg_daily_transactions": freq_trend["avg_daily_transactions"],
        "note": "Proxy based on visit frequency - no customer-ID system exists to measure individual retention.",
    }


def risk_alerts(analysis: dict, currency: str) -> list[dict]:
    """Deterministic, threshold-based alerts - real numbers, no LLM, so
    there's no risk of a model inventing or missing a risk signal."""
    alerts = []
    summary = analysis["summary"]
    trend = analysis["trend"]
    cat_conc = analysis["concentration"]["by_category"]

    if summary["products_tracked"]:
        ratio = summary["stockouts"] / summary["products_tracked"]
        if ratio > 0.3:
            alerts.append({
                "severity": "high",
                "text": f"{summary['stockouts']} of {summary['products_tracked']} products ({round(ratio * 100)}%) are out of stock.",
            })
        elif summary["stockouts"] > 0:
            alerts.append({"severity": "medium", "text": f"{summary['stockouts']} product(s) currently out of stock."})

    if trend["direction"] == "declining" and trend["r_squared"] > 0.1:
        alerts.append({
            "severity": "high",
            "text": f"Revenue is declining at {currency}{abs(trend['slope_per_day']):,.2f}/day (trend fit R²={trend['r_squared']}).",
        })

    if cat_conc["level"].startswith("high"):
        alerts.append({
            "severity": "medium",
            "text": f"Revenue is highly concentrated by category (HHI={cat_conc['hhi']}) - a disruption to top categories would hit hard.",
        })

    if not alerts:
        alerts.append({"severity": "low", "text": "No major risk signals detected in the current data."})

    return alerts


def compute_scorecard(analysis: dict, sale_items: pd.DataFrame, currency: str) -> dict:
    if analysis["summary"]["transactions"] == 0:
        # The scoring formulas below lean on defaults (e.g. "flat" trend,
        # "n/a" concentration treated as low-risk) that are meant to be
        # neutral fallbacks within a real dataset - on NO data at all they'd
        # combine into a misleadingly decent-looking score instead of
        # honestly saying there's nothing to score yet.
        no_score = {"score": None, "level": "insufficient data"}
        return {
            "business_health": no_score,
            "growth": no_score,
            "revenue_opportunity": {"estimated_monthly_value": 0.0, "products_affected": 0},
            "customer_health": {**no_score, "visit_frequency_trend": "n/a", "avg_daily_transactions": 0.0, "note": "No transaction data available."},
            "risk_alerts": [{"severity": "low", "text": "No sales data available yet."}],
        }

    freq_trend = transaction_frequency_trend(sale_items)
    return {
        "business_health": business_health_score(analysis),
        "growth": growth_score(analysis),
        "revenue_opportunity": revenue_opportunity_estimate(analysis),
        "customer_health": customer_health_score(freq_trend),
        "risk_alerts": risk_alerts(analysis, currency),
    }


def analyze_dataset(sale_items: pd.DataFrame, products: pd.DataFrame, category_map: dict, currency: str = "$") -> dict:
    if sale_items.empty:
        empty_analysis = {
            "summary": {"revenue": 0.0, "transactions": 0, "products_tracked": int(len(products)), "stockouts": 0},
            "pareto": {"by_category": [], "by_product": []},
            "trend_shifts": {"recent_window_days": segregation.RECENT_WINDOW_DAYS, "by_category": [], "by_product": []},
            "seasonality": [],
            "trend": {"slope_per_day": 0.0, "direction": "flat", "r_squared": 0.0},
            "concentration": {"by_category": {"hhi": 0.0, "level": "n/a"}, "by_product": {"hhi": 0.0, "level": "n/a"}},
            "stockouts": [],
        }
        empty_analysis["scorecard"] = compute_scorecard(empty_analysis, sale_items, currency)
        return empty_analysis

    pareto = segregation.pareto(sale_items, category_map)
    trend_shifts = segregation.trend_shifts(sale_items, category_map)

    # sale_id is only unique per store (see central_data.py) - include
    # store_id in the dedup key when present (multi-location data) so
    # transactions from different shops don't collide on the same sale_id.
    transaction_key = ["store_id", "sale_id"] if "store_id" in sale_items.columns else ["sale_id"]
    transactions = len(sale_items.drop_duplicates(subset=transaction_key))
    stockout_rows = products[products["stock"] == 0] if not products.empty else products
    stockouts = stockout_rows["name"].tolist() if not stockout_rows.empty else []

    analysis = {
        "summary": {
            "revenue": round(float(sale_items["subtotal"].sum()), 2),
            "transactions": transactions,
            "products_tracked": int(products["barcode"].nunique()) if not products.empty else 0,
            "stockouts": len(stockouts),
        },
        "pareto": pareto,
        "trend_shifts": trend_shifts,
        "seasonality": weekday_seasonality(sale_items),
        "trend": linear_trend(sale_items),
        "concentration": {
            "by_category": concentration_index(pareto["by_category"]),
            "by_product": concentration_index(pareto["by_product"]),
        },
        "stockouts": stockouts,
    }
    analysis["scorecard"] = compute_scorecard(analysis, sale_items, currency)
    return analysis


def build_narrative(title: str, currency: str, analysis: dict) -> str:
    s = analysis["summary"]
    lines = [f"## {title}", ""]

    if s["transactions"] == 0:
        lines.append("No sales data available for this section.")
        return "\n".join(lines)

    lines.append(
        f"Revenue: {currency}{s['revenue']:,.2f} across {s['transactions']} transactions, "
        f"{s['products_tracked']} products tracked, {s['stockouts']} currently out of stock."
    )

    trend = analysis["trend"]
    lines.append(
        f"Revenue trend: {trend['direction']} "
        f"({currency}{trend['slope_per_day']:+,.2f}/day, fit R²={trend['r_squared']})."
    )

    top_categories = [c for c in analysis["pareto"]["by_category"] if c["top_performer"]]
    if top_categories:
        names = ", ".join(c["name"] for c in top_categories)
        lines.append(f"Top-performing categories (Pareto 80/20): {names}.")

    cat_conc = analysis["concentration"]["by_category"]
    if cat_conc["level"] != "n/a":
        lines.append(f"Category revenue concentration: {cat_conc['level']} (HHI={cat_conc['hhi']}).")

    movers = analysis["trend_shifts"]["by_product"][:3]
    if movers:
        parts = [f"{m['name']} ({m['pct_change']:+.1f}%)" for m in movers]
        lines.append(f"Biggest week-over-week product movers: {', '.join(parts)}.")

    if analysis["seasonality"]:
        best_day = max(analysis["seasonality"], key=lambda d: d["avg_revenue"])
        worst_day = min(analysis["seasonality"], key=lambda d: d["avg_revenue"])
        lines.append(
            f"Busiest day of week: {best_day['weekday']} (avg {currency}{best_day['avg_revenue']:,.2f}); "
            f"slowest: {worst_day['weekday']} (avg {currency}{worst_day['avg_revenue']:,.2f})."
        )

    if analysis["stockouts"]:
        preview = ", ".join(analysis["stockouts"][:5])
        more = f" and {len(analysis['stockouts']) - 5} more" if len(analysis["stockouts"]) > 5 else ""
        lines.append(f"Out of stock: {preview}{more}.")

    return "\n".join(lines)
