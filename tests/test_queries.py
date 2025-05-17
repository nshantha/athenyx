#!/usr/bin/env python
"""
Test script to verify if our changes to the project structure query are working correctly.
"""
import asyncio
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_project_structure_query():
    """Test the project structure query with our new implementation."""
    from app.db.neo4j_manager import db_manager
    
    logger.info("Testing project structure query...")
    
    # 1. Connect to Neo4j
    await db_manager.connect()
    logger.info("Connected to Neo4j database")
    
    # 2. Get the active repository
    active_repo = await db_manager.get_active_repository()
    if active_repo:
        repo_url = active_repo.get('url')
        logger.info(f"Active repository: {repo_url}")
    else:
        logger.warning("No active repository found!")
        return
    
    # 3. Test the DirectoryExplorer logic
    logger.info("Testing DirectoryExplorer logic...")
    
    query = """
    MATCH (r:Repository {url: $repo_url})<-[:BELONGS_TO]-(f:File)
    WITH f.path AS path
    RETURN path
    ORDER BY path
    LIMIT 20
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info("Found these paths:")
    for result in results:
        logger.info(f"  - {result.get('path')}")
    
    # 4. Test the project_structure query
    logger.info("Testing project_structure query...")
    
    results = await db_manager.query_high_level_info("project_structure", False, repo_url)
    
    logger.info(f"Query returned {len(results)} results")
    
    for i, result in enumerate(results[:5]):  # Show first 5 results
        logger.info(f"Result {i+1}:")
        logger.info(f"  Path: {result.get('path')}")
        logger.info(f"  Priority: {result.get('priority')}")
        logger.info(f"  Text snippet: {result.get('text')[:100]}...")
    
    # 5. Test the services query
    logger.info("Testing services query...")
    
    results = await db_manager.query_high_level_info("microservices", False, repo_url)
    
    logger.info(f"Query returned {len(results)} results for microservices")
    
    # 6. Test KnowledgeGraph query
    logger.info("Testing KnowledgeGraph tool logic...")
    
    query = """
    MATCH (r:Repository {url: $repo_url})<-[:BELONGS_TO]-(s:Service)
    RETURN s.name as name, s.language as language, s.description as description
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info(f"Found {len(results)} services:")
    for result in results:
        logger.info(f"  - {result.get('name')} ({result.get('language')}): {result.get('description')}")
    
    # 7. Test service relationships
    logger.info("Testing service relationships...")
    
    query = """
    MATCH (s1:Service {repo_url: $repo_url})-[r]->(s2:Service {repo_url: $repo_url})
    RETURN s1.name as from, s2.name as to, type(r) as relationship
    LIMIT 10
    """
    
    results = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info(f"Found {len(results)} service relationships:")
    for result in results:
        logger.info(f"  - {result.get('from')} {result.get('relationship')} {result.get('to')}")
    
    logger.info("Test completed successfully")

# Entry point
if __name__ == "__main__":
    asyncio.run(test_project_structure_query())
