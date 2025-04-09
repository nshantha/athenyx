# app/core/logging_conf.py
import logging
import sys
from app.core.config import settings

def setup_logging():
    """Configures basic logging for the application."""
    log_level = settings.log_level.upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout, # Log to stdout, suitable for containers
    )
    # Optionally suppress overly verbose logs from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING) # Can be INFO if needed for DB debugging
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")