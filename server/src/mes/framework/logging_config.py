"""
LOG-CONFIG: Centralized logging configuration for the MES server.

Configures a rotating file handler plus a console handler for both the
application (``mes.*``) loggers and the uvicorn/access loggers so that all
server output is captured to disk in addition to the terminal.

Controlled via ``MES_LOG_*`` environment variables (see mes.config.Settings):
- MES_LOG_DIR         (default: "logs")
- MES_LOG_FILE        (default: "mes_server.log")
- MES_LOG_LEVEL       (default: "INFO")
- MES_LOG_MAX_BYTES   (default: 10 MB)
- MES_LOG_BACKUP_COUNT(default: 5)
- MES_LOG_TO_CONSOLE  (default: True)
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from mes.config import settings

_configured = False


def configure_logging() -> Path:
    """
    Initialize root + MES + uvicorn loggers with a rotating file handler.

    Idempotent: calling more than once is a no-op (uvicorn --reload can
    trigger re-import). Returns the resolved log file path.
    """
    global _configured

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / settings.LOG_FILE

    if _configured:
        return log_path

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d %(tz)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Inject local timezone offset (e.g. "-07:00") into every record.
    import time as _time

    class _LocalTZFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            lt = _time.localtime(record.created)
            off_sec = -_time.altzone if lt.tm_isdst else -_time.timezone
            sign = "+" if off_sec >= 0 else "-"
            hh, rem = divmod(abs(off_sec), 3600)
            mm = rem // 60
            record.tz = f"{sign}{hh:02d}:{mm:02d}"
            return True

    tz_filter = _LocalTZFilter()

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    file_handler.addFilter(tz_filter)

    handlers: list[logging.Handler] = [file_handler]
    if settings.LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(fmt)
        console_handler.addFilter(tz_filter)
        handlers.append(console_handler)

    # Attach to root so everything propagates in.
    root = logging.getLogger()
    root.setLevel(level)
    # Remove any pre-existing handlers (e.g. uvicorn's default) to avoid dupes.
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)

    # Make sure the named loggers we use propagate to root.
    for name in ("mes", "uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine", "alembic"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.propagate = True
        # Clear handlers so records flow to root only (avoids duplicate lines).
        for h in list(lg.handlers):
            lg.removeHandler(h)

    _configured = True
    logging.getLogger("mes").info("Logging initialized -> %s (level=%s)", log_path, settings.LOG_LEVEL.upper())
    return log_path
