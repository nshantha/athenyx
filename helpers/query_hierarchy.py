#!/usr/bin/env python
"""
Script to query and display sample hierarchy from the knowledge graph.
"""
import asyncio
import os
import sys
import logging
import argparse
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def print_repository_structure(db_manager, repo_url: str, limit: int = 5):
    """
    Print a sample of the repository structure.
    
    Args:
        db_manager: The Neo4j database manager
        repo_url: The repository URL to query
        limit: Maximum number of each entity type to display
    """
    # Get repository info
    repo_result = await db_manager.run_query(
        """
        MATCH (r:Repository {url: $repo_url})
        RETURN r.url as url, r.name as name
        """,
        {"repo_url": repo_url}
    )
    
    if not repo_result:
        logger.error(f"Repository {repo_url} not found in database.")
        return
        
    repo_name = repo_result[0].get("name", "Unknown")
    print(f"\n📁 Repository: {repo_name} ({repo_url})")
    
    # Get sample files
    file_result = await db_manager.run_query(
        """
        MATCH (r:Repository {url: $repo_url})<-[:BELONGS_TO]-(f:File)
        RETURN f.path as path, f.language as language
        LIMIT $limit
        """,
        {"repo_url": repo_url, "limit": limit}
    )
    
    for file in file_result:
        file_path = file.get("path", "Unknown")
        language = file.get("language", "Unknown")
        print(f"  ├── 📄 File: {file_path} ({language})")
        
        # Get functions in this file
        func_result = await db_manager.run_query(
            """
            MATCH (f:File {path: $path, repo_url: $repo_url})-[:CONTAINS]->(fn:Function)
            RETURN fn.name as name, fn.start_line as start_line, fn.end_line as end_line
            LIMIT $limit
            """,
            {"path": file_path, "repo_url": repo_url, "limit": limit}
        )
        
        if not func_result:
            print(f"  │   ├── No functions found")
        else:
            for i, func in enumerate(func_result):
                func_name = func.get("name", "Unknown")
                start_line = func.get("start_line", "?")
                end_line = func.get("end_line", "?")
                
                is_last = i == len(func_result) - 1
                prefix = "  │   └──" if is_last else "  │   ├──"
                print(f"{prefix} 🔧 Function: {func_name} (lines {start_line}-{end_line})")
                
                # Get code chunks for this function
                chunk_result = await db_manager.run_query(
                    """
                    MATCH (fn:Function {name: $name, repo_url: $repo_url})-[:CONTAINS]->(cc:CodeChunk)
                    RETURN cc.chunk_id as id, cc.start_line as start_line, cc.end_line as end_line
                    LIMIT $limit
                    """,
                    {"name": func_name, "repo_url": repo_url, "limit": 2}
                )
                
                if chunk_result:
                    for j, chunk in enumerate(chunk_result):
                        chunk_id = chunk.get("id", "Unknown")
                        chunk_start = chunk.get("start_line", "?")
                        chunk_end = chunk.get("end_line", "?")
                        
                        chunk_is_last = j == len(chunk_result) - 1
                        chunk_prefix = "  │       └──" if chunk_is_last else "  │       ├──"
                        print(f"{chunk_prefix} 📝 CodeChunk: {chunk_id[:20]}... (lines {chunk_start}-{chunk_end})")
                
        # Get classes in this file
        class_result = await db_manager.run_query(
            """
            MATCH (f:File {path: $path, repo_url: $repo_url})-[:CONTAINS]->(c:Class)
            RETURN c.name as name, c.start_line as start_line, c.end_line as end_line
            LIMIT $limit
            """,
            {"path": file_path, "repo_url": repo_url, "limit": limit}
        )
        
        if not class_result:
            print(f"  │   └── No classes found")
        else:
            for i, cls in enumerate(class_result):
                class_name = cls.get("name", "Unknown")
                start_line = cls.get("start_line", "?")
                end_line = cls.get("end_line", "?")
                
                is_last = i == len(class_result) - 1
                prefix = "  │   └──" if is_last else "  │   ├──"
                print(f"{prefix} 🧩 Class: {class_name} (lines {start_line}-{end_line})")
                
                # Get code chunks for this class
                chunk_result = await db_manager.run_query(
                    """
                    MATCH (c:Class {name: $name, repo_url: $repo_url})-[:CONTAINS]->(cc:CodeChunk)
                    RETURN cc.chunk_id as id, cc.start_line as start_line, cc.end_line as end_line
                    LIMIT $limit
                    """,
                    {"name": class_name, "repo_url": repo_url, "limit": 2}
                )
                
                if chunk_result:
                    for j, chunk in enumerate(chunk_result):
                        chunk_id = chunk.get("id", "Unknown")
                        chunk_start = chunk.get("start_line", "?")
                        chunk_end = chunk.get("end_line", "?")
                        
                        chunk_is_last = j == len(chunk_result) - 1
                        chunk_prefix = "  │       └──" if chunk_is_last else "  │       ├──"
                        print(f"{chunk_prefix} 📝 CodeChunk: {chunk_id[:20]}... (lines {chunk_start}-{chunk_end})")
        
        # Get direct code chunks in this file (not through functions or classes)
        direct_chunks_result = await db_manager.run_query(
            """
            MATCH (f:File {path: $path, repo_url: $repo_url})-[:CONTAINS]->(cc:CodeChunk)
            WHERE NOT EXISTS {
                MATCH (fn:Function)-[:CONTAINS]->(cc)
            }
            AND NOT EXISTS {
                MATCH (c:Class)-[:CONTAINS]->(cc)
            }
            RETURN cc.chunk_id as id, cc.start_line as start_line, cc.end_line as end_line
            LIMIT $limit
            """,
            {"path": file_path, "repo_url": repo_url, "limit": 2}
        )
        
        if direct_chunks_result:
            print(f"  │   └── Direct Code Chunks:")
            for i, chunk in enumerate(direct_chunks_result):
                chunk_id = chunk.get("id", "Unknown")
                chunk_start = chunk.get("start_line", "?")
                chunk_end = chunk.get("end_line", "?")
                
                is_last = i == len(direct_chunks_result) - 1
                prefix = "  │       └──" if is_last else "  │       ├──"
                print(f"{prefix} 📝 CodeChunk: {chunk_id[:20]}... (lines {chunk_start}-{chunk_end})")
    
    # Count total entities
    counts_result = await db_manager.run_query(
        """
        MATCH (r:Repository {url: $repo_url})
        OPTIONAL MATCH (r)<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
        OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
        OPTIONAL MATCH (any)-[:CONTAINS]->(cc:CodeChunk)
        WHERE any:Function OR any:Class OR any:File
        RETURN 
            count(DISTINCT f) as file_count,
            count(DISTINCT fn) as function_count,
            count(DISTINCT c) as class_count,
            count(DISTINCT cc) as chunk_count
        """,
        {"repo_url": repo_url}
    )
    
    if counts_result:
        counts = counts_result[0]
        print(f"\nTotals:")
        print(f"  Files: {counts.get('file_count', 0)}")
        print(f"  Functions: {counts.get('function_count', 0)}")
        print(f"  Classes: {counts.get('class_count', 0)}")
        print(f"  Code Chunks: {counts.get('chunk_count', 0)}")

async def run_hierarchy_query(repo_url: str):
    """
    Display a sample of the repository hierarchy from the knowledge graph.
    
    Args:
        repo_url: The repository URL to query
    """
    from app.db.neo4j_manager import db_manager
    
    try:
        await db_manager.connect()
        logger.info("Connected to Neo4j database")
        
        await print_repository_structure(db_manager, repo_url)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await db_manager.close()

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query and display repository hierarchy from Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to query")
    
    args = parser.parse_args()
    
    asyncio.run(run_hierarchy_query(args.repo_url)) 