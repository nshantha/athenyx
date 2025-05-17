import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking Repository nodes...")
    result = await db_manager.run_query('MATCH (r:Repository) RETURN r.service_name as service_name')
    print(f"Found {len(result)} Repository nodes")
    for repo in result:
        print(f"- {repo}")
    
    print("Closing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 