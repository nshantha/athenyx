# app/schemas/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    """Model for user query requests to the agent."""
    query: str
    conversation_history: Optional[str] = None
    user_id: Optional[str] = None # Example: For potential future context/personalization

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