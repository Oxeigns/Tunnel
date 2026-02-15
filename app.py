import logging
import os
import tempfile
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import Config
from pyrogram import Client
from pyrogram.errors import RPCError

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
settings = Config.load()

app.config["MAX_CONTENT_LENGTH"] = settings.max_file_size
app.config["UPLOAD_FOLDER"] = settings.upload_folder
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

_client = None
_client_lock = Lock()


def get_client() -> Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                if not Config.validate_runtime(settings):
                    raise RuntimeError(
                        "Telegram client cannot start due to missing/invalid runtime configuration"
                    )

                client = Client(
                    "upload_forwarder_bot",
                    api_id=settings.api_id,
                    api_hash=settings.api_hash,
                    bot_token=settings.bot_token,
                    workdir=settings.pyrogram_workdir,
                )
                client.start()
                _client = client
                logger.info("Pyrogram client started")
    return _client


def get_uploader_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(_error):
    return jsonify({"error": "File exceeds 50MB limit"}), 413


@app.route("/", methods=["GET"])
def health():
    return "App is running ✅", 200


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix="upload_",
            suffix=f"_{filename}",
            dir=app.config["UPLOAD_FOLDER"],
            delete=False,
        ) as tmp:
            temp_file_path = tmp.name
            file.save(tmp)

        file_size = os.path.getsize(temp_file_path)
        uploader_ip = get_uploader_ip()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        caption = (
            f"File name: {filename}\n"
            f"File size: {file_size} bytes\n"
            f"Uploader IP: {uploader_ip}\n"
            f"Timestamp: {timestamp}"
        )

        client = get_client()
        client.send_document(
            chat_id=int(settings.log_group_id),
            document=temp_file_path,
            caption=caption,
        )

        return jsonify({"status": "File uploaded and forwarded"}), 200

    except RuntimeError as exc:
        logger.warning("Upload attempted without valid runtime config: %s", exc)
        return jsonify({"error": "Server is missing Telegram configuration"}), 503
    except RPCError:
        logger.exception("Telegram API error while forwarding file")
        return jsonify({"error": "Failed to forward file to Telegram"}), 502
    except Exception:
        logger.exception("Unexpected error during upload")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                logger.exception("Failed to remove temporary file: %s", temp_file_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
