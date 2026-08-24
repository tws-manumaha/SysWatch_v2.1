"""
SysWatch v2.1 — Granular Application Logging
Logs to both file (/var/log/syswatch/application.log) and database.
Uses timezone-aware datetimes (no deprecated utcnow()).
"""
import os
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Optional

from modules.config import Config

LOG_DIR = Config.LOG_DIR
LOG_FILE = os.path.join(LOG_DIR, "application.log")


def setup_logging(app=None, level: str = None):
    """
    Configure structured JSON logging to file + console.
    Idempotent — safe to call multiple times.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"module": "%(name)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicates on re-init
    root_logger.handlers.clear()

    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=50 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    if app:
        app.logger.info("Logging initialized")

    logging.getLogger("syswatch").info("Logging initialized — file=%s, level=%s", LOG_FILE, log_level)


def utcnow() -> datetime:
    """Return timezone-aware UTC datetime (replaces deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)


def log_event(
    module: str,
    level: str,
    event_type: str,
    message: str,
    user_id: Optional[str] = None,
    hostname: Optional[str] = None,
    details: Optional[dict] = None,
    source_ip: Optional[str] = None,
):
    """
    Log an event to both file and database.
    Database failures are logged to file but do not raise.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger(f"syswatch.{module}")
    logger.log(log_level, message)

    # Persist to database
    try:
        from modules.database import db
        db.execute(
            """INSERT INTO application_logs
               (timestamp, level, module, user_id, hostname, event_type, message, details, source_ip)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                utcnow(),
                level.upper(),
                module,
                user_id,
                hostname,
                event_type,
                message,
                json.dumps(details or {}),
                source_ip,
            ),
        )
    except Exception as e:
        # Don't use log_event recursively — use the logger directly
        logger.error("Failed to persist log event to database: %s", e)


def cleanup_old_logs(retention_days: int = None):
    """Delete logs older than retention period from database."""
    if retention_days is None:
        retention_days = Config.LOG_RETENTION_DAYS
    try:
        from modules.database import db
        deleted = db.execute(
            "DELETE FROM application_logs WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (retention_days,),
        )
        logging.getLogger("syswatch.logging").info(
            "Cleaned up %s old log entries (older than %s days)", deleted, retention_days
        )
    except Exception as e:
        logging.getLogger("syswatch.logging").error("Failed to cleanup old logs: %s", e)
