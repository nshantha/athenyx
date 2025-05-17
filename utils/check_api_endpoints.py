#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nChecking API endpoints in the database:")
    result = await db_manager.run_query('''
    MATCH (api:ApiEndpoint)
    WHERE api.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN api.path as path, api.method as method, api.function as function, api.framework as framework, api.file_path as file_path
    ORDER BY api.path
    ''')
    
    print(f"Found {len(result)} API endpoints:")
    for record in result:
        print(f"- {record['method']} {record['path']} -> {record['function']} (in {record['file_path']}, framework: {record['framework']})")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 