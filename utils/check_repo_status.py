#!/usr/bin/env python
"""
Script to check repository status in the database
"""
import asyncio
from app.db.neo4j_manager import db_manager

async def check_repo_status():
    """Check repository status in the database"""
    await db_manager.connect()
    
    try:
        # Check repository status
        repo_query = """
        MATCH (r:Repository) 
        WHERE r.url CONTAINS 'microservices-demo' 
        RETURN r.url, r.last_indexed_commit
        """
        result = await db_manager.run_query(repo_query)
        print("Repository status:")
        for record in result:
            print(f"URL: {record.get('r.url')}")
            print(f"Last indexed commit: {record.get('r.last_indexed_commit')}")
        
        # Check if any nodes exist for the repository
        count_query = """
        MATCH (n) 
        WHERE n.repo_url CONTAINS 'microservices-demo' 
        RETURN count(n) as node_count
        """
        count_result = await db_manager.run_query(count_query)
        print(f"\nNodes for repository: {count_result[0]['node_count'] if count_result else 0}")
        
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_repo_status()) 