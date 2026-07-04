"""Segregation engine: classical (non-LLM) analysis that turns raw line-item
sales history into insight-worthy signals, using the business's own
categories from the onboarding wizard.
"""

import pandas as pd

RECENT_WINDOW_DAYS = 7


def _with_category(sale_items: pd.DataFrame, category_map: dict) -> pd.DataFrame:
    df = sale_items.copy()
    df["category"] = df["barcode"].map(category_map)
    return df


def _ranked_with_cumulative(revenue_by_group: pd.Series) -> list[dict]:
    ranked = revenue_by_group.sort_values(ascending=False)
    total = ranked.sum()
    cumulative = ranked.cumsum() / total * 100 if total else ranked.cumsum()
    out = []
    crossed_80 = False
    for name, revenue in ranked.items():
        cum_pct = float(cumulative[name])
        is_top_performer = not crossed_80
        if cum_pct >= 80:
            crossed_80 = True
        out.append(
            {
                "name": name,
                "revenue": round(float(revenue), 2),
                "cumulative_pct": round(cum_pct, 1),
                "top_performer": is_top_performer,
            }
        )
    return out


def pareto(sale_items: pd.DataFrame, category_map: dict) -> dict:
    df = _with_category(sale_items, category_map)
    by_category = _ranked_with_cumulative(df.groupby("category")["subtotal"].sum())
    by_product = _ranked_with_cumulative(df.groupby("product_name")["subtotal"].sum())
    return {"by_category": by_category, "by_product": by_product}


def _window_avg_daily(df: pd.DataFrame, group_col: str) -> pd.Series:
    revenue = df.groupby(group_col)["subtotal"].sum()
    distinct_days = df["timestamp"].dt.date.nunique() or 1
    return revenue / distinct_days


def _trend_shifts_for(df: pd.DataFrame, group_col: str, cutoff) -> list[dict]:
    recent = df[df["timestamp"] >= cutoff]
    baseline = df[df["timestamp"] < cutoff]

    recent_avg = _window_avg_daily(recent, group_col)
    baseline_avg = _window_avg_daily(baseline, group_col)

    names = set(recent_avg.index) | set(baseline_avg.index)
    rows = []
    for name in names:
        r = float(recent_avg.get(name, 0.0))
        b = float(baseline_avg.get(name, 0.0))
        if b == 0:
            continue  # no baseline to compare against; not a "shift"
        pct_change = (r - b) / b * 100
        rows.append(
            {
                "name": name,
                "baseline_avg_daily_revenue": round(b, 2),
                "recent_avg_daily_revenue": round(r, 2),
                "pct_change": round(pct_change, 1),
            }
        )
    rows.sort(key=lambda row: abs(row["pct_change"]), reverse=True)
    return rows


def trend_shifts(sale_items: pd.DataFrame, category_map: dict) -> dict:
    df = _with_category(sale_items, category_map)
    max_date = df["timestamp"].max()
    cutoff = max_date.normalize() - pd.Timedelta(days=RECENT_WINDOW_DAYS - 1)
    return {
        "recent_window_days": RECENT_WINDOW_DAYS,
        "by_category": _trend_shifts_for(df, "category", cutoff),
        "by_product": _trend_shifts_for(df, "product_name", cutoff),
    }
