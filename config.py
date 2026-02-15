import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    bot_token: Optional[str]
    api_id: Optional[int]
    api_hash: Optional[str]
    log_group_id: str
    upload_folder: str
    pyrogram_workdir: str
    max_file_size: int


class Config:
    """Runtime configuration loader.

    Uses os.getenv for safe access, supports local defaults, and never raises at import time.
    """

    MAX_FILE_SIZE = 50 * 1024 * 1024
    DEFAULT_API_ID = 123456
    DEFAULT_API_HASH = "local-dev-api-hash"
    DEFAULT_LOG_GROUP_ID = "-1000000000000"

    @classmethod
    def _use_local_defaults(cls) -> bool:
        # Heroku sets DYNO; defaults are useful for local smoke testing.
        return os.getenv("USE_LOCAL_DEFAULTS", "1") == "1" and not os.getenv("DYNO")

    @classmethod
    def load(cls) -> Settings:
        use_defaults = cls._use_local_defaults()

        bot_token = os.getenv("BOT_TOKEN")
        api_hash = os.getenv("API_HASH") or (cls.DEFAULT_API_HASH if use_defaults else None)
        api_id_raw = os.getenv("API_ID")
        log_group_id = os.getenv("LOG_GROUP_ID") or (
            cls.DEFAULT_LOG_GROUP_ID if use_defaults else ""
        )

        api_id: Optional[int] = None
        if api_id_raw:
            try:
                api_id = int(api_id_raw)
            except ValueError:
                logger.warning("API_ID is set but invalid (must be an integer): %r", api_id_raw)
        elif use_defaults:
            api_id = cls.DEFAULT_API_ID

        return Settings(
            bot_token=bot_token,
            api_id=api_id,
            api_hash=api_hash,
            log_group_id=log_group_id,
            upload_folder=os.getenv("UPLOAD_FOLDER", "/tmp/uploads"),
            pyrogram_workdir=os.getenv("PYROGRAM_WORKDIR", "/tmp"),
            max_file_size=cls.MAX_FILE_SIZE,
        )

    @classmethod
    def validate_runtime(cls, settings: Settings) -> bool:
        """Runtime validation that logs warnings instead of raising exceptions."""
        valid = True

        if settings.api_id is None:
            logger.warning("Missing or invalid API_ID. Telegram client features are disabled.")
            valid = False

        if not settings.api_hash:
            logger.warning("Missing API_HASH. Telegram client features are disabled.")
            valid = False

        if not settings.log_group_id:
            logger.warning("Missing LOG_GROUP_ID. Telegram forwarding is disabled.")
            valid = False
        elif not settings.log_group_id.startswith("-100"):
            logger.warning("Invalid LOG_GROUP_ID format. It must start with '-100'.")
            valid = False

        return valid
