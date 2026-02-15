import os


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))

    MAX_FILE_SIZE = 50 * 1024 * 1024
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/uploads")
    PYROGRAM_WORKDIR = os.getenv("PYROGRAM_WORKDIR", "/tmp")

    @classmethod
    def validate(cls) -> None:
        missing = []
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if cls.API_ID <= 0:
            missing.append("API_ID")
        if not cls.API_HASH:
            missing.append("API_HASH")
        if cls.LOG_GROUP_ID == 0:
            missing.append("LOG_GROUP_ID")

        if missing:
            raise ValueError(f"Missing or invalid environment variables: {', '.join(missing)}")


Config.validate()
