"""Centralized logging configuration for fmea-risk-analyzer."""

import logging
import os


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured once per process."""
    logger = logging.getLogger(name)
    if not logging.root.handlers:
        level = os.environ.get("FMEA_LOG_LEVEL", "WARNING").upper()
        logging.basicConfig(
            level=getattr(logging, level, logging.WARNING),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    return logger
