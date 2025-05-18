import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    try:
        # Connect to Neo4j
        await db_manager.connect()
        
        # Check if repositories exist
        repos = await db_manager.run_query('MATCH (r:Repository) RETURN r')
        print(f"Found repositories: {repos}")
        
        # Get all repositories using the manager method
        all_repos = await db_manager.get_all_repositories()
        print(f"All repositories: {all_repos}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 