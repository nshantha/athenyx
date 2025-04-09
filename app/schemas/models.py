# app/schemas/models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    """Request model for querying the knowledge graph."""
    query: str
    user_id: Optional[str] = None # Example: For potential future context/personalization

class ChunkResult(BaseModel):
    """Represents a retrieved context chunk."""
    text: str
    path: Optional[str] = None
    start_line: Optional[int] = None
    score: Optional[float] = None
    # Add other metadata if needed

class QueryResponse(BaseModel):
    """Response model containing the answer and potentially context."""
    answer: str
    retrieved_context: Optional[List[ChunkResult]] = None # Context used for the answer
    error: Optional[str] = None # Include if an error occurred