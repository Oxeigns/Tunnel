import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
    UPLOAD_SECRET = os.getenv("UPLOAD_SECRET")

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    ALLOWED_EXTENSIONS = {
        "txt",
        "pdf",
        "jpg",
        "png",
        "mp4",
        "zip"
    }
