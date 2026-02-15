from datetime import datetime

from flask import Flask, jsonify, request
from telegram import Bot
from werkzeug.utils import secure_filename

from config import Config

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_SIZE


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def get_bot():
    if not Config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not configured")
    return Bot(token=Config.BOT_TOKEN)


@app.route("/")
def home():
    missing = [
        name
        for name, value in {
            "BOT_TOKEN": Config.BOT_TOKEN,
            "GROUP_CHAT_ID": Config.GROUP_CHAT_ID,
            "UPLOAD_SECRET": Config.UPLOAD_SECRET,
        }.items()
        if not value
    ]

    return (
        jsonify(
            {
                "status": "healthy" if not missing else "degraded",
                "service": "tunnel",
                "upload_endpoint": "/upload",
                "missing_env": missing,
            }
        ),
        200,
    )


@app.route("/upload", methods=["POST"])
def upload():
    if request.headers.get("X-SECRET") != Config.UPLOAD_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        bot = get_bot()
        bot.send_document(
            chat_id=Config.GROUP_CHAT_ID,
            document=file,
            filename=filename,
            caption=f"📂 New File Uploaded\n🕒 {timestamp}\n📎 {filename}",
        )

        return jsonify({"status": "File sent to group"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
