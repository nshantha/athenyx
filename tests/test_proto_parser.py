#!/usr/bin/env python
"""
Script to test SimpleParser with protobuf files
"""
import os
import json
from ingestion.sources.git_loader import GitLoader
from ingestion.parsing.simple_parser import SimpleParser

def test_proto_parser():
    """Test SimpleParser with protobuf files"""
    # Initialize GitLoader with the microservices-demo repository
    repo_url = "https://github.com/GoogleCloudPlatform/microservices-demo"
    loader = GitLoader(repo_url=repo_url, branch="main")
    
    # Get repository and commit
    repo, commit_sha = loader.get_repo_and_commit()
    print(f"Repository cloned/updated at commit: {commit_sha}")
    
    # Get all files with .proto extension
    target_extensions = [".proto"]
    proto_files = loader.get_files_content(target_extensions)
    
    print(f"\nFound {len(proto_files)} protobuf files")
    
    # Initialize SimpleParser for protobuf
    parser = SimpleParser("protobuf")
    
    # Parse each protobuf file
    for file_path, content in proto_files:
        print(f"\nParsing {file_path}...")
        try:
            result = parser.parse(file_path, content)
            
            # Check for parse errors
            if result.get('parse_error'):
                print(f"ERROR: Parse error in {file_path}")
                continue
            
            # Print summary of parsed data
            messages = result.get('messages', [])
            services = result.get('services', [])
            print(f"Successfully parsed {file_path}:")
            print(f"- Found {len(messages)} messages (data models)")
            print(f"- Found {len(services)} services (APIs)")
            
            # Print details of first message and service if available
            if messages:
                first_message = messages[0]
                print(f"\nFirst message: {first_message['name']}")
                print(f"Fields: {len(first_message['fields'])}")
                for field in first_message['fields'][:3]:  # Show first 3 fields
                    print(f"  - {field['name']}: {field['type']}")
                if len(first_message['fields']) > 3:
                    print(f"  - ... and {len(first_message['fields']) - 3} more fields")
            
            if services:
                first_service = services[0]
                print(f"\nFirst service: {first_service['name']}")
                print(f"Methods: {len(first_service['methods'])}")
                for method in first_service['methods'][:3]:  # Show first 3 methods
                    print(f"  - {method['name']}: {method['request_type']} -> {method['response_type']}")
                if len(first_service['methods']) > 3:
                    print(f"  - ... and {len(first_service['methods']) - 3} more methods")
                    
        except Exception as e:
            print(f"ERROR: Exception while parsing {file_path}: {e}")

if __name__ == "__main__":
    test_proto_parser() 