# ui/app.py
import streamlit as st
import requests # Simple library for making HTTP requests
import os
from dotenv import load_dotenv
import logging # Import standard logging
import uuid
from datetime import datetime
import json
import re

# Configure logging for the UI app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file, especially for the API URL
load_dotenv()

# --- Configuration ---
# Get the Backend API URL from environment variable set in docker-compose / .env
# Use a default for local running if the env var isn't set somehow
BACKEND_API_URL = "http://localhost:8000"
QUERY_ENDPOINT = f"{BACKEND_API_URL}/api/query" # Construct the full endpoint URL

# --- Streamlit App Layout ---

st.set_page_config(page_title="AI Knowledge Graph Q&A", layout="wide")
st.title("AI Knowledge Graph Q&A 💬")
st.caption("Ask questions about the indexed software project.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# Helper function to format markdown - simplified version
def format_markdown(text):
    """Simple formatting to ensure markdown renders correctly"""
    # Clean up the text
    text = text.strip()
    
    # Ensure code blocks are properly formatted
    text = re.sub(r'```(\w+)\s+', r'```\1\n', text)  # Fix language markers
    text = re.sub(r'\n\s*```', '\n```', text)  # Fix closing code blocks
    
    return text

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
user_query = st.chat_input("Ask a question about the project...")

# --- Logic for Handling Query ---

if user_query:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_query)
    
    # Display assistant response with a spinner
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            logger.info(f"UI received query: '{user_query}'")
            
            # Prepare conversation history
            conversation_history = ""
            if len(st.session_state.messages) > 1:
                for msg in st.session_state.messages[:-1]:
                    prefix = "User: " if msg["role"] == "user" else "Assistant: "
                    conversation_history += prefix + msg["content"] + "\n\n"
            
            # Prepare request payload
            payload = {
                "query": user_query,
                "conversation_history": conversation_history if conversation_history else None
            }
            headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
            
            # Stream the response
            with requests.post(QUERY_ENDPOINT, json=payload, headers=headers, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            chunk = line[6:]  # Remove 'data: ' prefix
                            # Unescape newlines that were escaped for SSE format
                            chunk = chunk.replace('\\n', '\n').replace('\\"', '"')
                            full_response += chunk
                            message_placeholder.markdown(full_response + "▌")
            
            # Final update without cursor
            message_placeholder.markdown(full_response)
            
            # Add to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except requests.exceptions.RequestException as req_err:
            logger.error(f"HTTP Request failed: {req_err}", exc_info=True)
            error_message = f"⚠️ Connection Error: Could not reach the backend API at {QUERY_ENDPOINT}. Is it running?"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        except Exception as e:
            logger.error(f"An error occurred in the UI: {e}", exc_info=True)
            error_message = "An unexpected error occurred while processing your request."
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Add a button to clear chat history
if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.conversation_id = str(uuid.uuid4())
    st.rerun()