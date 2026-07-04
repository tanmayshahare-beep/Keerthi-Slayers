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


def analyze_dataset(sale_items: pd.DataFrame, products: pd.DataFrame, category_map: dict) -> dict:
    if sale_items.empty:
        return {
            "summary": {"revenue": 0.0, "transactions": 0, "products_tracked": int(len(products)), "stockouts": 0},
            "pareto": {"by_category": [], "by_product": []},
            "trend_shifts": {"recent_window_days": segregation.RECENT_WINDOW_DAYS, "by_category": [], "by_product": []},
            "seasonality": [],
            "trend": {"slope_per_day": 0.0, "direction": "flat", "r_squared": 0.0},
            "concentration": {"by_category": {"hhi": 0.0, "level": "n/a"}, "by_product": {"hhi": 0.0, "level": "n/a"}},
            "stockouts": [],
        }

    pareto = segregation.pareto(sale_items, category_map)
    trend_shifts = segregation.trend_shifts(sale_items, category_map)

    # sale_id is only unique per store (see central_data.py) - include
    # store_id in the dedup key when present (multi-location data) so
    # transactions from different shops don't collide on the same sale_id.
    transaction_key = ["store_id", "sale_id"] if "store_id" in sale_items.columns else ["sale_id"]
    transactions = len(sale_items.drop_duplicates(subset=transaction_key))
    stockout_rows = products[products["stock"] == 0] if not products.empty else products
    stockouts = stockout_rows["name"].tolist() if not stockout_rows.empty else []

    return {
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
