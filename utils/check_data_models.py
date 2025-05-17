#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nChecking data models in the database:")
    result = await db_manager.run_query('''
    MATCH (dm:DataModel)
    WHERE dm.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN dm.name as name, dm.service_name as service_name, dm.file_path as file_path
    ORDER BY dm.name
    ''')
    
    print(f"Found {len(result)} data models:")
    for record in result:
        print(f"- {record['name']} (in {record['file_path']}, service: {record['service_name']})")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 