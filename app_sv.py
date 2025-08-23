from uuid import uuid4
from flask import Flask, render_template, request, jsonify, session
import requests

from utils.word_replacer import load_replacement_data, replace_words, load_stopwords

app = Flask(__name__, static_folder='public')
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

@app.route("/")
def index():
    return render_template("index_sv.html")

@app.route("/send_message", methods=["POST"])
def send_message():
    sender_id = request.form.get("sender_id")
    replacements = load_replacement_data('data/standardization.txt')
    stopwords = load_stopwords('data/stopwords.txt')
    user_message = request.form.get("message")
    replaced = replace_words(user_message, replacements, stopwords)
    print(f"Replaced message: {replaced}")
    payload = {"sender": sender_id, "message": replaced}

    try:
        response = requests.post(RASA_URL, json=payload)
        bot_response = response.json()

        messages = [msg.get("text", "") for msg in bot_response]
        return jsonify({"responses": messages})
    except Exception as e:
        return jsonify({"responses": [f"Lỗi: {str(e)}"]})

if __name__ == "__main__":
    app.run(debug=True)
