# app/api/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncGenerator
import json

from app.schemas.models import QueryRequest, QueryResponse, ChunkResult # Import request/response models
from app.agent.agent_executor import run_agent # Import the agent runner
from app.db.neo4j_manager import db_manager # Import DB manager for repository context

logger = logging.getLogger(__name__)
router = APIRouter()

async def stream_agent_response(query: str, conversation_history: str = None, repository_url: str = None) -> AsyncGenerator[str, None]:
    """Stream the agent's response with proper SSE formatting."""
    try:
        # If repository_url is not specified, try to get the active repository
        if not repository_url:
            active_repo = await db_manager.get_active_repository()
            if active_repo:
                repository_url = active_repo.get('url')
                logger.info(f"Using active repository context: {repository_url}")
            
        # Include repository context in the prompt if available
        repository_context = ""
        if repository_url:
            # Get repository name for clearer context
            repo_name = repository_url.split('/')[-1].replace('.git', '')
            repository_context = (
                f"Repository context: {repository_url}\n\n"
                f"IMPORTANT: You are currently analyzing the '{repo_name}' repository. "
                f"Only use information from this specific repository. "
                f"Do not reference or use data from other repositories like spring-petclinic-microservices "
                f"unless explicitly asked about them. "
                f"If the answer to a question is not in this repository, state that clearly."
            )
        
        async for chunk in run_agent(query, conversation_history, repository_context):
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
        stream_agent_response(request.query, request.conversation_history, request.repository_url),
        media_type="text/event-stream"
    )