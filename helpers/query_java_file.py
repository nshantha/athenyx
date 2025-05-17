#!/usr/bin/env python
"""
Script to query and display hierarchy for a specific Java file.
"""
import asyncio
import os
import sys
import logging
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def find_java_files(db_manager, repo_url: str, limit: int = 5):
    """Find Java files in the repository"""
    return await db_manager.run_query(
        """
        MATCH (f:File {repo_url: $repo_url})
        WHERE f.language = 'java'
        RETURN f.path as path
        LIMIT $limit
        """,
        {"repo_url": repo_url, "limit": limit}
    )

async def print_file_hierarchy(db_manager, repo_url: str, file_path: str):
    """
    Print detailed hierarchy for a specific file.
    
    Args:
        db_manager: The Neo4j database manager
        repo_url: The repository URL
        file_path: Path of the file to query
    """
    # Get file info
    file_result = await db_manager.run_query(
        """
        MATCH (f:File {path: $path, repo_url: $repo_url})
        RETURN f.path as path, f.language as language
        """,
        {"path": file_path, "repo_url": repo_url}
    )
    
    if not file_result:
        logger.error(f"File {file_path} not found in repository {repo_url}")
        return
        
    language = file_result[0].get("language", "Unknown")
    print(f"\n📄 File: {file_path} ({language})")
    
    # Get classes in this file
    class_result = await db_manager.run_query(
        """
        MATCH (f:File {path: $path, repo_url: $repo_url})-[:CONTAINS]->(c:Class)
        RETURN c.name as name, c.start_line as start_line, c.end_line as end_line
        ORDER BY c.start_line
        """,
        {"path": file_path, "repo_url": repo_url}
    )
    
    if not class_result:
        print(f"  └── No classes found")
    else:
        print(f"  └── Classes:")
        for i, cls in enumerate(class_result):
            class_name = cls.get("name", "Unknown")
            start_line = cls.get("start_line", "?")
            end_line = cls.get("end_line", "?")
            
            is_last = i == len(class_result) - 1
            prefix = "      └──" if is_last else "      ├──"
            print(f"{prefix} 🧩 Class: {class_name} (lines {start_line}-{end_line})")
            
            # Get functions in this class
            func_result = await db_manager.run_query(
                """
                MATCH (f:File {path: $path, repo_url: $repo_url})-[:CONTAINS]->(fn:Function)
                WHERE fn.start_line >= $start_line AND fn.end_line <= $end_line
                RETURN fn.name as name, fn.start_line as start_line, fn.end_line as end_line
                ORDER BY fn.start_line
                """,
                {
                    "path": file_path, 
                    "repo_url": repo_url, 
                    "start_line": start_line, 
                    "end_line": end_line
                }
            )
            
            if func_result:
                inner_prefix = "      │   " if not is_last else "          "
                print(f"{inner_prefix}└── Methods:")
                for j, func in enumerate(func_result):
                    func_name = func.get("name", "Unknown")
                    func_start = func.get("start_line", "?")
                    func_end = func.get("end_line", "?")
                    
                    func_is_last = j == len(func_result) - 1
                    func_prefix = "      │       └──" if func_is_last else "      │       ├──"
                    if is_last:
                        func_prefix = "              └──" if func_is_last else "              ├──"
                    
                    print(f"{func_prefix} 🔧 Method: {func_name} (lines {func_start}-{func_end})")
                    
            # Get code chunks for this class
            chunk_result = await db_manager.run_query(
                """
                MATCH (c:Class {name: $name, repo_url: $repo_url})-[:CONTAINS]->(cc:CodeChunk)
                RETURN cc.chunk_id as id, cc.start_line as start_line, cc.end_line as end_line
                ORDER BY cc.start_line
                LIMIT 3
                """,
                {"name": class_name, "repo_url": repo_url}
            )
            
            if chunk_result:
                inner_prefix = "      │   " if not is_last else "          "
                print(f"{inner_prefix}└── Code Chunks:")
                for j, chunk in enumerate(chunk_result):
                    chunk_id = chunk.get("id", "Unknown")
                    chunk_start = chunk.get("start_line", "?")
                    chunk_end = chunk.get("end_line", "?")
                    
                    chunk_is_last = j == len(chunk_result) - 1
                    chunk_prefix = "      │       └──" if chunk_is_last else "      │       ├──"
                    if is_last:
                        chunk_prefix = "              └──" if chunk_is_last else "              ├──"
                    
                    print(f"{chunk_prefix} 📝 CodeChunk: {chunk_id[:20]}... (lines {chunk_start}-{chunk_end})")

async def run_java_query(repo_url: str, file_path: str = None):
    """
    Find and display hierarchy for Java files in the repository.
    
    Args:
        repo_url: The repository URL to query
        file_path: Optional specific file path to query
    """
    from app.db.neo4j_manager import db_manager
    
    try:
        await db_manager.connect()
        logger.info("Connected to Neo4j database")
        
        if file_path:
            await print_file_hierarchy(db_manager, repo_url, file_path)
        else:
            # Find Java files and display their hierarchy
            java_files = await find_java_files(db_manager, repo_url)
            
            if not java_files:
                logger.info(f"No Java files found in repository {repo_url}")
                return
                
            for file in java_files:
                file_path = file.get("path")
                await print_file_hierarchy(db_manager, repo_url, file_path)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query Java file hierarchy from Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to query")
    parser.add_argument("--file-path", help="Specific file path to query")
    
    args = parser.parse_args()
    
    asyncio.run(run_java_query(args.repo_url, args.file_path)) 