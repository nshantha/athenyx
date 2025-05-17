#!/usr/bin/env python
"""
Script to run the enhanced ingestion on the microservices_demo folder.

This script processes the microservices_demo repository using the enhanced knowledge system
to create a comprehensive knowledge graph with relationships and chunks.

Usage:
    python scripts/ingest_microservices_demo.py
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.neo4j_manager import db_manager
from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem


async def ingest_microservices_demo():
    """Run the enhanced ingestion on the microservices_demo folder."""
    # Path to the microservices_demo repository
    repo_path = os.path.join(project_root, "ingestion", "repos", "microservices_demo")
    
    # Check if the repository exists
    if not os.path.exists(repo_path):
        logger.error(f"Repository not found at {repo_path}")
        return
    
    logger.info(f"Using repository at: {repo_path}")
    
    # Create a configuration for the ingestion
    config = {
        "repositories": [
            {
                "url": f"file://{repo_path}",  # Use file:// protocol for local repositories
                "branch": "main",
                "service_name": "microservices-demo",
                "force_reindex": True  # Force reindexing even if already indexed
            }
        ],
        "cross_repo_analysis": True
    }
    
    # Create an instance of the enhanced knowledge system
    knowledge_system = EnhancedKnowledgeSystem()
    knowledge_system.config = config
    
    try:
        # Connect to the database
        logger.info("Connecting to the database...")
        await db_manager.connect()
        
        # Run the enhanced ingestion
        logger.info("Starting enhanced ingestion...")
        await knowledge_system.run_enhanced_ingestion()
        
        # Print summary statistics
        await print_summary_statistics()
        
        logger.info("Ingestion completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
    finally:
        # Close the database connection
        await db_manager.close()


async def print_summary_statistics():
    """Print summary statistics about the ingested data."""
    logger.info("Gathering summary statistics...")
    
    # Count repository nodes
    repo_query = """
    MATCH (r:Repository {service_name: 'microservices-demo'})
    RETURN count(r) as count
    """
    
    result = await db_manager.run_query(repo_query)
    repo_count = result[0]['count'] if result else 0
    logger.info(f"Repository nodes: {repo_count}")
    
    # Count service nodes
    service_query = """
    MATCH (s:Service)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices-demo'})
    RETURN count(s) as count
    """
    
    result = await db_manager.run_query(service_query)
    service_count = result[0]['count'] if result else 0
    logger.info(f"Service nodes: {service_count}")
    
    # Count file nodes
    file_query = """
    MATCH (f:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices-demo'})
    RETURN count(f) as count
    """
    
    result = await db_manager.run_query(file_query)
    file_count = result[0]['count'] if result else 0
    logger.info(f"File nodes: {file_count}")
    
    # Count code chunks
    chunk_query = """
    MATCH (cc:CodeChunk)<-[:CONTAINS]-(:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices-demo'})
    RETURN count(cc) as count
    """
    
    result = await db_manager.run_query(chunk_query)
    chunk_count = result[0]['count'] if result else 0
    logger.info(f"Code chunk nodes: {chunk_count}")
    
    # Count API endpoints
    api_query = """
    MATCH (api:ApiEndpoint)<-[:EXPOSES]-(s:Service)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices-demo'})
    RETURN count(api) as count
    """
    
    result = await db_manager.run_query(api_query)
    api_count = result[0]['count'] if result else 0
    logger.info(f"API endpoint nodes: {api_count}")
    
    # Count data models
    model_query = """
    MATCH (dm:DataModel)<-[:USES]-(s:Service)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices-demo'})
    RETURN count(dm) as count
    """
    
    result = await db_manager.run_query(model_query)
    model_count = result[0]['count'] if result else 0
    logger.info(f"Data model nodes: {model_count}")
    
    # Count relationships
    relationship_query = """
    MATCH (n1)-[r]-(n2)
    WHERE n1.repo_url CONTAINS 'microservices-demo' OR n2.repo_url CONTAINS 'microservices-demo'
    RETURN type(r) as type, count(r) as count
    ORDER BY count DESC
    """
    
    result = await db_manager.run_query(relationship_query)
    
    logger.info("Relationship counts:")
    for record in result:
        logger.info(f"  {record['type']}: {record['count']}")
    
    # Count total relationships
    total_rel_query = """
    MATCH (n1)-[r]-(n2)
    WHERE n1.repo_url CONTAINS 'microservices-demo' OR n2.repo_url CONTAINS 'microservices-demo'
    RETURN count(r) as count
    """
    
    result = await db_manager.run_query(total_rel_query)
    total_rel_count = result[0]['count'] if result else 0
    logger.info(f"Total relationships: {total_rel_count}")


if __name__ == "__main__":
    # Run the ingestion
    asyncio.run(ingest_microservices_demo()) 