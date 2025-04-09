# app/agent/graph.py
import logging
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field

from app.core.config import settings
from app.agent.tools import available_tools # Import the instantiated tools

logger = logging.getLogger(__name__)

# --- Agent State ---
class AgentState(TypedDict):
    """Represents the state of our agent graph."""
    query: str                               # The user's input query
    messages: Annotated[Sequence[BaseMessage], operator.add] # Accumulates message history
    # context: Optional[List[Dict[str, Any]]] = None  # Raw retrieved context (optional if storing in messages)
    answer: Optional[str] = None             # The final generated answer
    # Intermediate scratchpad fields if needed for complex reasoning (not used in this simple graph yet)
    # search_queries: Optional[List[str]] = None


# --- LLM Definition ---
# Use a model that supports tool calling
llm = ChatOpenAI(model=settings.openai_llm_model, temperature=0)
# Bind the tools to the LLM instance
llm_with_tools = llm.bind_tools(available_tools)


# --- Node Functions ---

async def call_model(state: AgentState):
    """Invokes the LLM with the current messages and tools."""
    logger.debug(f"Calling LLM. Current messages: {state['messages']}")
    response = await llm_with_tools.ainvoke(state["messages"])
    logger.debug(f"LLM Response: {response}")
    # The response will be an AIMessage possibly containing tool_calls
    return {"messages": [response]}


async def call_tool(state: AgentState):
    """Executes tools based on the last AIMessage."""
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        logger.debug("No tool calls found in the last message.")
        return # Should not happen in a correct flow, but good practice

    tool_messages = []
    tool_map = {tool.name: tool for tool in available_tools}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        logger.info(f"Executing tool: {tool_name} with args: {tool_call['args']}")
        if tool_name not in tool_map:
            logger.warning(f"Tool '{tool_name}' not found.")
            # Return an error message to the model
            tool_messages.append(
                ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_call["id"])
            )
            continue

        selected_tool = tool_map[tool_name]
        try:
            # Use ainvoke for async tools, invoke for sync ones if needed
            # Assuming tools here are async compatible via Tool definition
            tool_output = await selected_tool.ainvoke(tool_call["args"])
            logger.debug(f"Tool '{tool_name}' output length: {len(str(tool_output))}")
            # Truncate if output is excessively long? Add logic here if needed.
            tool_messages.append(
                ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"])
            )
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            tool_messages.append(
                 ToolMessage(content=f"Error executing tool '{tool_name}': {str(e)}", tool_call_id=tool_call["id"])
            )

    return {"messages": tool_messages}


# --- Conditional Edge Logic ---

def should_continue(state: AgentState) -> str:
    """Determines whether to continue calling tools or end."""
    last_message = state["messages"][-1]
    # If the LLM response has tool calls, continue to execute tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "continue"
    # Otherwise, the LLM has provided the final answer
    else:
        # Extract final answer from the last message
        final_answer = last_message.content if isinstance(last_message, AIMessage) else "Error: Could not determine final answer."
        logger.info(f"Agent finished. Final Answer: {final_answer[:200]}...") # Log snippet
        return "end"


# --- Graph Definition ---

def create_agent_graph() -> StateGraph:
    """Builds the LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    # Define nodes
    workflow.add_node("agent", call_model) # Node that calls the LLM
    workflow.add_node("action", call_tool) # Node that executes tools

    # Define edges
    workflow.set_entry_point("agent") # Start with the agent node

    # Conditional edge: After LLM call ('agent'), check if tools need to be run ('should_continue')
    workflow.add_conditional_edges(
        "agent", # Source node
        should_continue, # Function to decide the next node
        {
            "continue": "action", # If tools need to run, go to 'action' node
            "end": END           # If no tools needed (final answer), end the graph
        }
    )

    # Edge: After executing tools ('action'), always go back to the LLM ('agent')
    # so it can process the tool results
    workflow.add_edge("action", "agent")

    logger.info("LangGraph workflow created.")
    return workflow

# Instantiate the graph
agent_graph = create_agent_graph()