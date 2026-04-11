from flask import Flask, request, render_template, redirect
import pandas as pd
import sqlite3
from datetime import datetime
import os
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import sqlite3
import pandas as pd
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Shelf life (in days)
shelf_life_map = {
    "milk": 3,
    "curd": 5,
    "paneer": 4,
    "rice": 180,
    "onion": 10,
    "tomato": 5,
    "potato": 15,
    "chicken": 2,
    "fish": 2,
    "egg": 7
}
# -------------------------------
# PATH SETUP
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load ML models
risk_model = joblib.load(os.path.join(BASE_DIR, "../models/risk_model.pkl"))
encoder = joblib.load(os.path.join(BASE_DIR, "../models/encoder.pkl"))
nutrition_model = joblib.load("../models/dish_nutrition_model.pkl")
# 🔥 Nutrition ML model

nutrition_vectorizer = joblib.load("../models/dish_vectorizer.pkl")

# 🔥 Recommender model
tfidf_vectorizer = joblib.load(os.path.join(BASE_DIR, "../models/tfidf_vectorizer.pkl"))
tfidf_matrix = joblib.load(os.path.join(BASE_DIR, "../models/tfidf_matrix.pkl"))
recipes_df = joblib.load(os.path.join(BASE_DIR, "../models/recipes_df.pkl"))

# Flask setup
app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# CATEGORY FUNCTION
# -------------------------------
def check_inventory():

    conn = sqlite3.connect("pantry.db")
    df = pd.read_sql_query("SELECT * FROM pantry", conn)
    conn.close()

    alerts = []
    shopping_list = []

    for _, row in df.iterrows():

        item = row["item_name"]
        qty = row["quantity"]

        # ---------------- SPOILAGE ----------------
        purchase_date = datetime.strptime(row["purchase_date"], "%Y-%m-%d")
        days = (datetime.now() - purchase_date).days

        shelf_life = shelf_life_map.get(item, 5)

        if days > shelf_life:
            alerts.append(f"⚠️ {item} may be spoiled!")

        # ---------------- ML-BASED CONSUMPTION ----------------
        avg_use = get_avg_consumption(item)

        if avg_use > 0:
            days_left = qty / avg_use
        else:
            days_left = 10

        if days_left < 3:
            shopping_list.append(f"🛒 Buy {item} in {int(days_left)} days")

    return alerts, shopping_list
def scheduled_job():
    alerts, shopping = check_inventory()
    print("Daily Alerts:", alerts)
    print("Shopping List:", shopping)


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'interval', days=1)
scheduler.start()
def get_category(item):
    item = item.lower()

    if item in ["milk", "curd", "paneer", "butter"]:
        return "Dairy Products"
    elif item in ["rice", "wheat flour", "oats"]:
        return "Grains & Cereals"
    elif item in ["chicken", "fish", "eggs"]:
        return "Meat & Seafood"
    elif item in ["tea", "coffee"]:
        return "Beverages"
    else:
        return "Fruits & Vegetables"

# -------------------------------
# DATABASE SETUP
# -------------------------------
def init_db():
    conn = sqlite3.connect("pantry.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity REAL,
            unit TEXT,
            purchase_date DATE
        )
    """)

    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_nutrition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    recipe_name TEXT,
    calories REAL,
    protein REAL,
    fat REAL,
    carbs REAL
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS cooking_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_name TEXT,
    item TEXT,
    quantity_used REAL,
    cooked_on DATE
)
""")

    conn.commit()
    conn.close()

init_db()

# -------------------------------
# NORMALIZE
# -------------------------------
def get_avg_consumption(item):

    conn = sqlite3.connect("pantry.db")

    df = pd.read_sql_query("""
        SELECT * FROM cooking_log
        WHERE item = ?
    """, conn, params=(item,))

    conn.close()

    if df.empty:
        return 0.3   # fallback

    df["cooked_on"] = pd.to_datetime(df["cooked_on"])

    # group by day
    daily = df.groupby("cooked_on")["quantity_used"].sum()

    return daily.mean()
def normalize_item(name):
    return name.strip().lower()

# -------------------------------
# HOME
# -------------------------------
@app.route("/")
def home():
    return render_template("upload.html")

# -------------------------------
# RECOMMENDER
# -------------------------------
def recommend_recipes(pantry_items, high_risk_items):

    pantry_text = " ".join(pantry_items)
    pantry_vec = tfidf_vectorizer.transform([pantry_text])

    scores = cosine_similarity(pantry_vec, tfidf_matrix).flatten()

    for i, row in recipes_df.iterrows():
        if any(item in row["ingredients"] for item in high_risk_items):
            scores[i] += 0.3

    top_indices = scores.argsort()[-5:][::-1]

    return recipes_df.iloc[top_indices][
        ["recipe_name", "Cuisine", "URL", "image-url"]
    ]

# -------------------------------
# UPLOAD CSV
# -------------------------------
@app.route("/nutrition")
def nutrition_page():

    conn = sqlite3.connect("pantry.db")

    df = pd.read_sql_query("""
        SELECT * FROM daily_nutrition
        WHERE date = date('now')
    """, conn)

    conn.close()

    # ---------------- TOTAL CALC ----------------
    total = df[["calories","protein","fat","carbs"]].sum()

    return render_template(
        "nutrition.html",
        items=df.values,
        total_cal=round(total["calories"],2),
        total_pro=round(total["protein"],2),
        total_fat=round(total["fat"],2),
        total_carbs=round(total["carbs"],2)
    )
@app.route("/shopping")
def shopping():

    alerts, shopping_list = check_inventory()

    return render_template(
        "shopping.html",
        alerts=alerts,
        shopping_list=shopping_list
    )
@app.route("/cook", methods=["POST"])
def cook_recipe():

    recipe_name = request.form["recipe_name"]

    # ---------------- ML PREDICTION ----------------
    dish_input = [recipe_name.lower()]
    vec = nutrition_vectorizer.transform(dish_input)
    prediction = nutrition_model.predict(vec)[0]

    calories = round(prediction[0], 2)
    protein = round(prediction[1], 2)
    fat = round(prediction[2], 2)
    carbs = round(prediction[3], 2)

    # ---------------- STORE IN DB ----------------
    conn = sqlite3.connect("pantry.db")
    cursor = conn.cursor()

    today = datetime.now().date()

    cursor.execute("""
        INSERT INTO daily_nutrition (date, recipe_name, calories, protein, fat, carbs)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (today, recipe_name, calories, protein, fat, carbs))
    # Example (you can later connect with recipe ingredients)
    cursor.execute("""
INSERT INTO cooking_log (recipe_name, item, quantity_used, cooked_on)
VALUES (?, ?, ?, ?)
""", (recipe_name, "rice", 0.2, today))

    conn.commit()
    conn.close()

    # 👉 Redirect to tracker page
    return redirect("/nutrition")
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_csv(filepath)

        # 🔥 FIXED COLUMN NAME
        df["item_name"] = df["item_name"].apply(normalize_item)
        df["unit"] = df["unit"].str.lower()

        today = datetime.now().date()
        df["purchase_date"] = today

        conn = sqlite3.connect("pantry.db")
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO pantry (item_name, quantity, unit, purchase_date)
                VALUES (?, ?, ?, ?)
            """, (row["item_name"], row["quantity"], row["unit"], row["purchase_date"]))

        conn.commit()
        conn.close()

        return redirect("/pantry")

    return "Upload failed"

# -------------------------------
# PANTRY VIEW
# -------------------------------

@app.route("/pantry")
def view_pantry():
    conn = sqlite3.connect("pantry.db")
    df = pd.read_sql_query("SELECT * FROM pantry", conn)
    conn.close()

    today = datetime.now().date()

    risks = []
    alerts = []

    for _, row in df.iterrows():
        purchase_date = datetime.strptime(row["purchase_date"], "%Y-%m-%d").date()
        days_old = (today - purchase_date).days

        quantity = row["quantity"]
        category = get_category(row["item_name"])
        category_encoded = encoder.transform([category])[0]

        pred = risk_model.predict([[4, quantity, days_old, category_encoded]])[0]

        if pred == 0:
            risks.append("LOW 🟢")
        elif pred == 1:
            risks.append("MEDIUM 🟡")
        else:
            risks.append("HIGH 🔴")

        if pred == 2:
            alerts.append("⚠ Use Today")
        elif pred == 1:
            alerts.append("⏳ Use Soon")
        elif quantity < 1:
            alerts.append("🛒 Low Stock")
        elif days_old > 5:
            alerts.append("🚨 May Spoil")
        else:
            alerts.append("✅ Safe")

    df["risk"] = risks
    df["alert"] = alerts

    return render_template("pantry.html", items=df.values)

# -------------------------------
# RECIPES PAGE
# -------------------------------
@app.route("/recipes")
def recipes_page():
    conn = sqlite3.connect("pantry.db")
    df = pd.read_sql_query("SELECT * FROM pantry", conn)
    conn.close()

    pantry_items = df["item_name"].tolist()

    # 🔥 HANDLE EMPTY PANTRY FIRST
    if not pantry_items:
        return render_template(
            "recipes.html",
            recipes=[],
            message="⚠️ Pantry is empty! Add items to get recommendations."
        )

    high_risk_items = []
    today = datetime.now().date()

    for _, row in df.iterrows():
        purchase_date = datetime.strptime(row["purchase_date"], "%Y-%m-%d").date()
        days_old = (today - purchase_date).days

        category = get_category(row["item_name"])
        category_encoded = encoder.transform([category])[0]

        pred = risk_model.predict([[4, row["quantity"], days_old, category_encoded]])[0]

        if pred == 2:
            high_risk_items.append(row["item_name"])

    recipes = recommend_recipes(pantry_items, high_risk_items)

    return render_template(
        "recipes.html",
        recipes=recipes.values,
        message=None
    )
# -------------------------------
# 🍳 COOK ROUTE (NEW MODULE)
# -------------------------------


# -------------------------------
# DELETE
# -------------------------------
@app.route("/delete/<int:item_id>")
def delete_item(item_id):
    conn = sqlite3.connect("pantry.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM pantry WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

    return redirect("/pantry")

# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)