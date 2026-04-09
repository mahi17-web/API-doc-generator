"""
core/logger.py - Centralised logging configuration.

Import `logger` anywhere to get a consistently formatted logger.
"""

import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE = "%H:%M:%S"


def _build_logger(name: str = "apidoc", level: int = logging.INFO) -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log  # already configured

    log.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE))

    log.addHandler(handler)
    log.propagate = False
    return log


logger = _build_logger()
