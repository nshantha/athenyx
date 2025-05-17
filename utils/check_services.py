import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking Service nodes...")
    result = await db_manager.run_query('''
    MATCH (s:Service)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    RETURN s.name as name
    ''')
    
    print(f"Found {len(result)} services:")
    for record in result:
        print(f"- {record['name']}")
    
    print("\nChecking files per service...")
    result = await db_manager.run_query('''
    MATCH (f:File)-[:BELONGS_TO]->(r:Repository {service_name: 'microservices_demo'})
    WITH f.path as path, split(f.path, '/') as parts
    WITH path, parts[3] as service
    WHERE service IS NOT NULL
    RETURN service, count(path) as file_count
    ORDER BY file_count DESC
    ''')
    
    for record in result:
        print(f"- {record['service']}: {record['file_count']} files")
    
    print("\nChecking service directories in repository...")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url CONTAINS 'microservices_demo'
    AND f.path CONTAINS '/src/'
    WITH split(f.path, '/') as parts
    WITH parts[size(parts)-2] as service
    WHERE service IS NOT NULL
    RETURN DISTINCT service
    ORDER BY service
    ''')
    
    print(f"Found {len(result)} service directories:")
    for record in result:
        print(f"- {record['service']}")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 