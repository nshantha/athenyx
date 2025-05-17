#!/usr/bin/env python
"""
Script to fix Function nodes that are missing connections to their Repository,
Files and CodeChunks.
"""
import asyncio
import os
import sys
import logging
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def connect_functions_to_repositories(db_manager, repo_url):
    """Connect Function nodes directly to their Repository"""
    logger.info("Connecting Function nodes to Repository...")
    
    result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        MATCH (r:Repository {url: $repo_url})
        WHERE NOT (fn)-[:BELONGS_TO]->(r)
        MERGE (fn)-[:BELONGS_TO]->(r)
        RETURN count(fn) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result[0]['fixed_count']} Function nodes to Repository")

async def connect_functions_to_files(db_manager, repo_url):
    """Connect Function nodes to their parent File nodes"""
    logger.info("Connecting Function nodes to File nodes...")
    
    # Find Functions with file_path and connect to Files
    result1 = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        WHERE fn.file_path IS NOT NULL
        MATCH (f:File {path: fn.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(fn)
        MERGE (f)-[:CONTAINS]->(fn)
        RETURN count(fn) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result1[0]['fixed_count']} Function nodes to Files using file_path property")
    
    # Find Functions without file_path and try to connect via chunks
    result2 = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        WHERE fn.file_path IS NULL
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.parent_id CONTAINS fn.unique_id
        WITH fn, cc
        MATCH (f:File {path: cc.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(fn)
        MERGE (f)-[:CONTAINS]->(fn)
        SET fn.file_path = cc.file_path
        RETURN count(fn) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result2[0]['fixed_count']} Function nodes to Files using CodeChunk parent_id")

async def connect_functions_to_chunks(db_manager, repo_url):
    """Connect Function nodes to their CodeChunk nodes"""
    logger.info("Connecting Function nodes to CodeChunk nodes...")
    
    # Connect via parent_id in chunks
    result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.parent_id CONTAINS fn.unique_id
        AND NOT (fn)-[:CONTAINS]->(cc)
        MERGE (fn)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result[0]['fixed_count']} Function nodes to CodeChunks")
    
    # Try to connect via line range overlap for remaining chunks
    result2 = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        WHERE fn.file_path IS NOT NULL
        AND fn.start_line IS NOT NULL
        AND fn.end_line IS NOT NULL
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.file_path = fn.file_path
        AND cc.start_line >= fn.start_line
        AND cc.end_line <= fn.end_line
        AND NOT (fn)-[:CONTAINS]->(cc)
        AND NOT EXISTS((cc)-[:BELONGS_TO]->(:Class))
        MERGE (fn)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result2[0]['fixed_count']} additional Function nodes to CodeChunks via line ranges")

async def fix_function_connections(repo_url: str):
    """
    Fix Function connections to Repository, Files, and CodeChunks.
    
    Args:
        repo_url: The repository URL to fix Function connections for
    """
    from app.db.neo4j_manager import db_manager
    
    logger.info(f"Starting Function connections repair for {repo_url}...")
    
    # Connect to Neo4j
    try:
        await db_manager.connect()
        logger.info("Connected to Neo4j database")
        
        # Fix connections in order
        await connect_functions_to_repositories(db_manager, repo_url)
        await connect_functions_to_files(db_manager, repo_url)
        await connect_functions_to_chunks(db_manager, repo_url)
        
        logger.info(f"Function connections repair completed for {repo_url}")
    except Exception as e:
        logger.error(f"An error occurred while fixing Function connections: {e}")
    finally:
        await db_manager.close()

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix Function node connections in Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to fix Function connections for")
    
    args = parser.parse_args()
    
    asyncio.run(fix_function_connections(args.repo_url)) 