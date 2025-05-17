#!/usr/bin/env python
"""
Script to fix the Neo4j loader issue with protobuf files
"""
import asyncio
import os
from ingestion.sources.git_loader import GitLoader
from ingestion.parsing.simple_parser import SimpleParser
from app.db.neo4j_manager import db_manager

async def fix_neo4j_loader():
    """Fix the Neo4j loader issue with protobuf files"""
    # Connect to the database
    await db_manager.connect()
    
    try:
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
        
        # Process each protobuf file
        for file_path, content in proto_files:
            print(f"\nProcessing {file_path}...")
            
            # Parse the file
            parsed_data = parser.parse(file_path, content)
            
            # Check for parse errors
            if parsed_data.get('parse_error'):
                print(f"ERROR: Parse error in {file_path}, skipping")
                continue
            
            # Create File node
            file_name = os.path.basename(file_path)
            await create_file_node(file_path, file_name, "protobuf", repo_url)
            print(f"Created File node for {file_path}")
            
            # Process messages (data models)
            for message in parsed_data.get('messages', []):
                await create_message_node(message, file_path, repo_url)
                print(f"Created Message node for {message['name']}")
            
            # Process services (APIs)
            for service in parsed_data.get('services', []):
                await create_service_node(service, file_path, repo_url)
                print(f"Created Service node for {service['name']}")
        
        print("\nAll protobuf files processed successfully")
        
    finally:
        await db_manager.close()

async def create_file_node(path, name, language, repo_url):
    """Create a File node in Neo4j"""
    query = """
    MERGE (f:File {path: $path})
    SET f.name = $name,
        f.language = $language,
        f.file_type = 'proto',
        f.repo_url = $repo_url,
        f.is_documentation = false
    RETURN f
    """
    params = {
        "path": path,
        "name": name,
        "language": language,
        "repo_url": repo_url
    }
    await db_manager.run_query(query, params)

async def create_message_node(message, file_path, repo_url):
    """Create a Class node for a protobuf message"""
    query = """
    MERGE (c:Class {unique_id: $unique_id})
    SET c.name = $name,
        c.start_line = $start_line,
        c.end_line = $end_line,
        c.file_path = $file_path,
        c.repo_url = $repo_url,
        c.is_data_model = true,
        c.is_api = false,
        c.type = 'message'
    WITH c
    MATCH (f:File {path: $file_path})
    MERGE (f)-[:CONTAINS]->(c)
    RETURN c
    """
    params = {
        "unique_id": message['unique_id'],
        "name": message['name'],
        "start_line": message['start_line'],
        "end_line": message['end_line'],
        "file_path": file_path,
        "repo_url": repo_url
    }
    await db_manager.run_query(query, params)

async def create_service_node(service, file_path, repo_url):
    """Create a Class node for a protobuf service"""
    query = """
    MERGE (c:Class {unique_id: $unique_id})
    SET c.name = $name,
        c.start_line = $start_line,
        c.end_line = $end_line,
        c.file_path = $file_path,
        c.repo_url = $repo_url,
        c.is_data_model = false,
        c.is_api = true,
        c.type = 'service',
        c.framework = 'gRPC'
    WITH c
    MATCH (f:File {path: $file_path})
    MERGE (f)-[:CONTAINS]->(c)
    RETURN c
    """
    params = {
        "unique_id": service['unique_id'],
        "name": service['name'],
        "start_line": service['start_line'],
        "end_line": service['end_line'],
        "file_path": file_path,
        "repo_url": repo_url
    }
    await db_manager.run_query(query, params)

if __name__ == "__main__":
    asyncio.run(fix_neo4j_loader()) 