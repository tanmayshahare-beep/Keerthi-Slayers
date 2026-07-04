import sqlite3
import random
import datetime

# --- 1. Connect to the POS Database ---
conn = sqlite3.connect('pos_system.db')
cursor = conn.cursor()

# --- 2. Clear existing data (reset simulation) ---
print("Clearing old data...")
cursor.execute("DELETE FROM sale_items;")
cursor.execute("DELETE FROM sales;")
cursor.execute("DELETE FROM products;")

# --- 3. Define Grocery Product Catalog ---
# Format: (barcode, name, price, initial_stock)
products = [
    ("4011", "Bananas (per lb)", 0.69, 150),
    ("4022", "Avocado (each)", 1.29, 60),
    ("4032", "Apple - Gala (per lb)", 1.49, 100),
    ("4045", "Lettuce - Iceberg", 1.99, 40),
    ("4050", "Tomatoes (per lb)", 1.79, 80),
    ("4100", "Milk - 2% (1 gal)", 3.99, 75),
    ("4111", "Eggs - Large (dozen)", 4.99, 50),
    ("4122", "Bread - White", 2.49, 45),
    ("4133", "Chicken Breast (per lb)", 5.99, 60),
    ("4144", "Ground Beef (per lb)", 6.49, 55),
    ("4155", "Cheddar Cheese (8oz)", 3.49, 40),
    ("4166", "Butter - Salted (1lb)", 4.29, 35),
    ("4177", "Orange Juice (52oz)", 3.89, 30),
    ("4188", "Coca Cola (12pk)", 7.49, 45),
    ("4199", "Potato Chips (family size)", 3.99, 60),
    ("4200", "Peanut Butter (18oz)", 2.99, 40),
    ("4211", "Jelly - Strawberry (16oz)", 3.49, 30),
    ("4222", "Pasta - Spaghetti (1lb)", 1.29, 80),
    ("4233", "Pasta Sauce - Marinara (24oz)", 2.99, 50),
    ("4244", "Rice - White (5lb)", 4.49, 35),
    ("4255", "Paper Towels (6 roll)", 6.99, 25),
    ("4266", "Toilet Paper (12 roll)", 8.99, 30),
    ("4277", "Dish Soap (18oz)", 2.49, 20),
    ("4288", "Laundry Detergent (50oz)", 12.99, 15),
    ("4299", "Canned Soup - Chicken (10oz)", 1.49, 100),
]

print(f"Inserting {len(products)} products...")
cursor.executemany("""
    INSERT INTO products (barcode, name, price, stock) 
    VALUES (?, ?, ?, ?)
""", products)

# --- 4. Simulate 30 Days of Sales History ---
print("Simulating 30 days of sales transactions...")
start_date = datetime.datetime.now() - datetime.timedelta(days=30)
product_data = cursor.execute("SELECT id, price FROM products").fetchall()

for day_offset in range(30):
    current_day = start_date + datetime.timedelta(days=day_offset)
    
    # Each day, generate between 20 and 50 transactions
    num_transactions = random.randint(20, 50)
    
    for _ in range(num_transactions):
        num_items = random.randint(1, 5)
        total_amount = 0.0
        sale_items = []  # Store (product_id, quantity, subtotal)
        
        for _ in range(num_items):
            prod_id, price = random.choice(product_data)
            quantity = random.randint(1, 3)
            subtotal = round(price * quantity, 2)
            total_amount += subtotal
            sale_items.append((prod_id, quantity, subtotal))
        
        total_amount = round(total_amount, 2)
        
        # Insert the Sales Header
        cursor.execute("""
            INSERT INTO sales (timestamp, total_amount) 
            VALUES (?, ?)
        """, (current_day.isoformat(), total_amount))
        
        sale_id = cursor.lastrowid
        
        # --- FIXED: Insert Sale Items with 'subtotal' column ---
        for prod_id, quantity, subtotal in sale_items:
            cursor.execute("""
                INSERT INTO sale_items (sale_id, product_id, quantity, subtotal) 
                VALUES (?, ?, ?, ?)
            """, (sale_id, prod_id, quantity, subtotal))
            
            # Deduct stock
            cursor.execute("""
                UPDATE products 
                SET stock = stock - ? 
                WHERE id = ?
            """, (quantity, prod_id))

# --- 6. Ensure no stock goes negative ---
cursor.execute("UPDATE products SET stock = 0 WHERE stock < 0")

# Commit everything
conn.commit()

# --- 7. Verification Report ---
cursor.execute("SELECT COUNT(*) FROM products")
product_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM sales")
sales_count = cursor.fetchone()[0]
cursor.execute("SELECT SUM(stock) FROM products")
total_stock = cursor.fetchone()[0] or 0

print("\n===== SEEDING COMPLETE =====")
print(f"✅ {product_count} products inserted.")
print(f"✅ {sales_count} sales transactions simulated.")
print(f"📦 Total remaining stock across all items: {total_stock} units.")
print("🚀 You can now open Hegxib POS and run your OS connector.")

conn.close()