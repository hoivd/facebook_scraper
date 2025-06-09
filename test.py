import logging 
from logger import setup_logger

logger = setup_logger(__name__, logging.INFO)

if __name__ == "__main__":
    root_logger = setup_logger("parser")
    root_logger.info("Bat dau parser")

    child_logger = setup_logger("parser.api")
    child_logger.info("Bat dau parser api")