# app/agent/agent_executor.py
import logging
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import AsyncGenerator
import re

from app.agent.graph import agent_graph, AgentState # Import compiled graph and state type

logger = logging.getLogger(__name__)

# Compile the graph into a runnable LangChain object
# Use checkpointing in memory for simplicity in MVP
# For production, consider persistent checkpointing (e.g., Redis, DB)
try:
    compiled_graph = agent_graph.compile()
    logger.info("Agent graph compiled successfully.")
except Exception as e:
     logger.critical(f"Failed to compile agent graph: {e}", exc_info=True)
     # Application might not be usable, handle appropriately (e.g., raise SystemExit)
     compiled_graph = None # Ensure it's None if compilation fails

def format_code_block(text: str) -> str:
    """Format code blocks with proper language markers and spacing."""
    # Language detection patterns
    lang_patterns = {
        'csharp': r'(public\s+class|private\s+static|protected\s+|internal\s+|namespace\s+|using\s+[\w\.]+;)',
        'python': r'(def\s+\w+|class\s+\w+|import\s+[\w\.]+|from\s+[\w\.]+\s+import)',
        'javascript': r'(const\s+\w+\s*=|let\s+\w+\s*=|function\s+\w+|class\s+\w+|import\s+.*from)',
        'java': r'(public\s+class|private\s+static|protected\s+|package\s+[\w\.]+|import\s+[\w\.]+)',
        'typescript': r'(interface\s+\w+|type\s+\w+|export\s+class)',
        'sql': r'(SELECT\s+.*FROM|INSERT\s+INTO|UPDATE\s+.*SET|DELETE\s+FROM)'
    }

    # Detect language and format code block
    for lang, pattern in lang_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            return f"```{lang}\n{text}\n```"
    return text

async def run_agent(query: str, conversation_history: str = None) -> AsyncGenerator[str, None]:
    """Runs the compiled agent graph with the user query and streams the response."""
    if compiled_graph is None:
         logger.error("Agent graph is not compiled. Cannot run agent.")
         yield "Error: Agent graph failed to compile."
         return

    logger.info(f"Running agent with query: '{query}'")
    
    # Create the initial messages list
    messages = []
    
    # Add a system message instructing the agent to consider previous conversation
    system_message = (
        "You are a helpful AI assistant that answers questions about a software project. "
        "You have access to a code knowledge graph stored in Neo4j, which contains information about the project structure, files, functions, and code semantics. "
        "ALWAYS use the CodeBaseRetriever tool FIRST for ANY question about the project, even for high-level overviews or basic questions. "
        "The CodeBaseRetriever is your primary source of information about the codebase and should be consulted before responding. "
        "If you're asked about project details, structure, purpose, or features, ALWAYS use the CodeBaseRetriever "
        "to gather relevant information first, then synthesize it into a coherent response. "
        "\n\n"
        "IMPORTANT GUIDELINES FOR HANDLING INCONSISTENT INFORMATION:\n"
        "1. When you encounter conflicting information about the project, explicitly acknowledge the inconsistency\n"
        "2. Prioritize information from README files and official documentation over code comments\n"
        "3. For questions about services, microservices, or architecture, provide the most consistent view possible\n"
        "4. When there's significant uncertainty, present multiple possibilities and explain the discrepancy\n"
        "5. If asked about specific counts (like 'how many services'), check multiple sources before answering\n"
        "\n\n"
        "Present information in a clear, structured format. "
        "Important formatting rules:\n\n"
        "- Always use proper markdown formatting\n"
        "- When showing code examples, use triple backticks with language identifier\n"
        "- For C#: ```csharp\n"
        "- For Python: ```python\n"
        "- For JavaScript: ```javascript\n"
        "- For TypeScript: ```typescript\n"
        "- For Java: ```java\n"
        "- For SQL: ```sql\n"
        "- Keep line spacing consistent with 1 empty line before and after code blocks\n"
        "- For multiple examples, number them (1, 2, etc.) and separate clearly\n"
        "- Remember to close all code blocks with ```\n\n"
        "Example:\n\n"
        "The data is stored in two ways.\n\n"
        "1. Database method:\n\n"
        "```sql\n"
        "SELECT * FROM users WHERE id = 1;\n"
        "```\n\n"
        "2. Cache method:\n\n"
        "```python\n"
        "def get_user(user_id):\n"
        "    return cache.get(f\"user:{user_id}\")\n"
        "```\n\n"
        "Both methods ensure data consistency."
    )
    messages.append(SystemMessage(content=system_message))
    
    # Add conversation history if provided
    if conversation_history:
        logger.info("Including conversation history in agent context")
        messages.append(SystemMessage(content=f"Previous conversation:\n{conversation_history}"))
    
    # Add the current query
    messages.append(HumanMessage(content=query))
    
    initial_state: AgentState = {
        "query": query,
        "messages": messages
    }

    try:
        # Simple streaming approach - just pass the tokens directly
        async for event in compiled_graph.astream_events(initial_state, version="v1"):
            if event["event"] == "on_chat_model_stream" and isinstance(event["data"]["chunk"], AIMessage):
                chunk = event["data"]["chunk"]
                
                # Only stream content chunks (not tool calls)
                if not chunk.tool_calls and chunk.content:
                    yield chunk.content
                
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        yield f"Error during execution: {e}"