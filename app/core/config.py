# app/core/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Neo4j Connection
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_username: str = Field(..., env="NEO4J_USERNAME")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")

    # OpenAI API Key
    openai_api_key: str = Field(..., env="OPENAI_API_KEY") # Make it required

    # Embedding Model
    openai_embedding_model: str = Field(..., env="OPENAI_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(..., env="EMBEDDING_DIMENSIONS")

    # LLM Model for Generation (Used in Phase 3)
    openai_llm_model: str = Field(..., env="OPENAI_LLM_MODEL")

    # Web Search Tool (Used in Phase 3)
    tavily_api_key: str | None = None

    # Backend API URL (Used by UI in Phase 4)
    backend_api_url: str = Field(..., env="BACKEND_API_URL")

    # Logging Level
    log_level: str = "INFO"

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        # If you want to load from system environment variables too, uncomment below
        # case_sensitive = True
        extra = 'ignore' # Ignore extra fields if environment has more vars

# Instantiate settings once
settings = Settings()