import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking Service nodes...")
    result = await db_manager.run_query('MATCH (s:Service) RETURN s LIMIT 5')
    print(f"Found {len(result)} Service nodes")
    
    print("Checking constraints...")
    result = await db_manager.run_query('SHOW CONSTRAINTS')
    print("Constraints:")
    for constraint in result:
        print(f"- {constraint}")
    
    print("Closing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 