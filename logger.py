import logging
from logging import Logger

def setup_logger(name: str, level: int = logging.INFO) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handle = logging.StreamHandler()
    handle.setFormatter(logging.Formatter("<%(name)s-%(levelname)s> - %(message)s"))
    logger.addHandler(handle)

    return logger

