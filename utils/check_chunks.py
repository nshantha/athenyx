import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking CodeChunk nodes...")
    result = await db_manager.run_query('MATCH (cc:CodeChunk) RETURN count(cc) as count')
    print(f"Found {result[0]['count']} CodeChunk nodes")
    
    print("Checking CONTAINS relationships...")
    result = await db_manager.run_query('MATCH (:File)-[r:CONTAINS]->(:CodeChunk) RETURN count(r) as count')
    print(f"Found {result[0]['count']} CONTAINS relationships")
    
    print("Checking IMPORTS relationships...")
    result = await db_manager.run_query('MATCH (:File)-[r:IMPORTS]->(:File) RETURN count(r) as count')
    print(f"Found {result[0]['count']} IMPORTS relationships")
    
    print("Checking API endpoints...")
    result = await db_manager.run_query('MATCH (api:ApiEndpoint) RETURN count(api) as count')
    print(f"Found {result[0]['count']} API endpoints")
    
    print("Checking sample code chunks...")
    result = await db_manager.run_query('MATCH (cc:CodeChunk) RETURN cc.content as content LIMIT 1')
    if result:
        print(f"Sample code chunk content: {result[0]['content'][:100]}...")
    
    print("Closing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 