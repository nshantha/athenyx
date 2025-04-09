# app/api/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.models import QueryRequest, QueryResponse, ChunkResult # Import request/response models
from app.agent.agent_executor import run_agent # Import the agent runner

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Receives a user query, runs the agent, and returns the response.
    """
    logger.info(f"Received query: '{request.query}'")
    if not request.query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty."
        )

    try:
        # Run the agent asynchronously
        final_state = await run_agent(request.query)

        # TODO: Extract context used for the answer if needed.
        # This requires modifying the AgentState and potentially the graph
        # to explicitly store the documents retrieved by the tools.
        # For now, we just return the answer.
        retrieved_context = None # Placeholder

        if final_state.get("error"):
             # If the agent itself caught an error and put it in the state
             logger.error(f"Agent execution finished with error: {final_state['error']}")
             # Return error in response body, maybe use 500?
             return QueryResponse(answer=final_state.get("answer", "Agent failed"), error=final_state["error"])
             # Or raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=final_state["error"])


        answer = final_state.get("answer", "No answer generated.")

        return QueryResponse(answer=answer, retrieved_context=retrieved_context)

    except Exception as e:
        # Catch unexpected errors during the API call/agent invocation setup
        logger.critical(f"Unexpected error processing query '{request.query}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {e}"
        )