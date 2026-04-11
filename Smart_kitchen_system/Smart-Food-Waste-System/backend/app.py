from flask import Flask, request, render_template, redirect
import pandas as pd
import sqlite3
from datetime import datetime
import os
from sklearn.metrics.pairwise import cosine_similarity

import joblib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

risk_model = joblib.load(os.path.join(BASE_DIR, "../models/risk_model.pkl"))
encoder = joblib.load(os.path.join(BASE_DIR, "../models/encoder.pkl"))



# Load ML models
vectorizer = joblib.load("../models/tfidf_vectorizer.pkl")
tfidf_matrix = joblib.load("../models/tfidf_matrix.pkl")
recipes_df = joblib.load("../models/recipes_df.pkl")
app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
def get_category(item):
    item = item.lower()

    if item in ["milk", "curd", "paneer", "butter"]:
        return "Dairy Products"
    elif item in ["rice", "wheat flour", "oats"]:
        return "Grains & Cereals"
    elif item in ["chicken", "fish", "eggs"]:
        return "Meat & Seafood"
    elif item in ["juice", "tea", "coffee"]:
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

    conn.commit()
    conn.close()

init_db()

# -------------------------------
# NORMALIZE FUNCTION
# -------------------------------
def normalize_item(name):
    return name.strip().lower()

# -------------------------------
# HOME PAGE
# -------------------------------
@app.route("/")
def home():
    return render_template("upload.html")
def recommend_recipes(pantry_items, high_risk_items):

    pantry_text = " ".join(pantry_items)

    pantry_vec = vectorizer.transform([pantry_text])

    scores = cosine_similarity(pantry_vec, tfidf_matrix).flatten()

    # 🔥 Boost high-risk items
    for i, row in recipes_df.iterrows():
        if any(item in row["ingredients"] for item in high_risk_items):
            scores[i] += 0.3

    top_indices = scores.argsort()[-5:][::-1]

    return recipes_df.iloc[top_indices][
        ["recipe_name", "Cuisine", "URL", "image-url"]
    ]
# -------------------------------
# FILE UPLOAD
# -------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Read CSV
        df = pd.read_csv(filepath)

        # Normalize
        df["item"] = df["item"].apply(normalize_item)
        df["unit"] = df["unit"].str.lower()

        # Add purchase date (ML IMPORTANT)
        today = datetime.now().date()
        df["purchase_date"] = today

        # Insert into DB
        conn = sqlite3.connect("pantry.db")
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO pantry (item_name, quantity, unit, purchase_date)
                VALUES (?, ?, ?, ?)
            """, (row["item"], row["quantity"], row["unit"], row["purchase_date"]))

        conn.commit()
        conn.close()

        return redirect("/pantry")

    return "❌ Upload failed"

# -------------------------------
# VIEW PANTRY
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
        family_size = 4

        category = get_category(row["item_name"])
        category_encoded = encoder.transform([category])[0]

        pred = risk_model.predict([[family_size, quantity, days_old, category_encoded]])[0]

        # 🔹 Risk label
        if pred == 0:
            risks.append("LOW 🟢")
        elif pred == 1:
            risks.append("MEDIUM 🟡")
        else:
            risks.append("HIGH 🔴")

        # 🔥 ALERT LOGIC
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
@app.route("/recipes")
def recipes_page():

    # Load pantry data
    conn = sqlite3.connect("pantry.db")
    df = pd.read_sql_query("SELECT * FROM pantry", conn)
    conn.close()

    today = datetime.now().date()

    risks = []

    for _, row in df.iterrows():

        purchase_date = datetime.strptime(row["purchase_date"], "%Y-%m-%d").date()
        days_old = (today - purchase_date).days

        quantity = row["quantity"]
        family_size = 4

        category = get_category(row["item_name"])
        category_encoded = encoder.transform([category])[0]

        pred = risk_model.predict([[family_size, quantity, days_old, category_encoded]])[0]

        if pred == 2:
            risks.append("HIGH")
        elif pred == 1:
            risks.append("MEDIUM")
        else:
            risks.append("LOW")

    # 🔥 Pantry items
    pantry_items = df["item_name"].tolist()

    # 🔥 High risk items
    high_risk_items = [
        df.iloc[i]["item_name"] for i in range(len(df)) if risks[i] == "HIGH"
    ]

    # 🔥 Get recipes
    recipes = recommend_recipes(pantry_items, high_risk_items)

    return render_template("recipes.html", recipes=recipes.values)
# -------------------------------
# DELETE ITEM
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