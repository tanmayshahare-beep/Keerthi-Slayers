"""Category mapping for the Tamil Nadu multi-shop catalog
(pos-system/tamil_nadu_local_simulator.py).

Barcodes in that catalog are shaped 89-0-<category digit>-<item number>, so
the category is derivable straight from the barcode rather than needing a
hand-maintained table that drifts out of sync with the product list.
"""

CATEGORY_BY_DIGIT = {
    "1": "Staples & Grains",
    "2": "Vegetables & Fruits",
    "3": "Dairy & Beverages",
    "4": "Masalas & Spices",
    "5": "Snacks & Packaged Foods",
    "6": "Household & Personal Care",
}


def category_for_barcode(barcode: str) -> str:
    if not barcode or len(barcode) < 4:
        return "Uncategorized"
    return CATEGORY_BY_DIGIT.get(barcode[3], "Uncategorized")


def build_category_map(barcodes) -> dict:
    return {barcode: category_for_barcode(barcode) for barcode in barcodes}
