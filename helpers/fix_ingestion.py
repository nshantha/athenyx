#!/usr/bin/env python
"""
Script to fix the ingestion for any repository.
This re-ingests the repository with explicit relationships and directory structure.
"""
import asyncio
import os
import sys
import logging
import argparse
from typing import List, Tuple, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_repository_ingestion(repo_url: str, repo_description: str = None):
    """
    Re-ingest a repository with proper relationships.
    
    Args:
        repo_url: The repository URL to fix
        repo_description: Optional description for the repository
    """
    from app.db.neo4j_manager import db_manager
    from ingestion.config import ingestion_settings
    
    logger.info(f"Starting repository re-ingestion process for {repo_url}...")
    
    # 1. Connect to Neo4j
    await db_manager.connect()
    logger.info("Connected to Neo4j database")
    
    # 2. Set up the repository info
    repo_name = ingestion_settings.extract_repo_name(repo_url)
    repo_path = os.path.join(ingestion_settings.base_clone_dir, repo_name)
    service_name = repo_name
    
    if not repo_description:
        repo_description = f"Repository {repo_name}"
    
    logger.info(f"Using repository path: {repo_path}")
    if not os.path.exists(repo_path):
        logger.error(f"Repository path does not exist: {repo_path}")
        logger.info("Please make sure the repository is cloned first.")
        return
    
    # 3. Check if repository exists
    check_query = """
    MATCH (r:Repository {url: $repo_url})
    RETURN r.url as url
    """
    check_result = await db_manager.run_query(check_query, {"repo_url": repo_url})
    
    repo_exists = len(check_result) > 0
    
    if not repo_exists:
        # Create Repository node
        logger.info("Creating Repository node")
        await db_manager.run_query(
            """
            MERGE (r:Repository {url: $url})
            SET r.service_name = $service_name,
                r.description = $description,
                r.last_updated = datetime(),
                r.is_active = true
            RETURN r
            """,
            {
                "url": repo_url, 
                "service_name": service_name,
                "description": repo_description
            }
        )
    else:
        # Set repository as active
        logger.info("Repository already exists, setting as active")
        await db_manager.run_query(
            """
            MATCH (r:Repository {url: $url})
            SET r.service_name = $service_name,
                r.description = $description,
                r.last_updated = datetime(),
                r.is_active = true
            RETURN r
            """,
            {
                "url": repo_url, 
                "service_name": service_name,
                "description": repo_description
            }
        )
    
    # 4. Walk directory to collect files and directories
    logger.info(f"Walking directory: {repo_path}")
    files_to_process = []
    dirs_to_create = set()
    
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(('.md', '.py', '.java', '.go', '.cs', '.js', '.yaml', '.yml', '.json', '.txt', '.proto')):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                
                # Create directory entries
                dir_parts = os.path.dirname(rel_path).split(os.sep)
                current_dir = ""
                for part in dir_parts:
                    if not part:  # Skip empty parts
                        continue
                    if current_dir:
                        current_dir = f"{current_dir}/{part}"
                    else:
                        current_dir = part
                    dirs_to_create.add(current_dir)
                
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    # Add to files list
                    files_to_process.append((rel_path, content))
                    
                except Exception as e:
                    logger.warning(f"Error reading file {rel_path}: {e}")
    
    logger.info(f"Found {len(files_to_process)} files and {len(dirs_to_create)} directories")
    
    # 5. Create relationships between Repository and File nodes
    logger.info("Creating Repository-File relationships")
    
    # First, check for existing file nodes
    existing_files_query = """
    MATCH (f:File {repo_url: $repo_url})
    RETURN f.path as path
    """
    existing_files_result = await db_manager.run_query(existing_files_query, {"repo_url": repo_url})
    existing_files = set(result["path"] for result in existing_files_result)
    
    for file_path, _ in files_to_process:
        if file_path in existing_files:
            # Create relationship if not exists
            await db_manager.run_query(
                """
                MATCH (r:Repository {url: $repo_url})
                MATCH (f:File {path: $path, repo_url: $repo_url})
                MERGE (f)-[:BELONGS_TO]->(r)
                """,
                {
                    "repo_url": repo_url,
                    "path": file_path
                }
            )

    # 6. Create or update Directory nodes with hierarchical structure
    logger.info("Creating Directory nodes and relationships")
    
    # First check for existing directories
    existing_dirs_query = """
    MATCH (d:Directory {repo_url: $repo_url})
    RETURN d.path as path
    """
    existing_dirs_result = await db_manager.run_query(existing_dirs_query, {"repo_url": repo_url})
    existing_dirs = set(result["path"] for result in existing_dirs_result)
    
    for dir_path in sorted(dirs_to_create):  # Sort for parent-child order
        parent_path = os.path.dirname(dir_path).replace("\\", "/")
        dir_name = os.path.basename(dir_path)
        
        # Create Directory node if not exists
        if dir_path not in existing_dirs:
            try:
                await db_manager.run_query(
                    """
                    MERGE (d:Directory {path: $path, repo_url: $repo_url})
                    SET d.name = $name,
                        d.last_updated = datetime()
                    WITH d
                    MATCH (r:Repository {url: $repo_url})
                    MERGE (d)-[:BELONGS_TO]->(r)
                    RETURN d
                    """,
                    {
                        "path": dir_path,
                        "repo_url": repo_url,
                        "name": dir_name
                    }
                )
            except Exception as e:
                logger.error(f"Error creating directory node {dir_path}: {e}")
                continue
        
        # Create parent-child directory relationship
        if parent_path:
            try:
                await db_manager.run_query(
                    """
                    MATCH (parent:Directory {path: $parent_path, repo_url: $repo_url})
                    MATCH (child:Directory {path: $child_path, repo_url: $repo_url})
                    MERGE (parent)-[:CONTAINS]->(child)
                    """,
                    {
                        "parent_path": parent_path,
                        "child_path": dir_path,
                        "repo_url": repo_url
                    }
                )
            except Exception as e:
                logger.error(f"Error creating directory relationship {parent_path} -> {dir_path}: {e}")
    
    # 7. Create File to Directory relationships
    logger.info("Creating File to Directory relationships")
    for file_path, _ in files_to_process:
        dir_path = os.path.dirname(file_path).replace("\\", "/")
        if dir_path:
            try:
                await db_manager.run_query(
                    """
                    MATCH (d:Directory {path: $dir_path, repo_url: $repo_url})
                    MATCH (f:File {path: $file_path, repo_url: $repo_url})
                    MERGE (d)-[:CONTAINS]->(f)
                    """,
                    {
                        "dir_path": dir_path,
                        "file_path": file_path,
                        "repo_url": repo_url
                    }
                )
            except Exception as e:
                logger.error(f"Error creating file relationship {dir_path} -> {file_path}: {e}")
    
    # 10. Set as active repository
    logger.info("Setting as active repository")
    await db_manager.set_active_repository(repo_url)
    
    logger.info(f"Finished repository re-ingestion process for {repo_url}")

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix repository ingestion with proper relationships")
    parser.add_argument("--repo-url", required=True, help="Repository URL to fix")
    parser.add_argument("--description", help="Optional repository description")
    
    args = parser.parse_args()
    
    asyncio.run(fix_repository_ingestion(args.repo_url, args.description))
