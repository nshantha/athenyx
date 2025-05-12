# app/schemas/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    """Model for user query requests to the agent."""
    query: str
    conversation_history: Optional[str] = None
    user_id: Optional[str] = None # Example: For potential future context/personalization
    repository_url: Optional[str] = None # Added for repository context

class ChunkResult(BaseModel):
    """Model for a single context chunk result."""
    text: str
    path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    start_line: Optional[int] = None
    score: Optional[float] = None
    # Add other metadata if needed

class QueryResponse(BaseModel):
    """Model for agent responses to user queries."""
    answer: str
    retrieved_context: Optional[List[ChunkResult]] = None
    error: Optional[str] = None
    
class RepositoryInfo(BaseModel):
    """Model for repository information."""
    url: str
    service_name: Optional[str] = None
    description: Optional[str] = None
    last_commit: Optional[str] = None
    last_indexed: Optional[str] = None
    is_active: Optional[bool] = False
    
class RepositoryList(BaseModel):
    """Model for a list of repositories."""
    repositories: List[RepositoryInfo]
    active_repository: Optional[RepositoryInfo] = None
    
class RepositoryCreate(BaseModel):
    """Model for creating a new repository."""
    url: str
    branch: Optional[str] = None
    description: Optional[str] = None
    
class RepositoryResponse(BaseModel):
    """Model for repository operation responses."""
    success: bool
    message: str
    repository: Optional[RepositoryInfo] = None