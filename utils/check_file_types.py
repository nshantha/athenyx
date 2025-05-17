import asyncio
from app.db.neo4j_manager import db_manager

async def main():
    print("Connecting to Neo4j...")
    await db_manager.connect()
    
    print("Checking Repository nodes...")
    result = await db_manager.run_query('MATCH (r:Repository) RETURN r.name as name, r.url as url')
    for repo in result:
        print(f"Repository: {repo['name']} - {repo['url']}")
    
    print("\nChecking File nodes by file type...")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url CONTAINS 'microservices_demo'
    RETURN f.file_type as file_type, count(f) as count
    ORDER BY count DESC
    ''')
    
    for record in result:
        print(f"- {record['file_type']}: {record['count']} files")
    
    print("\nChecking total number of files...")
    result = await db_manager.run_query('''
    MATCH (f:File)
    WHERE f.repo_url CONTAINS 'microservices_demo'
    RETURN count(f) as count
    ''')
    print(f"Total files: {result[0]['count']}")
    
    print("\nChecking CodeChunk distribution...")
    result = await db_manager.run_query('''
    MATCH (cc:CodeChunk)<-[:CONTAINS]-(f:File)
    WHERE f.repo_url CONTAINS 'microservices_demo'
    RETURN f.file_type as file_type, count(cc) as count
    ORDER BY count DESC
    ''')
    
    for record in result:
        print(f"- {record['file_type']}: {record['count']} code chunks")
    
    print("\nChecking API endpoints...")
    result = await db_manager.run_query('''
    MATCH (api:ApiEndpoint)
    RETURN api.path as path, api.method as method
    ''')
    
    for record in result:
        print(f"- {record['method']} {record['path']}")
    
    print("\nClosing connection...")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 