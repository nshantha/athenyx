"""
Test script for running the enhanced ingestion on the microservices_demo folder.

This script tests the enhanced ingestion system by processing the microservices_demo
repository and verifying that it correctly extracts relationships and chunks.
"""

import os
import sys
import asyncio
import logging
import pytest
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.neo4j_manager import db_manager
from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem


@pytest.mark.asyncio
async def test_microservices_demo_ingestion():
    """Test the enhanced ingestion on the microservices_demo folder."""
    # Path to the microservices_demo repository
    repo_path = os.path.join(project_root, "ingestion", "repos", "microservices_demo")
    
    # Check if the repository exists
    assert os.path.exists(repo_path), f"Repository not found at {repo_path}"
    
    # Create a configuration for the test
    config = {
        "repositories": [
            {
                "url": f"file://{repo_path}",  # Use file:// protocol for local repositories
                "branch": "main",
                "service_name": "microservices_demo",
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
        await db_manager.connect()
        
        # Run the enhanced ingestion
        await knowledge_system.run_enhanced_ingestion()
        
        # Verify the results
        await verify_repository_node()
        await verify_service_nodes()
        await verify_file_nodes()
        await verify_code_chunks()
        await verify_relationships()
        
    finally:
        # Close the database connection
        await db_manager.close()


async def verify_repository_node():
    """Verify that the repository node was created correctly."""
    logger.info("Verifying repository node...")
    
    query = """
    MATCH (r:Repository {service_name: 'microservices_demo'})
    RETURN r
    """
    
    result = await db_manager.run_query(query)
    assert result, "Repository node not found"
    assert len(result) == 1, f"Expected 1 repository node, found {len(result)}"
    
    logger.info("Repository node verified successfully")


async def verify_service_nodes():
    """Verify that service nodes were created correctly."""
    logger.info("Verifying service nodes...")
    
    query = """
    MATCH (s:Service)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    RETURN s.name as name
    """
    
    result = await db_manager.run_query(query)
    assert result, "No service nodes found"
    
    # Microservices demo should have multiple services
    assert len(result) >= 1, f"Expected at least 1 service node, found {len(result)}"
    
    # Log the service names
    service_names = [record['name'] for record in result]
    logger.info(f"Found services: {', '.join(service_names)}")
    
    logger.info(f"Service nodes verified successfully: {len(result)} services found")


async def verify_file_nodes():
    """Verify that file nodes were created correctly."""
    logger.info("Verifying file nodes...")
    
    query = """
    MATCH (f:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    RETURN count(f) as file_count
    """
    
    result = await db_manager.run_query(query)
    assert result, "File count query failed"
    
    file_count = result[0]['file_count']
    assert file_count > 0, "No file nodes found"
    
    logger.info(f"File nodes verified successfully: {file_count} files found")
    
    # Check for specific file types
    query_by_type = """
    MATCH (f:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    RETURN f.file_type as file_type, count(f) as count
    ORDER BY count DESC
    """
    
    result = await db_manager.run_query(query_by_type)
    
    # Log file types
    for record in result:
        logger.info(f"Found {record['count']} files of type: {record['file_type']}")


async def verify_code_chunks():
    """Verify that code chunks were created correctly."""
    logger.info("Verifying code chunks...")
    
    query = """
    MATCH (cc:CodeChunk)<-[:CONTAINS]-(:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    RETURN count(cc) as chunk_count
    """
    
    result = await db_manager.run_query(query)
    assert result, "Code chunk count query failed"
    
    chunk_count = result[0]['chunk_count']
    assert chunk_count > 0, "No code chunks found"
    
    logger.info(f"Code chunks verified successfully: {chunk_count} chunks found")
    
    # Check that chunks have embeddings
    query_embeddings = """
    MATCH (cc:CodeChunk)<-[:CONTAINS]-(:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    WHERE cc.embedding IS NOT NULL
    RETURN count(cc) as chunk_count
    """
    
    result = await db_manager.run_query(query_embeddings)
    
    chunks_with_embeddings = result[0]['chunk_count']
    assert chunks_with_embeddings > 0, "No code chunks with embeddings found"
    
    logger.info(f"Found {chunks_with_embeddings} code chunks with embeddings")


async def verify_relationships():
    """Verify that relationships were created correctly."""
    logger.info("Verifying relationships...")
    
    # Check for CONTAINS relationships
    contains_query = """
    MATCH (f:File)-[r:CONTAINS]->(cc:CodeChunk)
    WHERE f.repo_url CONTAINS 'microservices_demo'
    RETURN count(r) as rel_count
    """
    
    result = await db_manager.run_query(contains_query)
    contains_count = result[0]['rel_count']
    assert contains_count > 0, "No CONTAINS relationships found"
    
    logger.info(f"Found {contains_count} CONTAINS relationships")
    
    # Check for IMPORTS relationships
    imports_query = """
    MATCH (:File)-[r:IMPORTS]->(:File)
    WHERE r.repo_url CONTAINS 'microservices_demo'
    RETURN count(r) as rel_count
    """
    
    result = await db_manager.run_query(imports_query)
    imports_count = result[0]['rel_count'] if result and result[0]['rel_count'] else 0
    
    logger.info(f"Found {imports_count} IMPORTS relationships")
    
    # Check for API endpoints
    api_query = """
    MATCH (api:ApiEndpoint)<-[:EXPOSES]-(s:Service)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    RETURN count(api) as api_count
    """
    
    result = await db_manager.run_query(api_query)
    api_count = result[0]['api_count'] if result and result[0]['api_count'] else 0
    
    logger.info(f"Found {api_count} API endpoints")
    
    # Check for COMMUNICATES_WITH relationships
    comms_query = """
    MATCH (s1:Service)-[r:COMMUNICATES_WITH]->(s2:Service)
    WHERE s1.name = 'microservices_demo' OR s2.name = 'microservices_demo'
    RETURN count(r) as rel_count
    """
    
    result = await db_manager.run_query(comms_query)
    comms_count = result[0]['rel_count'] if result and result[0]['rel_count'] else 0
    
    logger.info(f"Found {comms_count} COMMUNICATES_WITH relationships")
    
    logger.info("Relationships verified successfully")


if __name__ == "__main__":
    # Run the test directly
    asyncio.run(test_microservices_demo_ingestion()) 