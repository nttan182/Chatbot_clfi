from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
app = Flask(__name__, static_folder='public')
# file_path = "data/standardization.txt"

@app.route("/")
def index():
    return render_template("index_sv.html")
def load_standardization(file_path):
    standardization_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                values = [v.strip() for v in parts[1].split(',')]
                standardization_dict[key] = values
    return standardization_dict
def normalize_text(text, standardization_dict):
    normalized_text = text.lower()  # Chuyển về chữ thường để xử lý nhất quán
    for standard, variants in standardization_dict.items():
        for variant in variants:
            normalized_text = normalized_text.replace(variant.lower(), standard.lower())
    return normalized_text
@app.route("/send_message", methods=["POST"])
def send_message():
    user_message = request.form.get("message")
    payload = {"sender": "user", "message": user_message}

    try:
        response = requests.post(RASA_URL, json=payload)
        bot_response = response.json()

        messages = [msg.get("text", "") for msg in bot_response]
        return jsonify({"responses": messages})
    except Exception as e:
        return jsonify({"responses": [f"Lỗi: {str(e)}"]})

if __name__ == "__main__":
    app.run(debug=True)
