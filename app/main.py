# app/main.py
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api import endpoints # Import the router
from app.api import repository # Import the repository router
from app.core.logging_conf import setup_logging # Import logging setup
from app.db.neo4j_manager import db_manager # Import DB manager for startup/shutdown

# Setup logging BEFORE creating FastAPI app instance
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("Application startup...")
    # Connect to Neo4j
    try:
        await db_manager.connect()
        # You could potentially pre-load models here if needed,
        # but sentence-transformer model is loaded on import in embedding.py
        # Ensure tools are loaded (they are loaded on import in tools.py)
        # Ensure graph is compiled (loaded on import in agent_executor.py)
        if not agent_executor.compiled_graph: # Check compilation status
            logger.critical("Agent graph failed to compile during startup. Application might be unstable.")
            # Depending on severity, you might want to raise an exception here to stop startup
        logger.info("Neo4j connected and resources initialized.")
    except Exception as e:
        logger.critical(f"Application startup failed: {e}", exc_info=True)
        # Handle failure (e.g., raise the exception to prevent FastAPI from starting fully)
        raise
    yield
    # --- Shutdown ---
    logger.info("Application shutdown...")
    await db_manager.close()
    logger.info("Neo4j connection closed.")


# Create FastAPI app instance with lifespan context manager
app = FastAPI(
    title="AI Knowledge Graph API",
    description="API for querying the software knowledge graph.",
    version="0.1.0",
    lifespan=lifespan
)

# Include the API routers
app.include_router(endpoints.router, prefix="/api") # Add a /api prefix
app.include_router(repository.router, prefix="/api") # Add repository endpoints

# Import agent_executor here to ensure graph compilation check in lifespan works
from app.agent import agent_executor

@app.get("/", tags=["Health Check"])
async def read_root():
    """Simple health check endpoint."""
    return {"status": "OK"}

# Note: If running with uvicorn directly, use: uvicorn app.main:app --reload
# Dockerfile/docker-compose already handles this.