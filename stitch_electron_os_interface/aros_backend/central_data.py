import os
import sqlite3

import pandas as pd

CENTRAL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "HQ_Retail_OS", "central_hq.db")

# Only the Tamil Nadu simulator's catalog (barcode prefix "89") is treated as
# a "location" for insights purposes. This deliberately excludes STORE_001
# (the real POS's sync target) which uses a different barcode range and a
# different currency (USD) - summing the two would be meaningless.
TN_BARCODE_PREFIX = "89%"


def _connect():
    if not os.path.exists(CENTRAL_DB_PATH):
        raise FileNotFoundError(f"{CENTRAL_DB_PATH} not found.")
    return sqlite3.connect(f"file:{CENTRAL_DB_PATH}?mode=ro", uri=True)


def label_for_store(store_id: str) -> str:
    """DINDIGUL_001 -> Dindigul"""
    return store_id.rsplit("_", 1)[0].replace("_", " ").title()


def get_locations() -> pd.DataFrame:
    """One row per Tamil Nadu store that has a product catalog, with totals
    computed from its own sale_items (so it's always internally consistent -
    a store with no sales yet still shows up with revenue 0)."""
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT cp.store_id,
                   COUNT(DISTINCT csi.sale_id) AS transactions,
                   COALESCE(SUM(csi.subtotal), 0) AS revenue
            FROM central_products cp
            LEFT JOIN central_sale_items csi
                   ON csi.store_id = cp.store_id AND csi.product_id = cp.product_id
            WHERE cp.barcode LIKE ?
            GROUP BY cp.store_id
            ORDER BY revenue DESC
            """,
            conn,
            params=(TN_BARCODE_PREFIX,),
        )


def get_products(store_id: str | None = None) -> pd.DataFrame:
    query = "SELECT store_id, product_id, barcode, name, price, stock FROM central_products WHERE barcode LIKE ?"
    params = [TN_BARCODE_PREFIX]
    if store_id and store_id != "all":
        query += " AND store_id = ?"
        params.append(store_id)
    with _connect() as conn:
        return pd.read_sql(query, conn, params=params)


def get_sale_items(store_id: str | None = None) -> pd.DataFrame:
    """Line items joined to product name/barcode, optionally scoped to one
    store. Always restricted to the Tamil Nadu catalog (see TN_BARCODE_PREFIX)
    so an "all locations" aggregate never mixes currencies."""
    query = """
        SELECT csi.store_id, csi.sale_id, csi.quantity, csi.subtotal,
               cs.timestamp, cp.barcode, cp.name AS product_name
        FROM central_sale_items csi
        JOIN central_sales cs ON cs.store_id = csi.store_id AND cs.sale_id = csi.sale_id
        JOIN central_products cp ON cp.store_id = csi.store_id AND cp.product_id = csi.product_id
        WHERE cp.barcode LIKE ?
    """
    params = [TN_BARCODE_PREFIX]
    if store_id and store_id != "all":
        query += " AND csi.store_id = ?"
        params.append(store_id)
    with _connect() as conn:
        return pd.read_sql(query, conn, params=params, parse_dates=["timestamp"])
