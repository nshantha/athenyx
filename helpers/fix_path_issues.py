#!/usr/bin/env python
"""
Fix repository URL path issues in Neo4j database.
"""
import asyncio
import os
import sys
import logging
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_file_paths(pattern=None, target_url=None):
    """
    Fix file paths in Neo4j database by updating repo_url to consistent format.
    
    Args:
        pattern: String pattern to match repository URLs (e.g., 'microservices')
        target_url: The target repository URL to use for all matched nodes
    """
    from app.db.neo4j_manager import db_manager
    
    logger.info("Starting file path fix process...")
    
    # 1. Connect to Neo4j
    await db_manager.connect()
    logger.info("Connected to Neo4j database")
    
    # Define the query to find inconsistent repo_urls
    check_query = """
    MATCH (n)
    WHERE EXISTS(n.repo_url)
    """
    
    # Add pattern filter if provided
    if pattern:
        check_query += f" AND n.repo_url CONTAINS '{pattern}'"
    
    check_query += """
    RETURN DISTINCT n.repo_url as repo_url
    """
    
    repo_urls = await db_manager.run_query(check_query)
    
    if not repo_urls:
        logger.info("No matching repository URLs found. Nothing to fix.")
        return
    
    logger.info(f"Found repository URLs: {[url['repo_url'] for url in repo_urls]}")
    
    # If target_url isn't provided, prompt for confirmation
    if not target_url and len(repo_urls) > 1:
        logger.warning("Multiple repository URLs found but no target URL provided.")
        logger.info("Please run again with --target-url parameter to specify the correct URL")
        return
    
    # If only one URL found and no target specified, nothing to do
    if len(repo_urls) == 1 and not target_url:
        logger.info("Only one repository URL found and no target URL specified. Nothing to change.")
        return
    
    # Use the first URL as target if not specified
    if not target_url:
        target_url = repo_urls[0]['repo_url']
        logger.info(f"Using {target_url} as the target repository URL")
    
    # Update repo_url in all nodes
    update_query = """
    MATCH (n)
    WHERE n.repo_url IN $old_urls
    SET n.repo_url = $new_url
    RETURN count(n) as updated_nodes
    """
    
    old_urls = [url['repo_url'] for url in repo_urls if url['repo_url'] != target_url]
    
    if not old_urls:
        logger.info("All nodes already have the correct repository URL.")
        return
    
    result = await db_manager.run_query(update_query, {"old_urls": old_urls, "new_url": target_url})
    
    logger.info(f"Updated {result[0]['updated_nodes']} nodes to use consistent repository URL")
    
    # Update the repository node itself
    repo_query = """
    MATCH (r:Repository)
    WHERE r.url IN $old_urls
    SET r.url = $new_url
    RETURN count(r) as updated_repos
    """
    
    repo_result = await db_manager.run_query(repo_query, {"old_urls": old_urls, "new_url": target_url})
    
    logger.info(f"Updated {repo_result[0]['updated_repos']} repository nodes")
    
    # Close database connection
    await db_manager.close()
    
    logger.info("File path fix process completed successfully!")

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix repository URL inconsistencies in Neo4j database")
    parser.add_argument("--pattern", help="Pattern to match in repository URLs (e.g., 'microservices')")
    parser.add_argument("--target-url", help="Target repository URL to use for all matched nodes")
    
    args = parser.parse_args()
    
    asyncio.run(fix_file_paths(args.pattern, args.target_url)) 