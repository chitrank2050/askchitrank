"""
Logging Configuration Module.
Configures Loguru for console and file output.
Intercepts stdlib logging to ensure consistent formatting across dependencies.
"""

import logging
import sys
from pathlib import Path

from loguru import logger


class InterceptHandler(logging.Handler):
    """Redirect stdlib logging (httpx, mlflow etc) through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(
    log_level: str = "INFO",
    log_format: str = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    ),
    enable_file: bool = False,
    log_file_name: str = "",
    log_file_retention: str = "30 days",
    log_file_format: str = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    ),
    silence_modules: list[str] | None = None,
    log_dir: Path | None = None,
) -> None:
    """
    Configure Loguru for the project.
    Call once at entry point only — main.py, never inside modules.
    """
    # Intercept all stdlib logging through Loguru
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level)

    # Silence noisy third-party dependencies
    for module in silence_modules or []:
        logging.getLogger(module).setLevel(logging.ERROR)

    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        level=log_level,
        format=log_format,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # File handler — optional, disabled by default
    if enable_file:
        from src.utils.paths import PROJECT_ROOT

        resolved_dir = log_dir or PROJECT_ROOT / "logs"
        resolved_dir.mkdir(exist_ok=True)

        logger.add(
            resolved_dir / log_file_name,
            level=log_level,
            rotation="10 MB",
            retention=log_file_retention,
            compression="zip",
            format=log_file_format,
            enqueue=True,
        )
