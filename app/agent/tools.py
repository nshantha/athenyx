# app/agent/tools.py
import logging
from typing import List, Dict, Any
from langchain_core.tools import Tool
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun # Import Async manager
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI # Keep import if needed elsewhere, though LLM is defined in graph.py
from langchain_community.tools.tavily_search import TavilySearchResults
import asyncio # Import asyncio for the sync wrapper

from app.db.neo4j_manager import db_manager # Import the instantiated manager
from app.core.config import settings
from app.schemas.models import ChunkResult

logger = logging.getLogger(__name__)

# --- Custom Neo4j Vector Retriever ---
class Neo4jCodeRetriever(BaseRetriever):
    """Custom LangChain retriever for Neo4j vector search results."""
    k: int = 5 # Number of results to return

    # --- FIX: Add the synchronous method implementation ---
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Synchronously retrieves relevant documents.
           NOTE: This is a wrapper around the async version for compatibility.
                 Consider implementing natively sync logic if performance is critical
                 and async is not strictly needed everywhere.
        """
        # Simple way: Run the async version using asyncio.run()
        # Be cautious using asyncio.run() inside an already running event loop
        # A better approach might involve checking if a loop is running or using a thread.
        # For simplicity now, let's raise NotImplementedError or run it simply.
        logger.warning("Running Neo4j retriever synchronously (wrapping async call).")
        try:
            # This might cause issues if called from within an existing async context/event loop.
            # A dedicated synchronous DB query method might be safer if needed.
            return asyncio.run(self._aget_relevant_documents(query, run_manager=run_manager)) # Use run_manager here if needed by async method's interface
            # Alternatively, raise error if sync use is unexpected:
            # raise NotImplementedError("Synchronous retrieval not implemented directly. Use aget_relevant_documents.")
        except RuntimeError as e:
             logger.error(f"RuntimeError calling async retriever from sync: {e}. This might happen if called from within an event loop.")
             return []


    # --- Keep the Asynchronous method ---
    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun # Use Async manager type hint
    ) -> List[Document]:
        """Asynchronously retrieves relevant documents from Neo4j vector index."""
        # 1. Embed the query
        try:
            from ingestion.processing.embedding import aclient as openai_aclient # Re-use client
            response = await openai_aclient.embeddings.create(
                input=[query],
                model=settings.openai_embedding_model
            )
            query_embedding = response.data[0].embedding
            logger.debug(f"Successfully embedded query for retrieval.")
        except Exception as e:
             logger.error(f"Failed to embed query '{query}': {e}", exc_info=True)
             return []

        # 2. Perform vector search
        try:
            search_results: List[Dict[str, Any]] = await db_manager.vector_search_code_chunks(
                query_embedding=query_embedding,
                k=self.k
            )
            logger.debug(f"Neo4j vector search returned {len(search_results)} results.")
        except Exception as e:
            logger.error(f"Failed to retrieve from Neo4j vector index: {e}", exc_info=True)
            return []

        # 3. Convert results
        documents = []
        for result in search_results:
            metadata = {
                "source": result.get("path", "unknown"),
                "score": result.get("score"),
                "start_line": result.get("start_line"),
            }
            metadata = {k: v for k, v in metadata.items() if v is not None}
            doc = Document(page_content=result.get("text", ""), metadata=metadata)
            documents.append(doc)

        return documents

# --- Tool Definitions ---

def get_tools() -> List[Tool]:
    """Initializes and returns the list of tools available to the agent."""
    tools = []

    # 1. RAG Retriever Tool
    try:
        code_retriever = Neo4jCodeRetriever(k=5) # Should instantiate now
        rag_tool = Tool(
            name="CodeBaseRetriever",
            # Ensure the primary func used by the Tool is the async one if agent calls are async
            func=code_retriever.ainvoke, # Use async invoke
            description="Searches and retrieves relevant code snippets (functions, classes, chunks) from the indexed codebase based on semantic similarity to the query. Use this to answer questions about how specific code works, find examples, or understand functionalities.",
            coroutine=code_retriever.ainvoke # Explicitly specify coroutine for async use
        )
        tools.append(rag_tool)
        logger.info("CodeBaseRetriever tool initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize CodeBaseRetriever tool: {e}", exc_info=True)


    # 2. Web Search Tool (Tavily)
    if settings.tavily_api_key:
        try:
            # Pass the key explicitly to be safer if env var loading is suspect
            # tavily_tool = TavilySearchResults(max_results=3, tavily_api_key=settings.tavily_api_key)
            # Or rely on env var loading:
            tavily_tool = TavilySearchResults(max_results=3)
            tavily_tool.name = "WebSearch" # Give it a specific name
            tavily_tool.description = "Performs a web search using Tavily to find information about general programming concepts, external libraries, error messages, or recent developments not present in the indexed codebase. Use when the question seems to require up-to-date external knowledge or context."
            tools.append(tavily_tool)
            logger.info("WebSearch tool (Tavily) initialized.")
        except Exception as e:
            # Log the specific pydantic error if it occurs
            logger.error(f"Failed to initialize WebSearch tool (Tavily): {e}", exc_info=True)
            logger.warning("Proceeding without WebSearch tool. Ensure TAVILY_API_KEY is set in .env if needed.")
    else:
        logger.warning("TAVILY_API_KEY not found in environment config. WebSearch tool will not be available.")

    return tools

# Instantiate tools once
available_tools = get_tools()