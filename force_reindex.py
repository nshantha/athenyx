#!/usr/bin/env python
"""
Script to force reindex a repository
"""
import asyncio
import os
from app.db.neo4j_manager import db_manager
from ingestion.modules.knowledge_system import EnterpriseKnowledgeSystem

async def force_reindex_repository():
    """Force reindex the microservices_demo repository"""
    # Connect to the database
    await db_manager.connect()
    
    try:
        # Clear existing data for the repository
        repo_url = "https://github.com/GoogleCloudPlatform/microservices-demo"
        print(f"Clearing existing data for {repo_url}...")
        await db_manager.clear_repository_data(repo_url)
        print("Data cleared successfully")
        
        # Initialize the knowledge system
        print("Initializing knowledge system...")
        knowledge_system = EnterpriseKnowledgeSystem()
        
        # Create a repository configuration with force_reindex set to True
        repo_config = {
            "url": repo_url,
            "branch": "main",
            "service_name": "microservices_demo",
            "description": "Google Cloud Platform microservices demo",
            "force_reindex": True
        }
        
        # Run the ingestion process
        print(f"Starting ingestion for {repo_url}...")
        await knowledge_system.ingest_code_repository(repo_config)
        print("Ingestion completed")
        
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(force_reindex_repository()) 