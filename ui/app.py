# ui/app.py
import streamlit as st
import requests # Simple library for making HTTP requests
import os
from dotenv import load_dotenv
import logging # Import standard logging

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

# Input field for the user query
user_query = st.text_input("Enter your question:", placeholder="e.g., What does the Email Service do?", key="query_input")

# Submit button
submit_button = st.button("Ask AI Assistant", type="primary")

# --- Logic for Handling Query ---

if submit_button and user_query:
    logger.info(f"UI received query: '{user_query}'")
    # Show a spinner while waiting for the backend response
    with st.spinner("Thinking... 🤔"):
        try:
            # Prepare the request payload
            payload = {"query": user_query}
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            logger.info(f"Sending request to backend: {QUERY_ENDPOINT}")
            # Make the POST request to the backend API
            response = requests.post(QUERY_ENDPOINT, json=payload, headers=headers, timeout=300) # Add timeout (e.g., 5 mins)

            # Check if the request was successful
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

            # Parse the JSON response
            response_data = response.json()
            logger.info(f"Received response from backend: {response_data.get('answer', 'No answer found')[:100]}...") # Log snippet

            # Display the answer
            st.subheader("Answer:")
            st.markdown(response_data.get("answer", "Sorry, I couldn't generate an answer."))

            # Display any error message returned by the agent/backend
            if response_data.get("error"):
                st.error(f"Backend Error: {response_data['error']}")

            # TODO (Post-MVP): Display retrieved context if available and desired
            # if response_data.get("retrieved_context"):
            #     st.subheader("Retrieved Context:")
            #     for chunk in response_data["retrieved_context"]:
            #         # Format context display nicely
            #         st.text_area(label=f"Source: {chunk.get('path', 'N/A')}", value=chunk.get('text', ''), height=100, disabled=True)

        except requests.exceptions.RequestException as req_err:
            logger.error(f"HTTP Request failed: {req_err}", exc_info=True)
            st.error(f"⚠️ Connection Error: Could not reach the backend API at {QUERY_ENDPOINT}. Is it running?")
        except Exception as e:
            logger.error(f"An error occurred in the UI: {e}", exc_info=True)
            st.error("An unexpected error occurred while processing your request.")

elif submit_button and not user_query:
    st.warning("Please enter a question.")