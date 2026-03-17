"""Core application package."""

from .config import settings
from .logger import logger, setup_logger


def bootstrap() -> None:
    """Initialise logger and suppress known warnings.

    Lazy imports inside function body — prevents circular imports
    by deferring utils imports until runtime, not module load time.
    """
    # Lazy import — warnings.py is Level 1 but imports paths (Level 0)
    # Importing here instead of module level breaks the potential cycle
    from src.utils.warnings import suppress_known_warnings

    setup_logger(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        enable_file=settings.ENABLE_LOG_FILE,
        log_file_name=settings.LOG_FILE_NAME,
        log_file_retention=settings.LOG_FILE_RETENTION,
        log_file_format=settings.LOG_FILE_FORMAT,
        silence_modules=settings.LOG_SILENCE_MODULES,
    )
    suppress_known_warnings()


__all__ = ["bootstrap", "logger", "settings", "setup_logger"]
