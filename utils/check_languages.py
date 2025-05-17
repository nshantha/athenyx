#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking file languages...")
    result = await db_manager.run_query('''
    MATCH (f:File {repo_url: 'https://github.com/GoogleCloudPlatform/microservices-demo.git'})
    RETURN f.language as language, count(f) as count
    ORDER BY count DESC
    ''')
    
    for record in result:
        print(f"- {record['language']}: {record['count']} files")
    
    print("\nChecking IMPORTS relationships...")
    result = await db_manager.run_query('''
    MATCH (source:File)-[r:IMPORTS]->(target:File)
    WHERE source.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN source.language as source_language, count(r) as count
    ORDER BY count DESC
    ''')
    
    for record in result:
        print(f"- {record['source_language']} imports: {record['count']} relationships")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 