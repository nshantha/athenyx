#!/usr/bin/env python
"""
Wrapper script to run the Streamlit app with proper error handling
"""
import os
import sys
import subprocess

def run_streamlit_app():
    """Run the Streamlit app with proper error handling"""
    try:
        # Try to run the app directly
        print("Starting Actuamind UI...")
        cmd = ["streamlit", "run", "ui/app.py", "--server.port", "8501"]
        subprocess.run(cmd, check=True)
    except PermissionError as e:
        print(f"Permission error: {e}")
        print("Changing to home directory and trying again...")
        
        # Change to home directory
        os.chdir(os.path.expanduser("~"))
        print(f"Working directory changed to: {os.getcwd()}")
        
        # Get the absolute path to the app.py file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(script_dir, "ui", "app.py")
        
        # Run with absolute path
        print(f"Running Streamlit with absolute path: {app_path}")
        cmd = ["streamlit", "run", app_path, "--server.port", "8501"]
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Error running Streamlit app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_streamlit_app() 