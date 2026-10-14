from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import json
import qrcode
from io import BytesIO
import base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB_PATH = os.path.join(os.path.dirname(__file__), "queueless.db")

PRODUCTS = [
    (1, "Rice 1 kg", "Groceries", 68.00, "RICE001"),
    (2, "Milk 500 ml", "Dairy", 28.00, "MILK002"),
    (3, "Bread", "Bakery", 35.00, "BREAD003"),
    (4, "Apples 1 kg", "Fruits", 120.00, "APPLE004"),
    (5, "Shampoo", "Personal Care", 99.00, "SHAMP005"),
    (6, "Toothpaste", "Personal Care", 55.00, "PASTE006"),
    (7, "Eggs (6 pack)", "Dairy", 48.00, "EGG007"),
    (8, "Biscuits", "Snacks", 20.00, "BISC008"),
    (9, "Cooking Oil 1 L", "Groceries", 145.00, "OIL009"),
    (10, "Bananas 1 dozen", "Fruits", 60.00, "BANA010"),
]

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                code TEXT UNIQUE NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO products (id, name, category, price, code) VALUES (?, ?, ?, ?, ?)",
                PRODUCTS
            )

def get_products():
    with connect_db() as conn:
        return conn.execute("SELECT * FROM products ORDER BY name").fetchall()

def get_cart_details():
    cart = session.get("cart", {})
    products = {str(p["id"]): p for p in get_products()}
    items = []
    total = 0
    for product_id, qty in cart.items():
        product = products.get(str(product_id))
        if product and int(qty) > 0:
            subtotal = float(product["price"]) * int(qty)
            items.append({
                "id": product["id"], "name": product["name"],
                "category": product["category"], "price": float(product["price"]),
                "code": product["code"], "qty": int(qty), "subtotal": subtotal
            })
            total += subtotal
    return items, round(total, 2)

def make_qr_data_uri(data):
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

@app.route("/")
def index():
    products = get_products()
    category = request.args.get("category", "All")
    search = request.args.get("q", "").strip().lower()
    if category != "All":
        products = [p for p in products if p["category"] == category]
    if search:
        products = [p for p in products if search in p["name"].lower() or search in p["code"].lower()]
    categories = sorted({p["category"] for p in get_products()})
    cart_count = sum(int(q) for q in session.get("cart", {}).values())
    return render_template("index.html", products=products, categories=categories,
                           selected_category=category, search=search, cart_count=cart_count)

@app.route("/add/<int:product_id>", methods=["POST"])
def add(product_id):
    valid_ids = {p["id"] for p in get_products()}
    if product_id not in valid_ids:
        flash("Product not found.", "error")
        return redirect(url_for("index"))
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = int(cart.get(key, 0)) + 1
    session["cart"] = cart
    flash("Product added to your cart.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/scan", methods=["POST"])
def scan():
    code = request.form.get("code", "").strip().upper()
    with connect_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE UPPER(code)=?", (code,)).fetchone()
    if not product:
        flash("No product found for that QR/product code.", "error")
        return redirect(url_for("index"))
    cart = session.get("cart", {})
    key = str(product["id"])
    cart[key] = int(cart.get(key, 0)) + 1
    session["cart"] = cart
    flash(f'{product["name"]} added using product code.', "success")
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    items, total = get_cart_details()
    return render_template("cart.html", items=items, total=total)

@app.route("/update/<int:product_id>", methods=["POST"])
def update(product_id):
    try:
        qty = int(request.form.get("qty", "1"))
    except ValueError:
        qty = 1
    cart_data = session.get("cart", {})
    if qty <= 0:
        cart_data.pop(str(product_id), None)
    else:
        cart_data[str(product_id)] = min(qty, 99)
    session["cart"] = cart_data
    return redirect(url_for("cart"))

@app.route("/remove/<int:product_id>", methods=["POST"])
def remove(product_id):
    cart_data = session.get("cart", {})
    cart_data.pop(str(product_id), None)
    session["cart"] = cart_data
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = get_cart_details()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        order_json = json.dumps(items)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with connect_db() as conn:
            cursor = conn.execute(
                "INSERT INTO orders (items_json, total, created_at) VALUES (?, ?, ?)",
                (order_json, total, created_at)
            )
            order_id = cursor.lastrowid
        payload = json.dumps({"order_id": order_id, "total": total, "status": "PAYMENT_PENDING"})
        qr_data = make_qr_data_uri(payload)
        session["cart"] = {}
        return render_template("receipt.html", order_id=order_id, items=items, total=total,
                               created_at=created_at, qr_data=qr_data)
    return render_template("checkout.html", items=items, total=total)

@app.route("/orders")
def orders():
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50").fetchall()
    return render_template("orders.html", orders=rows)

@app.route("/recommendations")
def recommendations():
    items, _ = get_cart_details()
    categories_in_cart = {item["category"] for item in items}
    products = get_products()
    # Simple content-based recommendation demo: suggest items from categories not yet in cart.
    suggested = [p for p in products if p["category"] not in categories_in_cart][:6]
    if len(suggested) < 6:
        suggested += [p for p in products if p not in suggested][:6-len(suggested)]
    return render_template("recommendations.html", products=suggested)

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
