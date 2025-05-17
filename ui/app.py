# ui/app.py
import streamlit as st
import requests # Simple library for making HTTP requests
import os
import sys
from dotenv import load_dotenv
import logging # Import standard logging
import uuid
from datetime import datetime
import json
import re
import threading
import time
import subprocess # Import for Git command execution

# Handle permission errors that might occur when accessing the current working directory
try:
# Configure logging for the UI app
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Load environment variables from .env file, especially for the API URL
    load_dotenv()
except PermissionError as e:
    # If we can't access the current directory, change to a directory we likely have access to
    os.chdir(os.path.expanduser("~"))  # Change to user's home directory
    print(f"Changed working directory to {os.getcwd()} due to permission error")
    
    # Try again with the new directory
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    load_dotenv()

# --- Configuration ---
# Get the Backend API URL from environment variable set in docker-compose / .env
# Use a default for local running if the env var isn't set somehow
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
QUERY_ENDPOINT = f"{BACKEND_API_URL}/api/query" # Construct the full endpoint URL
REPOSITORIES_ENDPOINT = f"{BACKEND_API_URL}/api/repositories" # Repository management endpoint

# Initialize session state for auto-refresh
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False  # Default to off

if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = 10  # Increase refresh interval to 10 seconds

# Initialize session state for repository refresh throttling
if "last_repo_fetch" not in st.session_state:
    st.session_state.last_repo_fetch = 0

# --- Streamlit App Layout ---

st.set_page_config(
    page_title="Actuamind", 
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/niteshx/actuamind',
        'Report a bug': 'https://github.com/niteshx/actuamind/issues',
        'About': 'Actuamind: Enterprise AI Knowledge Platform'
    }
)

# Add global styling
st.markdown("""
<style>
    /* Main app styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Custom app header styling */
    .app-header {
        background: linear-gradient(90deg, #1E1E1E 0%, #2C2C2C 100%);
        margin: -1rem -1rem 1rem -1rem;
        padding: 1.5rem 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
    }
    
    .app-logo {
        font-size: 32px;
        font-weight: bold;
        background: linear-gradient(90deg, #4CAF50 0%, #66BB6A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-right: 10px;
    }
    
    .app-subtitle {
        color: rgba(255, 255, 255, 0.8);
        font-size: 18px;
        margin-left: 10px;
    }
    
    /* Welcome section styling */
    .welcome-container {
        background-color: rgba(30, 30, 30, 0.5);
        border-radius: 10px;
        padding: 30px;
        margin-bottom: 30px;
        border: 1px solid rgba(76, 175, 80, 0.2);
    }
    
    .welcome-heading {
        color: #4CAF50;
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    
    .welcome-description {
        color: rgba(255, 255, 255, 0.9);
        font-size: 18px;
        margin-bottom: 30px;
        line-height: 1.5;
    }
    
    .feature-section {
        margin-top: 20px;
        margin-bottom: 40px;
    }
    
    .feature-card {
        background-color: rgba(30, 30, 30, 0.6);
        border-radius: 10px;
        padding: 20px;
        height: 100%;
        border-left: 3px solid #4CAF50;
        transition: transform 0.2s;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
    }
    
    .feature-icon {
        font-size: 28px;
        margin-bottom: 15px;
        color: #4CAF50;
    }
    
    .feature-title {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #fff;
    }
    
    .feature-description {
        color: rgba(255, 255, 255, 0.8);
        font-size: 16px;
    }
    
    /* Example question styling */
    .examples-container {
        background-color: rgba(30, 30, 30, 0.5);
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 30px;
        border: 1px solid rgba(41, 121, 255, 0.2);
    }
    
    .examples-heading {
        color: #2979FF;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    
    .example-button {
        background-color: rgba(41, 121, 255, 0.1);
        color: white;
        border: 1px solid rgba(41, 121, 255, 0.3);
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 10px;
        cursor: pointer;
        font-size: 16px;
        transition: background-color 0.2s;
    }
    
    .example-button:hover {
        background-color: rgba(41, 121, 255, 0.2);
    }
    
    /* Sidebar styling */
    .sidebar-header {
        color: #4CAF50;
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(76, 175, 80, 0.3);
    }
    
    .sidebar-section {
        margin-bottom: 30px;
    }
    
    /* Repository status styling */
    .status-container {
        background-color: rgba(41, 121, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .status-header {
        color: #2979FF;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    
    .status-card {
        background-color: rgba(30, 30, 30, 0.6);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    
    /* Ingestion status styling */
    .ingestion-container {
        background-color: rgba(255, 152, 0, 0.05);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 152, 0, 0.2);
    }
    
    .ingestion-header {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 15px;
        color: #ff9800;
    }
    
    .ingestion-repo-title {
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 10px;
        color: #ff9800;
    }
    
    .ingestion-info {
        background-color: rgba(255, 152, 0, 0.1);
        padding: 12px;
        border-radius: 8px;
        font-size: 15px;
        margin: 12px 0;
    }
    
    /* Footer styling */
    .app-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #1E1E1E;
        padding: 0.5rem;
        text-align: center;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
    }
    
    /* Hide default Streamlit footer */
    footer {
        visibility: hidden;
    }
    
    /* Fix for raw HTML tags showing */
    .stMarkdown div {
        overflow-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)

# --- Main App Content ---

# --- Repository Management ---

# Initialize session state for active repository and chat tracking
if "active_repository" not in st.session_state:
    st.session_state.active_repository = None
if "switching_repository" not in st.session_state:
    st.session_state.switching_repository = False
if "repositories_ingesting" not in st.session_state:
    st.session_state.repositories_ingesting = {}
if "last_status_check" not in st.session_state:
    st.session_state.last_status_check = {}

# --- Streamlit App Header ---
st.markdown("""
<div class="app-header">
    <span class="app-logo">Actuamind</span>
    <span class="app-brain">🧠</span>
    <span class="app-subtitle">Enterprise AI Knowledge Platform</span>
</div>
""", unsafe_allow_html=True)

# Function to verify if a Git repository exists
def verify_git_repository(repo_url):
    """
    Verify if a Git repository exists and is accessible.
    Returns (success, message) tuple.
    """
    try:
        # Use git ls-remote to check if the repository exists without cloning it
        result = subprocess.run(
            ["git", "ls-remote", repo_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10  # Timeout after 10 seconds
        )
        
        if result.returncode == 0:
            return True, "Repository verified successfully"
        else:
            error_message = result.stderr.strip()
            return False, f"Invalid repository: {error_message}"
    except subprocess.TimeoutExpired:
        return False, "Repository verification timed out. The server might be slow or unreachable."
    except subprocess.SubprocessError as e:
        return False, f"Error verifying repository: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

# Function to fetch repositories from the API
def fetch_repositories():
    # Check if we should throttle requests
    current_time = time.time()
    if (current_time - st.session_state.last_repo_fetch) < 5:  # 5 second throttle
        if "cached_repositories" in st.session_state:
            return st.session_state.cached_repositories
        
    try:
        response = requests.get(REPOSITORIES_ENDPOINT)
        response.raise_for_status()
        result = response.json()
        
        # Update cache and timestamp
        st.session_state.cached_repositories = result
        st.session_state.last_repo_fetch = current_time
        
        return result
    except Exception as e:
        st.error(f"Error fetching repositories: {str(e)}")
        # Return cached data if available, otherwise empty result
        return st.session_state.get("cached_repositories", {"repositories": [], "active_repository": None})

# Function to set active repository
def set_active_repository(repo_url):
    try:
        # For URLs with special characters, the encoding is handled by the requests library
        response = requests.post(f"{REPOSITORIES_ENDPOINT}/{repo_url}/activate")
        response.raise_for_status()
        result = response.json()
        if result["success"]:
            # Store previous repository for context change message
            previous_repo = st.session_state.active_repository
            
            # Update active repository
            st.session_state.active_repository = result["repository"]
            st.session_state.switching_repository = True  # Flag to indicate we're just switching repositories
            
            # Do NOT clear conversation history, just add a context switch message
            if previous_repo and previous_repo.get("url") != repo_url and "messages" in st.session_state:
                # Add a system message indicating repository changed
                repo_name = result["repository"].get('service_name', 'Unknown')
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"*Repository context switched to: {repo_name}*"
                })
            
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
        # Check if the URL is empty
        if not repo_url or repo_url.strip() == "":
            st.error("Repository URL cannot be empty.")
            return False
            
        # First verify if the repository exists
        st.info("Verifying repository accessibility...")
        is_valid, message = verify_git_repository(repo_url)
        if not is_valid:
            st.error(f"Repository validation failed: {message}")
            return False
        
        st.info("Repository verified. Submitting for ingestion...")    
        payload = {
            "url": repo_url,
            "branch": branch,
            "description": description
        }
        response = requests.post(REPOSITORIES_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json()
        if result["success"]:
            # Add to ingesting repositories list without affecting current active repository
            service_name = result["repository"].get("service_name", "Repository")
            st.session_state.repositories_ingesting[repo_url] = {
                "service_name": service_name,
                "start_time": datetime.now().isoformat(),
                "progress_value": 0,
                "status_checks": 0,  # Track how many times we've checked
                "last_progress": 0   # Track last progress to detect stalls
            }
            
            # Display a success message that makes it clear ingestion is happening in background
            st.success(f"""Repository '{service_name}' added and is being ingested in the background. 
                      You can continue using your current repository while ingestion completes.
                      
                      Check the 'Repository Ingestion Status' section for progress updates.""")
            
            logger.info(f"Added repository {repo_url} for ingestion")
            
            # Force a rerun to start showing the ingestion status section
            time.sleep(1)
            st.rerun()
            
            return True
        else:
            st.error(f"Failed to add repository: {result['message']}")
            return False
    except Exception as e:
        st.error(f"Error adding repository: {str(e)}")
        logger.error(f"Error adding repository: {str(e)}", exc_info=True)
        return False

# Function to check repository indexing status
def check_repository_status(repo_url):
    """Check if a repository has been indexed by checking for last_indexed timestamp"""
    try:
        logger.info(f"Checking ingestion status for repository: {repo_url}")
        response = requests.get(REPOSITORIES_ENDPOINT)
        response.raise_for_status()
        repo_data = response.json()
        
        # Find the repository
        for repo in repo_data.get("repositories", []):
            if repo.get("url") == repo_url:
                # If it has a last_indexed timestamp, ingestion is complete
                if repo.get("last_indexed"):
                    logger.info(f"Repository {repo_url} has been indexed at {repo.get('last_indexed')}")
                    return True, repo.get("last_indexed"), None
                else:
                    # Check how long it's been since ingestion started
                    start_time = st.session_state.repositories_ingesting.get(repo_url, {}).get("start_time")
                    if start_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time)
                            elapsed = datetime.now() - start_dt
                            elapsed_seconds = elapsed.total_seconds()
                            elapsed_str = f"{int(elapsed_seconds // 60)} minutes {int(elapsed_seconds % 60)} seconds"
                            
                            # If more than 30 minutes have passed, consider it complete 
                            # to avoid getting stuck indefinitely
                            if elapsed_seconds > 1800:  # 30 minutes
                                logger.warning(f"Repository {repo_url} ingestion has been running for over 30 minutes, marking as complete")
                                return True, datetime.now().isoformat(), None
                        except Exception as e:
                            logger.error(f"Error calculating elapsed time: {str(e)}")
                            elapsed_str = "unknown time"
                            elapsed_seconds = 30  # Default to avoid division by zero
                    else:
                        elapsed_str = "unknown time"
                        elapsed_seconds = 30  # Default value
                    
                    # Calculate progress based on elapsed time (rough estimation)
                    # Assuming ingestion takes about 5 minutes on average
                    max_expected_time = 300  # 5 minutes in seconds
                    progress = min(95, (elapsed_seconds / max_expected_time) * 100) if 'elapsed_seconds' in locals() else 30
                    
                    logger.info(f"Repository {repo_url} still being ingested, elapsed: {elapsed_str}, progress: {progress:.1f}%")
                    return False, None, {"elapsed": elapsed_str, "progress": progress}
        
        # Repository not found
        logger.warning(f"Repository {repo_url} not found in API response")
        return False, None, None
    except Exception as e:
        logger.error(f"Error checking repository status: {str(e)}")
        return False, None, None

# --- Sidebar Layout ---
with st.sidebar:
    st.markdown('<div class="sidebar-header">Repository Management</div>', unsafe_allow_html=True)
    
    # Fetch repositories
    repo_data = fetch_repositories()
    repositories = repo_data.get("repositories", [])
    active_repo = repo_data.get("active_repository")
    
    # Always update session state with active repository from the backend
    # This ensures the UI always shows the correct active repository
    st.session_state.active_repository = active_repo
    
    # Show active repository information in sidebar-section
    if st.session_state.active_repository:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight: bold; color: #4CAF50; margin-bottom: 10px;">Active Repository</div>', unsafe_allow_html=True)
        
        repo_info = st.session_state.active_repository
        st.markdown(f"""
        <div class="status-card" style="background-color: rgba(76, 175, 80, 0.1); border-left: 2px solid #4CAF50;">
            <div style="font-weight: bold; font-size: 16px;">{repo_info.get('service_name', 'Unknown')}</div>
            <div style="font-size: 12px; word-break: break-all; color: rgba(255, 255, 255, 0.7);">URL: {repo_info.get('url', 'N/A')}</div>
        """, unsafe_allow_html=True)
        
        if repo_info.get('description'):
            st.markdown(f"""<div style="margin-top: 8px; font-size: 14px;">{repo_info.get('description')}</div>""", unsafe_allow_html=True)
            
        if repo_info.get('last_indexed'):
            st.markdown(f"""<div style="font-size: 12px; margin-top: 8px; color: rgba(255, 255, 255, 0.5);"><span style="color: #4CAF50;">✓</span> Indexed: {repo_info.get('last_indexed')}</div>""", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Repository selection in sidebar-section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    
    if repositories:
        st.markdown('<div style="font-weight: bold; color: #4CAF50; margin-bottom: 10px;">Select Repository</div>', unsafe_allow_html=True)
        
        repo_options = [repo.get("service_name", repo.get("url", "Unknown")) for repo in repositories]
        repo_options.append("➕ Add New Repository")
        
        selected_option = st.selectbox("Select a repository", repo_options, label_visibility="collapsed")
        
        if selected_option == "➕ Add New Repository":
            # Show add repository form with improved styling
            st.markdown('<div style="margin-top: 20px; font-weight: bold; color: #4CAF50; margin-bottom: 10px;">Add New Repository</div>', unsafe_allow_html=True)
            
            with st.form("add_repo_form"):
                new_url = st.text_input("Repository URL :red[*]", placeholder="https://github.com/username/repository.git")
                new_branch = st.text_input("Branch (optional)", placeholder="main")
                new_desc = st.text_area("Description (optional)", placeholder="Description of this repository")
                
                submitted = st.form_submit_button("Add Repository", use_container_width=True)
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
                    last_indexed = selected_repo.get("last_indexed", "")
                    status_text = f"Indexed: {last_indexed}" if last_indexed else "Not indexed yet"
                    
                    st.markdown(f"""
                    <div style="background-color: rgba(41, 121, 255, 0.1); padding: 12px; border-radius: 8px; margin: 8px 0 12px 0; border: 1px solid rgba(41, 121, 255, 0.2);">
                        <div style="font-weight: bold; font-size: 15px; margin-bottom: 6px;">{selected_repo.get('service_name')}</div>
                        <div style="font-size: 12px; color: rgba(255, 255, 255, 0.7);">{status_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Set as Active Repository", use_container_width=True, type="primary"):
                        # The set_active_repository function will call st.rerun() on success
                        set_active_repository(selected_repo.get("url"))
    else:
        st.warning("No repositories found")
        
        # Show add repository form
        st.markdown('<div style="margin-top: 20px; font-weight: bold; color: #4CAF50; margin-bottom: 10px;">Add New Repository</div>', unsafe_allow_html=True)
        
        with st.form("add_repo_form"):
            new_url = st.text_input("Repository URL :red[*]", placeholder="https://github.com/username/repository.git")
            new_branch = st.text_input("Branch (optional)", placeholder="main")
            new_desc = st.text_area("Description (optional)", placeholder="Description of this repository")
            
            submitted = st.form_submit_button("Add Repository", use_container_width=True)
            if submitted:
                add_repository(new_url, new_branch, new_desc)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add divider and New Chat button
    st.divider()
    
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    
    # Style the New Chat button to match our new styling
    if st.button("New Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()
    
    # Add a simple reset button as well
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Ingestion Status Section ---
# This is now separate from the sidebar to prevent UI freezing
if st.session_state.repositories_ingesting:
    st.markdown("""
    <style>
    .ingestion-header {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 15px;
        color: #ff9800;
    }
    .ingestion-container {
        background-color: rgba(255, 152, 0, 0.05);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 152, 0, 0.2);
    }
    .ingestion-repo-title {
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 10px;
        color: #ff9800;
    }
    .ingestion-info {
        background-color: rgba(255, 152, 0, 0.1);
        padding: 10px;
        border-radius: 5px;
        font-size: 14px;
        margin: 10px 0;
    }
    .refresh-controls {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 15px;
    }
    </style>
    
    <div class="ingestion-container">
        <div class="ingestion-header">Repository Ingestion Status</div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh toggle with improved styling
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
        <div style="color: rgba(255, 255, 255, 0.8); font-size: 14px;">
            Status updates every {st.session_state.refresh_interval} seconds
        </div>
        """, unsafe_allow_html=True)
    with col2:
        auto_refresh = st.toggle("Auto-refresh", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
            
    # Allow user to configure refresh interval with improved styling
    st.markdown('<div style="margin-bottom: 20px;">', unsafe_allow_html=True)
    st.session_state.refresh_interval = st.slider(
        "Refresh interval", 
        min_value=5, 
        max_value=60, 
        value=st.session_state.refresh_interval,
        format="%d seconds"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create columns for better layout
    cols = st.columns(2)
    
    # Check repositories that are being ingested
    repos_to_remove = []
    current_time = datetime.now()
    
    for idx, (repo_url, repo_info) in enumerate(st.session_state.repositories_ingesting.items()):
        col_idx = idx % 2
        with cols[col_idx]:
            st.markdown(f"""
            <div class="ingestion-repo-title">{repo_info.get('service_name', 'Repository')}</div>
            """, unsafe_allow_html=True)
            
            # Check status based on refresh interval
            check_interval = st.session_state.refresh_interval if st.session_state.auto_refresh else 30
            last_check = st.session_state.last_status_check.get(repo_url, 0)
            if time.time() - last_check > check_interval:
                repo_info["status_checks"] = repo_info.get("status_checks", 0) + 1
                
                indexed, timestamp, progress_info = check_repository_status(repo_url)
                st.session_state.last_status_check[repo_url] = time.time()
                
                if indexed:
                    st.success(f"✅ Ingestion completed at {timestamp}")
                    repos_to_remove.append(repo_url)
                    # Button to activate the repository
                    if st.button(f"Set {repo_info.get('service_name')} as Active", key=f"activate_{repo_url}", use_container_width=True):
                        set_active_repository(repo_url)
                    continue
                
                # Update progress information
                if progress_info:
                    # Store previous progress to detect stalls
                    last_progress = repo_info.get("progress_value", 0)
                    repo_info["last_progress"] = last_progress
                    
                    repo_info["elapsed"] = progress_info.get("elapsed", "calculating...")
                    repo_info["progress_value"] = progress_info.get("progress", 30)
                    
                    # Check if progress is stalled (same progress for 3+ checks)
                    if (repo_info.get("status_checks", 0) > 3 and 
                        abs(repo_info.get("progress_value", 0) - repo_info.get("last_progress", 0)) < 1):
                        repo_info["potentially_stalled"] = True
            
            # Get start_time from repo_info to calculate elapsed time even between refreshes
            start_time = repo_info.get("start_time")
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    elapsed = datetime.now() - start_dt
                    elapsed_seconds = elapsed.total_seconds()
                    elapsed_minutes = int(elapsed_seconds // 60)
                    elapsed_hours = int(elapsed_minutes // 60)
                    
                    # After 45 minutes, consider it potentially stuck
                    if elapsed_minutes > 45:
                        repo_info["potentially_stalled"] = True
                    
                    # Format elapsed time more clearly
                    if elapsed_hours > 0:
                        repo_info["elapsed"] = f"{elapsed_hours}h {elapsed_minutes % 60}m"
                    else:
                        repo_info["elapsed"] = f"{elapsed_minutes}m {int(elapsed_seconds % 60)}s"
                except:
                    pass
            
            # Check for potential stall
            is_stalled = repo_info.get("potentially_stalled", False)
            
            # Show progress bar with elapsed time
            if is_stalled:
                st.warning("⚠️ Ingestion may be stalled")
                # Use a different color for stalled progress
                st.markdown(f"""
                <div style="height: 20px; background-color: rgba(255, 152, 0, 0.2); border-radius: 3px; margin-bottom: 10px;">
                    <div style="width: {int(repo_info.get('progress_value', 30))}%; 
                                height: 100%; 
                                background-color: #ff9800; 
                                border-radius: 3px;"></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                progress_bar = st.progress(int(repo_info.get("progress_value", 30)))
            
            # Update status message
            if is_stalled:
                st.markdown(f"""
                <div class="ingestion-info" style="border-left: 3px solid #ff9800;">
                    <div>⚠️ Ingestion might be stalled or taking longer than expected</div>
                    <div>⏱️ Elapsed time: {repo_info.get('elapsed', 'calculating...')}</div>
                    <div style="margin-top: 8px; font-size: 12px;">You can try clicking "Set as Active" to use the repository even if ingestion is incomplete</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Set {repo_info.get('service_name')} as Active Anyway", key=f"force_activate_{repo_url}", use_container_width=True):
                    repos_to_remove.append(repo_url)
                    set_active_repository(repo_url)
            else:
                st.markdown(f"""
                <div class="ingestion-info">
                    <div>⏳ Ingestion in progress...</div>
                    <div>⏱️ Elapsed time: {repo_info.get('elapsed', 'calculating...')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.caption("You can continue using the app while ingestion completes.")
    
    # Remove completed repositories
    for repo_url in repos_to_remove:
        del st.session_state.repositories_ingesting[repo_url]
        if repo_url in st.session_state.last_status_check:
            del st.session_state.last_status_check[repo_url]
    
    # Auto-refresh logic
    if st.session_state.auto_refresh and st.session_state.repositories_ingesting:
        if "last_auto_refresh" not in st.session_state:
            st.session_state.last_auto_refresh = 0
            
        # Show time until next refresh
        time_since_refresh = time.time() - st.session_state.last_auto_refresh
        time_until_next = max(0, st.session_state.refresh_interval - time_since_refresh)
        
        st.markdown(f"""
        <div style="text-align: center; margin-top: 15px; color: rgba(255, 255, 255, 0.6);">
            Next refresh in {int(time_until_next)} seconds
        </div>
        """, unsafe_allow_html=True)
        
        # Don't rerun too frequently
        if time.time() - st.session_state.last_auto_refresh > st.session_state.refresh_interval:
            st.session_state.last_auto_refresh = time.time()
            time.sleep(0.5)  # Small delay to ensure UI updates
            st.rerun()
    
    # Close the container div
    st.markdown('</div>', unsafe_allow_html=True)

# --- Chat Interface ---
st.markdown("""
<div style="margin-bottom: 20px; color: rgba(255, 255, 255, 0.7); font-size: 16px; display: flex; align-items: center;">
    <span style="margin-right: 8px;">💬</span> Ask questions about code, architecture, or functionality in natural language
</div>
""", unsafe_allow_html=True)

# Display repository context
if st.session_state.active_repository:
    repo_name = st.session_state.active_repository.get('service_name', 'Unknown repository')
    repo_url = st.session_state.active_repository.get('url', '')
    
    # Create a more visually appealing repository context indicator
    st.markdown(f"""
    <div class="status-container">
        <h3 class="status-header">Active Repository Context</h3>
        <div class="status-card">
            <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">{repo_name}</div>
            <div style="color: rgba(255, 255, 255, 0.7); font-size: 14px; word-break: break-all;">{repo_url}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show a badge if other repositories are being ingested in parallel
    if st.session_state.repositories_ingesting:
        ingesting_count = len(st.session_state.repositories_ingesting)
        st.markdown(f"""
        <div style="
            background-color: rgba(255, 152, 0, 0.2); 
            color: white; 
            padding: 10px 16px; 
            border-radius: 8px; 
            margin-bottom: 20px;
            border: 1px solid rgba(255, 152, 0, 0.3);
            font-weight: bold;
            display: inline-block;">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 20px; margin-right: 10px;">📊</span>
                <span>{ingesting_count} repository/repositories being ingested in background</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
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
    # Note: Message is already added in the set_active_repository function

# Show project information if no messages yet
if len(st.session_state.messages) == 0:
    # Create a clean welcome section using our new styling
    st.markdown("""
    <div class="welcome-container">
        <h1 class="welcome-heading">Welcome to Actuamind 🧠</h1>
        <p class="welcome-description">Actuamind is an Enterprise AI Knowledge Platform that helps you understand and navigate complex codebases through a natural language interface.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature section with cards
    st.markdown('<div class="feature-section">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">Navigate Complex Codebases</div>
            <p class="feature-description">Ask questions about code structure, functionality, architecture, and specific implementations.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Multi-Repository Support</div>
            <p class="feature-description">Index and query across multiple repositories with context switching.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔄</div>
            <div class="feature-title">Seamless Integration</div>
            <p class="feature-description">Add new repositories without interrupting your current work context.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Example questions section
    st.markdown("""
    <div class="examples-container">
        <h3 class="examples-heading">Try asking questions like:</h3>
    """, unsafe_allow_html=True)
    
    # Create clickable example questions
    example_questions = [
        "What are the main services in this repository?",
        "Explain the authentication flow in the code",
        "How is the project structured?",
        "What are the main API endpoints?",
        "Show me the implementation of the main service class"
    ]
    
    # Display example questions in a 2-column layout
    example_cols = st.columns(2)
    for i, question in enumerate(example_questions):
        with example_cols[i % 2]:
            if st.button(question, key=f"example_{question}", use_container_width=True):
                # This will be picked up by the chat input
                st.session_state.messages.append({"role": "user", "content": question})
                # Force a rerun to process the question
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

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

# Add footer with better styling
st.markdown("""
<div class="app-footer">
    <div>Actuamind - Enterprise AI Knowledge Platform</div>
    <div>🌐 <a href="https://github.com/nshantha/actuamind" target="_blank" style="color: #4CAF50; text-decoration: none;">GitHub</a> | Made with ❤️ for developers</div>
</div>
""", unsafe_allow_html=True)