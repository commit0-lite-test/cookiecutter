"""Module for setting up logging."""

import logging
import sys
from typing import Union

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
LOG_FORMATS = {
    "DEBUG": "%(levelname)s %(name)s: %(message)s",
    "INFO": "%(levelname)s: %(message)s",
}


def configure_logger(
    stream_level: str = "DEBUG", debug_file: Union[str, None] = None
) -> logging.Logger:
    """Configure logging for cookiecutter.

    Set up logging to stdout with given level. If ``debug_file`` is given set
    up logging to file with DEBUG level.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a stream handler for stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(LOG_LEVELS.get(stream_level, logging.DEBUG))
    stream_formatter = logging.Formatter(
        LOG_FORMATS.get(stream_level, LOG_FORMATS["DEBUG"])
    )
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    # If debug_file is provided, set up file logging
    if debug_file:
        file_handler = logging.FileHandler(debug_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMATS["DEBUG"])
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
