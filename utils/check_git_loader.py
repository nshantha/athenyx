#!/usr/bin/env python
"""
Script to check if GitLoader is finding protobuf files
"""
from ingestion.sources.git_loader import GitLoader

def check_git_loader():
    """Check if GitLoader is finding protobuf files"""
    # Initialize GitLoader with the microservices-demo repository
    repo_url = "https://github.com/GoogleCloudPlatform/microservices-demo"
    loader = GitLoader(repo_url=repo_url, branch="main")
    
    # Get repository and commit
    repo, commit_sha = loader.get_repo_and_commit()
    print(f"Repository cloned/updated at commit: {commit_sha}")
    
    # Get all files with .proto extension
    target_extensions = [".proto"]
    proto_files = loader.get_files_content(target_extensions)
    
    # Print results
    print(f"\nFound {len(proto_files)} protobuf files:")
    for file_path, _ in proto_files:
        print(f"- {file_path}")
    
    # Check if files are being properly loaded
    if proto_files:
        print("\nSample content from first protobuf file:")
        sample_path, sample_content = proto_files[0]
        print(f"\nFile: {sample_path}")
        print("First 200 characters:")
        print(sample_content[:200])
        
        # Check if the file contains message or service definitions
        message_count = sample_content.count("message ")
        service_count = sample_content.count("service ")
        print(f"\nFound {message_count} message definitions and {service_count} service definitions in the sample file")

if __name__ == "__main__":
    check_git_loader() 