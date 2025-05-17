#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nChecking inheritance relationships:")
    result = await db_manager.run_query('''
    MATCH (c1:Class)-[r:INHERITS_FROM]->(c2:Class)
    WHERE c1.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN c1.name as subclass, c2.name as superclass
    ''')
    
    print(f"Found {len(result)} inheritance relationships:")
    for record in result:
        print(f"- {record['subclass']} inherits from {record['superclass']}")
    
    print("\nChecking implementation relationships:")
    result = await db_manager.run_query('''
    MATCH (c1:Class)-[r:IMPLEMENTS]->(c2:Class)
    WHERE c1.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN c1.name as class_name, c2.name as interface_name
    ''')
    
    print(f"Found {len(result)} implementation relationships:")
    for record in result:
        print(f"- {record['class_name']} implements {record['interface_name']}")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 