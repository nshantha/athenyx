#!/usr/bin/env python
"""
Script to clear repository data from Neo4j
"""
import asyncio
from app.db.neo4j_manager import db_manager

async def clear_repository_data():
    """Clear data for the microservices_demo repository"""
    # Connect to the database
    await db_manager.connect()
    
    try:
        # Repository URL
        repo_url = "https://github.com/GoogleCloudPlatform/microservices-demo"
        print(f"Clearing data for repository: {repo_url}")
        
        # Clear the repository data
        await db_manager.clear_repository_data(repo_url)
        print("Repository data cleared successfully")
        
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(clear_repository_data()) 