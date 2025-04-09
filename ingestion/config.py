# ingestion/config.py
import os
from app.core.config import Settings, settings # Import base settings

class IngestionSettings(Settings):
    """
    Specific settings for the ingestion pipeline, inheriting common settings.
    """
    ingest_repo_url: str = "https://github.com/langchain-ai/langchain.git" # Example default
    ingest_repo_branch: str | None = None # Ingest default branch if None
    # Comma-separated list of file extensions to parse (e.g., ".py,.java")
    ingest_target_extensions: str = ".py"
    # Local path where the repository will be cloned
    clone_dir: str = os.path.join(os.getcwd(), "ingestion", "cloned_repo")

    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Batch sizes for processing
    embedding_batch_size: int = 100
    neo4j_batch_size: int = 500 # Adjust based on performance

    # Flag to force re-indexing even if commit SHA hasn't changed
    force_reindex: bool = False

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from base Settings if not needed

# Instantiate the settings for ingestion
ingestion_settings = IngestionSettings()

# Helper to get target extensions as a list
def get_target_extensions() -> list[str]:
    return [ext.strip() for ext in ingestion_settings.ingest_target_extensions.split(',') if ext.strip()]