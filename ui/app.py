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
import time

# Configure logging for the UI app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file, especially for the API URL
load_dotenv()

# --- Configuration ---
# Get the Backend API URL from environment variable set in docker-compose / .env
# Use a default for local running if the env var isn't set somehow
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
QUERY_ENDPOINT = f"{BACKEND_API_URL}/api/query" # Construct the full endpoint URL
REPOSITORIES_ENDPOINT = f"{BACKEND_API_URL}/api/repositories" # Repository management endpoint

# --- Streamlit App Layout ---

st.set_page_config(page_title="Actuamind", layout="wide")
st.title("Actuamind 🧠 Enterprise AI Knowledge Platform")

# --- Repository Management ---

# Initialize session state for active repository and chat tracking
if "active_repository" not in st.session_state:
    st.session_state.active_repository = None
if "switching_repository" not in st.session_state:
    st.session_state.switching_repository = False

# Function to fetch repositories from the API
def fetch_repositories():
    try:
        response = requests.get(REPOSITORIES_ENDPOINT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching repositories: {str(e)}")
        return {"repositories": [], "active_repository": None}

# Function to set active repository
def set_active_repository(repo_url):
    try:
        # For URLs with special characters, the encoding is handled by the requests library
        response = requests.post(f"{REPOSITORIES_ENDPOINT}/{repo_url}/activate")
        response.raise_for_status()
        result = response.json()
        if result["success"]:
            st.session_state.active_repository = result["repository"]
            st.session_state.switching_repository = True  # Flag to indicate we're just switching repositories
            st.success(f"Active repository set to: {result['repository']['service_name']}")
            # Force a page reload to update the UI
            st.rerun()
            return True
        else:
            st.error(f"Failed to set active repository: {result['message']}")
            return False
    except Exception as e:
        st.error(f"Error setting active repository: {str(e)}")
        return False

# Function to add new repository
def add_repository(repo_url, branch=None, description=None):
    try:
        payload = {
            "url": repo_url,
            "branch": branch,
            "description": description
        }
        response = requests.post(REPOSITORIES_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json()
        if result["success"]:
            st.session_state.active_repository = result["repository"]
            st.success(f"Repository added: {result['repository']['service_name']}")
            # Set progress to show ingestion is happening
            st.session_state.ingestion_in_progress = True
            st.session_state.ingesting_repo_url = repo_url
            st.session_state.progress_value = 0
            # Force an immediate page refresh to show the new repository
            st.rerun()
            return True
        else:
            st.error(f"Failed to add repository: {result['message']}")
            return False
    except Exception as e:
        st.error(f"Error adding repository: {str(e)}")
        return False

# Function to check repository indexing status
def check_repository_status(repo_url):
    """Check if a repository has been indexed by checking for last_indexed timestamp"""
    try:
        response = requests.get(REPOSITORIES_ENDPOINT)
        response.raise_for_status()
        repo_data = response.json()
        
        # Find the repository
        for repo in repo_data.get("repositories", []):
            if repo.get("url") == repo_url:
                # If it has a last_indexed timestamp, ingestion is complete
                if repo.get("last_indexed"):
                    return True, repo.get("last_indexed")
                else:
                    return False, None
        
        # Repository not found
        return False, None
    except Exception as e:
        st.error(f"Error checking repository status: {str(e)}")
        return False, None

# --- Sidebar Layout ---
with st.sidebar:
    st.header("Repository Management")
    
    # Fetch repositories
    repo_data = fetch_repositories()
    repositories = repo_data.get("repositories", [])
    active_repo = repo_data.get("active_repository")
    
    # Always update session state with active repository from the backend
    # This ensures the UI always shows the correct active repository
    st.session_state.active_repository = active_repo
    
    # Show active repository information
    if st.session_state.active_repository:
        st.subheader("Active Repository")
        repo_info = st.session_state.active_repository
        st.info(f"{repo_info.get('service_name', 'Unknown')}")
        st.caption(f"URL: {repo_info.get('url', 'N/A')}")
        if repo_info.get('description'):
            st.write(repo_info.get('description'))
        if repo_info.get('last_indexed'):
            st.caption(f"Last indexed: {repo_info.get('last_indexed')}")
    
    # Repository selection
    if repositories:
        st.subheader("Select Repository")
        repo_options = [repo.get("service_name", repo.get("url", "Unknown")) for repo in repositories]
        repo_options.append("➕ Add New Repository")
        
        selected_option = st.selectbox("Repositories:", repo_options)
        
        if selected_option == "➕ Add New Repository":
            # Show add repository form
            st.subheader("Add New Repository")
            with st.form("add_repo_form"):
                new_url = st.text_input("Repository URL", "https://github.com/username/repo.git")
                new_branch = st.text_input("Branch (optional)")
                new_desc = st.text_area("Description (optional)")
                
                submitted = st.form_submit_button("Add Repository")
                if submitted:
                    add_repository(new_url, new_branch, new_desc)
        else:
            # Find the selected repository
            selected_repo = next((repo for repo in repositories 
                                 if repo.get("service_name") == selected_option or 
                                    repo.get("url") == selected_option), None)
            
            if selected_repo:
                # Check if this repo is different from the active one (if any)
                active_repo_url = st.session_state.active_repository.get("url", "") if st.session_state.active_repository else ""
                
                if selected_repo.get("url") != active_repo_url:
                    if st.button(f"Set as Active"):
                        # The set_active_repository function will call st.rerun() on success
                        set_active_repository(selected_repo.get("url"))
    else:
        st.warning("No repositories found")
        
        # Show add repository form
        st.subheader("Add New Repository")
        with st.form("add_repo_form"):
            new_url = st.text_input("Repository URL", "https://github.com/username/repo.git")
            new_branch = st.text_input("Branch (optional)")
            new_desc = st.text_area("Description (optional)")
            
            submitted = st.form_submit_button("Add Repository")
            if submitted:
                add_repository(new_url, new_branch, new_desc)
    
    # Display ingestion progress if needed
    if st.session_state.get("ingestion_in_progress", False):
        st.subheader("Ingestion Status")
        
        # Get the repository being ingested
        ingesting_repo_url = st.session_state.get("ingesting_repo_url")
        if ingesting_repo_url:
            # Check actual status from the backend
            indexed, timestamp = check_repository_status(ingesting_repo_url)
            
            if indexed:
                # Ingestion complete
                st.success(f"Repository ingestion completed at {timestamp}")
                st.session_state.ingestion_in_progress = False
                st.session_state.ingesting_repo_url = None
                
                # Add a button to continue
                if st.button("Continue"):
                    st.rerun()
            else:
                # Still in progress
                st.info("Repository ingestion in progress. This may take several minutes depending on repository size.")
                
                # Show indeterminate progress bar
                progress_placeholder = st.empty()
                with progress_placeholder.container():
                    progress_bar = st.progress(0)
                    progress_value = st.session_state.get("progress_value", 0)
                    progress_bar.progress(progress_value)
                    st.session_state.progress_value = (progress_value + 1) % 100
                
                # Add auto-refresh in 10 seconds
                with st.expander("Status Details", expanded=True):
                    st.write("The system is currently:")
                    st.write("1. Cloning the repository")
                    st.write("2. Parsing the code files")
                    st.write("3. Creating embeddings for code chunks")
                    st.write("4. Storing the knowledge graph in Neo4j")
                    
                    refresh_seconds = 10
                    st.write(f"Automatically checking status in {refresh_seconds} seconds...")
                    
                    # Add manual refresh button
                    if st.button("Check Status Now"):
                        st.rerun()
                
                # Auto refresh after delay
                time.sleep(refresh_seconds)
                st.rerun()
    
    # Add divider
    st.divider()
    
    # New Chat button
    if st.button("New Chat"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

# --- Chat Interface ---
st.caption("Ask questions about the indexed software project.")

# Display repository context
if st.session_state.active_repository:
    st.info(f"Currently querying: {st.session_state.active_repository.get('service_name', 'Unknown repository')}")
else:
    st.warning("No active repository selected. Please select a repository from the sidebar.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# Check if we're switching repositories, and if so, handle it
if st.session_state.get("switching_repository", False):
    # Clear the switching flag but keep the chat history
    st.session_state.switching_repository = False
    # Add a system message indicating repository changed
    if st.session_state.active_repository:
        repo_name = st.session_state.active_repository.get('service_name', 'Unknown')
        if st.session_state.messages and len(st.session_state.messages) > 0:
            st.session_state.messages.append({
                "role": "assistant", 
                "content": f"*Repository context switched to: {repo_name}*"
            })

# Show project information if no messages yet
if len(st.session_state.messages) == 0:
    st.markdown("""
    ## Welcome to Actuamind
    
    Actuamind is an Enterprise AI Knowledge Platform that helps you understand and navigate complex codebases.
    
    ### Getting Started
    
    1. **Add a repository** - Use the sidebar to add a Git repository you want to analyze
    2. **Select a repository** - Set a repository as active to query it
    3. **Ask questions** - Inquire about code structure, functionality, architecture, or specific files
    
    ### Example Questions
    
    - What are the main services in this repository?
    - How is the project structured?
    - Explain the authentication flow in the code
    - What technology stack is used in this project?
    - Show me the implementation of [specific function]
    """)

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
user_query = st.chat_input("Ask a question about the project..." if st.session_state.active_repository else "Please select a repository first")

# --- Logic for Handling Query ---

if user_query and st.session_state.active_repository:
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
                "conversation_history": conversation_history if conversation_history else None,
                "repository_url": st.session_state.active_repository.get("url")
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

# Add footer with credits
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; opacity: 0.7; font-size: 0.8em;">
        <p>Actuamind - Enterprise AI Knowledge Platform</p>
    </div>
    """, 
    unsafe_allow_html=True
)