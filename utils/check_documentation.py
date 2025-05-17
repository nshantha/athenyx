#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nChecking documentation files in the database:")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    AND (f.is_documentation = true OR f.name CONTAINS "README" OR f.path CONTAINS "LICENSE" OR f.path ENDS WITH ".md")
    RETURN f.path as path, f.is_documentation as is_documentation
    ORDER BY f.path
    ''')
    
    print(f"Found {len(result)} documentation files:")
    for record in result:
        print(f"- {record['path']} (is_documentation: {record['is_documentation']})")
    
    print("\nChecking for README chunks:")
    result = await db_manager.run_query('''
    MATCH (f:File)-[:CONTAINS]->(c:CodeChunk)
    WHERE f.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    AND (f.name CONTAINS "README" OR f.is_documentation = true)
    RETURN f.path as path, count(c) as chunk_count
    ORDER BY chunk_count DESC
    ''')
    
    print(f"Found README files with {sum([r['chunk_count'] for r in result])} chunks:")
    for record in result:
        print(f"- {record['path']}: {record['chunk_count']} chunks")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 