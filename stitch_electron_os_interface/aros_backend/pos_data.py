import os
import sqlite3

import pandas as pd

POS_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pos-system", "pos_system.db")


def _connect():
    if not os.path.exists(POS_DB_PATH):
        raise FileNotFoundError(
            f"{POS_DB_PATH} not found. Seed it first: cd pos-system && "
            "python3 -c \"from database import POSDatabase; POSDatabase()\" && python3 seed_data.py"
        )
    return sqlite3.connect(f"file:{POS_DB_PATH}?mode=ro", uri=True)


def get_products() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql("SELECT id, barcode, name, price, stock FROM products ORDER BY name", conn)


def get_sale_items() -> pd.DataFrame:
    """One row per line item, joined to its sale timestamp and product barcode/name."""
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT si.id, si.sale_id, si.quantity, si.subtotal,
                   s.timestamp,
                   p.id AS product_id, p.barcode, p.name AS product_name
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN products p ON p.id = si.product_id
            """,
            conn,
            parse_dates=["timestamp"],
        )


def get_recent_sales(limit: int = 15) -> pd.DataFrame:
    """Most recent transactions with their item count. Note: customer_name is
    almost always "Guest" in this dataset (no loyalty/customer-ID system
    exists yet) - this is transaction activity, not a per-customer view."""
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT s.id, s.timestamp, s.total_amount, s.customer_name,
                   COUNT(si.id) AS item_count
            FROM sales s
            LEFT JOIN sale_items si ON si.sale_id = s.id
            GROUP BY s.id
            ORDER BY s.timestamp DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
            parse_dates=["timestamp"],
        )
