import joblib
import pandas as pd
import os
from sklearn.neighbors import NearestNeighbors

BASE_DIR = os.path.dirname(__file__)

model = joblib.load(os.path.join(BASE_DIR, "../models/recipe_knn.pkl"))
vectorizer = joblib.load(os.path.join(BASE_DIR, "../models/tfidf_vectorizer.pkl"))

df = pd.read_csv(os.path.join(BASE_DIR, "../data/final_recipes.csv"))


def recommend_recipes(pantry_items, top_n=5):

    pantry_items = [item.lower() for item in pantry_items]

    pantry_str = " ".join(pantry_items)
    pantry_vec = vectorizer.transform([pantry_str])

    distances, indices = model.kneighbors(pantry_vec)

    results = []

    for idx, dist in zip(indices[0], distances[0]):

        recipe_name = df.iloc[idx]["recipe_name"]
        ingredients = df.iloc[idx]["ingredients"].lower()

        # ✅ STRICT MATCH
        match_count = sum(
            1 for item in pantry_items if f" {item} " in f" {ingredients} "
        )

        # ✅ KEEP ONLY VALID RECIPES
        if match_count >= 1:
            results.append((recipe_name, dist))

    # ❌ if nothing matched → fallback
    if len(results) == 0:
        return ["No suitable recipes found"]

    # sort by similarity
    results = sorted(results, key=lambda x: x[1])

    return [r[0] for r in results[:top_n]]