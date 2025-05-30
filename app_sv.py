from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

@app.route("/")
def index():
    return render_template("index_sv.html")

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
