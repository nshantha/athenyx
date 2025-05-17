#!/usr/bin/env python
"""
Test script to verify the microservices_demo structure and relationships.
"""
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_microservices_structure():
    """Test the microservices_demo structure and relationships."""
    from app.db.neo4j_manager import db_manager
    
    logger.info("Starting structure test...")
    
    # 1. Connect to Neo4j
    await db_manager.connect()
    logger.info("Connected to Neo4j database")
    
    # 2. Set repository as active
    repo_url = "local://microservices_demo"
    await db_manager.set_active_repository(repo_url)
    
    # 3. Test DirectoryExplorer logic
    logger.info("\n--- Testing Directory Structure ---")
    
    query = """
    MATCH (d:Directory {repo_url: $repo_url})
    WHERE d.path = '' OR NOT d.path CONTAINS '/'
    RETURN d.path AS path, d.name AS name
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info("Top-level directories:")
    for result in results:
        logger.info(f"  - {result.get('path', result.get('name', 'unknown'))}")
    
    # 4. Test README content
    logger.info("\n--- Testing README Content ---")
    
    query = """
    MATCH (f:File {repo_url: $repo_url})
    WHERE f.path = 'README.md'
    RETURN f.path AS path, 
           substring(f.content, 0, 200) AS preview
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    for result in results:
        logger.info(f"README found at {result.get('path')}")
        logger.info(f"Preview: {result.get('preview')}...")
    
    # 5. Test Service nodes
    logger.info("\n--- Testing Service Nodes ---")
    
    query = """
    MATCH (s:Service {repo_url: $repo_url})
    RETURN s.name AS name, s.language AS language
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info(f"Found {len(results)} services:")
    for result in results:
        logger.info(f"  - {result.get('name')} ({result.get('language')})")
    
    # 6. Test service relationships
    logger.info("\n--- Testing Service Relationships ---")
    
    query = """
    MATCH (s1:Service {repo_url: $repo_url})-[r:CALLS]->(s2:Service {repo_url: $repo_url})
    RETURN s1.name AS from, s2.name AS to
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info(f"Found {len(results)} service relationships:")
    for result in results:
        logger.info(f"  - {result.get('from')} calls {result.get('to')}")
    
    # 7. Test our new query methods
    logger.info("\n--- Testing Project Structure Query ---")
    
    results = await db_manager.query_high_level_info("project_structure", False, repo_url)
    
    logger.info(f"Project structure query returned {len(results)} results")
    if len(results) > 0:
        logger.info("Top 3 results:")
        for i, result in enumerate(results[:3]):
            logger.info(f"  - Path: {result.get('path')}")
            logger.info(f"    Priority: {result.get('priority')}")
            text_preview = result.get('text', '')[:100]
            logger.info(f"    Text preview: {text_preview}...")
    else:
        logger.error("No results from project structure query!")
    
    # Test for microservices
    logger.info("\n--- Testing Microservices Query ---")
    
    results = await db_manager.query_high_level_info("microservices", False, repo_url)
    
    logger.info(f"Microservices query returned {len(results)} results")
    
    # Test completed
    logger.info("\nStructure test completed")

# Entry point
if __name__ == "__main__":
    asyncio.run(test_microservices_structure())
