import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking Repository nodes...")
    result = await db_manager.run_query('MATCH (r:Repository) RETURN r')
    print(f"Found {len(result)} Repository nodes")
    for repo in result:
        print(f"- {repo}")
    
    print("Checking Service nodes...")
    result = await db_manager.run_query('MATCH (s:Service) RETURN s')
    print(f"Found {len(result)} Service nodes")
    
    print("Checking File nodes...")
    result = await db_manager.run_query('MATCH (f:File) RETURN count(f) as count')
    print(f"Found {result[0]['count']} File nodes")
    
    print("Closing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 