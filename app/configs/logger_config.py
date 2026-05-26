"""
Centralized Logging Configuration
===================================
Enterprise-grade structlog setup with:
- Environment-aware output (JSON for production, Console for development)
- Sensitive data redaction processor
- File handler with rotation (configurable max size and backup count)
- Standard library bridge so third-party libs (uvicorn, sqlalchemy) flow through structlog
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

import structlog

from app.configs.app_config import settings
from app.utils.logger import redact_sensitive_data


def setup_logging() -> None:
    """Configure the application logging pipeline."""

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # ------------------------------------------------------------------
    # 1. Shared structlog processors (applied to EVERY log line)
    # ------------------------------------------------------------------
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Inject redaction processor if enabled
    if settings.LOG_REDACT_ENABLED:
        shared_processors.insert(0, redact_sensitive_data)

    # ------------------------------------------------------------------
    # 2. Choose renderer based on LOG_FORMAT
    # ------------------------------------------------------------------
    if settings.LOG_FORMAT.lower() == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # ------------------------------------------------------------------
    # 3. Configure structlog
    # ------------------------------------------------------------------
    structlog.configure(
        processors=shared_processors + [renderer],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    # ------------------------------------------------------------------
    # 4. Standard library bridge (uvicorn, sqlalchemy, etc.)
    # ------------------------------------------------------------------
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # ------------------------------------------------------------------
    # 5. File handler with rotation (if enabled)
    # ------------------------------------------------------------------
    if settings.LOG_OUTPUT in ("file", "both"):
        log_path = Path(settings.LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=settings.LOG_FILE_MAX_BYTES,
            backupCount=settings.LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        # Attach to root logger so structlog output also goes to file
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # ------------------------------------------------------------------
    # 6. Done
    # ------------------------------------------------------------------
    logger = structlog.get_logger("app.logging")
    logger.info(
        "logging_initialized",
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        output=settings.LOG_OUTPUT,
        redaction_enabled=settings.LOG_REDACT_ENABLED,
        slow_request_threshold_ms=settings.LOG_SLOW_REQUEST_THRESHOLD_MS,
    )
