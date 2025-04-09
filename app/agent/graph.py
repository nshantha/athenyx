# app/agent/graph.py
import logging
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence, NotRequired
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
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
    # context: NotRequired[List[Dict[str, Any]]]  # Raw retrieved context (optional if storing in messages)
    answer: NotRequired[str]             # The final generated answer
    # Intermediate scratchpad fields if needed for complex reasoning (not used in this simple graph yet)
    # search_queries: NotRequired[List[str]]
    error: NotRequired[str]              # Error message if something went wrong


# --- LLM Definition ---
# Use a model that supports tool calling with streaming enabled
llm = ChatOpenAI(model=settings.openai_llm_model, temperature=0, streaming=True)
# Bind the tools to the LLM instance
llm_with_tools = llm.bind_tools(available_tools)


# --- Node Functions ---

async def call_model(state: AgentState):
    """Invokes the LLM with the current messages and tools."""
    logger.debug(f"Calling LLM. Current messages: {state['messages']}")
    
    # If this is the first call and it's a high-level query, add a hint to use appropriate tools
    if len(state["messages"]) == 3:  # Only the system message, optional history, and user query
        query = state["query"].lower()
        
        # Check if this is a query about project structure or services
        is_project_structure_query = any(term in query for term in [
            "overview", "about", "what is", "purpose", "high-level", "features", 
            "how many", "architecture", "summary", "microservices", "services"
        ])
        
        # Check for graph structure questions
        is_graph_structure_query = any(term in query for term in [
            "relationship", "connected", "depends on", "structure", "relationship", 
            "organization", "architecture", "graph", "dependency"
        ])
        
        if is_graph_structure_query:
            # Recommend the KnowledgeGraph tool for graph relationship queries
            hint_message = SystemMessage(content=(
                "IMPORTANT: This appears to be a question about code relationships or project structure. "
                "You should use the KnowledgeGraph tool FIRST to analyze structural relationships in the code, "
                "then use the CodeBaseRetriever for additional details. The KnowledgeGraph tool "
                "provides insights based on graph relationships rather than just text similarity."
            ))
            state["messages"].append(hint_message)
            logger.info("Added KnowledgeGraph tool hint for structural query")
        elif is_project_structure_query:
            # For specific counts or service questions, suggest ProjectInfo tool
            if any(term in query for term in ["how many", "microservice", "service"]):
                hint_message = SystemMessage(content=(
                    "IMPORTANT: This appears to be a question about the project's services or microservices. "
                    "You should use the ProjectInfo tool FIRST to get information about the services, "
                    "then use the KnowledgeGraph tool with query_type='services' to analyze service relationships, "
                    "and finally use the CodeBaseRetriever if you need additional details."
                ))
            else:
                # For general project questions, suggest CodeBaseRetriever first, then ProjectInfo
                hint_message = SystemMessage(content=(
                    "IMPORTANT: This appears to be a high-level question about the project. "
                    "You should use the CodeBaseRetriever tool FIRST to gather detailed information, "
                    "and then consider using the ProjectInfo tool to get high-level information. "
                    "Combine both sources to provide a comprehensive answer and highlight any inconsistencies."
                ))
                
            state["messages"].append(hint_message)
            logger.info("Added tool hint for high-level query")
    
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