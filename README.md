Smart Kitchen System (AI-Powered)

An intelligent AI-based Smart Kitchen Management System that helps users manage pantry items, reduce food waste, get recipe recommendations, track nutrition, and generate smart shopping alerts.

📌 Features
🥗 1. Pantry Management
Add items manually or via CSV upload
Tracks:
Item name
Quantity
Purchase date
Data stored using SQLite database
⚠️ 2. Food Waste Prediction (ML Model)

Predicts spoilage risk using:

Quantity
Days since purchase
Category

Models Used:

Decision Tree (Classification)
Random Forest (Classification)
🍲 3. Recipe Recommendation System
Uses TF-IDF + Cosine Similarity
Suggests recipes based on:
Pantry items
High-risk ingredients
Prioritizes recipes that help reduce food waste
🍳 4. Cooking Module
Allows users to cook selected recipes
Automatically updates pantry
Logs cooking activity
📊 5. Nutrition Tracker (ML-Based)

Predicts nutrition of dishes using:

TF-IDF + Random Forest Regression

Tracks:

Calories
Protein
Fat
Carbohydrates

Displays daily intake summary

🛒 6. Smart Shopping & Alerts
Spoilage Alerts
Based on shelf-life rules
Shopping Prediction
Uses cooking history (cooking_log)
Estimates consumption rate

Suggests:

Items to buy soon
🧠 Technologies Used
💻 Frontend
HTML
CSS
JavaScript
⚙️ Backend
Python
Flask
🗄 Database
SQLite
🤖 Machine Learning
Scikit-learn
TF-IDF Vectorizer
Random Forest
Decision Tree
📁 Project Structure

Smart-Food-Waste-System/

│
├── backend/
│ ├── app.py
│ ├── pantry.db
│ ├── utils.py
│ ├── recipe_models.py
│
├── models/
│ ├── risk_model.pkl
│ ├── dish_nutrition_model.pkl
│ ├── dish_vectorizer.pkl
│ ├── tfidf_vectorizer.pkl
│ ├── tfidf_matrix.pkl
│
├── data/
│ ├── dataset.csv
│ ├── final_recipes.csv
│ ├── wastage.csv
│
├── templates/
├── static/
├── requirements.txt
└── README.md

⚙️ Installation & Setup
1️⃣ Clone Repository

git clone https://github.com/your-username/smart-kitchen-system.git

cd smart-kitchen-system

2️⃣ Install Dependencies

pip install -r requirements.txt

3️⃣ Run Application

python app.py

4️⃣ Open in Browser

http://127.0.0.1:5000/

📊 Machine Learning Workflow
🔹 Waste Prediction Model

Input:

Quantity
Days since purchase
Category

Output:

Low / Medium / High Risk
🔹 Recipe Recommendation
TF-IDF on ingredient text
Cosine similarity for matching
🔹 Nutrition Prediction Model

Input: Dish name

Output:

Calories
Protein
Fat
Carbohydrates
🎯 Key Highlights

✔ End-to-end full-stack application
✔ Real-world ML integration
✔ Data-driven decision making
✔ User-friendly UI
✔ Scalable architecture

🎓 Use Cases
Reduce food wastage
Smart meal planning
Nutrition tracking
Automated grocery suggestions
🚀 Future Enhancements

📈 Time-series forecasting (Prophet / ARIMA)
📱 Mobile app integration
🔔 Email / push notifications
🧠 Deep learning-based recommendation system

👩‍💻 Author

Varsha
B.Tech AIML Student
SRET, Chennai


This project is for academic and learning purposes only.
