# ============================================
# SMART FOOD WASTE SYSTEM (PERSISTENT + AUTO)
# ============================================

from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np
from datetime import datetime
import json
import os
from recipe_models import recommend_recipes

# --------------------------------------------
# APP CONFIG
# --------------------------------------------
app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# --------------------------------------------
# LOAD MODELS
# --------------------------------------------
waste_model = joblib.load("../models/waste_model.pkl")
encoder = joblib.load("../models/encoder.pkl")

# --------------------------------------------
# FILE STORAGE
# --------------------------------------------
DATA_FILE = "pantry.json"

# Load pantry if exists
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        PANTRY = json.load(f)
else:
    PANTRY = []

# Save pantry
def save_pantry():
    with open(DATA_FILE, "w") as f:
        json.dump(PANTRY, f)

# --------------------------------------------
# FOOD CATEGORY MAP
# --------------------------------------------
FOOD_MAP = {
    "apple": "Fruits & Vegetables",
    "banana": "Fruits & Vegetables",
    "milk": "Dairy Products",
    "bread": "Bakery Items",
    "rice": "Grains & Cereals",
    "chicken": "Meat & Seafood",
    "fish": "Meat & Seafood",
    "juice": "Beverages",
    "pizza": "Prepared Food"
}

EXPIRY_MAP = {
    "Fruits & Vegetables": 5,
    "Dairy Products": 3,
    "Bakery Items": 4,
    "Meat & Seafood": 2,
    "Prepared Food": 2,
    "Beverages": 7,
    "Grains & Cereals": 30
}
# --------------------------------------------
# HOME
# --------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# Module 1
@app.route("/pantry")
def pantry():
    return render_template("pantry.html")

# Module 2
@app.route("/recipes")
def recipes():
    return render_template("recipes.html")

# Future modules (optional placeholders)
@app.route("/shopping")
def shopping():
    return "<h2>Coming Soon 🚀</h2>"

@app.route("/nutrition")
def nutrition():
    return "<h2>Coming Soon 🚀</h2>"

# --------------------------------------------
# ADD ITEM
# --------------------------------------------
@app.route("/add_item", methods=["POST"])
def add_item():

    try:
        data = request.get_json()

        name = data.get("name", "").lower()
        quantity = float(data.get("quantity", 0))
        family_size = float(data.get("family_size", 0))

        # ❌ validation
        if not name or quantity <= 0 or family_size <= 0:
            return jsonify({"error": "Invalid input"}), 400

        category = FOOD_MAP.get(name, "Prepared Food")

        item = {
            "name": name,
            "category": category,
            "quantity": quantity,
            "family_size": family_size,
            "date_added": datetime.now().strftime("%Y-%m-%d")
        }

        PANTRY.append(item)
        save_pantry()

        return jsonify({"message": "Added"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/delete_item/<int:index>", methods=["POST"])
def delete_item(index):
    try:
        if 0 <= index < len(PANTRY):
            PANTRY.pop(index)
            save_pantry()
            return jsonify({"message": "Deleted"})
        else:
            return jsonify({"error": "Invalid index"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --------------------------------------------
# GET PANTRY (AUTO CALCULATED)
# --------------------------------------------
@app.route("/get_pantry")
def get_pantry():

    result = []

    for item in PANTRY:

        # Calculate storage days
        added_date = datetime.strptime(item["date_added"], "%Y-%m-%d")
        storage_days = (datetime.now() - added_date).days

        # Encode
        item_encoded = encoder.transform([item["category"]])[0]

        features = np.array([[
            item["family_size"],
            item["quantity"],
            storage_days,
            item_encoded
        ]])

        # Predict waste
        waste = waste_model.predict(features)[0]
        waste = max(0, waste)

        # Rule-based risk
        ratio = waste / item["quantity"]

        if ratio < 0.3:
            risk = "LOW"
        elif ratio <= 0.6:
            risk = "MEDIUM"
        else:
            risk = "HIGH"
        expiry_days = EXPIRY_MAP.get(item["category"], 5)

        days_left = expiry_days - storage_days

        if days_left <= 0:
            alert = "EXPIRED"
        elif days_left <= 2:
            alert = "USE SOON"
        else:
            alert = "FRESH"

        result.append({
            "name": item["name"],
            "category": item["category"],
            "quantity": item["quantity"],
            "days": storage_days,
            "waste": round(float(waste), 2),
            "risk": risk,
             "expiry": alert
        })

    return jsonify(result)
@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.get_json()
    pantry = data.get("pantry", [])

    print("PANTRY RECEIVED:", pantry)   # 👈 ADD THIS

    recipes = recommend_recipes(pantry)

    print("RECIPES:", recipes)          # 👈 ADD THIS

    return jsonify({"recipes": recipes})

# --------------------------------------------
# CLEAR PANTRY
# --------------------------------------------
@app.route("/clear_pantry", methods=["POST"])
def clear():
    PANTRY.clear()
    save_pantry()
    return jsonify({"message": "cleared"})

# --------------------------------------------
# RUN
# --------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)