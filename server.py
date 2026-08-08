from __future__ import annotations

from dataclasses import asdict

from flask import Flask, jsonify, request, send_from_directory

from chat import EligibilityChatbot
from logs import masking_log

app = Flask(__name__)
bot = EligibilityChatbot()


@app.get("/")
def index():
    return send_from_directory(app.root_path, "index.html")


@app.get("/view")
def view():
    return send_from_directory(app.root_path, "view.html")


@app.get("/api/logs")
def get_logs():
    return jsonify([asdict(entry) for entry in masking_log.all()])


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    message = data.get("message")

    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "user_id is required"}), 400
    if message is not None and not isinstance(message, str):
        return jsonify({"error": "message must be a string"}), 400

    reply = bot.run(user_id=user_id, message=message or None, verbose=False)
    return jsonify({"reply": reply})


@app.post("/api/reset")
def reset():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "user_id is required"}), 400

    bot.reset(user_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
