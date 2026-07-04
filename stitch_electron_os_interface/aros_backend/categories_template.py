"""Suggested starting categories for the onboarding wizard.

Keyed by barcode (stable, unique in pos-system/products) rather than product
name. This is only a prefilled suggestion -- the user can rename groups or
reassign products in the wizard before POSTing the final assignments.
"""

SUGGESTED_TEMPLATE = {
    "Produce & Bakery": [
        "4011",  # Bananas (per lb)
        "4022",  # Avocado (each)
        "4032",  # Apple - Gala (per lb)
        "4045",  # Lettuce - Iceberg
        "4050",  # Tomatoes (per lb)
        "4122",  # Bread - White
    ],
    "Dairy, Meat & Deli": [
        "4100",  # Milk - 2% (1 gal)
        "4111",  # Eggs - Large (dozen)
        "4133",  # Chicken Breast (per lb)
        "4144",  # Ground Beef (per lb)
        "4155",  # Cheddar Cheese (8oz)
        "4166",  # Butter - Salted (1lb)
        "4177",  # Orange Juice (52oz)
    ],
    "Pantry & Household": [
        "4188",  # Coca Cola (12pk)
        "4199",  # Potato Chips (family size)
        "4200",  # Peanut Butter (18oz)
        "4211",  # Jelly - Strawberry (16oz)
        "4222",  # Pasta - Spaghetti (1lb)
        "4233",  # Pasta Sauce - Marinara (24oz)
        "4244",  # Rice - White (5lb)
        "4255",  # Paper Towels (6 roll)
        "4266",  # Toilet Paper (12 roll)
        "4277",  # Dish Soap (18oz)
        "4288",  # Laundry Detergent (50oz)
        "4299",  # Canned Soup - Chicken (10oz)
    ],
}


def suggested_assignments() -> dict:
    """Flatten to {barcode: category_name}."""
    return {
        barcode: category
        for category, barcodes in SUGGESTED_TEMPLATE.items()
        for barcode in barcodes
    }
