from uuid import uuid4
from flask import Flask, render_template, request, jsonify, session
import requests

from utils.word_replacer import load_replacement_data, replace_words, load_stopwords

app = Flask(__name__, static_folder='public')
app.secret_key = "change-me"
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

@app.route("/")
def index():
    return render_template("index_sv.html")

def get_sender_id() -> str:
    """
    Ưu tiên:
    1) Header X-User-Id do frontend gửi (nếu bạn đã có user id khi đăng nhập)
    2) session cookie của Flask (tạo mới nếu chưa có)
    """
    sender_id = request.headers.get("X-User-Id")
    if not sender_id:
        sender_id = session.get("sender_id")
        if not sender_id:
            sender_id = str(uuid4())
            session["sender_id"] = sender_id
    return sender_id

@app.route("/send_message", methods=["POST"])
def send_message():
    sender_id = get_sender_id()
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
