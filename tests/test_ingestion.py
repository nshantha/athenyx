#!/usr/bin/env python
"""
Script to test the ingestion process by clearing and re-ingesting a repository.
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

async def clear_and_ingest(repo_url):
    """
    Clear repository data from Neo4j and then reingest it.
    
    Args:
        repo_url: The repository URL to clear and reingest
    """
    from app.db.neo4j_manager import db_manager
    
    logger.info(f"Starting test of ingestion for {repo_url}")
    
    # Connect to Neo4j
    await db_manager.connect()
    logger.info("Connected to Neo4j database")
    
    # Step 1: Clear existing repository data
    logger.info(f"Clearing data for repository: {repo_url}")
    await db_manager.clear_repository_data(repo_url)
    logger.info("Repository data cleared successfully")
    
    # Close the database connection
    await db_manager.close()
    
    # Step 2: Run the ingestion process
    logger.info("Starting ingestion process")
    from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem
    
    knowledge_system = EnhancedKnowledgeSystem()
    await knowledge_system.ingest_repositories([repo_url])
    
    logger.info("Ingestion completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ingestion by clearing and re-ingesting a repository")
    parser.add_argument("--repo-url", default="https://github.com/GoogleCloudPlatform/microservices-demo.git", 
                        help="Repository URL to test (default: microservices-demo)")
    
    args = parser.parse_args()
    
    asyncio.run(clear_and_ingest(args.repo_url)) 