# app/api/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncGenerator
import json

from app.schemas.models import QueryRequest, QueryResponse, ChunkResult # Import request/response models
from app.agent.agent_executor import run_agent # Import the agent runner

logger = logging.getLogger(__name__)
router = APIRouter()

async def stream_agent_response(query: str, conversation_history: str = None) -> AsyncGenerator[str, None]:
    """Stream the agent's response with proper SSE formatting."""
    try:
        async for chunk in run_agent(query, conversation_history):
            if chunk:
                # Properly escape newlines and quote characters for SSE
                escaped_chunk = chunk.replace('\n', '\\n').replace('"', '\\"')
                # Format as Server-Sent Event
                yield f"data: {escaped_chunk}\n\n"
            # Add periodic keep-alive for long-running operations
            await asyncio.sleep(0)
    except Exception as e:
        logger.error(f"Error streaming response: {e}", exc_info=True)
        error_msg = str(e).replace('\n', '\\n').replace('"', '\\"')
        yield f"data: Error: {error_msg}\n\n"

@router.post("/query")
async def query_agent(request: QueryRequest):
    """
    Receives a user query, runs the agent, and returns a streaming response.
    """
    logger.info(f"Received query: '{request.query}'")
    if not request.query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty."
        )

    return StreamingResponse(
        stream_agent_response(request.query, request.conversation_history),
        media_type="text/event-stream"
    )