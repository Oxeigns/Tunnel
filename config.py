import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class Config:
    """Application configuration sourced from environment variables.

    This class is intentionally tolerant at import time so process managers
    like Gunicorn can start workers even when runtime secrets are not set yet.
    """

    BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN") or None
    API_HASH: Optional[str] = os.getenv("API_HASH") or None

    _api_id_raw = os.getenv("API_ID")
    _log_group_id_raw = os.getenv("LOG_GROUP_ID") or "-1002625483900"

    try:
        API_ID: Optional[int] = int(_api_id_raw) if _api_id_raw else None
    except (TypeError, ValueError):
        API_ID = None

    try:
        LOG_GROUP_ID: Optional[int] = int(_log_group_id_raw) if _log_group_id_raw else None
    except (TypeError, ValueError):
        LOG_GROUP_ID = None

    MAX_FILE_SIZE = 50 * 1024 * 1024
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/uploads")
    PYROGRAM_WORKDIR = os.getenv("PYROGRAM_WORKDIR", "/tmp")

    @classmethod
    def validate(cls, raise_on_error: bool = False) -> ValidationResult:
        """Validate required environment variables without crashing imports.

        Args:
            raise_on_error: If True, raises ValueError when required variables
                are missing/invalid. Keep False in Gunicorn/Heroku startup paths.

        Returns:
            ValidationResult with validity, error list, and warning list.
        """

        errors: list[str] = []
        warnings: list[str] = []

        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is missing (expected non-empty string).")
            warnings.append(
                "BOT_TOKEN is not configured; Telegram bot authentication will fail until set."
            )

        if cls.API_ID is None:
            raw = os.getenv("API_ID")
            if raw:
                errors.append(f"API_ID must be an integer, got: {raw!r}.")
            else:
                errors.append("API_ID is missing (expected integer).")
            warnings.append("API_ID is not configured; Pyrogram client cannot start.")
        elif cls.API_ID <= 0:
            errors.append(f"API_ID must be a positive integer, got: {cls.API_ID}.")

        if not cls.API_HASH:
            errors.append("API_HASH is missing (expected non-empty string).")
            warnings.append("API_HASH is not configured; Pyrogram client cannot start.")

        if cls.LOG_GROUP_ID is None:
            raw = os.getenv("LOG_GROUP_ID")
            if raw:
                errors.append(f"LOG_GROUP_ID must be an integer, got: {raw!r}.")
            else:
                errors.append("LOG_GROUP_ID is missing (expected integer).")
            warnings.append("LOG_GROUP_ID is not configured; forwarding destination is unavailable.")

        is_valid = not errors

        if warnings:
            for warning in warnings:
                logger.warning("Config warning: %s", warning)

        if errors:
            logger.error("Config validation errors: %s", " | ".join(errors))
            if raise_on_error:
                raise ValueError("Missing or invalid environment variables: " + "; ".join(errors))

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


# Validate at import time, but never crash worker boot by default.
CONFIG_VALIDATION = Config.validate(raise_on_error=False)
