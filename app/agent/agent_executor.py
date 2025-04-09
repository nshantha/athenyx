# app/agent/agent_executor.py
import logging
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, AIMessage 

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

async def run_agent(query: str) -> AgentState:
    """Runs the compiled agent graph with the user query."""
    if compiled_graph is None:
         logger.error("Agent graph is not compiled. Cannot run agent.")
         # Return a state indicating error
         return AgentState(query=query, messages=[], answer="Error: Agent graph failed to compile.", error="Agent graph compilation failed")

    logger.info(f"Running agent with query: '{query}'")
    initial_state: AgentState = {
        "query": query,
        "messages": [HumanMessage(content=query)]
    }

    final_state = None
    try:
        # Use ainvoke for asynchronous execution
        async for output in compiled_graph.astream(initial_state):
            # stream() yields intermediate states. We are interested in the final one.
            # The final state is the one prior to the END node being reached.
            # LangGraph streaming typically yields states keyed by node name.
            # We can just grab the last value emitted before END.
            # logger.debug(f"Agent stream output: {output}") # Optional: Log intermediate steps
            # The last output before END should contain the final state under the last active node key
             last_node = list(output.keys())[-1]
             final_state = output[last_node]


        if final_state and final_state.get("messages"):
             last_message = final_state["messages"][-1]
             # Extract answer from the last AIMessage
             if isinstance(last_message, AIMessage):
                 final_state["answer"] = last_message.content
             else:
                 final_state["answer"] = "Error: Agent execution did not end with an AIMessage."
                 final_state["error"] = "Agent execution ended unexpectedly." # Add error field
             logger.info("Agent execution finished.")
             return final_state
        else:
             logger.error("Agent execution finished with no final state or messages.")
             return AgentState(query=query, messages=initial_state["messages"], answer="Error: Agent failed to produce a final state.", error="Agent execution failed")

    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        return AgentState(query=query, messages=initial_state["messages"], answer=f"Error during execution: {e}", error=str(e))