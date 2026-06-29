"""
utils/logger.py
---------------
Centralized logging configuration for PyAutoFlow.
Provides a pre-configured logger with console and file handlers.
"""

import logging
import os
from datetime import datetime


def get_logger(name: str = "pyautoflow", log_dir: str = "logs") -> logging.Logger:
    """
    Create and return a configured logger instance.

    Parameters
    ----------
    name : str
        Name of the logger (default: 'pyautoflow').
    log_dir : str
        Directory where log files will be stored (default: 'logs').

    Returns
    -------
    logging.Logger
        Configured logger with console and file handlers.

    Examples
    --------
    >>> logger = get_logger("my_module")
    >>> logger.info("Pipeline started")
    """
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f"pyautoflow_{datetime.now().strftime('%Y%m%d')}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_fmt = logging.Formatter(
            "\033[36m%(asctime)s\033[0m | \033[1m%(levelname)-8s\033[0m | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)

        # File handler
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
