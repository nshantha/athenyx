#!/usr/bin/env python3
import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("\nChecking file extensions in the database:")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    RETURN f.file_type as extension, count(*) as count
    ORDER BY count DESC
    ''')
    
    print(f"Found {len(result)} file extensions:")
    for record in result:
        print(f"- {record['extension']}: {record['count']} files")
    
    print("\nChecking for documentation and configuration files:")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    AND (f.path CONTAINS "README" OR f.path CONTAINS ".git" OR f.path ENDS WITH ".md" 
         OR f.path ENDS WITH ".yaml" OR f.path ENDS WITH ".yml" OR f.path CONTAINS "LICENSE")
    RETURN f.path as path, f.name as name
    ORDER BY f.path
    ''')
    
    print(f"Found {len(result)} documentation and configuration files:")
    for record in result:
        print(f"- {record['path']}")
        
    print("\nLooking for README.md specifically:")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url = 'https://github.com/GoogleCloudPlatform/microservices-demo.git'
    AND f.name = "README.md"
    RETURN f.path as path
    ''')
    
    if result:
        print("README.md found in:")
        for record in result:
            print(f"- {record['path']}")
    else:
        print("README.md not found in the database")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 