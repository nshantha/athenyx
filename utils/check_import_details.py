#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nChecking IMPORTS relationships details...")
    result = await db_manager.run_query('''
    MATCH (source:File)-[r:IMPORTS]->(target:File)
    WHERE source.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN source.path as source_path, target.path as target_path, r.import_name as import_name
    ''')
    
    for record in result:
        print(f"- {record['source_path']} -> {record['target_path']} (import name: {record['import_name']})")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 