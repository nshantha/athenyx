#!/usr/bin/env python
"""
Script to fix Class nodes that are missing connections to their Repository,
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

async def connect_classes_to_repositories(db_manager, repo_url):
    """Connect Class nodes directly to their Repository"""
    logger.info("Connecting Class nodes to Repository...")
    
    result = await db_manager.run_query(
        """
        MATCH (c:Class {repo_url: $repo_url})
        MATCH (r:Repository {url: $repo_url})
        WHERE NOT (c)-[:BELONGS_TO]->(r)
        MERGE (c)-[:BELONGS_TO]->(r)
        RETURN count(c) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result[0]['fixed_count']} Class nodes to Repository")

async def connect_classes_to_files(db_manager, repo_url):
    """Connect Class nodes to their parent File nodes"""
    logger.info("Connecting Class nodes to File nodes...")
    
    # Find Classes with file_path and connect to Files
    result1 = await db_manager.run_query(
        """
        MATCH (c:Class {repo_url: $repo_url})
        WHERE c.file_path IS NOT NULL
        MATCH (f:File {path: c.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(c)
        MERGE (f)-[:CONTAINS]->(c)
        RETURN count(c) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result1[0]['fixed_count']} Class nodes to Files using file_path property")
    
    # Find Classes without file_path and try to connect via chunks
    result2 = await db_manager.run_query(
        """
        MATCH (c:Class {repo_url: $repo_url})
        WHERE c.file_path IS NULL
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.parent_id CONTAINS c.unique_id
        WITH c, cc
        MATCH (f:File {path: cc.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(c)
        MERGE (f)-[:CONTAINS]->(c)
        SET c.file_path = cc.file_path
        RETURN count(c) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result2[0]['fixed_count']} Class nodes to Files using CodeChunk parent_id")

async def connect_classes_to_chunks(db_manager, repo_url):
    """Connect Class nodes to their CodeChunk nodes"""
    logger.info("Connecting Class nodes to CodeChunk nodes...")
    
    # Connect via parent_id in chunks
    result = await db_manager.run_query(
        """
        MATCH (c:Class {repo_url: $repo_url})
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.parent_id CONTAINS c.unique_id
        AND NOT (c)-[:CONTAINS]->(cc)
        MERGE (c)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result[0]['fixed_count']} Class nodes to CodeChunks")
    
    # Try to connect via line range overlap for remaining chunks
    result2 = await db_manager.run_query(
        """
        MATCH (c:Class {repo_url: $repo_url})
        WHERE c.file_path IS NOT NULL
        AND c.start_line IS NOT NULL
        AND c.end_line IS NOT NULL
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.file_path = c.file_path
        AND cc.start_line >= c.start_line
        AND cc.end_line <= c.end_line
        AND NOT (c)-[:CONTAINS]->(cc)
        AND NOT EXISTS((cc)-[:BELONGS_TO]->(:Function))
        MERGE (c)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    
    logger.info(f"Connected {result2[0]['fixed_count']} additional Class nodes to CodeChunks via line ranges")

async def fix_class_connections(repo_url: str):
    """
    Fix Class connections to Repository, Files, and CodeChunks.
    
    Args:
        repo_url: The repository URL to fix Class connections for
    """
    from app.db.neo4j_manager import db_manager
    
    logger.info(f"Starting Class connections repair for {repo_url}...")
    
    # Connect to Neo4j
    try:
        await db_manager.connect()
        logger.info("Connected to Neo4j database")
        
        # Fix connections in order
        await connect_classes_to_repositories(db_manager, repo_url)
        await connect_classes_to_files(db_manager, repo_url)
        await connect_classes_to_chunks(db_manager, repo_url)
        
        logger.info(f"Class connections repair completed for {repo_url}")
    except Exception as e:
        logger.error(f"An error occurred while fixing Class connections: {e}")
    finally:
        await db_manager.close()

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix Class node connections in Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to fix Class connections for")
    
    args = parser.parse_args()
    
    asyncio.run(fix_class_connections(args.repo_url)) 