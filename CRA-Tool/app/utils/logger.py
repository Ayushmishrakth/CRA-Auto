"""
Centralized logging configuration.

Import `logger` anywhere in the app instead of configuring logging per file.
"""

import logging
import sys

from app.core.config import settings

# Log format: timestamp, level, module name, message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "cra") -> logging.Logger:
    """Create and configure the application logger."""
    log = logging.getLogger(name)

    if log.handlers:
        return log

    log.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    log.addHandler(handler)

    # Prevent duplicate logs if uvicorn reloads the process
    log.propagate = False

    return log


logger = setup_logger()
