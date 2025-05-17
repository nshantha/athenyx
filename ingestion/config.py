# ingestion/config.py
import os
from app.core.config import Settings, settings # Import base settings
import re
from pydantic import Field

class IngestionSettings(Settings):
    """
    Specific settings for the ingestion pipeline, inheriting common settings.
    """
    ingest_repo_url: str = Field(
        default="https://github.com/langchain-ai/langchain.git",
        env="INGEST_REPO_URL", 
        description="Repository URL to clone and analyze"
    )
    ingest_repo_branch: str | None = Field(
        default=None, 
        env="INGEST_REPO_BRANCH",
        description="Branch to analyze (default: main/master)"
    )
    # Microservices repository settings - removed in favor of single INGEST_REPO_URL
    
    # Comma-separated list of file extensions to parse (e.g., ".py,.java")
    ingest_target_extensions: str = Field(
        default=".py,.java,.go,.js,.jsx,.ts,.tsx,.cs,.proto,.md,.yaml,.yml,.json", 
        env="INGEST_TARGET_EXTENSIONS",
        description="File extensions to analyze, comma-separated"
    )
    # Local path where repositories will be cloned
    base_clone_dir: str = os.path.join(os.getcwd(), "ingestion", "repos")
    
    # Will be set dynamically based on the repository URL
    clone_dir: str = ""
    
    # Add repo_dir attribute for compatibility with chunking.py
    repo_dir: str = os.path.join(os.getcwd(), "ingestion")

    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Batch sizes for processing
    embedding_batch_size: int = 100
    neo4j_batch_size: int = 500 # Adjust based on performance

    # Flag to force re-indexing even if commit SHA hasn't changed
    force_reindex: bool = Field(
        default=False,
        env="FORCE_REINDEX",
        description="Force reindexing even if repo hasn't changed"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set clone_dir based on repo URL
        self.update_clone_dir()
        
    def update_clone_dir(self):
        """Update clone directory based on the repository URL."""
        if not self.ingest_repo_url:
            self.clone_dir = os.path.join(self.base_clone_dir, "default_repo")
            return
            
        # Extract repo name from URL
        repo_name = self.extract_repo_name(self.ingest_repo_url)
        self.clone_dir = os.path.join(self.base_clone_dir, repo_name)
        
    @staticmethod
    def extract_repo_name(repo_url: str) -> str:
        """
        Extract repository name from URL.
        
        Args:
            repo_url: The repository URL
            
        Returns:
            A sanitized repository name suitable for file paths
        """
        if not repo_url:
            return "unknown_repo"
            
        # For local URLs with a clear format, return the name directly
        if repo_url.startswith("local://"):
            return repo_url.replace("local://", "")
            
        # Remove trailing slashes and .git extension
        clean_url = repo_url.rstrip('/')
        if clean_url.endswith('.git'):
            clean_url = clean_url[:-4]  # Remove .git extension
        
        # Get the last part of the URL (the repo name)
        parts = clean_url.split('/')
        repo_name = parts[-1] if parts else "unknown_repo"
        
        # Replace any problematic characters with underscores
        # This ensures consistency in directory naming
        repo_name = re.sub(r'[^a-zA-Z0-9_]', '_', repo_name)
        
        return repo_name

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from base Settings if not needed

# Instantiate the settings for ingestion
ingestion_settings = IngestionSettings()

# Helper to get target extensions as a list
def get_target_extensions() -> list[str]:
    return [ext.strip() for ext in ingestion_settings.ingest_target_extensions.split(',') if ext.strip()]