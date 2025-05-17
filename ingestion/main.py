# ingestion/main.py
"""
Main entry point for the ingestion system.
This file serves as a thin wrapper around the modular functionality.
"""
import logging
import os

# Configure logging early
# You might want a more sophisticated setup using app.core.logging_conf later
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Debug env vars (using direct os.getenv for comparison)
logger.info("Checking environment variables directly from OS:")
logger.info(f"INGEST_REPO_URL (os.getenv) = {os.getenv('INGEST_REPO_URL')}")
logger.info(f"NEO4J_URI (os.getenv) = {os.getenv('NEO4J_URI')}")

# Import modules after basic logging is configured
from ingestion.modules.enhanced_knowledge_system import run_enhanced_ingestion
from ingestion.modules.cli import main

# Re-export the main functionality
__all__ = ["run_enhanced_ingestion", "main"]

# Run the main function when executed directly
if __name__ == "__main__":
    main()