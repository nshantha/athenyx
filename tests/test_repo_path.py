#!/usr/bin/env python
"""
Test script to verify repository path handling across different URL formats.
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from ingestion.config import ingestion_settings

def test_repo_path_handling():
    """Test repository path handling for different URL formats."""
    test_urls = [
        "https://github.com/GoogleCloudPlatform/microservices-demo.git",
        "https://github.com/GoogleCloudPlatform/microservices-demo",
        "https://github.com/organization/repo-name.git",
        "https://github.com/user/project.name.git",
        "local://my_local_repo",
        "git@github.com:organization/repo-name.git"
    ]
    
    print("Testing repository path handling:")
    print("--------------------------------")
    
    for url in test_urls:
        repo_name = ingestion_settings.extract_repo_name(url)
        repo_path = os.path.join(ingestion_settings.base_clone_dir, repo_name)
        
        # Update clone_dir for verification
        ingestion_settings.ingest_repo_url = url
        ingestion_settings.update_clone_dir()
        
        print(f"\nRepository URL: {url}")
        print(f"Extracted name: {repo_name}")
        print(f"Clone directory: {ingestion_settings.clone_dir}")
        
        # Check if both methods produce the same path
        manual_path = os.path.join(ingestion_settings.base_clone_dir, repo_name)
        print(f"Manual path: {manual_path}")
        print(f"Paths match: {manual_path == ingestion_settings.clone_dir}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_repo_path_handling() 