#!/usr/bin/env python3
"""
Run Enhanced Ingestion Script

This script runs the enhanced knowledge system ingestion process on a specified repository.
It demonstrates the integration of the knowledge_graph and ingestion systems.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, List, Optional

from app.db.neo4j_manager import db_manager
from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem, run_enhanced_ingestion
from ingestion.config import ingestion_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


async def run_ingestion(repo_url: str, branch: str = "main", force_reindex: bool = True):
    """
    Run the enhanced ingestion process on a specified repository.
    
    Args:
        repo_url: URL of the repository to ingest
        branch: Branch to ingest (default: main)
        force_reindex: Whether to force reindexing even if the repository has already been indexed
    """
    logger.info(f"Running enhanced ingestion on repository: {repo_url}, branch: {branch}")
    
    # Create the enhanced knowledge system
    system = EnhancedKnowledgeSystem()
    
    # Connect to the database
    success = await system.connect_database()
    if not success:
        logger.error("Failed to connect to the database. Aborting.")
        return
    
    # Create a repository configuration
    repo_config = {
        "url": repo_url,
        "branch": branch,
        "force_reindex": force_reindex
    }
    
    # Run the ingestion process
    await system.ingest_repository(repo_config)
    
    # Print summary statistics
    await print_ingestion_summary(repo_url)


async def print_ingestion_summary(repo_url: str):
    """
    Print a summary of the ingestion results.
    
    Args:
        repo_url: URL of the repository that was ingested
    """
    logger.info(f"Ingestion summary for repository: {repo_url}")
    
    # Count files by language
    files_query = """
    MATCH (f:File {repo_url: $repo_url})
    WITH f.language as language, count(f) as count
    RETURN language, count
    ORDER BY count DESC
    """
    
    files_result = await db_manager.run_query(files_query, {"repo_url": repo_url})
    
    logger.info("Files by language:")
    total_files = 0
    for row in files_result:
        language = row['language'] or "unknown"
        count = row['count']
        total_files += count
        logger.info(f"  {language}: {count} files")
    logger.info(f"  Total: {total_files} files")
    
    # Count code chunks
    chunks_query = """
    MATCH (c:CodeChunk {repo_url: $repo_url})
    RETURN count(c) as count
    """
    
    chunks_result = await db_manager.run_query(chunks_query, {"repo_url": repo_url})
    chunks_count = chunks_result[0]['count'] if chunks_result else 0
    logger.info(f"Code chunks: {chunks_count}")
    
    # Count relationships by type
    rels_query = """
    MATCH (n)-[r]->(m)
    WHERE r.repo_url = $repo_url
    WITH type(r) as rel_type, count(r) as count
    RETURN rel_type, count
    ORDER BY count DESC
    """
    
    rels_result = await db_manager.run_query(rels_query, {"repo_url": repo_url})
    
    logger.info("Relationships by type:")
    total_rels = 0
    for row in rels_result:
        rel_type = row['rel_type']
        count = row['count']
        total_rels += count
        logger.info(f"  {rel_type}: {count}")
    logger.info(f"  Total: {total_rels} relationships")
    
    # Count IMPORTS relationships specifically
    imports_query = """
    MATCH (source:File)-[r:IMPORTS]->(target:File)
    WHERE r.repo_url = $repo_url
    RETURN count(r) as count
    """
    
    imports_result = await db_manager.run_query(imports_query, {"repo_url": repo_url})
    imports_count = imports_result[0]['count'] if imports_result else 0
    logger.info(f"IMPORTS relationships: {imports_count}")
    
    # Count API endpoints
    api_query = """
    MATCH (api:ApiEndpoint {repo_url: $repo_url})
    RETURN count(api) as count
    """
    
    api_result = await db_manager.run_query(api_query, {"repo_url": repo_url})
    api_count = api_result[0]['count'] if api_result else 0
    logger.info(f"API endpoints: {api_count}")
    
    # Count data models
    models_query = """
    MATCH (dm:DataModel {repo_url: $repo_url})
    RETURN count(dm) as count
    """
    
    models_result = await db_manager.run_query(models_query, {"repo_url": repo_url})
    models_count = models_result[0]['count'] if models_result else 0
    logger.info(f"Data models: {models_count}")


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        logger.info("Usage: python run_enhanced_ingestion.py <repository_url> [branch] [force_reindex]")
        logger.info("  repository_url: URL of the repository to ingest")
        logger.info("  branch: Branch to ingest (default: main)")
        logger.info("  force_reindex: Whether to force reindexing (default: true)")
        return
    
    repo_url = sys.argv[1]
    branch = sys.argv[2] if len(sys.argv) > 2 else "main"
    force_reindex = sys.argv[3].lower() != "false" if len(sys.argv) > 3 else True
    
    await run_ingestion(repo_url, branch, force_reindex)


if __name__ == "__main__":
    asyncio.run(main()) 