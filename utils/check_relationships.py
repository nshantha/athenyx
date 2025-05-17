#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nCounting all relationship types in the database:")
    result = await db_manager.run_query('''
    MATCH (a)-[r]->(b)
    WHERE a.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git' OR 
          b.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN type(r) as relationship_type, count(r) as count
    ORDER BY count DESC
    ''')
    
    print(f"Found {len(result)} relationship types:")
    for record in result:
        print(f"- {record['relationship_type']}: {record['count']} relationships")
    
    print("\nChecking node types in the database:")
    result = await db_manager.run_query('''
    MATCH (n)
    WHERE n.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN labels(n) as node_type, count(n) as count
    ORDER BY count DESC
    ''')
    
    print(f"Found {len(result)} node types:")
    for record in result:
        print(f"- {record['node_type']}: {record['count']} nodes")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 