# app/core/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Neo4j Connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"

    # OpenAI API Key
    openai_api_key: str = Field(..., env="OPENAI_API_KEY") # Make it required

    # Embedding Model
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # LLM Model for Generation (Used in Phase 3)
    openai_llm_model: str = "gpt-4o-mini"

    # Web Search Tool (Used in Phase 3)
    tavily_api_key: str | None = None

    # Backend API URL (Used by UI in Phase 4)
    backend_api_url: str = "http://localhost:8000"

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