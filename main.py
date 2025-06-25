from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, db
import os

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")  # 放你 Firebase JSON 私鑰
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-database.firebaseio.com'  # 改成你實際網址
})

@app.route("/")
def home():
    return "Firebase webhook running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    # Save data to Firebase Realtime DB
    ref = db.reference('/webhook_data')
    ref.push(data)

    return jsonify({"status": "success", "data": data}), 200

if __name__ == "__main__":
    app.run(debug=True)
